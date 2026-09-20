from pricing_intel.discovery.urls import canonicalize


def test_canonicalize_removes_tracking_and_preserves_variant_parameters() -> None:
    url = "HTTPS://SHOP.EXAMPLE/phone/?utm_source=test&color=blue&storage=128&fbclid=abc"

    assert canonicalize(url) == "https://shop.example/phone?color=blue&storage=128"


def test_canonicalize_sorts_query_and_removes_fragment() -> None:
    assert (
        canonicalize("https://shop.example/item?z=2&a=1#details")
        == "https://shop.example/item?a=1&z=2"
    )
