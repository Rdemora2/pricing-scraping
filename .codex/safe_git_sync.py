#!/usr/bin/env python3
"""Sincroniza a default branch local por fast-forward, sem comandos arbitrários."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Mapping, Sequence


class PolicyError(ValueError):
    """A operação solicitada não satisfaz o contrato de sincronização."""


def run_git(
    git: str,
    repository: Path,
    arguments: Sequence[str],
    env: Mapping[str, str],
    *,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [git, "-C", str(repository), *arguments],
            check=False,
            capture_output=True,
            cwd=repository,
            env=dict(env),
            shell=False,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PolicyError(f"Git indisponível ou excedeu timeout: {type(exc).__name__}") from exc


def require_success(result: subprocess.CompletedProcess[str], operation: str) -> str:
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        suffix = f": {detail[-1]}" if detail else ""
        raise PolicyError(f"{operation} falhou{suffix}")
    return result.stdout.strip()


def resolve_repository(cwd: Path, git: str, env: Mapping[str, str]) -> Path:
    top = require_success(
        run_git(git, cwd, ["rev-parse", "--show-toplevel"], env),
        "Descoberta do Git root",
    )
    repository = Path(top).resolve(strict=True)
    if cwd.resolve(strict=True) != repository:
        raise PolicyError("Execute safe_git_sync.py na raiz exata do repositório.")
    return repository


def detect_default_branch(repository: Path, git: str, env: Mapping[str, str]) -> str:
    symbolic = run_git(
        git,
        repository,
        ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"],
        env,
    )
    if symbolic.returncode == 0:
        value = symbolic.stdout.strip()
        if value.startswith("origin/") and len(value) > len("origin/"):
            return value.removeprefix("origin/")

    candidates = []
    for branch in ("main", "master"):
        local = run_git(git, repository, ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], env)
        remote = run_git(
            git,
            repository,
            ["show-ref", "--verify", "--quiet", f"refs/remotes/origin/{branch}"],
            env,
        )
        if local.returncode == 0 and remote.returncode == 0:
            candidates.append(branch)
    if len(candidates) != 1:
        raise PolicyError("Default branch ambígua ou ausente; configure origin/HEAD.")
    return candidates[0]


def require_clean(repository: Path, git: str, env: Mapping[str, str]) -> None:
    status = require_success(
        run_git(git, repository, ["status", "--porcelain=v1", "--untracked-files=all"], env),
        "Leitura do worktree",
    )
    if status:
        raise PolicyError("A sincronização exige worktree e index limpos.")


def sync_main(cwd: Path, *, git: str, source_env: Mapping[str, str]) -> None:
    env = dict(source_env)
    env.update({"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"})
    repository = resolve_repository(cwd, git, env)
    require_clean(repository, git, env)

    current = require_success(
        run_git(git, repository, ["symbolic-ref", "--quiet", "--short", "HEAD"], env),
        "Leitura da branch atual",
    )
    if not current:
        raise PolicyError("Detached HEAD não é permitido.")
    origins = require_success(
        run_git(git, repository, ["config", "--local", "--get-all", "remote.origin.url"], env),
        "Leitura de origin",
    ).splitlines()
    if len(origins) != 1 or not origins[0]:
        raise PolicyError("origin deve possuir exatamente uma URL configurada.")

    branch = detect_default_branch(repository, git, env)
    remote_ref = f"refs/remotes/origin/{branch}"
    refspec = f"refs/heads/{branch}:{remote_ref}"
    require_success(
        run_git(
            git,
            repository,
            ["fetch", "--no-tags", "--no-recurse-submodules", "origin", refspec],
            env,
            timeout=300,
        ),
        "Fetch da default branch",
    )
    ancestry = run_git(
        git,
        repository,
        ["merge-base", "--is-ancestor", f"refs/heads/{branch}", remote_ref],
        env,
    )
    if ancestry.returncode == 1:
        raise PolicyError("Default branch local divergiu de origin; fast-forward recusado.")
    if ancestry.returncode != 0:
        raise PolicyError("Não foi possível validar a ancestralidade da default branch.")

    require_success(run_git(git, repository, ["switch", branch], env), "Retorno à default branch")
    require_success(
        run_git(git, repository, ["merge", "--ff-only", remote_ref], env),
        "Fast-forward da default branch",
    )
    head = require_success(run_git(git, repository, ["rev-parse", "HEAD"], env), "Leitura de HEAD")
    remote = require_success(run_git(git, repository, ["rev-parse", remote_ref], env), "Leitura remota")
    if head != remote:
        raise PolicyError("A default branch local não terminou sincronizada.")
    require_clean(repository, git, env)


def self_test() -> None:
    assert require_success(subprocess.CompletedProcess([], 0, "ok\n", ""), "teste") == "ok"
    print("safe_git_sync self-test: ok")


def main(argv: Sequence[str]) -> int:
    if list(argv) == ["self-test"]:
        self_test()
        return 0
    if list(argv) not in (["sync-main"], ["--help"], ["-h"]):
        print("Uso: python3 .codex/safe_git_sync.py {sync-main|self-test}", file=sys.stderr)
        return 2
    if argv[0] in {"--help", "-h"}:
        print("Uso: python3 .codex/safe_git_sync.py {sync-main|self-test}")
        return 0
    git = shutil.which("git")
    if not git:
        print("safe_git_sync: bloqueado: Git não encontrado.", file=sys.stderr)
        return 2
    try:
        sync_main(Path.cwd(), git=git, source_env=os.environ)
        print("safe_git_sync: sync-main concluído")
        return 0
    except (OSError, PolicyError, UnicodeError) as exc:
        print(f"safe_git_sync: bloqueado: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
