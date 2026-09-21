import os

import httpx
import pytest

API_BASE_URL = os.getenv("API_BASE_URL")
pytestmark = pytest.mark.skipif(
    API_BASE_URL is None,
    reason="API_BASE_URL is required for container integration tests",
)


def test_containerized_api_exposes_seeded_catalog_and_intelligence() -> None:
    assert API_BASE_URL is not None
    with httpx.Client(base_url=API_BASE_URL, timeout=10) as client:
        health = client.get("/health")
        products_response = client.get("/products")

        assert health.status_code == 200
        assert health.json() == {"status": "ok"}
        assert products_response.status_code == 200

        products = products_response.json()
        iphone = next(item for item in products if item["name"] == "Apple iPhone 17 Pro")
        intelligence = client.get(f"/products/{iphone['id']}/intelligence")

        assert intelligence.status_code == 200
        payload = intelligence.json()
        assert payload["product_id"] == iphone["id"]
        assert payload["catalog_variant_count"] > 0
        assert payload["sample_status"] in {"no_data", "limited", "developing", "strong"}


def test_containerized_openapi_documents_the_intelligence_contract() -> None:
    assert API_BASE_URL is not None
    response = httpx.get(f"{API_BASE_URL}/openapi.json", timeout=10)

    assert response.status_code == 200
    assert "/products/{product_id}/intelligence" in response.json()["paths"]
