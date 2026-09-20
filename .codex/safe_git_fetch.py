#!/usr/bin/env python3
"""Leitura e fetch Git determinísticos para uso opcional em roots governados."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit


class PolicyError(ValueError):
    pass


def sanitized_environment(source: dict[str, str]) -> dict[str, str]:
    allowed = ("PATH", "HOME", "USERPROFILE", "SystemRoot", "COMSPEC", "LANG", "LC_ALL", "CI")
    clean = {key: source[key] for key in allowed if source.get(key)}
    clean.update({"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"})
    return clean


def trusted_git(which: str | None = None) -> Path:
    raw = which or shutil.which("git")
    if not raw:
        raise PolicyError("Git não encontrado.")
    path = Path(raw)
    resolved = path.resolve()
    approved = {
        Path(candidate).resolve()
        for candidate in (
            "/usr/bin/git", "/usr/local/bin/git", "/opt/homebrew/bin/git",
            "C:/Program Files/Git/cmd/git.exe", "C:/Program Files/Git/bin/git.exe",
        )
        if Path(candidate).exists()
    }
    if resolved not in approved or not resolved.is_file():
        raise PolicyError("Executável Git fora dos paths confiáveis.")
    return resolved


def run(git: Path, root: Path, args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(git), *args], cwd=root, env=env, check=False, capture_output=True,
        text=True, timeout=120,
    )


def output(git: Path, root: Path, args: list[str], env: dict[str, str]) -> str:
    result = run(git, root, args, env)
    if result.returncode != 0:
        raise PolicyError(f"Git falhou em {args[0]}.")
    return result.stdout.strip()


def exact_root(git: Path, cwd: Path, env: dict[str, str]) -> Path:
    root = Path(output(git, cwd, ["rev-parse", "--show-toplevel"], env)).resolve()
    if root != cwd.resolve():
        raise PolicyError("Execute na raiz exata do repositório.")
    return root


def validate_origin(git: Path, root: Path, env: dict[str, str]) -> str:
    urls = [line for line in output(git, root, ["config", "--local", "--get-all", "remote.origin.url"], env).splitlines() if line]
    if len(urls) != 1:
        raise PolicyError("Exatamente uma URL de origin é obrigatória.")
    parsed = urlsplit(urls[0])
    if parsed.scheme != "https" or parsed.hostname != "github.com" or parsed.username or parsed.password:
        raise PolicyError("Origin deve usar HTTPS sem credenciais em github.com.")
    push_urls = run(git, root, ["config", "--local", "--get-all", "remote.origin.pushurl"], env)
    if push_urls.returncode == 0 and push_urls.stdout.strip():
        raise PolicyError("pushurl separado não é permitido.")
    config = output(git, root, ["config", "--local", "--list"], env)
    if any(line.lower().startswith("url.") and ".insteadof=" in line.lower() for line in config.splitlines()):
        raise PolicyError("Reescrita local de URL não é permitida.")
    return urls[0]


def self_test() -> None:
    assert sanitized_environment({"PATH": "/bin", "TOKEN": "secret"}) == {
        "PATH": "/bin", "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"
    }
    assert urlsplit("https://github.com/ValiantGroup/repo").hostname == "github.com"


def main(argv: list[str]) -> int:
    mode = argv[0] if argv else "fetch"
    if len(argv) > 1 or mode not in {"fetch", "--status", "--baseline", "--diff", "self-test"}:
        print("Uso: safe_git_fetch.py [fetch|--status|--baseline|--diff|self-test]", file=sys.stderr)
        return 2
    if mode == "self-test":
        self_test()
        return 0
    try:
        env = sanitized_environment(dict(os.environ))
        git = trusted_git()
        root = exact_root(git, Path.cwd(), env)
        validate_origin(git, root, env)
        if mode == "fetch":
            result = run(git, root, ["fetch", "--prune", "--no-tags", "origin", "+refs/heads/*:refs/remotes/origin/*"], env)
            if result.returncode != 0:
                raise PolicyError("Fetch autorizado falhou.")
        elif mode in {"--status", "--baseline"}:
            print(output(git, root, ["status", "--short", "--branch", "--untracked-files=all"], env))
            if mode == "--baseline" and run(git, root, ["rev-parse", "--verify", "HEAD"], env).returncode != 0:
                print("[VALIANT BASELINE] Root sem HEAD; todos os untracked do escopo integram a baseline.")
        else:
            print(output(git, root, ["diff", "--no-ext-diff", "--no-textconv", "--"], env))
        return 0
    except (OSError, subprocess.TimeoutExpired, PolicyError) as exc:
        print(f"[VALIANT SAFE GIT] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
