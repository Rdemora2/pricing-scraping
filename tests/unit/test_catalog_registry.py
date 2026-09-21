from pricing_intel.catalog import CATALOG_PRODUCTS
from pricing_intel.matching.signature import compute_signature
from scripts.seed_catalog import SOURCES


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


def test_search_capable_sources_are_registered_once_at_domain_root() -> None:
    dynamic_sources = [
        item
        for item in SOURCES
        if item.adapter_name
        in {
            "amazon",
            "americanas",
            "carrefour",
            "zoom",
            "buscape",
            "kabum",
            "bondfaro",
            "samsung_shop",
        }
    ]

    assert {(item.name, item.base_url) for item in dynamic_sources} == {
        ("Amazon Brasil", "https://www.amazon.com.br/"),
        ("Americanas", "https://www.americanas.com.br/"),
        ("Carrefour", "https://www.carrefour.com.br/"),
        ("Zoom", "https://www.zoom.com.br/"),
        ("Buscapé", "https://www.buscape.com.br/"),
        ("KaBuM!", "https://www.kabum.com.br/"),
        ("Bondfaro", "https://www.bondfaro.com.br/"),
        ("Samsung Shop", "https://shop.samsung.com/br/"),
    }
    assert {item.name for item in dynamic_sources if item.status == "enabled"} == {
        "Americanas",
        "Buscapé",
        "KaBuM!",
        "Samsung Shop",
        "Zoom",
    }


def test_national_source_portfolio_is_registered_without_fake_enablement() -> None:
    by_name = {item.name: item for item in SOURCES}
    expected_candidates = {
        "Amazon Brasil",
        "Carrefour",
        "Casas Bahia",
        "Ponto",
        "Extra",
        "Magalu",
        "Mercado Livre",
        "Shopee Brasil",
        "AliExpress Brasil",
        "Fast Shop",
        "Pichau",
        "TerabyteShop",
        "Claro Loja Online",
        "Vivo Loja Online",
        "TIM Loja Online",
        "JáCotei",
        "Promobit",
        "Pelando",
        "Bondfaro",
    }

    assert expected_candidates <= by_name.keys()
    assert all(by_name[name].status == "candidate" for name in expected_candidates)
    assert by_name["Magalu"].base_url == "https://www.magazineluiza.com.br/"
    assert by_name["Ponto"].base_url == "https://www.ponto.com.br/"


def test_only_validated_market_search_collectors_are_enabled() -> None:
    enabled_market = {
        item.name for item in SOURCES if item.kind == "real" and item.status == "enabled"
    }

    assert enabled_market == {
        "Americanas",
        "Buscapé",
        "KaBuM!",
        "Samsung Shop",
        "Zoom",
    }
