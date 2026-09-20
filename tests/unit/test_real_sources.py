import json

from pricing_intel.collection.extraction import iter_product_json_ld
from pricing_intel.collection.real_sources import (
    MAX_AGGREGATE_OFFERS,
    extract_fast_shop_listing,
    extract_iplace_listings,
    extract_kabum_listing,
    extract_samsung_shop_listings,
    extract_zoom_listings,
)
from pricing_intel.domain.enums import Availability, Condition
from pricing_intel.matching.signature import compute_signature
from scripts.seed_catalog import PRODUCTS


def _html(payload: object) -> str:
    return f'<script type="application/ld+json">{json.dumps(payload)}</script>'


def test_iter_product_json_ld_flattens_arrays_and_graphs() -> None:
    payload = [{"@graph": [{"@type": "BreadcrumbList"}, {"@type": "Product", "sku": "1"}]}]

    assert [item["sku"] for item in iter_product_json_ld(_html(payload))] == ["1"]


def test_iplace_extracts_multiple_real_variants() -> None:
    payload = [
        {
            "@type": "Product",
            "name": f"iPhone 17 {storage}GB {color}",
            "sku": sku,
            "gtin13": "9999999999999",
            "url": f"https://www.iplace.com.br/produto?skuId={sku}",
            "offers": {
                "@type": "Offer",
                "price": price,
                "priceCurrency": "BRL",
                "availability": "http://schema.org/InStock",
                "itemCondition": "http://schema.org/NewCondition",
            },
        }
        for storage, color, sku, price in (
            ("256", "Preto", "100080116", "5599"),
            ("512", "Lavanda", "100080224", "6959"),
        )
    ]

    listings = extract_iplace_listings(_html(payload), "https://www.iplace.com.br/produto")

    assert [item.external_listing_id for item in listings] == ["100080116", "100080224"]
    assert listings[0].attributes == {
        "brand": "apple",
        "model": "iphone_17",
        "region": "br",
        "storage_gb": "256",
        "color": "Preto",
    }
    assert listings[0].availability == Availability.IN_STOCK
    assert listings[0].condition == Condition.NEW
    assert listings[0].gtin is None
    seeded_signatures = {
        compute_signature(variant.attributes)
        for product in PRODUCTS
        if product.name == "Apple iPhone 17"
        for variant in product.variants
    }
    assert {compute_signature(item.attributes) for item in listings} <= seeded_signatures


def test_fast_shop_extracts_attributes_and_out_of_stock_state() -> None:
    payload = {
        "@type": "Product",
        "name": "iPhone 17 Apple, 256GB, Preto",
        "sku": "167316",
        "description": "Modelo: MG6J4BR/A | Cor: Preto | EAN/UPC: 195950643428",
        "offers": {
            "@type": "Offer",
            "price": "5599",
            "priceCurrency": "BRL",
            "availability": "https://schema.org/OutOfStock",
            "itemCondition": "https://schema.org/NewCondition",
        },
    }

    listing = extract_fast_shop_listing(_html(payload), "https://site.fastshop.com.br/item")

    assert listing.external_listing_id == "167316"
    assert listing.gtin is None
    assert listing.attributes["color"] == "Preto"
    assert listing.availability == Availability.OUT_OF_STOCK


def test_fast_shop_maps_pro_model_and_defers_unseeded_gtin() -> None:
    payload = {
        "@type": "Product",
        "name": 'iPhone 17 Pro (256GB) Azul Intenso, Tela de 6,3"',
        "sku": "4000058865",
        "gtin13": "195950628074",
        "description": "Modelo: MG8J4BE/A | Cor: Azul-intenso | EAN: 195950628074",
        "offers": {
            "@type": "Offer",
            "price": "10919.16",
            "priceCurrency": "BRL",
            "availability": "https://schema.org/InStock",
            "itemCondition": "https://schema.org/NewCondition",
        },
    }

    listing = extract_fast_shop_listing(_html(payload), "https://site.fastshop.com.br/item")

    assert listing.attributes["model"] == "iphone_17_pro"
    assert listing.attributes["color"] == "Azul-Intenso"
    assert listing.gtin is None


def test_kabum_extracts_visible_seller_and_cash_price() -> None:
    payload = {
        "@type": "Product",
        "name": "iPhone 17 Pro Apple 256GB, Prateado",
        "sku": "925346",
        "description": "iPhone 17 Pro Apple 256GB, Prateado",
        "offers": {
            "@type": "Offer",
            "url": "https://www.kabum.com.br/produto/925346/iphone-17-pro-prateado",
            "price": "9999.99",
            "priceCurrency": "BRL",
            "availability": "https://schema.org/InStock",
        },
    }
    page = _html(payload) + '<span>Vendido e entregue por:</span><b class="seller">KaBuM!</b></div>'

    listing = extract_kabum_listing(page, "https://www.kabum.com.br/produto/925346")

    assert listing.external_listing_id == "925346"
    assert listing.seller_display_name == "KaBuM!"
    assert listing.seller_external_id == "kabum"
    assert listing.attributes["model"] == "iphone_17_pro"
    assert listing.attributes["storage_gb"] == "256"
    assert listing.attributes["color"] == "Prateado"
    assert listing.condition == Condition.NEW
    assert listing.payment_terms.price_basis.value == "advertised"


def test_kabum_extracts_marketplace_seller_from_button() -> None:
    payload = {
        "@type": "Product",
        "name": "Samsung Galaxy S26 Ultra 256GB Preto",
        "sku": "1048105",
        "offers": {
            "@type": "Offer",
            "price": "7998.89",
            "priceCurrency": "BRL",
            "availability": "https://schema.org/InStock",
        },
    }
    page = (
        _html(payload)
        + "<span>Vendido e entregue por:</span><span>"
        + "<button>NOVA ERA COMERCIO DE CELULARES LTDA</button></span></div>"
    )

    listing = extract_kabum_listing(page, "https://www.kabum.com.br/produto/1048105")

    assert listing.seller_display_name == "NOVA ERA COMERCIO DE CELULARES LTDA"
    assert listing.attributes["model"] == "galaxy_s26_ultra"


def test_retail_price_preserves_and_flags_commercial_condition() -> None:
    payload = [
        {
            "@type": "Product",
            "name": "iPhone 17 256GB Preto",
            "sku": "100080116",
            "offers": {
                "@type": "Offer",
                "name": "R$ 4.999 em 12x exclusivo no Cartão iPlace",
                "price": "4999",
                "priceCurrency": "BRL",
                "availability": "https://schema.org/InStock",
                "itemCondition": "https://schema.org/NewCondition",
            },
        }
    ]

    listing = extract_iplace_listings(_html(payload), "https://www.iplace.com.br/produto")[0]

    assert listing.payment_terms.is_conditional is True
    assert listing.payment_terms.price_basis.value == "conditional"
    assert listing.payment_terms.installment_count == 12
    assert listing.payment_terms.condition_summary == "cartão iPlace"


def test_samsung_shop_extracts_product_group_variants() -> None:
    variants = [
        {
            "@type": "Product",
            "name": f"Celular Samsung Galaxy {model} 5G, {storage}, 12GB RAM {color}",
            "sku": sku,
            "gtin": gtin,
            "color": color,
            "url": f"https://shop.samsung.com/br/galaxy-s26/p?skuId={sku}",
            "offers": {
                "@type": "Offer",
                "price": price,
                "priceCurrency": "BRL",
                "availability": "https://schema.org/InStock",
                "itemCondition": "https://schema.org/NewCondition",
                "seller": {"@type": "Organization", "name": "Samsung Brasil"},
            },
        }
        for model, storage, color, sku, gtin, price in (
            ("S26", "256GB", "Preto", "13645", "7892509147552", 7499),
            ("S26+", "512GB", "Azul", "13711", "7892509148009", 10799),
            ("S26 Ultra", "1TB", "Violeta", "13890", "7892509149006", 15499),
        )
    ]
    payload = {"@type": "ProductGroup", "name": "Galaxy S26", "hasVariant": variants}

    listings = extract_samsung_shop_listings(
        _html(payload), "https://shop.samsung.com/br/galaxy-s26/p"
    )

    assert len(listings) == 3
    assert [listing.attributes["model"] for listing in listings] == [
        "galaxy_s26",
        "galaxy_s26_plus",
        "galaxy_s26_ultra",
    ]
    assert listings[2].attributes["storage_gb"] == "1024"
    assert listings[0].gtin is None
    assert listings[0].price_amount == 7499
    seeded_signatures = {
        compute_signature(variant.attributes)
        for product in PRODUCTS
        if product.brand == "Samsung"
        for variant in product.variants
    }
    assert {compute_signature(item.attributes) for item in listings} <= seeded_signatures


def test_zoom_extracts_bounded_multi_retailer_sample() -> None:
    offers = [
        {
            "@type": "Offer",
            "id": external_id,
            "name": f"Apple iPhone 17 Pro Max (256 GB) - {color}",
            "offeredBy": seller,
            "price": price,
            "priceCurrency": "BRL",
        }
        for external_id, color, seller, price in (
            ("offer-1", "Prateado", "Amazon", "9757.11"),
            ("offer-2", "Laranja-Cósmico", "Fast Shop", "10299.00"),
            ("offer-3", "Azul", "KaBuM!", "9999.99"),
        )
    ]
    payload = {
        "@type": "Product",
        "name": "iPhone 17 Pro Max 256GB",
        "offers": {"@type": "AggregateOffer", "offers": offers},
    }

    listings = extract_zoom_listings(
        _html(payload), "https://www.zoom.com.br/celular/celular-apple-iphone-17-pro-max-256gb"
    )

    assert len(listings) == 3
    assert {item.seller_display_name for item in listings} == {"Amazon", "Fast Shop", "KaBuM!"}
    assert {item.attributes["color"] for item in listings} == {
        "Prateado",
        "Laranja-Cósmico",
        "Azul-Intenso",
    }
    assert all(item.payment_terms.price_basis.value == "cash" for item in listings)
    assert all(item.url.startswith("https://www.zoom.com.br/celular/") for item in listings)


def test_zoom_caps_untrusted_aggregate_offer_count() -> None:
    offers = [
        {
            "@type": "Offer",
            "id": f"offer-{index}",
            "name": "Apple iPhone 17 Pro Max (256 GB) - Prateado",
            "offeredBy": f"Retailer {index}",
            "price": "9999.00",
            "priceCurrency": "BRL",
        }
        for index in range(MAX_AGGREGATE_OFFERS + 10)
    ]
    payload = {
        "@type": "Product",
        "name": "iPhone 17 Pro Max 256GB",
        "offers": {"@type": "AggregateOffer", "offers": offers},
    }

    listings = extract_zoom_listings(_html(payload), "https://www.zoom.com.br/celular/item")

    assert len(listings) == MAX_AGGREGATE_OFFERS
