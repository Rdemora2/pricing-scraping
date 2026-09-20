#!/usr/bin/env python3
"""Valida mensagens convencionais e impede caminhos sensíveis em commits."""

import argparse
import re
import subprocess
import sys
from pathlib import Path


HEADER_PATTERN = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(\([a-z0-9][a-z0-9._/-]*\))?(!)?: \S.{0,99}$"
)
SAFE_ENV_EXAMPLES = {".env.example", ".env.sample", ".env.template"}
PROTECTED_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "credentials.json",
    "id_ed25519",
    "id_rsa",
    "service-account.json",
}
PROTECTED_SUFFIXES = (".key", ".p12", ".pem", ".pfx")


def validate_header(header: str) -> list[str]:
    header = header.strip()
    if not HEADER_PATTERN.fullmatch(header):
        return [
            "Mensagem fora do Conventional Commits.",
            "Use: tipo(escopo)!: descrição",
            "Tipos: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert.",
        ]
    return []


def validate_message(message_file: Path) -> list[str]:
    try:
        header = message_file.read_text(encoding="utf-8").splitlines()[0].strip()
    except (OSError, UnicodeDecodeError, IndexError):
        return ["Mensagem de commit ausente ou ilegível."]

    return validate_header(header)


def staged_files() -> set[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("Não foi possível consultar os arquivos staged.")
    return {line for line in result.stdout.splitlines() if line.strip()}


def is_protected_path(path: str) -> bool:
    normalized = path.replace("\\", "/").strip("/").lower()
    name = normalized.rsplit("/", 1)[-1]
    if name in PROTECTED_FILENAMES:
        return True
    if name.startswith(".env.") and name not in SAFE_ENV_EXAMPLES:
        return True
    if name.endswith(PROTECTED_SUFFIXES):
        return True
    return normalized == ".codex/sessions" or normalized.startswith(".codex/sessions/")


def validate_paths(paths: set[str]) -> list[str]:
    protected = sorted(path for path in paths if is_protected_path(path))
    if not protected:
        return []
    preview = ", ".join(protected[:5])
    if len(protected) > 5:
        preview += f" e mais {len(protected) - 5}"
    return [
        f"Caminho sensível não pode ser incluído no commit: {preview}.",
        "Remova o conteúdo sensível do staged; exclusões desses caminhos continuam permitidas.",
    ]


def validate_staged() -> list[str]:
    try:
        paths = staged_files()
    except RuntimeError as exc:
        return [str(exc)]
    return validate_paths(paths)


def git_output(arguments: list[str]) -> str:
    result = subprocess.run(
        ["git", *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Falha ao executar git {' '.join(arguments)}.")
    return result.stdout


def validate_range(commit_range: str) -> list[str]:
    errors = []
    try:
        commits = [line for line in git_output(["rev-list", "--reverse", commit_range]).splitlines() if line]
        for commit in commits:
            short_hash = commit[:8]
            header = git_output(["show", "-s", "--format=%s", commit]).strip()
            for error in validate_header(header):
                errors.append(f"{short_hash}: {error}")

            changed = {
                line
                for line in git_output(
                    ["diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "--diff-filter=ACMR", commit]
                ).splitlines()
                if line.strip()
            }
            for error in validate_paths(changed):
                errors.append(f"{short_hash}: {error}")
    except RuntimeError as exc:
        return [str(exc)]
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--message-file", type=Path)
    mode.add_argument("--staged", action="store_true")
    mode.add_argument("--range", dest="commit_range")
    args = parser.parse_args()

    if args.message_file:
        errors = validate_message(args.message_file)
    elif args.commit_range:
        errors = validate_range(args.commit_range)
    else:
        errors = validate_staged()
    if errors:
        print("[VALIANT COMMIT POLICY] Commit bloqueado:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
