import json

import pytest
from httpx import ASGITransport, AsyncClient
from parsel import Selector

from lab.sources.store_a.app import app as store_a
from lab.sources.store_b.app import app as store_b


@pytest.mark.asyncio
async def test_store_a_serves_paginated_real_html_with_json_ld() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=store_a), base_url="http://store-a"
    ) as client:
        first_page = await client.get("/categoria/smartphones")
        second_page = await client.get("/categoria/smartphones?page=2")
        product = await client.get("/produto/nimbus-phone-x-128-preto")

    assert first_page.status_code == 200
    assert 'class="pagination-next"' in first_page.text
    assert second_page.status_code == 200
    assert 'class="pagination-next"' not in second_page.text
    assert product.status_code == 200
    assert 'type="application/ld+json"' in product.text
    assert "DADOS SINTÉTICOS" in product.text


@pytest.mark.asyncio
async def test_store_b_exposes_multiple_sellers_and_commercial_conditions() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=store_b), base_url="http://store-b"
    ) as client:
        category = await client.get("/c/celulares")
        offer = await client.get("/anuncio/nimbus-phone-x-128-preto-boreal")

    assert category.status_code == 200
    assert "Boreal Oficial" in category.text
    assert "Parceiro X Imports" in category.text
    assert offer.status_code == 200
    raw_json_ld = Selector(text=offer.text).css('script[type="application/ld+json"]::text').get()
    assert raw_json_ld is not None
    payload = json.loads(raw_json_ld)
    properties = {item["name"]: item["value"] for item in payload["offers"]["additionalProperty"]}
    assert properties["couponCode"] == "PIX10"
