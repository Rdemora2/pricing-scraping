from pricing_intel.catalog import CATALOG_PRODUCTS
from pricing_intel.matching.signature import compute_signature


def test_catalog_covers_reviewed_flagship_families() -> None:
    names = {product.name for product in CATALOG_PRODUCTS}

    assert {
        "Apple iPhone 16",
        "Apple iPhone 16 Pro Max",
        "Apple iPhone 17",
        "Apple iPhone Air",
        "Apple iPhone 18 Pro",
        "Apple iPhone 18 Pro Max",
        "Samsung Galaxy S25",
        "Samsung Galaxy S25 Ultra",
        "Samsung Galaxy S26",
        "Samsung Galaxy S26 Ultra",
        "Motorola Edge 70 Pro",
    } <= names
    assert "Apple iPhone 18" not in names


def test_catalog_identity_and_variant_signatures_are_unique() -> None:
    names = [product.name for product in CATALOG_PRODUCTS]
    models = [product.model for product in CATALOG_PRODUCTS]
    signatures = [
        (product.name, compute_signature(variant.attributes))
        for product in CATALOG_PRODUCTS
        for variant in product.variants
    ]

    assert len(names) == len(set(names))
    assert len(models) == len(set(models))
    assert len(signatures) == len(set(signatures))


def test_market_catalog_has_provenance_and_only_positive_storage() -> None:
    market_products = [product for product in CATALOG_PRODUCTS if product.brand != "Nimbus"]

    assert len(market_products) == 17
    assert sum(len(product.variants) for product in market_products) == 221
    assert all(
        product.reference_url and product.reference_url.startswith("https://")
        for product in market_products
    )
    assert all(
        int(variant.attributes["storage_gb"]) > 0
        for product in CATALOG_PRODUCTS
        for variant in product.variants
    )


def test_lab_catalog_keeps_only_the_three_supported_variants() -> None:
    nimbus = next(product for product in CATALOG_PRODUCTS if product.brand == "Nimbus")
    variants = {
        (variant.attributes["storage_gb"], variant.attributes["color"])
        for variant in nimbus.variants
    }

    assert variants == {("128", "Preto"), ("256", "Preto"), ("128", "Azul")}
    assert all(variant.gtin is not None for variant in nimbus.variants)
