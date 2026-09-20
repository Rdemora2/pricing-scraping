#!/usr/bin/env python3
"""Gate local fail-closed para ferramentas mutáveis do Claude Code."""

import json
import re
import sys


SECRET_PATH = re.compile(
    r"(^|[/\\])(?:\.env(?:\.[^/\\]+)?|[^/\\]+\.(?:pem|key))$", re.IGNORECASE
)
BLOCKED_COMMANDS = (
    (r"\bgit\s+(?:rebase|reset|clean)\b", "reescrita ou limpeza destrutiva do Git"),
    (r"\bgit\s+(?:commit\b[^\n;&|]*\s--(?:amend|no-verify)\b|push\b[^\n;&|]*\s--(?:force(?:-with-lease)?|delete)\b)", "bypass ou reescrita de entrega Git"),
    (r"\bgit\s+(?:checkout\s+--|restore\b|switch\b[^\n;&|]*\s-[^\s]*[Cc]|branch\b[^\n;&|]*\s-D\b)", "descarte destrutivo de alterações Git"),
    (r"\b(?:sudo\b|rm\s+(?:-[^\s]*r[^\s]*f|-[^\s]*f[^\s]*r)\b)", "elevação ou remoção recursiva destrutiva"),
    (r"\b(?:kubectl|helm)\b[^\n;&|]*(?:\bapply\b|\bdelete\b|\bupgrade\b)", "mutação de infraestrutura"),
    (r"\bterraform\s+(?:apply|destroy)\b", "mutação de infraestrutura"),
    (r"\b(?:vercel|netlify)\s+(?:deploy|--prod)\b|\bflyctl\s+deploy\b", "deploy externo"),
    (r"\b(?:codex-security|security[_ -]?plugin)\b", "plugin Codex Security proibido"),
)
ASK_COMMANDS = (
    (r"\b(?:npm|pnpm|yarn|bun)\s+(?:add|install)\b", "instalação de dependência"),
    (r"\b(?:pip|pip3|uv)\s+install\b", "instalação de dependência"),
    (r"\b(?:brew|apt(?:-get)?|dnf|yum|choco|winget)\s+install\b", "instalação de ferramenta"),
)


def decision(value: str, reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": value,
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=False))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        tool_name = payload["tool_name"]
        tool_input = payload["tool_input"]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Valiant policy: entrada inválida ({exc}).", file=sys.stderr)
        return 2

    if not isinstance(tool_name, str) or not isinstance(tool_input, dict):
        print("Valiant policy: contrato de entrada inválido.", file=sys.stderr)
        return 2

    if tool_name in {"Read", "Edit", "Write"}:
        path = tool_input.get("file_path") or tool_input.get("path")
        if not isinstance(path, str):
            print("Valiant policy: caminho ausente; operação bloqueada.", file=sys.stderr)
            return 2
        if SECRET_PATH.search(path.replace("\\", "/")):
            decision("deny", "Arquivos de segredos e chaves não podem ser acessados.")
        return 0

    if tool_name == "Bash":
        command = tool_input.get("command")
        if not isinstance(command, str):
            print("Valiant policy: comando ausente; operação bloqueada.", file=sys.stderr)
            return 2
        normalized = command.strip().lower()
        for pattern, reason in BLOCKED_COMMANDS:
            if re.search(pattern, normalized, flags=re.IGNORECASE):
                decision("deny", f"Bloqueado pela política Valiant: {reason}.")
                return 0
        for pattern, reason in ASK_COMMANDS:
            if re.search(pattern, normalized, flags=re.IGNORECASE):
                decision("ask", f"Aprovação necessária para {reason}.")
                return 0
        return 0

    print(f"Valiant policy: ferramenta inesperada no matcher ({tool_name}).", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
