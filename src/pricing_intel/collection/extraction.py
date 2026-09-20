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
    "http://schema.org/InStock": Availability.IN_STOCK,
    "https://schema.org/OutOfStock": Availability.OUT_OF_STOCK,
    "http://schema.org/OutOfStock": Availability.OUT_OF_STOCK,
}

_CONDITION_MAP = {
    "https://schema.org/NewCondition": Condition.NEW,
    "http://schema.org/NewCondition": Condition.NEW,
    "https://schema.org/UsedCondition": Condition.USED,
    "http://schema.org/UsedCondition": Condition.USED,
    "https://schema.org/RefurbishedCondition": Condition.REFURBISHED,
    "http://schema.org/RefurbishedCondition": Condition.REFURBISHED,
}

# Attribute-level PropertyValue names that identify a *variant* (as opposed
# to commercial-terms properties, which live on the Offer, not the Product).
_VARIANT_ATTRIBUTE_NAMES = {"storage_gb", "color"}


def _walk_json_ld(value: object):
    if isinstance(value, list):
        for item in value:
            yield from _walk_json_ld(item)
    elif isinstance(value, dict):
        graph = value.get("@graph")
        if graph is not None:
            yield from _walk_json_ld(graph)
        variants = value.get("hasVariant")
        if variants is not None:
            yield from _walk_json_ld(variants)
        yield value


def iter_product_json_ld(html: str):
    """Yields Product blocks from objects, arrays and ``@graph`` containers."""
    selector = Selector(text=html)
    for raw in selector.css('script[type="application/ld+json"]::text').getall():
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for item in _walk_json_ld(data):
            item_types = item.get("@type")
            if item_types == "Product" or (
                isinstance(item_types, list) and "Product" in item_types
            ):
                yield item


def find_product_json_ld(html: str) -> dict:
    """Returns the first ``schema.org/Product`` JSON-LD block on the page."""
    product = next(iter_product_json_ld(html), None)
    if product is not None:
        return product
    raise ExtractionError("no schema.org Product JSON-LD block found on page")


def parse_availability(value: str) -> Availability:
    return _AVAILABILITY_MAP.get(value, Availability.UNKNOWN)


def parse_condition(value: str) -> Condition:
    return _CONDITION_MAP.get(value, Condition.UNKNOWN)


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
    try:
        return PaymentTerms(
            installment_count=int(installment_count) if installment_count else None,
            cash_discount_pct=Decimal(cash_discount_pct) if cash_discount_pct else None,
            coupon_code=properties.get("couponCode") or None,
        )
    except (InvalidOperation, ValueError) as exc:
        raise ExtractionError("Offer contains invalid payment terms") from exc


def _parse_shipping(properties: dict[str, str]) -> ShippingTerms:
    known = properties.get("shippingKnown", "false").lower() == "true"
    if not known:
        return ShippingTerms(known=False)
    cost = properties.get("shippingCostMinorUnits")
    threshold = properties.get("freeShippingThresholdMinorUnits")
    try:
        return ShippingTerms(
            known=True,
            cost_minor_units=int(cost) if cost is not None else None,
            cost_currency="BRL" if cost is not None else None,
            free_shipping_threshold_minor_units=int(threshold) if threshold is not None else None,
        )
    except ValueError as exc:
        raise ExtractionError("Offer contains invalid shipping terms") from exc


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
        price = offer["price"]
        price_currency = offer["priceCurrency"]
        seller_name = seller["name"]
    except KeyError as exc:
        raise ExtractionError(f"Product/Offer JSON-LD missing required field: {exc}") from exc

    return ExtractedListing(
        raw_title=name,
        gtin=product.get("gtin13") or product.get("gtin") or None,
        attributes=attributes,
        seller_display_name=seller_name,
        price_amount=_parse_price(price),
        currency=price_currency,
        availability=parse_availability(offer.get("availability", "")),
        condition=parse_condition(offer.get("itemCondition", "")),
        payment_terms=_parse_payment_terms(offer_properties),
        shipping=_parse_shipping(offer_properties),
    )
