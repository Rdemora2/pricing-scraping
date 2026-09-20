"""Opt-in evidence for deterministic, isolated Python gates; no Git state."""

from __future__ import annotations

import hashlib
from contextlib import contextmanager
import json
import os
from pathlib import Path
import platform
import stat
import sys
import tempfile


MAX_FILES = 10000
MAX_BYTES = 32 * 1024 * 1024
BLOCKED_PARTS = {".git", ".env", "private", "commercial", "sessions", "metrics", "node_modules"}


def command(gate: dict) -> list[str]:
    argv = gate["argv"]
    return [sys.executable, *argv[1:]] if gate.get("cache") and argv[0] == "python3" else argv


def execution_environment(gate: dict) -> dict[str, str] | None:
    if not gate.get("cache"):
        return None
    # No inherited Python hooks, CI flags, credentials or service endpoints.
    env = {"PATH": os.defpath, "LANG": "C", "LC_ALL": "C", "TZ": "UTC"}
    if os.name == "nt" and "SYSTEMROOT" in os.environ:
        env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    return env


def _digest(path: Path, remaining: list[int], captured: dict | None = None, relative: str = "") -> str:
    def identity(value: os.stat_result) -> tuple:
        return (value.st_dev, value.st_ino, value.st_mode, value.st_size, value.st_mtime_ns, value.st_ctime_ns)

    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > remaining[0]:
        raise ValueError("unbounded or non-regular input")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if identity(opened) != identity(before):
            raise ValueError("input changed before read")
        content = stream.read(remaining[0] + 1)
        after = os.fstat(stream.fileno())
    if len(content) > remaining[0] or identity(opened) != identity(after) or identity(path.lstat()) != identity(after):
        raise ValueError("input changed during read")
    remaining[0] -= len(content)
    if captured is not None:
        captured[relative] = content
    return hashlib.sha256(content).hexdigest()


def fingerprint(root: Path, gate: dict, *, captured: dict | None = None) -> str | None:
    """Absent/incomplete/unsafe manifests disable reuse, never fail a gate open.

    Inputs name complete files or directory trees, not changed-file lists.
    The host Python installation is a trusted runtime, identified by version
    and executable bytes. No service/network/Git-index dependent gate opts in.
    """
    manifest = gate.get("cache")
    if not isinstance(manifest, dict) or manifest.get("kind") != "isolated-python-v1":
        return None
    argv = gate.get("argv", [])
    inputs = manifest.get("inputs")
    if not isinstance(inputs, list) or not inputs or argv[1:4] != ["-I", "-S", "-B"]:
        return None
    try:
        executable = sys.executable
        if argv[0] != "python3":
            return None
        root = root.resolve(strict=True)
        remaining = [MAX_BYTES]
        snapshot: dict[str, str] = {}

        def visit(relative: str) -> None:
            if len(snapshot) >= MAX_FILES:
                raise ValueError("too many dependencies")
            parts = Path(relative).parts
            if not parts or Path(relative).is_absolute() or Path(relative).drive or ".." in parts:
                raise ValueError("invalid dependency path")
            current = root
            for part in parts:
                if part.lower() in BLOCKED_PARTS or part.lower().startswith(".env.") or part.lower().endswith((".pem", ".key", ".p12")):
                    raise ValueError("private dependency")
                current /= part
                if current.is_symlink():
                    raise ValueError("symlink dependency")
            if current.is_dir():
                snapshot[relative + "/"] = "directory"
                if captured is not None:
                    captured[relative + "/"] = None
                for child in sorted(current.iterdir()):
                    if child.name != "__pycache__":
                        visit(child.relative_to(root).as_posix())
            else:
                snapshot[relative] = _digest(current, remaining, captured, relative)

        for relative in inputs:
            visit(relative)
        for relative in (".codex/execution_control.py", ".codex/gate_cache.py"):
            visit(relative)
        payload = {
            "schema_version": 2,
            "gate": gate,
            "inputs": snapshot,
            "runtime": [sys.version, sys.platform, platform.machine(), _digest(Path(executable).resolve(), [MAX_BYTES])],
            "environment": execution_environment(gate),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    except (OSError, ValueError, TypeError, RecursionError):
        return None


@contextmanager
def execution_root(root: Path, gate: dict, expected: str | None):
    """Run cacheable gates against the bytes fingerprinted, outside the worktree.

    The private temporary directory is owned by this invocation only. Like the
    evidence store and Python installation, it trusts the local OS/user; this
    is not isolation against a malicious process with the same credentials.
    """
    if not expected or not gate.get("cache"):
        yield root
        return
    captured: dict[str, bytes | None] = {}
    if fingerprint(root, gate, captured=captured) != expected:
        raise ValueError("dependencies changed before snapshot")
    with tempfile.TemporaryDirectory(prefix="valiant-gate-") as temporary:
        isolated = Path(temporary)
        for relative, content in captured.items():
            destination = isolated / relative
            if content is None:
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
        if fingerprint(isolated, gate) != expected:
            raise ValueError("snapshot does not match evidence inputs")
        yield isolated
