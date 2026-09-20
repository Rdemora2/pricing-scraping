"""Shared HTML/JSON-LD rendering for the two simulated lab stores.

Every page is genuinely served over HTTP and genuinely fetched by the
Scrapy spiders — this module only avoids duplicating markup boilerplate
between the two stores' otherwise deliberately different templates.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass

SYNTHETIC_BANNER = (
    '<p class="synthetic-banner">DADOS SINTÉTICOS — loja simulada para fins de '
    "demonstração, não é uma loja real.</p>"
)


@dataclass(frozen=True, slots=True)
class ListingFixture:
    slug: str
    title: str
    gtin: str
    attributes: dict[str, str]
    seller_name: str
    price: str
    currency: str
    availability_uri: str
    condition_uri: str
    offer_properties: dict[str, str]


def render_json_ld(listing: ListingFixture) -> str:
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
            "priceCurrency": listing.currency,
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


def render_product_page(listing: ListingFixture, *, store_name: str) -> str:
    title = html.escape(listing.title)
    seller = html.escape(listing.seller_name)
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>{title} — {html.escape(store_name)}</title>
<script type="application/ld+json">{render_json_ld(listing)}</script>
</head>
<body>
{SYNTHETIC_BANNER}
<h1>{title}</h1>
<p class="seller">Vendido por: {seller}</p>
<p class="price">R$ {html.escape(listing.price)}</p>
</body>
</html>"""


def render_category_page(
    *,
    store_name: str,
    listing_links: list[tuple[str, str]],
    product_link_class: str,
    next_link_html: str | None = None,
) -> str:
    items = "\n".join(
        f'<li><a class="{html.escape(product_link_class)}" href="{html.escape(href)}">'
        f"{html.escape(title)}</a></li>"
        for href, title in listing_links
    )
    return f"""<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>{html.escape(store_name)} — Smartphones</title></head>
<body>
{SYNTHETIC_BANNER}
<h1>{html.escape(store_name)}</h1>
<ul>
{items}
</ul>
{next_link_html or ""}
</body>
</html>"""
