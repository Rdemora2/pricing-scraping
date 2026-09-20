"""Mercado Boreal (lab) — a simulated marketplace with multiple sellers.

Self-contained on purpose (see store_a/app.py's docstring). Deliberately
uses different markup/selectors than store_a to exercise the
adapter-per-source boundary in the spiders.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

STORE_NAME = "Mercado Boreal (lab)"

SYNTHETIC_BANNER = (
    '<p class="synthetic-banner">DADOS SINTÉTICOS — marketplace simulado para fins de '
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
            slug="nimbus-phone-x-128-preto-boreal",
            title="Nimbus Phone X 128GB Preto",
            gtin="7891234500018",
            attributes={"storage_gb": "128", "color": "Preto"},
            seller_name="Boreal Oficial",
            price="3699.00",
            availability_uri="https://schema.org/InStock",
            condition_uri="https://schema.org/NewCondition",
            offer_properties={
                "installmentCount": "12",
                "cashDiscountPct": "10",
                "couponCode": "PIX10",
                "shippingKnown": "true",
                "shippingCostMinorUnits": "0",
                "freeShippingThresholdMinorUnits": "0",
            },
        ),
        Listing(
            slug="nimbus-phone-x-128-preto-parceirox",
            title="Nimbus Phone X 128GB Preto",
            gtin="7891234500018",
            attributes={"storage_gb": "128", "color": "Preto"},
            seller_name="Parceiro X Imports",
            price="3599.00",
            availability_uri="https://schema.org/OutOfStock",
            condition_uri="https://schema.org/NewCondition",
            offer_properties={"shippingKnown": "false"},
        ),
        Listing(
            slug="nimbus-phone-x-128-azul-boreal",
            title="Nimbus Phone X 128GB Azul",
            gtin="7891234500032",
            attributes={"storage_gb": "128", "color": "Azul"},
            seller_name="Boreal Oficial",
            price="3649.00",
            availability_uri="https://schema.org/InStock",
            condition_uri="https://schema.org/NewCondition",
            offer_properties={"installmentCount": "12", "shippingKnown": "false"},
        ),
    ]
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


@app.get("/c/celulares", response_class=HTMLResponse)
async def category() -> str:
    items = "\n".join(
        f'<li><a class="offer-tile" href="/anuncio/{listing.slug}">'
        f"{html.escape(listing.title)} — {html.escape(listing.seller_name)}</a></li>"
        for listing in LISTINGS.values()
    )
    return f"""<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>{STORE_NAME} — Celulares</title></head>
<body>
{SYNTHETIC_BANNER}
<h1>{STORE_NAME}</h1>
<ul>
{items}
</ul>
</body>
</html>"""


@app.get("/anuncio/{slug}", response_class=HTMLResponse)
async def listing_page(slug: str) -> str:
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
