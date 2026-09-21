from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from pricing_intel.api.schemas import CollectionRequest
from pricing_intel.discovery.service import _manual_idempotency_key


def test_collection_request_requires_a_product() -> None:
    with pytest.raises(ValidationError):
        CollectionRequest.model_validate({})


def test_collection_idempotency_is_scoped_by_source_and_product() -> None:
    source_id = uuid4()
    first_product_id = uuid4()
    second_product_id = uuid4()
    now = datetime(2026, 9, 21, 12, 34, tzinfo=UTC)

    first = _manual_idempotency_key(source_id, product_id=first_product_id, now=now)
    replay = _manual_idempotency_key(source_id, product_id=first_product_id, now=now)
    second = _manual_idempotency_key(source_id, product_id=second_product_id, now=now)

    assert first == replay
    assert first != second
