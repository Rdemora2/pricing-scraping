from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from itemadapter import ItemAdapter

from pricing_intel.collection.items import ListingItem
from pricing_intel.collection.pipelines import PostgresPipeline
from pricing_intel.domain.enums import Availability, Condition, PriceBasis
from pricing_intel.domain.models import PaymentTerms, ShippingTerms


def test_pipeline_persists_offer_reference_and_evidence_document_separately() -> None:
    pipeline = PostgresPipeline(MagicMock())
    pipeline.db = MagicMock()
    pipeline.db.get_or_create_seller.return_value = SimpleNamespace(id="seller-1")
    pipeline.db.upsert_offer.return_value = SimpleNamespace(id="offer-1")
    pipeline.db.upsert_discovered_page.return_value = SimpleNamespace(id="page-1")
    product_url = "https://www.buscape.com.br/celular/item"
    api_url = "https://api-v1.zoom.com.br/sale-condition/v1/product/13994200"
    item = ListingItem(
        source_id="source-1",
        run_id="run-1",
        url=product_url,
        canonical_url=product_url,
        evidence_url=api_url,
        evidence_canonical_url=api_url,
        http_status=200,
        raw_html='{"hits": []}',
        extractor_name="buscape_public_product_offers",
        extractor_version="1.0.0",
        external_listing_id="offer-1",
        seller_external_id="seller-1",
        seller_display_name="Loja",
        raw_title="Smartphone Samsung Galaxy S26+ 256GB Violeta",
        gtin=None,
        attributes={
            "brand": "samsung",
            "model": "galaxy_s26_plus",
            "region": "br",
            "storage_gb": "256",
            "color": "Violeta",
        },
        price_amount=Decimal("8555.07"),
        currency="BRL",
        availability=Availability.IN_STOCK,
        condition=Condition.NEW,
        payment_terms=PaymentTerms(price_basis=PriceBasis.CASH),
        shipping=ShippingTerms(known=False),
    )

    pipeline._handle_listing(ItemAdapter(item), MagicMock())

    assert pipeline.db.upsert_offer.call_args.kwargs["url"] == product_url
    assert pipeline.db.record_evidence.call_args.kwargs["url"] == api_url
    assert pipeline.db.upsert_discovered_page.call_args.kwargs["url"] == api_url
