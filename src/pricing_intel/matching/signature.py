"""Shared attribute-signature computation.

Used both when seeding the canonical variant catalog and when matching
a freshly scraped listing against it, so the two sides are guaranteed
to agree on what counts as "the same variant".
"""

from __future__ import annotations


def compute_signature(attributes: dict[str, str]) -> str:
    normalized = {key.strip().lower(): value.strip().lower() for key, value in attributes.items()}
    return "|".join(f"{key}={value}" for key, value in sorted(normalized.items()))
