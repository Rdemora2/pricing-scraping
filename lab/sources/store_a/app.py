"""Loja Aurora (lab) — a simulated store standing in for a real one.

Self-contained on purpose: this represents an external system our
platform does not own, so it does not share code with the other lab
store or with the pricing_intel package. It serves genuine HTML over
HTTP — the Scrapy spider fetches it like it would any real site.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

STORE_NAME = "Loja Aurora (lab)"

SYNTHETIC_BANNER = (
    '<p class="synthetic-banner">DADOS SINTÉTICOS — loja simulada para fins de '
    "demonstração, não é uma loja real.</p>"
)


@dataclass(frozen=True, slots=True)
class Listing:
    slug: str
    title: str
    gtin: str
    attributes: dict[str, str]
    seller_name: str
    price: str
    availability_uri: str
    condition_uri: str
    offer_properties: dict[str, str]


LISTINGS = {
    listing.slug: listing
    for listing in [
        Listing(
            slug="nimbus-phone-x-128-preto",
            title="Nimbus Phone X 128GB Preto",
            gtin="7891234500018",
            attributes={"storage_gb": "128", "color": "Preto"},
            seller_name="Aurora Eletrônicos",
            price="3499.00",
            availability_uri="https://schema.org/InStock",
            condition_uri="https://schema.org/NewCondition",
            offer_properties={"installmentCount": "10", "shippingKnown": "false"},
        ),
        Listing(
            slug="nimbus-phone-x-128-preto-seminovo",
            title="Nimbus Phone X 128GB Preto (Seminovo)",
            gtin="7891234500018",
            attributes={"storage_gb": "128", "color": "Preto"},
            seller_name="Aurora Eletrônicos",
            price="2899.00",
            availability_uri="https://schema.org/InStock",
            condition_uri="https://schema.org/UsedCondition",
            offer_properties={"installmentCount": "6", "shippingKnown": "false"},
        ),
        Listing(
            slug="nimbus-phone-x-256-preto",
            title="Nimbus Phone X 256GB Preto",
            gtin="7891234500025",
            attributes={"storage_gb": "256", "color": "Preto"},
            seller_name="Aurora Eletrônicos",
            price="4199.00",
            availability_uri="https://schema.org/InStock",
            condition_uri="https://schema.org/NewCondition",
            offer_properties={"installmentCount": "10", "shippingKnown": "false"},
        ),
    ]
}

PAGES = {
    1: ["nimbus-phone-x-128-preto", "nimbus-phone-x-128-preto-seminovo"],
    2: ["nimbus-phone-x-256-preto"],
}

app = FastAPI(title=STORE_NAME)


def _render_json_ld(listing: Listing) -> str:
    payload = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": listing.title,
        "gtin13": listing.gtin,
        "brand": {"@type": "Brand", "name": "Nimbus"},
        "additionalProperty": [
            {"@type": "PropertyValue", "name": key, "value": value}
            for key, value in listing.attributes.items()
        ],
        "offers": {
            "@type": "Offer",
            "price": listing.price,
            "priceCurrency": "BRL",
            "availability": listing.availability_uri,
            "itemCondition": listing.condition_uri,
            "seller": {"@type": "Organization", "name": listing.seller_name},
            "additionalProperty": [
                {"@type": "PropertyValue", "name": key, "value": value}
                for key, value in listing.offer_properties.items()
            ],
        },
    }
    return json.dumps(payload, ensure_ascii=False)


@app.get("/categoria/smartphones", response_class=HTMLResponse)
async def category(page: int = Query(default=1, ge=1, le=2)) -> str:
    slugs = PAGES[page]
    items = "\n".join(
        f'<li><a class="product-card" href="/produto/{slug}">'
        f"{html.escape(LISTINGS[slug].title)}</a></li>"
        for slug in slugs
    )
    next_link = (
        '<a class="pagination-next" href="/categoria/smartphones?page=2">Próxima página</a>'
        if page == 1
        else ""
    )
    return f"""<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>{STORE_NAME} — Smartphones</title></head>
<body>
{SYNTHETIC_BANNER}
<h1>{STORE_NAME}</h1>
<ul>
{items}
</ul>
{next_link}
</body>
</html>"""


@app.get("/produto/{slug}", response_class=HTMLResponse)
async def product(slug: str) -> str:
    listing = LISTINGS[slug]
    title = html.escape(listing.title)
    seller = html.escape(listing.seller_name)
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>{title} — {STORE_NAME}</title>
<script type="application/ld+json">{_render_json_ld(listing)}</script>
</head>
<body>
{SYNTHETIC_BANNER}
<h1>{title}</h1>
<p class="seller">Vendido por: {seller}</p>
<p class="price">R$ {html.escape(listing.price)}</p>
</body>
</html>"""
