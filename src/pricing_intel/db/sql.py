"""Raw SQL shared between the async app (FastAPI, Procrastinate tasks) and
the synchronous Scrapy item pipeline.

Keeping the statements here means both execution styles run the exact
same SQL — only the connection/cursor machinery around them differs.
"""

LIST_ENABLED_SOURCES = """
    SELECT id, name, base_url, kind, status, adapter_name, created_at
    FROM source
    WHERE status = 'enabled'
    ORDER BY name
"""

LIST_SOURCES = """
    SELECT id, name, base_url, kind, status, adapter_name, created_at
    FROM source
    ORDER BY
        CASE status WHEN 'enabled' THEN 0 WHEN 'candidate' THEN 1 ELSE 2 END,
        name
"""

GET_SOURCE_BY_ID = """
    SELECT id, name, base_url, kind, status, adapter_name, created_at
    FROM source
    WHERE id = %(source_id)s
"""

UPSERT_DISCOVERED_PAGE = """
    INSERT INTO discovered_page (source_id, url, canonical_url, page_type, status)
    VALUES (%(source_id)s, %(url)s, %(canonical_url)s, %(page_type)s, %(status)s)
    ON CONFLICT (source_id, canonical_url)
    DO UPDATE SET last_seen_at = now()
    RETURNING id, source_id, url, canonical_url, page_type, status,
              first_discovered_at, last_seen_at
"""

LIST_PENDING_PAGES = """
    SELECT id, source_id, url, canonical_url, page_type, status,
           first_discovered_at, last_seen_at
    FROM discovered_page
    WHERE source_id = %(source_id)s AND status = 'pending' AND page_type = 'product'
    ORDER BY first_discovered_at
"""

MARK_PAGE_STATUS = """
    UPDATE discovered_page SET status = %(status)s
    WHERE id = %(page_id)s
"""

CREATE_RUN = """
    INSERT INTO collection_run (source_id, trigger, idempotency_key)
    VALUES (%(source_id)s, %(trigger)s, %(idempotency_key)s)
    ON CONFLICT (idempotency_key) DO UPDATE SET idempotency_key = EXCLUDED.idempotency_key
    RETURNING id, source_id, trigger, status, idempotency_key, started_at,
              finished_at, stats, failure_reason, created_at
"""

GET_RUN = """
    SELECT id, source_id, trigger, status, idempotency_key, started_at,
           finished_at, stats, failure_reason, created_at
    FROM collection_run
    WHERE id = %(run_id)s
"""

MARK_RUN_RUNNING = """
    UPDATE collection_run SET status = 'running', started_at = now()
    WHERE id = %(run_id)s AND status = 'pending'
"""

FINISH_RUN = """
    UPDATE collection_run
    SET status = %(status)s, finished_at = now(), stats = %(stats)s,
        failure_reason = %(failure_reason)s
    WHERE id = %(run_id)s
"""

COUNT_PENDING_PRODUCT_PAGES = """
    SELECT COUNT(*) FROM discovered_page
    WHERE source_id = %(source_id)s AND page_type = 'product' AND status = 'pending'
"""

COUNT_RUN_STATS = """
    SELECT
        (SELECT COUNT(*) FROM price_observation WHERE collection_run_id = %(run_id)s) AS offers_observed,
        (SELECT COUNT(*) FROM evidence WHERE collection_run_id = %(run_id)s) AS evidence_recorded,
        (SELECT COUNT(*) FROM listing_rejection
          WHERE collection_run_id = %(run_id)s AND stage = 'access') AS listings_rejected_access,
        (SELECT COUNT(*) FROM listing_rejection
          WHERE collection_run_id = %(run_id)s AND stage = 'extraction') AS listings_rejected_extraction,
        (SELECT COUNT(*) FROM listing_rejection
          WHERE collection_run_id = %(run_id)s AND stage = 'matching') AS listings_rejected_matching
"""

INSERT_LISTING_REJECTION = """
    INSERT INTO listing_rejection
        (collection_run_id, source_id, stage, reason, url, raw_title, attributes)
    VALUES
        (%(collection_run_id)s, %(source_id)s, %(stage)s, %(reason)s, %(url)s,
         %(raw_title)s, %(attributes)s)
"""

GET_OR_CREATE_SELLER = """
    INSERT INTO seller (source_id, external_id, display_name)
    VALUES (%(source_id)s, %(external_id)s, %(display_name)s)
    ON CONFLICT (source_id, external_id)
    DO UPDATE SET display_name = EXCLUDED.display_name
    RETURNING id, source_id, external_id, display_name
"""

FIND_VARIANT_BY_GTIN = """
    SELECT id, product_id, attributes, attributes_signature, gtin
    FROM variant
    WHERE gtin = %(gtin)s
"""

FIND_VARIANT_BY_SIGNATURE = """
    SELECT id, product_id, attributes, attributes_signature, gtin
    FROM variant
    WHERE attributes_signature = %(signature)s
"""

LIST_VARIANTS_FOR_PRODUCT = """
    SELECT id, product_id, attributes, attributes_signature, gtin
    FROM variant
    WHERE product_id = %(product_id)s
    ORDER BY attributes_signature
"""

GET_VARIANT = """
    SELECT id, product_id, attributes, attributes_signature, gtin
    FROM variant
    WHERE id = %(variant_id)s
"""

LIST_PRODUCTS = """
    SELECT id, name, brand, category, created_at
    FROM product
    ORDER BY name
"""

GET_PRODUCT = """
    SELECT id, name, brand, category, created_at
    FROM product
    WHERE id = %(product_id)s
"""

UPSERT_OFFER = """
    INSERT INTO offer (source_id, seller_id, external_listing_id, url, raw_title)
    VALUES (%(source_id)s, %(seller_id)s, %(external_listing_id)s, %(url)s, %(raw_title)s)
    ON CONFLICT (source_id, external_listing_id)
    DO UPDATE SET last_seen_at = now(), raw_title = EXCLUDED.raw_title, url = EXCLUDED.url
    RETURNING id, source_id, seller_id, external_listing_id, url, raw_title,
              first_seen_at, last_seen_at, last_price_minor_units,
              last_price_currency, last_verified_at, last_changed_at
"""

INSERT_PRICE_OBSERVATION = """
    INSERT INTO price_observation
        (offer_id, collection_run_id, observed_at, price_minor_units, currency,
         availability, condition, payment_terms, shipping)
    VALUES
        (%(offer_id)s, %(collection_run_id)s, %(observed_at)s, %(price_minor_units)s,
         %(currency)s, %(availability)s, %(condition)s, %(payment_terms)s, %(shipping)s)
    ON CONFLICT (offer_id, collection_run_id) DO NOTHING
    RETURNING id, offer_id, collection_run_id, observed_at, price_minor_units,
              currency, availability, condition, payment_terms, shipping
"""

GET_OFFER = """
    SELECT id, source_id, seller_id, external_listing_id, url, raw_title,
           first_seen_at, last_seen_at, last_price_minor_units,
           last_price_currency, last_verified_at, last_changed_at
    FROM offer
    WHERE id = %(offer_id)s
"""

UPDATE_OFFER_PRICE_SUMMARY = """
    UPDATE offer
    SET last_verified_at = %(observed_at)s,
        last_changed_at = CASE
            WHEN last_price_minor_units IS DISTINCT FROM %(price_minor_units)s
            THEN %(observed_at)s
            ELSE last_changed_at
        END,
        last_price_minor_units = %(price_minor_units)s,
        last_price_currency = %(currency)s
    WHERE id = %(offer_id)s
      AND (last_verified_at IS NULL OR last_verified_at <= %(observed_at)s)
"""

DEACTIVATE_ACTIVE_MATCHES = """
    UPDATE offer_match SET is_active = false
    WHERE offer_id = %(offer_id)s AND is_active
"""

INSERT_OFFER_MATCH = """
    INSERT INTO offer_match (offer_id, variant_id, confidence, method, rationale, is_active)
    VALUES (%(offer_id)s, %(variant_id)s, %(confidence)s, %(method)s, %(rationale)s, true)
    RETURNING id, offer_id, variant_id, confidence, method, rationale, matched_at, is_active
"""

GET_ACTIVE_MATCH = """
    SELECT id, offer_id, variant_id, confidence, method, rationale, matched_at, is_active
    FROM offer_match
    WHERE offer_id = %(offer_id)s AND is_active
"""

INSERT_EVIDENCE = """
    INSERT INTO evidence
        (collection_run_id, source_id, offer_id, evidence_type, url, http_status,
         extractor_name, extractor_version, content_hash, raw_excerpt, fetched_at)
    VALUES
        (%(collection_run_id)s, %(source_id)s, %(offer_id)s, %(evidence_type)s, %(url)s,
         %(http_status)s, %(extractor_name)s, %(extractor_version)s, %(content_hash)s,
         %(raw_excerpt)s, %(fetched_at)s)
    RETURNING id, collection_run_id, source_id, offer_id, evidence_type, url, http_status,
              extractor_name, extractor_version, content_hash, raw_excerpt, fetched_at
"""

PRUNE_EVIDENCE = """
    DELETE FROM evidence
    WHERE source_id = %(source_id)s
      AND url = %(url)s
      AND collection_run_id NOT IN (
          SELECT collection_run_id
          FROM evidence
          WHERE source_id = %(source_id)s AND url = %(url)s
          GROUP BY collection_run_id
          ORDER BY max(fetched_at) DESC
          LIMIT %(keep)s
      )
"""

LATEST_OBSERVATION_SNAPSHOTS_FOR_VARIANT = """
    SELECT DISTINCT ON (o.id)
        o.id AS offer_id,
        s.name AS source_name,
        sl.display_name AS seller_name,
        o.url AS url,
        po.condition AS condition,
        po.availability AS availability,
        po.price_minor_units AS price_minor_units,
        po.currency AS currency,
        po.observed_at AS observed_at,
        po.payment_terms AS payment_terms,
        po.shipping AS shipping
    FROM offer_match om
    JOIN offer o ON o.id = om.offer_id
    JOIN source s ON s.id = o.source_id
    JOIN seller sl ON sl.id = o.seller_id
    JOIN price_observation po ON po.offer_id = o.id
    WHERE om.variant_id = %(variant_id)s AND om.is_active
    ORDER BY o.id, po.observed_at DESC
"""

LATEST_OBSERVATION_SNAPSHOTS_FOR_PRODUCT = """
    SELECT DISTINCT ON (om.variant_id, o.id)
        om.variant_id AS variant_id,
        o.id AS offer_id,
        s.name AS source_name,
        sl.display_name AS seller_name,
        o.url AS url,
        po.condition AS condition,
        po.availability AS availability,
        po.price_minor_units AS price_minor_units,
        po.currency AS currency,
        po.observed_at AS observed_at,
        po.payment_terms AS payment_terms,
        po.shipping AS shipping
    FROM variant v
    JOIN offer_match om ON om.variant_id = v.id AND om.is_active
    JOIN offer o ON o.id = om.offer_id
    JOIN source s ON s.id = o.source_id
    JOIN seller sl ON sl.id = o.seller_id
    JOIN price_observation po ON po.offer_id = o.id
    WHERE v.product_id = %(product_id)s
    ORDER BY om.variant_id, o.id, po.observed_at DESC
"""

COUNT_SOURCES_FOR_VARIANT = """
    SELECT COUNT(DISTINCT o.source_id) AS source_count
    FROM offer_match om
    JOIN offer o ON o.id = om.offer_id
    WHERE om.variant_id = %(variant_id)s AND om.is_active
"""
