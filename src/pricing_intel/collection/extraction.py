"""Pure JSON-LD extraction — no I/O, no Scrapy imports.

Kept separate from the spiders/pipeline so it can be unit-tested
directly against saved HTML fixtures (tests/fixtures/html/), which is
the actual regression protection for source-specific markup changes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from parsel import Selector

from pricing_intel.domain.enums import Availability, Condition
from pricing_intel.domain.models import PaymentTerms, ShippingTerms


class ExtractionError(Exception):
    """The page did not contain a usable Product+Offer JSON-LD block."""


@dataclass(frozen=True, slots=True)
class ExtractedListing:
    raw_title: str
    gtin: str | None
    attributes: dict[str, str]
    seller_display_name: str
    price_amount: Decimal
    currency: str
    availability: Availability
    condition: Condition
    payment_terms: PaymentTerms
    shipping: ShippingTerms


_AVAILABILITY_MAP = {
    "https://schema.org/InStock": Availability.IN_STOCK,
    "https://schema.org/OutOfStock": Availability.OUT_OF_STOCK,
}

_CONDITION_MAP = {
    "https://schema.org/NewCondition": Condition.NEW,
    "https://schema.org/UsedCondition": Condition.USED,
    "https://schema.org/RefurbishedCondition": Condition.REFURBISHED,
}

# Attribute-level PropertyValue names that identify a *variant* (as opposed
# to commercial-terms properties, which live on the Offer, not the Product).
_VARIANT_ATTRIBUTE_NAMES = {"storage_gb", "color"}


def find_product_json_ld(html: str) -> dict:
    """Returns the first ``schema.org/Product`` JSON-LD block on the page."""
    selector = Selector(text=html)
    for raw in selector.css('script[type="application/ld+json"]::text').getall():
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") == "Product":
            return data
    raise ExtractionError("no schema.org Product JSON-LD block found on page")


def _properties_map(items: list[dict] | None) -> dict[str, str]:
    if not items:
        return {}
    return {
        item["name"]: str(item["value"])
        for item in items
        if item.get("@type") == "PropertyValue" and "name" in item and "value" in item
    }


def _parse_price(raw_price: object) -> Decimal:
    try:
        return Decimal(str(raw_price))
    except InvalidOperation as exc:
        raise ExtractionError(f"unparseable price value: {raw_price!r}") from exc


def _parse_payment_terms(properties: dict[str, str]) -> PaymentTerms:
    installment_count = properties.get("installmentCount")
    cash_discount_pct = properties.get("cashDiscountPct")
    return PaymentTerms(
        installment_count=int(installment_count) if installment_count else None,
        cash_discount_pct=Decimal(cash_discount_pct) if cash_discount_pct else None,
        coupon_code=properties.get("couponCode") or None,
    )


def _parse_shipping(properties: dict[str, str]) -> ShippingTerms:
    known = properties.get("shippingKnown", "false").lower() == "true"
    if not known:
        return ShippingTerms(known=False)
    cost = properties.get("shippingCostMinorUnits")
    threshold = properties.get("freeShippingThresholdMinorUnits")
    return ShippingTerms(
        known=True,
        cost_minor_units=int(cost) if cost is not None else None,
        cost_currency="BRL" if cost is not None else None,
        free_shipping_threshold_minor_units=int(threshold) if threshold is not None else None,
    )


def extract_listing(product: dict) -> ExtractedListing:
    offer = product.get("offers")
    if not isinstance(offer, dict):
        raise ExtractionError("Product JSON-LD is missing an 'offers' object")

    attributes = {
        name: value
        for name, value in _properties_map(product.get("additionalProperty")).items()
        if name in _VARIANT_ATTRIBUTE_NAMES
    }
    if not attributes:
        raise ExtractionError("Product JSON-LD has no variant-identifying attributes")

    offer_properties = _properties_map(offer.get("additionalProperty"))
    seller = offer.get("seller") or {}

    try:
        name = product["name"]
        price_currency = offer["priceCurrency"]
        seller_name = seller["name"]
    except KeyError as exc:
        raise ExtractionError(f"Product/Offer JSON-LD missing required field: {exc}") from exc

    return ExtractedListing(
        raw_title=name,
        gtin=product.get("gtin13") or product.get("gtin") or None,
        attributes=attributes,
        seller_display_name=seller_name,
        price_amount=_parse_price(offer["price"]),
        currency=price_currency,
        availability=_AVAILABILITY_MAP.get(offer.get("availability", ""), Availability.UNKNOWN),
        condition=_CONDITION_MAP.get(offer.get("itemCondition", ""), Condition.UNKNOWN),
        payment_terms=_parse_payment_terms(offer_properties),
        shipping=_parse_shipping(offer_properties),
    )
