import json
from decimal import Decimal

import pytest
from scrapy.http import Request, TextResponse

from pricing_intel.collection.extraction import ExtractionError, iter_product_json_ld
from pricing_intel.collection.items import ListingRejectedItem
from pricing_intel.collection.real_sources import (
    BUSCAPE_MAX_OFFER_PAGES,
    BUSCAPE_OFFER_PAGE_SIZE,
    MAX_AGGREGATE_OFFERS,
    BuscapeOfferParser,
    SkipLog,
    TwoAFinderMarkdownParser,
    extract_amazon_listing,
    extract_americanas_listing,
    extract_carrefour_listing,
    extract_fast_shop_listing,
    extract_iplace_listings,
    extract_kabum_listing,
    extract_product_search_urls,
    extract_samsung_shop_listings,
    extract_zoom_listings,
)
from pricing_intel.collection.spiders.retail import (
    AmazonSpider,
    AmericanasSpider,
    BondfaroSpider,
    BuscapeSpider,
    CarrefourSpider,
    KabumSpider,
    SamsungShopSpider,
    ZoomSpider,
)
from pricing_intel.domain.enums import Availability, Condition, RejectionStage
from pricing_intel.matching.signature import compute_signature
from scripts.seed_catalog import PRODUCTS


def _html(payload: object) -> str:
    return f'<script type="application/ld+json">{json.dumps(payload)}</script>'


def test_iter_product_json_ld_flattens_arrays_and_graphs() -> None:
    payload = [{"@graph": [{"@type": "BreadcrumbList"}, {"@type": "Product", "sku": "1"}]}]

    assert [item["sku"] for item in iter_product_json_ld(_html(payload))] == ["1"]


def test_amazon_prefers_visible_buy_box_over_stale_json_ld() -> None:
    page = (
        _html(
            {
                "@type": "Product",
                "name": "Apple iPhone 17 de 256 GB — Preto",
                "offers": {"@type": "Offer", "price": "6220.10", "priceCurrency": "BRL"},
            }
        )
        + """
        <h1><span id="productTitle"> Apple iPhone 17 de 256 GB — Preto </span></h1>
        <div id="corePrice_feature_div">
          <span class="a-price apex-pricetopay-value">
            <span class="a-offscreen">R$5.698,99</span>
          </span>
          <span>à vista no Pix ou NuPay</span>
        </div>
        <div id="availability"><span>Em estoque</span></div>
        <div offer-display-feature-name="desktop-merchant-info">
          <span class="a-size-small offer-display-feature-text-message">Amazon.com.br</span>
        </div>
    """
    )

    listing = extract_amazon_listing(
        page,
        "https://www.amazon.com.br/Apple-iPhone-17-256-GB/dp/B0GQW2J4SK",
    )

    assert listing.external_listing_id == "B0GQW2J4SK"
    assert listing.price_amount == Decimal("5698.99")
    assert listing.seller_display_name == "Amazon.com.br"
    assert listing.attributes["storage_gb"] == "256"
    assert listing.attributes["color"] == "Preto"
    assert listing.payment_terms.price_basis.value == "cash"


def test_amazon_accepts_visible_core_price_without_apex_class() -> None:
    page = """
        <h1><span id="productTitle">Apple iPhone 17 de 256 GB — Preto</span></h1>
        <div id="corePrice_feature_div">
          <span class="a-offscreen">R$6.220,10</span>
        </div>
        <div id="availability"><span>Em estoque</span></div>
        <div offer-display-feature-name="desktop-merchant-info">
          <span class="offer-display-feature-text-message">Amazon.com.br</span>
        </div>
    """

    listing = extract_amazon_listing(
        page,
        "https://www.amazon.com.br/Apple-iPhone-17-256-GB/dp/B0GQW2J4SK",
    )

    assert listing.price_amount == Decimal("6220.10")
    assert listing.payment_terms.price_basis.value == "advertised"


@pytest.mark.parametrize(
    ("seller", "sku", "price"),
    [
        ("mcs variedades", "337104577", "5669.10"),
        ("loja iplace", "340005163", "6029.10"),
    ],
)
def test_carrefour_uses_visible_pix_price_and_marketplace_seller(
    seller: str, sku: str, price: str
) -> None:
    payload = {
        "@type": "Product",
        "name": "Apple iPhone 17 256GB Preto 6,3 polegadas 48MP iOS 5G",
        "sku": sku,
        "offers": {
            "@type": "Offer",
            "price": "6299.00",
            "priceCurrency": "BRL",
            "availability": "http://schema.org/InStock",
            "itemCondition": "http://schema.org/NewCondition",
        },
    }
    # Render the expected Brazilian value explicitly; the JSON-LD list price
    # above must not override the scoped Pix price.
    formatted_price = "R$ 5.669,10" if price == "5669.10" else "R$ 6.029,10"
    page = (
        _html(payload)
        + f"<span>{formatted_price}</span><span>à vista no Pix</span>"
        + f'Vendido e entregue por<!-- --> <a href="/parceiro">{seller}</a>'
    )

    listing = extract_carrefour_listing(
        page,
        f"https://www.carrefour.com.br/produto/iphone-17-{sku}",
    )

    assert listing.price_amount == Decimal(price)
    assert listing.seller_display_name == seller
    assert listing.external_listing_id == sku
    assert listing.payment_terms.price_basis.value == "cash"


def test_americanas_selects_positive_in_stock_marketplace_offer() -> None:
    payload = {
        "@type": "Product",
        "name": "Apple iPhone 17 256GB Preto 6,3 polegadas 48MP iOS 5G",
        "sku": "8841126",
        "offers": [
            {
                "@type": "Offer",
                "price": "5799",
                "priceCurrency": "BRL",
                "availability": "https://schema.org/InStock",
                "seller": {"@type": "Organization", "name": "magazineluiza"},
            },
            {
                "@type": "Offer",
                "price": "0",
                "priceCurrency": "BRL",
                "availability": "https://schema.org/OutOfStock",
                "seller": {"@type": "Organization", "name": "1"},
            },
        ],
    }

    listing = extract_americanas_listing(_html(payload), "https://www.americanas.com.br/item/p")

    assert listing.external_listing_id == "8841126"
    assert listing.price_amount == Decimal("5799")
    assert listing.seller_display_name == "magazineluiza"
    assert listing.condition == Condition.NEW


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


def test_search_discovery_keeps_only_exact_same_host_product_pages() -> None:
    page = """
      <a href="/celular/celular-apple-iphone-17-pro-max-512gb">iPhone 17 Pro Max 512GB</a>
      <a href="/celular/celular-apple-iphone-17-pro-512gb">iPhone 17 Pro 512GB</a>
      <a href="https://attacker.example/celular/apple-iphone-17-pro-max-512gb">externo</a>
      <a href="/celular/celular-apple-iphone-17-pro-max-256gb">iPhone 17 Pro Max 256GB</a>
    """

    urls = extract_product_search_urls(
        page,
        "https://www.zoom.com.br/busca/apple%2Biphone%2B17%2Bpro%2Bmax%2B512gb",
        product_name="Apple iPhone 17 Pro Max",
        product_model="iphone_17_pro_max",
        storage_gb="512",
    )

    assert urls == ["https://www.zoom.com.br/celular/celular-apple-iphone-17-pro-max-512gb"]


def test_search_discovery_follows_every_color_up_to_the_catalog_maximum() -> None:
    # Galaxy S26 Ultra ships 6 colors (scripts/seed_catalog.py) — the highest
    # in the live catalog. A capacity search naming all of them must not be
    # silently truncated to the first few matches.
    colors = ["Titânio Preto", "Titânio Branco", "Titânio Prata", "Titânio Azul", "Verde", "Rosa"]
    page = "".join(
        f'<a href="/celular/samsung-galaxy-s26-ultra-256gb-{i}">Samsung Galaxy S26 Ultra 256GB {color}</a>'
        for i, color in enumerate(colors)
    )

    urls = extract_product_search_urls(
        page,
        "https://www.zoom.com.br/busca/samsung%2Bgalaxy%2Bs26%2Bultra%2B256gb",
        product_name="Samsung Galaxy S26 Ultra",
        product_model="galaxy_s26_ultra",
        storage_gb="256",
    )

    assert len(urls) == len(colors)


@pytest.mark.parametrize(
    ("product_name", "product_model", "expected_path"),
    [
        ("Apple iPhone 17", "iphone_17", "/celular/apple-iphone-17-256gb"),
        ("Apple iPhone 17 Pro", "iphone_17_pro", "/celular/apple-iphone-17-pro-256gb"),
        (
            "Apple iPhone 17 Pro Max",
            "iphone_17_pro_max",
            "/celular/apple-iphone-17-pro-max-256gb",
        ),
        ("Samsung Galaxy S26", "galaxy_s26", "/celular/samsung-galaxy-s26-256gb"),
        ("Samsung Galaxy S26+", "galaxy_s26_plus", "/celular/samsung-galaxy-s26-plus-256gb"),
    ],
)
def test_search_discovery_does_not_mix_neighboring_models(
    product_name: str, product_model: str, expected_path: str
) -> None:
    paths = [
        "/celular/apple-iphone-17-256gb",
        "/celular/apple-iphone-17-pro-256gb",
        "/celular/apple-iphone-17-pro-max-256gb",
        "/celular/samsung-galaxy-s26-256gb",
        "/celular/samsung-galaxy-s26-plus-256gb",
        "/celular/samsung-galaxy-s26-ultra-256gb",
    ]
    page = "".join(f'<a href="{path}">{path.replace("-", " ")}</a>' for path in paths)

    urls = extract_product_search_urls(
        page,
        "https://www.zoom.com.br/busca/produto",
        product_name=product_name,
        product_model=product_model,
        storage_gb="256",
    )

    assert urls == [f"https://www.zoom.com.br{expected_path}"]


def test_search_discovery_can_resolve_model_landing_page_without_capacity() -> None:
    page = """
      <a href="/br/smartphones/galaxy-s26-ultra/">Galaxy S26 Ultra</a>
      <a href="/br/smartphones/galaxy-s26/">Galaxy S26</a>
    """

    urls = extract_product_search_urls(
        page,
        "https://www.samsung.com/br/aisearch/?searchvalue=Galaxy+S26+Ultra",
        product_name="Samsung Galaxy S26 Ultra",
        product_model="galaxy_s26_ultra",
        storage_gb=None,
        product_path_markers=("/smartphones/",),
    )

    assert urls == ["https://www.samsung.com/br/smartphones/galaxy-s26-ultra/"]


@pytest.mark.asyncio
async def test_samsung_resolves_product_route_from_canonical_model() -> None:
    spider = SamsungShopSpider(
        source_id="source-1",
        run_id="run-1",
        base_url="https://shop.samsung.com/br/",
        product_name="Samsung Galaxy S26 Ultra",
        product_model="galaxy_s26_ultra",
        storages="256,512,1024",
    )
    requests = [request async for request in spider.start()]

    assert [item.url for item in requests] == ["https://shop.samsung.com/br/galaxy-s26-ultra/p"]
    assert requests[0].callback == spider.parse_product


@pytest.mark.parametrize(
    "spider_class",
    [
        AmazonSpider,
        AmericanasSpider,
        BondfaroSpider,
        CarrefourSpider,
        ZoomSpider,
        BuscapeSpider,
        KabumSpider,
    ],
)
def test_search_collectors_query_every_catalog_capacity(spider_class) -> None:
    spider = spider_class(
        source_id="00000000-0000-0000-0000-000000000001",
        run_id="00000000-0000-0000-0000-000000000002",
        base_url=f"https://www.{spider_class.name}.com.br/",
        product_name="Apple iPhone 17 Pro Max",
        product_model="iphone_17_pro_max",
        storages="256,512,1024,2048",
    )

    requests = list(spider.catalog_search_requests(spider.parse_search))

    assert len(requests) == 4
    assert all(any(marker in request.url for marker in ("/busca/", "/s?")) for request in requests)
    assert {request.cb_kwargs["storage_gb"] for request in requests} == {
        "256",
        "512",
        "1024",
        "2048",
    }


@pytest.mark.parametrize(
    "product",
    [product for product in PRODUCTS if product.reference_url is not None],
    ids=lambda product: product.model,
)
def test_zoom_normalizes_every_market_product_in_the_catalog(product) -> None:
    storage = product.storages_gb[0]
    color = product.colors[0]
    title = f"{product.name} {storage}GB {color.replace('-', ' ')}"
    payload = {
        "@type": "Product",
        "name": product.name,
        "offers": {
            "@type": "AggregateOffer",
            "offers": [
                {
                    "@type": "Offer",
                    "id": f"offer-{product.model}",
                    "name": title,
                    "offeredBy": "Varejista homologado",
                    "price": "4999.90",
                    "priceCurrency": "BRL",
                }
            ],
        },
    }

    listing = extract_zoom_listings(_html(payload), "https://www.zoom.com.br/celular/item")[0]

    assert listing.attributes == {
        "brand": product.brand.casefold(),
        "model": product.model,
        "region": "br",
        "storage_gb": storage,
        "color": color,
    }


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


def test_two_a_finder_parses_auditable_rows_and_literal_variant_separator() -> None:
    page = """# iPhone 17 Pro 256GB - Prateado

Onde comprar iPhone 17 Pro 256GB - Prateado: 2 ofertas ativas em 2 lojas.

| # | Preço | Loja | Vendedor | Condição | Frete | Variante | Verificado | Oferta ID | Próximo passo |
|---|---|---|---|---|---|---|---|---|---|
| 1 | R$\xa07.549,90 | Mercado Livre | LOJA_ALPHA | novo | grátis | storage=256 GB | cpu=Qualcomm | 2026-09-20T02:06:47.400Z | `cc672f0a-b759-4df6-bf80-d5c1e6c126cc` | https://2afinder.com/produto/iphone-17-pro |
| 2 | R$ 9.359,10 | Amazon Brasil | Amazon.com.br | não informada | a calcular | storage=256 GB | 2026-09-20T08:03:41.357Z | `0f87ef2f-8113-4618-b65a-34ee7e666270` | https://2afinder.com/produto/iphone-17-pro |
"""

    listings = TwoAFinderMarkdownParser().parse(
        page, "https://2afinder.com/produto/iphone-17-pro.md"
    )

    assert len(listings) == 2
    assert listings[0].price_amount == Decimal("7549.90")
    assert listings[0].seller_display_name == "LOJA_ALPHA · Mercado Livre"
    assert listings[0].attributes["model"] == "iphone_17_pro"
    assert listings[0].attributes["color"] == "Prateado"
    assert listings[0].condition == Condition.NEW
    assert listings[0].shipping.cost_minor_units == 0
    assert listings[1].condition == Condition.UNKNOWN
    assert listings[1].shipping.known is False
    assert all(item.url.endswith("iphone-17-pro.md") for item in listings)


def test_two_a_finder_caps_offer_table() -> None:
    rows = "\n".join(
        f"| {index} | R$ 7.000,00 | Mercado Livre | SELLER_{index} | novo | grátis | "
        "storage=1 TB · color=Preto | 2026-09-20T02:06:47.400Z | "
        f"`00000000-0000-0000-0000-{index:012d}` | "
        "https://2afinder.com/produto/galaxy-s26-ultra |"
        for index in range(1, MAX_AGGREGATE_OFFERS + 6)
    )
    page = (
        "# Galaxy S26 Ultra 1TB - Preto\n\n"
        f"Onde comprar Galaxy S26 Ultra: {MAX_AGGREGATE_OFFERS + 5} ofertas ativas "
        f"em {MAX_AGGREGATE_OFFERS + 5} lojas.\n\n{rows}"
    )

    listings = TwoAFinderMarkdownParser().parse(page, "https://2afinder.com/produto/item.md")

    assert len(listings) == MAX_AGGREGATE_OFFERS
    assert listings[0].attributes["storage_gb"] == "1024"


def test_two_a_finder_requires_explicit_active_offer_status() -> None:
    page = """# iPhone 17 Pro 256GB - Prateado

| 1 | R$ 7.549,90 | Mercado Livre | LOJA_ALPHA | novo | grátis | storage=256 GB | 2026-09-20T02:06:47.400Z | `cc672f0a-b759-4df6-bf80-d5c1e6c126cc` | https://2afinder.com/produto/iphone-17-pro |
"""

    with pytest.raises(ExtractionError, match="does not confirm active offers"):
        TwoAFinderMarkdownParser().parse(page, "https://2afinder.com/produto/iphone-17-pro.md")


def test_buscape_extracts_product_id_and_only_explicit_comparable_variants() -> None:
    parser = BuscapeOfferParser()
    page = '<script id="__NEXT_DATA__">{"prodId":13994200,"copy":{"prodId":13994200}}</script>'
    payload = {
        "hits": [
            {
                "offer_id": "offer-1",
                "name": "Smartphone Samsung Galaxy S26+ 256GB Violeta",
                "seller": {"id": "245", "name": "Webcontinental"},
                "sales_condition": {
                    "price": 8555.07,
                    "stock": 4,
                    "installments": [{"amount_months": 8}],
                },
                "condition": "NEW",
            },
            {
                "offer_id": "offer-2",
                "name": "Smartphone Samsung Galaxy S26+ 256GB",
                "seller": {"id": "22905", "name": "Magazine Luiza"},
                "sales_condition": {"price": 4599, "stock": 2},
                "condition": "NEW",
            },
        ]
    }

    assert parser.product_id(page) == "13994200"
    listings = parser.parse(json.dumps(payload), "https://www.buscape.com.br/celular/item")

    assert len(listings) == 1
    assert listings[0].seller_display_name == "Webcontinental"
    assert listings[0].attributes["model"] == "galaxy_s26_plus"
    assert listings[0].attributes["color"] == "Violeta"
    assert listings[0].payment_terms.installment_count == 8
    assert listings[0].payment_terms.price_basis.value == "cash"
    assert listings[0].availability == Availability.IN_STOCK


@pytest.mark.parametrize(
    ("stock", "expected"),
    [
        (None, Availability.UNKNOWN),
        (-1, Availability.OUT_OF_STOCK),
        (0, Availability.OUT_OF_STOCK),
        (1, Availability.IN_STOCK),
        (True, Availability.UNKNOWN),
    ],
)
def test_buscape_preserves_only_explicit_stock_status(stock, expected) -> None:
    payload = {
        "hits": [
            {
                "offer_id": "offer-1",
                "name": "Smartphone Samsung Galaxy S26+ 256GB Violeta",
                "seller": {"id": "245", "name": "Webcontinental"},
                "sales_condition": {"price": 8555.07, "stock": stock},
                "condition": "NEW",
            }
        ]
    }

    listing = BuscapeOfferParser().parse(
        json.dumps(payload), "https://www.buscape.com.br/celular/item"
    )[0]

    assert listing.availability == expected


def test_buscape_rejects_ambiguous_page_identity() -> None:
    parser = BuscapeOfferParser()

    with pytest.raises(ExtractionError, match="unambiguous product id"):
        parser.product_id('{"prodId":1,"nested":{"prodId":2}}')


def test_buscape_keeps_commercial_and_evidence_urls_distinct() -> None:
    product_url = "https://www.buscape.com.br/celular/item"
    api_url = "https://api-v1.zoom.com.br/sale-condition/v1/product/13994200"
    payload = json.dumps(
        {
            "hits": [
                {
                    "offer_id": "offer-1",
                    "name": "Smartphone Samsung Galaxy S26+ 256GB Violeta",
                    "seller": {"id": "245", "name": "Webcontinental"},
                    "sales_condition": {"price": 8555.07, "stock": 4},
                    "condition": "NEW",
                }
            ]
        }
    )
    response = TextResponse(
        url=api_url,
        request=Request(api_url),
        body=payload.encode(),
        encoding="utf-8",
    )
    spider = BuscapeSpider(source_id="source-1", run_id="run-1", base_url=product_url)

    item = next(spider.parse_offers(response, evidence_url=product_url))

    assert item["url"] == product_url
    assert item["evidence_url"] == api_url
    assert item["raw_html"] == payload


def _buscape_hit(index: int, *, color: str = "Violeta") -> dict:
    return {
        "offer_id": f"offer-{index}",
        "name": f"Smartphone Samsung Galaxy S26+ 256GB {color}",
        "seller": {"id": str(index), "name": f"Loja {index}"},
        "sales_condition": {"price": 8555.07 + index, "stock": 4},
        "condition": "NEW",
    }


def _buscape_offer_response(hits: list[dict], *, page: int) -> TextResponse:
    api_url = (
        "https://api-v1.zoom.com.br/sale-condition/v1/product/13994200"
        f"?order=DEFAULT&page={page}&pageSize={BUSCAPE_OFFER_PAGE_SIZE}"
    )
    body = json.dumps({"hits": hits}).encode()
    return TextResponse(url=api_url, request=Request(api_url), body=body, encoding="utf-8")


def test_buscape_offer_page_reports_raw_hit_count_not_kept_listings() -> None:
    # A page can be full of offers for other models and still be followed by
    # one holding a retailer we need, so fullness must key off raw hits.
    hits = [_buscape_hit(index) for index in range(BUSCAPE_OFFER_PAGE_SIZE - 1)]
    hits.append({"offer_id": "x", "name": "Capa de silicone", "seller": {}, "sales_condition": {}})

    page = BuscapeOfferParser().parse_page(
        json.dumps({"hits": hits}), "https://www.buscape.com.br/celular/item"
    )

    assert page.hit_count == BUSCAPE_OFFER_PAGE_SIZE
    assert len(page.listings) == BUSCAPE_OFFER_PAGE_SIZE - 1
    assert page.is_full


def test_buscape_follows_the_next_offer_page_while_pages_come_back_full() -> None:
    spider = BuscapeSpider(
        source_id="source-1",
        run_id="run-1",
        base_url="https://www.buscape.com.br/",
    )
    response = _buscape_offer_response(
        [_buscape_hit(index) for index in range(BUSCAPE_OFFER_PAGE_SIZE)], page=1
    )

    results = list(
        spider.parse_offers(
            response,
            evidence_url="https://www.buscape.com.br/celular/item",
            product_id="13994200",
            page=1,
        )
    )

    items = [result for result in results if not isinstance(result, Request)]
    followed = [result for result in results if isinstance(result, Request)]
    assert len(items) == BUSCAPE_OFFER_PAGE_SIZE
    assert len(followed) == 1
    assert "page=2" in followed[0].url
    assert followed[0].cb_kwargs["page"] == 2


def test_buscape_stops_paginating_on_a_short_page() -> None:
    spider = BuscapeSpider(
        source_id="source-1",
        run_id="run-1",
        base_url="https://www.buscape.com.br/",
    )
    response = _buscape_offer_response([_buscape_hit(1), _buscape_hit(2)], page=1)

    results = list(
        spider.parse_offers(
            response,
            evidence_url="https://www.buscape.com.br/celular/item",
            product_id="13994200",
            page=1,
        )
    )

    assert not [result for result in results if isinstance(result, Request)]


def test_buscape_never_paginates_past_the_configured_ceiling() -> None:
    spider = BuscapeSpider(
        source_id="source-1",
        run_id="run-1",
        base_url="https://www.buscape.com.br/",
    )
    response = _buscape_offer_response(
        [_buscape_hit(index) for index in range(BUSCAPE_OFFER_PAGE_SIZE)],
        page=BUSCAPE_MAX_OFFER_PAGES,
    )

    results = list(
        spider.parse_offers(
            response,
            evidence_url="https://www.buscape.com.br/celular/item",
            product_id="13994200",
            page=BUSCAPE_MAX_OFFER_PAGES,
        )
    )

    assert not [result for result in results if isinstance(result, Request)]


def test_zoom_skip_log_names_the_retailer_lost_to_an_unreadable_colour() -> None:
    # A retailer whose title does not name a catalog colour is dropped on
    # purpose — variant identity is never relaxed. The point here is that the
    # drop stops being invisible.
    offers = [
        {
            "@type": "Offer",
            "id": "offer-1",
            "name": "Apple iPhone 17 Pro Max (256 GB) - Prateado",
            "offeredBy": "Amazon",
            "price": "9757.11",
            "priceCurrency": "BRL",
        },
        {
            "@type": "Offer",
            "id": "offer-2",
            "name": "Apple iPhone 17 Pro Max 256 GB",
            "offeredBy": "Loja Sem Cor",
            "price": "9899.00",
            "priceCurrency": "BRL",
        },
    ]
    payload = {
        "@type": "Product",
        "name": "iPhone 17 Pro Max 256GB",
        "offers": {"@type": "AggregateOffer", "offers": offers},
    }
    skips = SkipLog()

    listings = extract_zoom_listings(
        _html(payload),
        "https://www.zoom.com.br/celular/celular-apple-iphone-17-pro-max-256gb",
        skips=skips,
    )

    assert [item.seller_display_name for item in listings] == ["Amazon"]
    assert len(skips.entries) == 1
    # The recorded title is what a human needs to grow _MODEL_COLOR_ALIASES,
    # and the reason has to name the field that failed.
    assert skips.entries[0].raw_title == "Apple iPhone 17 Pro Max 256 GB"
    assert "color" in skips.entries[0].reason


def test_zoom_spider_persists_each_skipped_entry_as_a_rejection() -> None:
    payload = {
        "@type": "Product",
        "name": "iPhone 17 Pro Max 256GB",
        "offers": {
            "@type": "AggregateOffer",
            "offers": [
                {
                    "@type": "Offer",
                    "id": "offer-1",
                    "name": "Apple iPhone 17 Pro Max (256 GB) - Prateado",
                    "offeredBy": "Amazon",
                    "price": "9757.11",
                    "priceCurrency": "BRL",
                },
                {
                    "@type": "Offer",
                    "id": "offer-2",
                    "name": "Apple iPhone 17 Pro Max 256 GB",
                    "offeredBy": "Loja Sem Cor",
                    "price": "9899.00",
                    "priceCurrency": "BRL",
                },
            ],
        },
    }
    url = "https://www.zoom.com.br/celular/celular-apple-iphone-17-pro-max-256gb"
    response = TextResponse(
        url=url, request=Request(url), body=_html(payload).encode(), encoding="utf-8"
    )
    spider = ZoomSpider(source_id="source-1", run_id="run-1", base_url="https://www.zoom.com.br/")

    results = list(spider.parse_product(response))

    rejections = [item for item in results if isinstance(item, ListingRejectedItem)]
    assert len(results) == 2
    assert len(rejections) == 1
    assert rejections[0]["stage"] == RejectionStage.EXTRACTION
    assert rejections[0]["url"] == url


def test_buscape_skip_log_reaches_the_spider_with_the_evidence_url() -> None:
    hits = [
        _buscape_hit(1),
        {
            "offer_id": "offer-2",
            "name": "Smartphone Samsung Galaxy S26+ 256GB",
            "seller": {"id": "9", "name": "Sem Cor"},
            "sales_condition": {"price": 4599, "stock": 2},
            "condition": "NEW",
        },
    ]
    evidence_url = "https://www.buscape.com.br/celular/item"
    spider = BuscapeSpider(
        source_id="source-1", run_id="run-1", base_url="https://www.buscape.com.br/"
    )

    results = list(
        spider.parse_offers(
            _buscape_offer_response(hits, page=1),
            evidence_url=evidence_url,
            product_id="13994200",
            page=1,
        )
    )

    rejections = [item for item in results if isinstance(item, ListingRejectedItem)]
    assert len(rejections) == 1
    # Buscapé's offers arrive from a different host than the commercial page;
    # the rejection has to point at the auditable evidence document.
    assert rejections[0]["url"] == evidence_url
