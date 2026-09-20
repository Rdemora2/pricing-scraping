from pricing_intel.api.routers.collection import _is_allowed_local_origin


def test_accepts_loopback_origins_on_any_local_port() -> None:
    assert _is_allowed_local_origin("http://localhost:3000")
    assert _is_allowed_local_origin("http://127.0.0.1:5173")


def test_rejects_non_local_or_ambiguous_origins() -> None:
    assert not _is_allowed_local_origin("https://attacker.example")
    assert not _is_allowed_local_origin("http://localhost.attacker.example:3000")
    assert not _is_allowed_local_origin("http://user@localhost:3000")
    assert not _is_allowed_local_origin("null")
