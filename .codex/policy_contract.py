"""Contrato estático de execução; somente JSON/TOML locais e biblioteca padrão."""
from pathlib import Path
import json
import sys
import tomllib


def validate(root: Path) -> list[str]:
    errors = []
    policy = json.loads((root / ".codex/execution-policy.json").read_text(encoding="utf-8"))
    config = tomllib.loads((root / ".codex/config.toml").read_text(encoding="utf-8"))
    if config.get("features", {}).get("fast_mode") is not False:
        errors.append("features.fast_mode deve ser false")
    if config.get("service_tier") != "default":
        errors.append("service_tier deve ser default")

    def check_overrides(value):
        if isinstance(value, dict):
            if value.get("fast_mode") is True or value.get("service_tier") in ("fast", "priority", "ultrafast"):
                errors.append("override Fast proibido")
            for child in value.values():
                check_overrides(child)
        elif isinstance(value, list):
            for child in value:
                check_overrides(child)

    check_overrides(config)
    if policy.get("schema_version") != 1:
        errors.append("schema de execução incompatível")
    profiles = policy["routing"]["profiles"]
    for risk in ("low", "medium", "high"):
        profile = profiles[risk]
        roles = profile["roles"]
        if "worker" not in roles or {"verifier", "delivery-manager"}.intersection(roles):
            errors.append("separe participantes e etapas operacionais")
        if set(profile.get("operational_stages", [])) != {"verifier", "delivery-manager"}:
            errors.append("etapas operacionais obrigatórias ausentes")
        if risk in ("medium", "high") and "reviewer" not in roles:
            errors.append("revisão independente ausente")
        if risk == "high" and "security-reviewer" not in roles:
            errors.append("revisão de segurança ausente")
        if profile["gate_level"] != ("full" if risk == "high" else "relevant"):
            errors.append("baseline de gates incompatível")
    critical = profiles["critical"]
    if critical.get("read_only") is not True or critical.get("gate_level") != "none":
        errors.append("barreira crítica read-only ausente")
    if "fast" in policy["gates"]["levels"]:
        errors.append("nível legado fast deve ser migrado")
    return errors


def main():
    try:
        errors = validate(Path(__file__).resolve().parents[1])
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        print("[FAIL] contrato de governança inválido ou incompleto")
        return 2
    if errors:
        print("[FAIL] " + "; ".join(sorted(set(errors))))
        return 1
    print("[PASS] contrato estático de governança")
    return 0


if __name__ == "__main__":
    sys.exit(main())
