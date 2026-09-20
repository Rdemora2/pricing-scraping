"""Outbound request policy shared by every collector.

External adapters are locked to HTTPS and exact reviewed hosts.  The local
laboratory explicitly opts into private addresses and HTTP.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Iterable
from urllib.parse import urlsplit

from scrapy.exceptions import IgnoreRequest


class UnsafeOutboundUrl(ValueError):
    pass


Resolver = Callable[..., list[tuple]]


def validate_reference_url(
    url: str,
    *,
    allowed_hosts: Iterable[str],
    allow_private: bool = False,
) -> str:
    parts = urlsplit(url)
    hostname = (parts.hostname or "").lower().rstrip(".")
    allowed = {host.lower().rstrip(".") for host in allowed_hosts}
    schemes = {"http", "https"} if allow_private else {"https"}

    if parts.scheme not in schemes:
        raise UnsafeOutboundUrl("URL scheme is not allowed")
    if not hostname or hostname not in allowed:
        raise UnsafeOutboundUrl("URL host is not on the adapter allowlist")
    if parts.username is not None or parts.password is not None:
        raise UnsafeOutboundUrl("URL credentials are not allowed")
    if parts.port is not None and parts.port not in ({80, 8000} if allow_private else {443}):
        raise UnsafeOutboundUrl("URL port is not allowed")
    return hostname


def validate_outbound_url(
    url: str,
    *,
    allowed_hosts: Iterable[str],
    allow_private: bool = False,
    resolver: Resolver = socket.getaddrinfo,
) -> None:
    hostname = validate_reference_url(
        url,
        allowed_hosts=allowed_hosts,
        allow_private=allow_private,
    )
    parts = urlsplit(url)

    try:
        addresses = resolver(hostname, parts.port or (443 if parts.scheme == "https" else 80))
    except OSError as exc:
        raise UnsafeOutboundUrl("URL host could not be resolved") from exc
    if not addresses:
        raise UnsafeOutboundUrl("URL host did not resolve")

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        unsafe = not ip.is_global
        if unsafe and not allow_private:
            raise UnsafeOutboundUrl("URL resolved to a non-public address")


class OutboundPolicyMiddleware:
    def __init__(self, crawler):
        self._crawler = crawler

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def process_request(self, request):
        spider = self._crawler.spider
        try:
            validate_outbound_url(
                request.url,
                allowed_hosts=getattr(spider, "allowed_domains", ()),
                allow_private=bool(getattr(spider, "allow_private_network", False)),
            )
        except UnsafeOutboundUrl as exc:
            raise IgnoreRequest(str(exc)) from exc
        return None
