#!/usr/bin/env python3
"""Roteamento, contexto, gates e telemetria locais da Valiant Group."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate_cache


RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
GATE_ORDER = {"none": 0, "relevant": 2, "full": 3}
SAFE_ID = re.compile(r"[^a-zA-Z0-9._-]+")


def fail(message: str) -> "NoReturn":
    print(f"[execution-control] {message}", file=sys.stderr)
    raise SystemExit(2)


def load_policy(root: Path) -> dict[str, Any]:
    path = root / ".codex" / "execution-policy.json"
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"política inválida em {path}: {exc}")
    if policy.get("schema_version") != 1:
        fail("schema de política incompatível; esperado 1")
    if "fast" in policy["gates"]["levels"] or any(
        profile["gate_level"] not in GATE_ORDER for profile in policy["routing"]["profiles"].values()
    ):
        fail("política legada: migre o nível fast antes de executar")
    return policy


def normalize_task_id(value: str) -> str:
    normalized = SAFE_ID.sub("-", value.strip()).strip("-.").lower()
    if not normalized or normalized in {".", ".."}:
        fail("task-id inválido")
    return normalized[:80]


def git_output(root: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def discover_changed_files(root: Path) -> list[str]:
    output = git_output(root, ["status", "--porcelain=v1", "--untracked-files=all"])
    files: list[str] = []
    for line in output.splitlines():
        candidate = line[3:]
        if " -> " in candidate:
            candidate = candidate.split(" -> ", 1)[1]
        candidate = candidate.strip().strip('"').replace("\\", "/")
        if candidate and candidate not in files:
            files.append(candidate)
    return sorted(files)


def normalize_files(files: list[str]) -> list[str]:
    normalized = []
    for value in files:
        candidate = value.strip().replace("\\", "/")
        path = Path(candidate)
        if not candidate or path.is_absolute() or ".." in path.parts:
            fail(f"caminho de escopo inseguro: {value}")
        if candidate not in normalized:
            normalized.append(candidate)
    if len(normalized) > 200:
        fail("escopo excede 200 caminhos; divida a tarefa")
    return sorted(normalized)


def path_matches(path: str, pattern: str) -> bool:
    normalized = path.replace("\\", "/")
    if fnmatch.fnmatchcase(normalized, pattern):
        return True
    if pattern.startswith("**/"):
        return fnmatch.fnmatchcase(normalized, pattern[3:])
    return False


def classify(policy: dict[str, Any], files: list[str], signals: list[str]) -> dict[str, Any]:
    routing = policy["routing"]
    observed_signals = {signal.strip().lower() for signal in signals if signal.strip()}
    risk = "low"
    reasons: list[str] = []

    for rule in routing["path_rules"]:
        matched_paths = sorted(
            path for path in files if any(path_matches(path, pattern) for pattern in rule["patterns"])
        )
        level = rule["risk"]
        if matched_paths and RISK_ORDER[level] > RISK_ORDER[risk]:
            risk = level
        if matched_paths:
            observed_signals.update(rule.get("signals", []))
            reasons.append(f"paths:{level}:{','.join(matched_paths[:5])}")

    normalized_signals = sorted(observed_signals)

    signal_sets = (
        ("critical", set(routing["critical_signals"])),
        ("high", set(routing["high_signals"])),
        ("medium", set(routing["medium_signals"])),
    )
    for level, known in signal_sets:
        matched = sorted(set(normalized_signals) & known)
        if matched and RISK_ORDER[level] > RISK_ORDER[risk]:
            risk = level
        if matched:
            reasons.append(f"signals:{','.join(matched)}")

    profile = dict(routing["profiles"][risk])
    roles = list(profile["roles"])
    for role, role_signals in profile.pop("conditional_roles", {}).items():
        if observed_signals.intersection(role_signals) and role not in roles:
            roles.insert(0, role)
    profile["roles"] = roles
    if "model_overrides" in profile:
        profile["model_overrides"] = {
            role: model for role, model in profile["model_overrides"].items() if role in roles
        }
    # Overrides belong to this invocation, never to the reusable policy.
    for escalation in routing.get("model_escalations", []):
        if observed_signals.intersection(escalation["signals"]):
            for role in escalation["roles"]:
                if role in roles:
                    profile.setdefault("model_overrides", {})[role] = escalation["model"]
                    reasons.append(f"model:{role}:{escalation['model']}")
    return {
        "risk": risk,
        "reasons": reasons or ["baseline:low"],
        "signals": normalized_signals,
        "files": sorted(dict.fromkeys(files)),
        "profile": profile,
    }


def is_docs_only(files: list[str], extensions: list[str]) -> bool:
    return bool(files) and all(Path(path).suffix.lower() in extensions for path in files)


def select_gates(policy: dict[str, Any], route: dict[str, Any], level: str | None = None) -> list[dict[str, str]]:
    gates = policy["gates"]
    baseline_level = route["profile"]["gate_level"]
    chosen_level = level or baseline_level
    if route["profile"].get("read_only"):
        if chosen_level != "none":
            fail("rota read_only não permite gates executáveis")
        return []
    if chosen_level not in GATE_ORDER or baseline_level not in GATE_ORDER:
        fail("nível de gate inválido ou proibido")
    if GATE_ORDER[chosen_level] < GATE_ORDER[baseline_level]:
        fail(f"gate {chosen_level} não pode reduzir a baseline {baseline_level}")
    if chosen_level == "none":
        return []
    keys = gates["levels"].get(chosen_level)
    if keys is None:
        fail(f"nível de gate desconhecido: {chosen_level}")
    selected: list[dict[str, str]] = []
    for key, spec in gates.get("evidence_gates", {}).items():
        argv = spec.get("argv")
        cwd = Path(spec.get("cwd", "."))
        if not isinstance(argv, list) or not argv or not all(isinstance(arg, str) and arg for arg in argv) or cwd.is_absolute() or cwd.drive or ".." in cwd.parts:
            fail("gate estruturado inválido")
        patterns = spec.get("impact_patterns", [])
        if route["files"] and patterns and not any(path_matches(path, pattern) for path in route["files"] for pattern in patterns):
            continue
        selected.append({**spec, "key": key, "command": " ".join(argv)})
    if is_docs_only(route["files"], gates["docs_only_extensions"]):
        return selected
    seen: set[str] = set()
    for key in keys:
        command = str(gates["commands"].get(key, "TODO")).strip()
        if not command or command == "TODO" or command in seen:
            continue
        seen.add(command)
        selected.append({"key": key, "command": command})
    return selected


def scoped_state_hash(root: Path, files: list[str]) -> str:
    head = git_output(root, ["rev-parse", "HEAD"]) or "NO_HEAD"
    status = git_output(root, ["status", "--porcelain=v1", "--untracked-files=all"])
    relevant = []
    file_set = set(files)
    for line in status.splitlines():
        candidate = line[3:]
        if " -> " in candidate:
            candidate = candidate.split(" -> ", 1)[1]
        candidate = candidate.strip().strip('"').replace("\\", "/")
        if not file_set or candidate in file_set:
            relevant.append(line[:2] + " " + candidate)
    file_state = {}
    for relative in sorted(files):
        path = root / relative
        try:
            stat = path.lstat()
            file_state[relative] = f"{stat.st_mode}:{stat.st_size}:{stat.st_mtime_ns}"
        except OSError:
            file_state[relative] = "MISSING_OR_UNREADABLE"
    payload = json.dumps(
        {
            "head": head,
            "files": sorted(files),
            "status": sorted(relevant),
            "file_state": file_state,
        },
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def task_fingerprint(goal: str, acceptance: list[str], route: dict[str, Any], state_hash: str) -> str:
    payload = json.dumps(
        {
            "goal": goal.strip(),
            "acceptance": acceptance,
            "route": route,
            "state_hash": state_hash,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def render_context(task_id: str, goal: str, acceptance: list[str], route: dict[str, Any], gates: list[dict[str, str]], state_hash: str, fingerprint: str) -> str:
    lines = [
        "# Contexto compacto da tarefa",
        "",
        f"- Tarefa: `{task_id}`",
        f"- Objetivo: {goal.strip()}",
        f"- Risco: `{route['risk']}`",
        f"- Estado: `{state_hash}`",
        f"- Fingerprint: `{fingerprint}`",
        f"- Papéis: `{', '.join(route['profile']['roles'])}`",
        f"- Etapas por scripts/orquestrador: `{', '.join(route['profile'].get('operational_stages', []))}`",
        f"- Ciclos máximos: `{route['profile']['max_cycles']}`",
    ]
    overrides = route["profile"].get("model_overrides", {})
    if overrides:
        lines.append("- Promoções: " + "; ".join(f"`{role}={model}`" for role, model in overrides.items()))
    lines.extend(("", "## Critérios de aceite"))
    lines.extend(f"- {item}" for item in acceptance) if acceptance else lines.append("- Não informados; não presuma critérios materiais.")
    lines.extend(("", "## Escopo observado"))
    lines.extend(f"- `{path}`" for path in route["files"]) if route["files"] else lines.append("- Nenhum caminho detectado; confirme o escopo antes de editar.")
    lines.extend(("", "## Sinais e justificativa"))
    lines.extend(f"- `{reason}`" for reason in route["reasons"])
    lines.extend(("", "## Gates selecionados"))
    lines.extend(f"- `{gate['key']}`: `{gate['command']}`" for gate in gates) if gates else lines.append("- Somente revisão e hooks; nenhum comando adicional selecionado.")
    lines.extend(("", "## Contrato", "", "Use este arquivo como handoff. Refaça a cápsula somente se objetivo, aceite, HEAD ou estado dos caminhos mudar. Não copie histórico, logs ou prompts para cá.", ""))
    return "\n".join(lines)


def prepare_context(root: Path, policy: dict[str, Any], args: argparse.Namespace) -> tuple[Path, bool]:
    task_id = normalize_task_id(args.task_id)
    goal = args.goal.strip()
    acceptance = [item.strip() for item in (args.acceptance or []) if item.strip()]
    if not goal or len(goal) > 500:
        fail("goal deve conter entre 1 e 500 caracteres")
    if len(acceptance) > 20 or any(len(item) > 300 for item in acceptance):
        fail("aceite excede 20 itens ou 300 caracteres por item")
    files = normalize_files(args.file or discover_changed_files(root))
    route = classify(policy, files, args.signal or [])
    gates = select_gates(policy, route)
    state_hash = scoped_state_hash(root, route["files"])
    fingerprint = task_fingerprint(goal, acceptance, route, state_hash)
    task_dir = root / ".codex" / "sessions" / task_id
    context_file = task_dir / "TASK_CONTEXT.md"
    state_file = task_dir / "route.json"
    previous = None
    if state_file.is_file():
        try:
            previous = json.loads(state_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            previous = None
    if previous and previous.get("fingerprint") == fingerprint and context_file.is_file():
        return context_file, False
    task_dir.mkdir(parents=True, exist_ok=True)
    context_file.write_text(
        render_context(task_id, goal, acceptance, route, gates, state_hash, fingerprint),
        encoding="utf-8",
    )
    state_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "task_id": task_id,
                "fingerprint": fingerprint,
                "state_hash": state_hash,
                "route": route,
                "gates": gates,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    return context_file, True


def gate_fingerprint(root: Path, gate: dict[str, Any], files=None) -> str | None:
    return gate_cache.fingerprint(root, gate)


def evidence_path(root: Path, task_id: str, key: str) -> Path:
    directory = root / ".codex/sessions" / normalize_task_id(task_id) / "gates"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / (normalize_task_id(key) + ".json")


def run_gates(root: Path, policy: dict[str, Any], selected: list[dict[str, str]], task_id: str | None = None) -> int:
    tail_lines = int(policy["gates"].get("failure_tail_lines", 40))
    timeout = int(policy["gates"].get("timeout_seconds", 1200))
    for gate in selected:
        fingerprint = gate_fingerprint(root, gate) if "argv" in gate else None
        evidence = None
        if task_id and "argv" in gate:
            evidence = evidence_path(root, task_id, gate["key"])
            try:
                cached = json.loads(evidence.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                cached = {}
            if fingerprint and isinstance(cached, dict) and cached.get("schema_version") == 2 and cached.get("outcome") == "success" and cached.get("fingerprint") == fingerprint:
                print(f"[REUSE] {gate['key']}")
                continue
        started = time.monotonic()
        try:
            with gate_cache.execution_root(root, gate, fingerprint) as execution_root:
                structured = "argv" in gate
                result = subprocess.run(
                    gate_cache.command(gate) if structured else gate["command"],
                    cwd=execution_root / gate.get("cwd", "."),
                    shell=not structured,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=gate_cache.execution_environment(gate) if structured else None,
                )
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            print(f"[FAIL] {gate['key']}: {type(exc).__name__}")
            return 124
        duration = time.monotonic() - started
        if fingerprint and gate_fingerprint(root, gate) != fingerprint:
            fingerprint = None
        if evidence:
            evidence.write_text(json.dumps({"schema_version": 2, "fingerprint": fingerprint,
                                          "outcome": "success" if result.returncode == 0 else "failure"}) + "\n", encoding="utf-8")
        if result.returncode == 0:
            print(f"[PASS] {gate['key']} ({duration:.1f}s)")
            continue
        combined = "\n".join(part for part in (result.stdout, result.stderr) if part)
        tail = combined.splitlines()[-tail_lines:]
        print(f"[FAIL] {gate['key']} exit={result.returncode} ({duration:.1f}s)")
        if tail:
            print("\n".join(tail))
        return result.returncode
    return 0


def telemetry_path(root: Path, policy: dict[str, Any]) -> Path:
    relative = Path(policy["telemetry"]["path"])
    if relative.is_absolute() or ".." in relative.parts:
        fail("caminho de telemetria inseguro")
    return root / relative


def record_metric(root: Path, policy: dict[str, Any], args: argparse.Namespace) -> Path:
    path = telemetry_path(root, policy)
    path.parent.mkdir(parents=True, exist_ok=True)
    if args.cycles < 0 or args.tool_calls < 0 or args.duration_seconds < 0:
        fail("métricas numéricas não podem ser negativas")
    record = {
        "schema_version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task_id": normalize_task_id(args.task_id),
        "stage": args.stage,
        "outcome": args.outcome,
        "model": args.model,
        "effort": args.effort,
        "cycles": args.cycles,
        "tool_calls": args.tool_calls,
        "duration_seconds": args.duration_seconds,
        "promoted": args.promoted,
    }
    existing: list[str] = []
    if path.is_file():
        existing = path.read_text(encoding="utf-8").splitlines()
    existing.append(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
    retention = int(policy["telemetry"].get("retention_records", 500))
    path.write_text("\n".join(existing[-retention:]) + "\n", encoding="utf-8")
    return path


def summarize_metrics(root: Path, policy: dict[str, Any], limit: int) -> dict[str, Any]:
    path = telemetry_path(root, policy)
    if not path.is_file():
        return {"records": 0, "successful": 0, "first_pass_success_rate": None, "promotion_rate": None}
    records = []
    for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    successful = [record for record in records if record.get("outcome") == "success"]
    first_pass = [record for record in successful if int(record.get("cycles") or 0) <= 1]
    promoted = [record for record in records if record.get("promoted") is True]
    return {
        "records": len(records),
        "successful": len(successful),
        "first_pass_success_rate": round(len(first_pass) / len(successful), 4) if successful else None,
        "promotion_rate": round(len(promoted) / len(records), 4) if records else None,
        "tool_calls": sum(int(record.get("tool_calls") or 0) for record in records),
        "duration_seconds": round(sum(float(record.get("duration_seconds") or 0) for record in records), 2),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Controle local de execução Valiant")
    parser.add_argument("--root", default=".", help="Raiz do repositório")
    subparsers = parser.add_subparsers(dest="command", required=True)

    route = subparsers.add_parser("route", help="Classifica risco, papéis e gates")
    route.add_argument("--file", action="append")
    route.add_argument("--signal", action="append")

    prepare = subparsers.add_parser("prepare", help="Cria ou reutiliza a cápsula da tarefa")
    prepare.add_argument("--task-id", required=True)
    prepare.add_argument("--goal", required=True)
    prepare.add_argument("--acceptance", action="append")
    prepare.add_argument("--file", action="append")
    prepare.add_argument("--signal", action="append")

    gates = subparsers.add_parser("gates", help="Seleciona ou executa gates proporcionais")
    gates.add_argument("--file", action="append")
    gates.add_argument("--signal", action="append")
    gates.add_argument("--level", choices=("relevant", "full"))
    gates.add_argument("--task-id", help="Reutilização local por tarefa, somente gates elegíveis")
    gates.add_argument("--run", action="store_true")

    record = subparsers.add_parser("record", help="Registra métrica sanitizada")
    record.add_argument("--task-id", required=True)
    record.add_argument("--stage", required=True)
    record.add_argument("--outcome", choices=("success", "corrected", "blocked"), required=True)
    record.add_argument("--model", required=True)
    record.add_argument("--effort", choices=("low", "medium", "high", "xhigh"), required=True)
    record.add_argument("--cycles", type=int, default=1)
    record.add_argument("--tool-calls", type=int, default=0)
    record.add_argument("--duration-seconds", type=float, default=0)
    record.add_argument("--promoted", action="store_true")

    summary = subparsers.add_parser("summary", help="Resume eficiência sem conteúdo da tarefa")
    summary.add_argument("--limit", type=int, default=100)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.root).resolve()
    policy = load_policy(root)
    if args.command == "prepare":
        path, changed = prepare_context(root, policy, args)
        print(json.dumps({"path": path.relative_to(root).as_posix(), "changed": changed}))
        return 0
    if args.command in {"route", "gates"}:
        files = normalize_files(args.file or discover_changed_files(root))
        route = classify(policy, files, args.signal or [])
        selected = select_gates(policy, route, getattr(args, "level", None))
        if args.command == "gates" and args.run:
            if route["profile"].get("read_only"):
                fail("rota read_only não permite --run")
            return run_gates(root, policy, selected, args.task_id)
        print(json.dumps({"route": route, "gates": selected}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "record":
        path = record_metric(root, policy, args)
        print(path.relative_to(root).as_posix())
        return 0
    if args.command == "summary":
        print(json.dumps(summarize_metrics(root, policy, args.limit), indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
