#!/usr/bin/env python3
"""Validate a bounded review receipt; not an identity or sandbox attestation."""
import argparse
import json
import re
import sys

FIELDS = {"role", "scope_fingerprint", "status", "verdict", "summary", "checked", "pending", "findings"}
ROLES = ("reviewer", "security-reviewer")
VERDICTS = ("APROVAR_LOCALMENTE", "CORRIGIR", "BLOQUEAR")


def text(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 4096


def validate(receipt, expected_scope, expected_role):
    if not isinstance(receipt, dict) or set(receipt) != FIELDS:
        raise ValueError("receipt fields missing or unknown")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_scope):
        raise ValueError("expected scope must be a SHA-256 fingerprint")
    if receipt["scope_fingerprint"] != expected_scope or receipt["role"] != expected_role:
        raise ValueError("stale scope or wrong reviewer role")
    if receipt["status"] not in ("complete", "incomplete") or receipt["verdict"] not in VERDICTS:
        raise ValueError("invalid status or verdict")
    if not text(receipt["summary"]):
        raise ValueError("missing summary")
    for field in ("checked", "pending"):
        values = receipt[field]
        if not isinstance(values, list) or len(values) > 100 or not all(text(v) for v in values):
            raise ValueError("invalid evidence list")
    findings = receipt["findings"]
    if not isinstance(findings, list) or len(findings) > 100:
        raise ValueError("invalid findings")
    for finding in findings:
        if not isinstance(finding, dict) or set(finding) != {"severity", "evidence", "summary"}:
            raise ValueError("invalid finding fields")
        if finding["severity"] not in ("blocking", "high", "medium", "low"):
            raise ValueError("invalid severity")
        if not text(finding["evidence"]) or not text(finding["summary"]):
            raise ValueError("finding lacks evidence")
    return (
        receipt["status"] == "complete"
        and receipt["verdict"] == "APROVAR_LOCALMENTE"
        and bool(receipt["checked"])
        and not receipt["pending"]
        and not any(f["severity"] in ("blocking", "high") for f in findings)
    )


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--role", required=True, choices=ROLES)
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.read(65_537)
        if len(raw.encode("utf-8")) > 65_536:
            raise ValueError("receipt exceeds 64 KiB")
        receipt = json.loads(raw, object_pairs_hook=unique_object)
        approved = validate(receipt, args.scope, args.role)
    except (ValueError, TypeError, UnicodeError):
        print("BLOQUEAR: recibo inválido, ausente ou incompatível; não é aprovação.", file=sys.stderr)
        return 2
    if not approved:
        print("BLOQUEAR: revisão incompleta ou com correções/pendências.", file=sys.stderr)
        return 1
    print("APROVAR_LOCALMENTE: estrutura e escopo do recibo validados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
