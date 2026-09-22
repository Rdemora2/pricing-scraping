from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from itemadapter import ItemAdapter

from pricing_intel.collection.items import ListingItem, ListingRejectedItem
from pricing_intel.collection.pipelines import PostgresPipeline
from pricing_intel.domain.enums import Availability, Condition, PriceBasis, RejectionStage
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


def test_pipeline_persists_a_rejected_listing_as_collection_loss() -> None:
    pipeline = PostgresPipeline(MagicMock())
    pipeline.db = MagicMock()
    item = ListingRejectedItem(
        source_id="source-1",
        run_id="run-1",
        stage=RejectionStage.ACCESS,
        reason="Carrefour product page refused with HTTP 403",
        url="https://www.carrefour.com.br/produto/example",
        raw_title="",
        attributes={},
    )

    pipeline.process_item(item)

    kwargs = pipeline.db.record_listing_rejection.call_args.kwargs
    assert kwargs["stage"] == RejectionStage.ACCESS
    assert kwargs["collection_run_id"] == "run-1"
    assert "403" in kwargs["reason"]
    # A rejection is not an offer: nothing may reach the offer tables.
    pipeline.db.upsert_offer.assert_not_called()
    pipeline.db.record_price_observation.assert_not_called()


def test_pipeline_records_why_an_offer_matched_no_canonical_variant() -> None:
    pipeline = PostgresPipeline(MagicMock())
    pipeline.db = MagicMock()
    pipeline.db.find_variant_by_signature.return_value = None
    pipeline.db.find_variant_by_gtin.return_value = None
    attributes = {
        "brand": "samsung",
        "model": "galaxy_s26_plus",
        "region": "br",
        "storage_gb": "256",
        "color": "Cor Inexistente",
    }
    adapter = ItemAdapter(
        ListingItem(
            source_id="source-1",
            run_id="run-1",
            raw_title="Smartphone Samsung Galaxy S26+ 256GB Cor Inexistente",
            gtin=None,
            attributes=attributes,
        )
    )

    pipeline._match_offer(adapter, offer_id="offer-1", spider=MagicMock(), url="https://x/p")

    kwargs = pipeline.db.record_listing_rejection.call_args.kwargs
    assert kwargs["stage"] == RejectionStage.MATCHING
    assert kwargs["attributes"] == attributes
    assert "matches no canonical variant" in kwargs["reason"]
    pipeline.db.set_offer_match.assert_not_called()
