import socket

import pytest

from pricing_intel.collection.network_policy import UnsafeOutboundUrl, validate_outbound_url


def resolver_for(ip: str):
    def resolve(host: str, port: int):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]

    return resolve


def test_external_adapter_accepts_reviewed_https_public_host() -> None:
    validate_outbound_url(
        "https://www.iplace.com.br/produto",
        allowed_hosts=["www.iplace.com.br"],
        resolver=resolver_for("93.184.216.34"),
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://www.iplace.com.br/produto",
        "https://attacker.example/produto",
        "https://user@www.iplace.com.br/produto",
        "https://www.iplace.com.br:8443/produto",
    ],
)
def test_external_adapter_rejects_urls_outside_policy(url: str) -> None:
    with pytest.raises(UnsafeOutboundUrl):
        validate_outbound_url(
            url,
            allowed_hosts=["www.iplace.com.br"],
            resolver=resolver_for("93.184.216.34"),
        )


def test_external_adapter_rejects_private_dns_answer() -> None:
    with pytest.raises(UnsafeOutboundUrl, match="non-public"):
        validate_outbound_url(
            "https://www.iplace.com.br/produto",
            allowed_hosts=["www.iplace.com.br"],
            resolver=resolver_for("127.0.0.1"),
        )


def test_lab_adapter_explicitly_allows_private_http() -> None:
    validate_outbound_url(
        "http://lab-store-a:8000/produto",
        allowed_hosts=["lab-store-a"],
        allow_private=True,
        resolver=resolver_for("172.20.0.3"),
    )
