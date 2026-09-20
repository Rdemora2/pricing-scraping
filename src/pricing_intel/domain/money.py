"""Exact monetary representation.

Prices are never stored or computed as binary floats (brief section 6).
Amounts live in the database as integer minor units (cents) plus an ISO
4217 currency code, and only ever pass through `decimal.Decimal` in
Python. The MVP targets BRL only, so two-decimal minor units are assumed;
a currency with a different exponent (e.g. JPY) would need this class
extended before use.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import NamedTuple

_CENTS = Decimal("0.01")


class Money(NamedTuple):
    minor_units: int
    currency: str

    @classmethod
    def from_decimal(cls, amount: Decimal, currency: str) -> Money:
        if not amount.is_finite():
            raise ValueError("Money amount must be finite")
        if amount <= 0:
            raise ValueError("Money amount must be positive")
        normalized_currency = currency.strip().upper()
        if len(normalized_currency) != 3 or not normalized_currency.isalpha():
            raise ValueError("Money currency must be a three-letter code")
        quantized = amount.quantize(_CENTS, rounding=ROUND_HALF_UP)
        return cls(minor_units=int(quantized * 100), currency=normalized_currency)

    def to_decimal(self) -> Decimal:
        # Plain division can normalize away trailing zeros (3499.00 -> 3499);
        # quantize back to 2 places so the wire format is always stable.
        return (Decimal(self.minor_units) / 100).quantize(_CENTS)

    def __str__(self) -> str:  # pragma: no cover - trivial formatting
        return f"{self.to_decimal():.2f} {self.currency}"
