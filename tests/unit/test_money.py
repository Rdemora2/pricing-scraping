from decimal import Decimal

import pytest

from pricing_intel.domain.money import Money


@pytest.mark.parametrize(
    ("amount", "expected_minor_units"),
    [
        ("0", 0),
        ("3499.00", 349900),
        ("10.005", 1001),
        ("10.004", 1000),
    ],
)
def test_money_uses_exact_minor_units(amount: str, expected_minor_units: int) -> None:
    money = Money.from_decimal(Decimal(amount), "brl")

    assert money.minor_units == expected_minor_units
    assert money.currency == "BRL"
    assert money.to_decimal().as_tuple().exponent == -2


@pytest.mark.parametrize("amount", [Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity")])
def test_money_rejects_invalid_amounts(amount: Decimal) -> None:
    with pytest.raises(ValueError):
        Money.from_decimal(amount, "BRL")


@pytest.mark.parametrize("currency", ["", "BR", "REAL", "12$"])
def test_money_rejects_invalid_currency_codes(currency: str) -> None:
    with pytest.raises(ValueError):
        Money.from_decimal(Decimal("10.00"), currency)
