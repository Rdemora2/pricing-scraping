import json
from copy import deepcopy

import pytest

from pricing_intel.collection.extraction import (
    ExtractionError,
    extract_listing,
    find_product_json_ld,
)
from pricing_intel.domain.enums import Availability, Condition


@pytest.fixture
def product_payload() -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Nimbus Phone X 128GB Preto",
        "gtin13": "7891234500018",
        "additionalProperty": [
            {"@type": "PropertyValue", "name": "storage_gb", "value": "128"},
            {"@type": "PropertyValue", "name": "color", "value": "Preto"},
            {"@type": "PropertyValue", "name": "weight", "value": "190g"},
        ],
        "offers": {
            "@type": "Offer",
            "price": "3499.00",
            "priceCurrency": "BRL",
            "availability": "https://schema.org/InStock",
            "itemCondition": "https://schema.org/NewCondition",
            "seller": {"@type": "Organization", "name": "Aurora Eletrônicos"},
            "additionalProperty": [
                {"@type": "PropertyValue", "name": "installmentCount", "value": "10"},
                {"@type": "PropertyValue", "name": "shippingKnown", "value": "false"},
            ],
        },
    }


def test_find_and_extract_product_json_ld(product_payload: dict) -> None:
    html = f"<html><script type='application/ld+json'>{json.dumps(product_payload)}</script></html>"

    listing = extract_listing(find_product_json_ld(html))

    assert listing.raw_title == "Nimbus Phone X 128GB Preto"
    assert listing.gtin == "7891234500018"
    assert listing.attributes == {"storage_gb": "128", "color": "Preto"}
    assert str(listing.price_amount) == "3499.00"
    assert listing.availability == Availability.IN_STOCK
    assert listing.condition == Condition.NEW
    assert listing.payment_terms.installment_count == 10
    assert listing.shipping.known is False


@pytest.mark.parametrize("missing_field", ["price", "priceCurrency"])
def test_extract_listing_rejects_missing_offer_fields(
    product_payload: dict, missing_field: str
) -> None:
    payload = deepcopy(product_payload)
    del payload["offers"][missing_field]

    with pytest.raises(ExtractionError):
        extract_listing(payload)


@pytest.mark.parametrize("price", ["0", "-1.00"])
def test_extract_listing_rejects_non_positive_price(product_payload: dict, price: str) -> None:
    payload = deepcopy(product_payload)
    payload["offers"]["price"] = price

    with pytest.raises(ExtractionError, match="positive"):
        extract_listing(payload)


def test_extract_listing_rejects_missing_variant_attributes(product_payload: dict) -> None:
    payload = deepcopy(product_payload)
    payload["additionalProperty"] = []

    with pytest.raises(ExtractionError, match="variant-identifying"):
        extract_listing(payload)


def test_extract_listing_rejects_invalid_commercial_terms(product_payload: dict) -> None:
    payload = deepcopy(product_payload)
    payload["offers"]["additionalProperty"] = [
        {"@type": "PropertyValue", "name": "installmentCount", "value": "many"}
    ]

    with pytest.raises(ExtractionError, match="payment terms"):
        extract_listing(payload)


def test_find_product_json_ld_ignores_malformed_blocks() -> None:
    html = "<script type='application/ld+json'>{not-json}</script>"

    with pytest.raises(ExtractionError):
        find_product_json_ld(html)
