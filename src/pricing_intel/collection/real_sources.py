"""Pure extractors for reviewed Brazilian retailer product pages.

Each adapter consumes structured data already published by the retailer.  It
does not attempt to defeat access controls, CAPTCHA or browser challenges.
"""

from __future__ import annotations

import html as html_module
import json
import re
import unicodedata
from contextlib import suppress
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from urllib.parse import unquote, urljoin, urlsplit

from parsel import Selector

from pricing_intel.catalog import CATALOG_PRODUCTS, CatalogProduct
from pricing_intel.collection.extraction import (
    ExtractionError,
    iter_product_json_ld,
    parse_availability,
    parse_condition,
)
from pricing_intel.domain.enums import Availability, Condition, PriceBasis
from pricing_intel.domain.models import PaymentTerms, ShippingTerms

MAX_PRODUCT_VARIANTS = 24
# Aggregator product pages publish one entry per competing retailer, and the
# comparison keeps at most one observation per retailer (see
# pricing/analysis.py::compare_variant) — so this ceiling caps observable
# retailer depth directly. It sat at 20 and was demonstrably binding: the
# INC-09 Buscapé run returned exactly 20 offers for the Galaxy S25 Ultra,
# the page size it was asking for. 60 clears the realistic Brazilian
# smartphone retailer population while still bounding a hostile payload.
MAX_AGGREGATE_OFFERS = 60

# Buscapé serves its public offer document in fixed-size pages. Reading only
# page 1 is what made the cap above bind; a bounded number of extra pages is
# the only way to observe the retailers listed after the first twenty.
BUSCAPE_OFFER_PAGE_SIZE = 20
BUSCAPE_MAX_OFFER_PAGES = 3

# Upper bound on skipped entries retained per extraction. The point of the
# skip log is to size a loss and name its cause, not to mirror a whole page.
MAX_RECORDED_SKIPS = 50


@dataclass(frozen=True, slots=True)
class SkippedEntry:
    raw_title: str
    reason: str


@dataclass(slots=True)
class SkipLog:
    """Collects the entries an extractor dropped, for the caller to persist.

    Aggregator pages are where retailer depth comes from, so an entry dropped
    there is a retailer that silently never reaches the comparison. Extractors
    stay fail-closed exactly as before; this only makes the cost of failing
    closed observable instead of invisible.
    """

    entries: list[SkippedEntry] = field(default_factory=list)

    def record(self, raw_title: str, reason: str) -> None:
        if len(self.entries) >= MAX_RECORDED_SKIPS:
            return
        self.entries.append(SkippedEntry(raw_title=raw_title[:300], reason=reason))


# Highest color count in the live catalog is 6 (Galaxy S26 family, see
# scripts/seed_catalog.py); +2 headroom for near-term catalog growth. A
# capacity search with more color matches than this silently drops the
# rest — it previously sat at 3, which quietly capped every catalog device
# with 4+ colors (15 of 18) to the first 3 colors search results happened
# to return.
MAX_SEARCH_RESULTS_PER_CAPACITY = 8

# Sitemap indexes list many documents; only a bounded number is followed, and
# only those whose own URL says they carry products. A retailer sitemap is a
# map of the whole store, and crawling it wholesale is neither polite nor
# useful when the target is one canonical device.
SITEMAP_MAX_DOCUMENTS = 5


@dataclass(frozen=True, slots=True)
class RetailListing:
    external_listing_id: str
    url: str
    raw_title: str
    gtin: str | None
    attributes: dict[str, str]
    seller_external_id: str
    seller_display_name: str
    price_amount: Decimal
    currency: str
    availability: Availability
    condition: Condition
    payment_terms: PaymentTerms
    shipping: ShippingTerms


_STORAGE = re.compile(
    r"(?:capacidade|armazenamento|mem[oó]ria)?\s*:?[ ]*(128|256|512|1024|2048)\s*gb",
    re.I,
)
_MODEL = re.compile(r"modelo\s*:?[ ]*([A-Z0-9/\-]+)", re.I)
_COLOR = re.compile(r"cor\s*:?[ ]*([\wÀ-ÿ\- ]+?)(?:<|\||,|$)", re.I)
_INSTALLMENTS = re.compile(r"\b(\d{1,2})\s*x\b", re.I)
_CONDITIONAL_TERMS = {
    "cartao da loja": "cartão da loja",
    "cartao iplace": "cartão iPlace",
    "clube": "programa ou clube",
    "trade-in": "troca de aparelho",
    "trade in": "troca de aparelho",
    "troca smart": "troca de aparelho",
    "cupom": "cupom",
    "assinante": "assinatura",
    "cliente ouro": "programa de fidelidade",
}


def _offer(product: dict) -> dict:
    offers = product.get("offers")
    if isinstance(offers, list):
        offers = next((item for item in offers if isinstance(item, dict)), None)
    if not isinstance(offers, dict):
        raise ExtractionError("Product JSON-LD is missing an Offer")
    return offers


def _price(offer: dict) -> Decimal:
    raw = offer.get("price", offer.get("lowPrice"))
    try:
        price = Decimal(str(raw))
    except (InvalidOperation, TypeError) as exc:
        raise ExtractionError(f"unparseable retail price: {raw!r}") from exc
    if not price.is_finite() or price <= 0:
        raise ExtractionError("retail price must be finite and positive")
    return price


def _fold_text(value: str) -> str:
    value = value.replace("+", " plus ")
    without_marks = "".join(
        character
        for character in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", " ", without_marks).strip()


def _identity_aliases(product: CatalogProduct) -> tuple[str, ...]:
    aliases = {
        product.name,
        re.sub(rf"^{re.escape(product.brand)}\s+", "", product.name, flags=re.I),
    }
    if "+" in product.name:
        aliases.update(alias.replace("+", " Plus") for alias in tuple(aliases))
    return tuple({_fold_text(alias) for alias in aliases})


_MARKET_PRODUCTS = tuple(
    product for product in CATALOG_PRODUCTS if product.reference_url is not None
)
_IDENTITY_ALIASES = tuple(
    sorted(
        ((alias, product) for product in _MARKET_PRODUCTS for alias in _identity_aliases(product)),
        key=lambda item: len(item[0]),
        reverse=True,
    )
)
_PRODUCT_BY_MODEL = {product.model: product for product in _MARKET_PRODUCTS}


def _catalog_identity(text: str) -> tuple[str, str, str]:
    normalized = f" {_fold_text(text)} "
    for alias, product in _IDENTITY_ALIASES:
        if f" {alias} " in normalized:
            return product.brand.casefold(), product.model, product.name
    raise ExtractionError("retail product is outside the canonical device catalog")


def _storage_from_text(text: str) -> str:
    match = re.search(r"\b(128|256|512|1024|2048)\s*gb\b|\b([12])\s*tb\b", text, re.I)
    if not match:
        raise ExtractionError("retail offer is missing storage capacity")
    if match.group(2):
        return str(int(match.group(2)) * 1024)
    return str(match.group(1))


_MODEL_COLOR_ALIASES: dict[str, dict[str, str]] = {
    "iphone_16": {"verde": "Verde-Acinzentado"},
    "iphone_16_plus": {"verde": "Verde-Acinzentado"},
    "iphone_16_pro": {
        "preto": "Titânio-Preto",
        "branco": "Titânio-Branco",
        "natural": "Titânio-Natural",
        "deserto": "Titânio-Deserto",
    },
    "iphone_16_pro_max": {
        "preto": "Titânio-Preto",
        "branco": "Titânio-Branco",
        "natural": "Titânio-Natural",
        "deserto": "Titânio-Deserto",
    },
    "iphone_17_pro": {"prata": "Prateado", "azul": "Azul-Intenso"},
    "iphone_17_pro_max": {"prata": "Prateado", "azul": "Azul-Intenso"},
    "galaxy_s25_ultra": {
        "azul": "Titânio-Azul",
        "preto": "Titânio-Preto",
        "cinza": "Titânio-Cinza",
        "prata": "Titânio-Prata",
    },
}


def _color_from_text(text: str, *, model: str) -> str:
    product = _PRODUCT_BY_MODEL.get(model)
    if product is None:
        raise ExtractionError(f"unknown canonical model: {model!r}")

    folded = f" {_fold_text(text)} "
    aliases = {_fold_text(color): color for color in product.colors}
    aliases.update(_MODEL_COLOR_ALIASES.get(model, {}))
    for marker, canonical in sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True):
        if f" {_fold_text(marker)} " in folded:
            return canonical
    raise ExtractionError(f"retail offer is missing a supported color: {text!r}")


def _external_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _brl_amount(value: str) -> Decimal:
    normalized = value.replace("\xa0", " ").replace("R$", "").strip()
    normalized = normalized.replace(".", "").replace(",", ".")
    try:
        amount = Decimal(normalized)
    except InvalidOperation as exc:
        raise ExtractionError(f"unparseable BRL price: {value!r}") from exc
    if amount <= 0:
        raise ExtractionError("retail price must be positive")
    return amount


def _plain_text(fragment: str) -> str:
    """Collapse a small, already-bounded HTML fragment into visible text."""
    without_tags = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html_module.unescape(without_tags)).strip()


_SITEMAP_LOC = re.compile(r"<loc>\s*(?P<loc>[^<\s]+)\s*</loc>", re.I)
_SITEMAP_INDEX = re.compile(r"<sitemapindex\b", re.I)


@dataclass(frozen=True, slots=True)
class _CatalogUrlFilter:
    """Decides whether one discovered URL is the canonical product we asked for.

    Shared by search-result discovery and sitemap discovery so both surfaces
    apply the same identity rule: same host, a product path, every token of the
    canonical name, the exact canonical model and the requested capacity.
    """

    product_name: str
    product_model: str
    storage_gb: str | None
    host: str
    product_path_markers: tuple[str, ...]

    def matches(self, candidate: str, *, visible_text: str) -> bool:
        parsed = urlsplit(candidate)
        if (parsed.hostname or "").casefold() != self.host:
            return False
        if not any(marker in parsed.path for marker in self.product_path_markers):
            return False
        haystack = _fold_text(f"{unquote(candidate)} {visible_text}")
        tokens = set(haystack.split())
        if not set(_fold_text(self.product_name).split()) <= tokens:
            return False
        try:
            _, discovered_model, _ = _catalog_identity(haystack)
        except ExtractionError:
            return False
        if discovered_model != self.product_model:
            return False
        markers = self._storage_markers()
        return not markers or any(marker in haystack for marker in markers)

    def _storage_markers(self) -> set[str]:
        if self.storage_gb is None:
            return set()
        value = int(self.storage_gb)
        markers = {f"{value} gb", f"{value}gb"}
        if value >= 1024:
            markers |= {f"{value // 1024} tb", f"{value // 1024}tb"}
        return markers


def extract_product_search_urls(
    page_html: str,
    page_url: str,
    *,
    product_name: str,
    product_model: str,
    storage_gb: str | None,
    product_path_markers: tuple[str, ...] = ("/celular/",),
) -> list[str]:
    """Select exact product pages from one retailer search result.

    Search pages are untrusted discovery surfaces. The adapter keeps only
    same-host smartphone URLs whose visible/link text includes the canonical
    product identity and requested capacity; every followed page is parsed
    again by the retailer-specific product extractor.
    """
    selector = Selector(text=page_html)
    identity = _CatalogUrlFilter(
        product_name=product_name,
        product_model=product_model,
        storage_gb=storage_gb,
        host=(urlsplit(page_url).hostname or "").casefold(),
        product_path_markers=product_path_markers,
    )
    results: list[str] = []
    seen: set[str] = set()

    for anchor in selector.css("a[href]"):
        href = anchor.attrib.get("href", "").strip()
        if not href:
            continue
        candidate = urljoin(page_url, href)
        visible = " ".join(anchor.css("::text").getall())
        if not identity.matches(candidate, visible_text=visible):
            continue
        canonical = candidate.split("#", 1)[0]
        if canonical in seen:
            continue
        seen.add(canonical)
        results.append(canonical)
        if len(results) >= MAX_SEARCH_RESULTS_PER_CAPACITY:
            break
    return results


def extract_sitemap_locations(document: str, *, allowed_host: str) -> list[str]:
    """Every same-host ``<loc>`` in a sitemap or sitemap index, in document order.

    Parsed with a narrow regex rather than an XML parser on purpose: the input
    is a third-party document, and this needs no entity resolution, no DTD and
    no namespace handling to read a list of URLs.
    """
    locations: list[str] = []
    seen: set[str] = set()
    for match in _SITEMAP_LOC.finditer(document):
        location = html_module.unescape(match.group("loc")).strip()
        parsed = urlsplit(location)
        if parsed.scheme != "https" or (parsed.hostname or "").casefold() != allowed_host:
            continue
        if location in seen:
            continue
        seen.add(location)
        locations.append(location)
    return locations


def is_sitemap_index(document: str) -> bool:
    return _SITEMAP_INDEX.search(document) is not None


def select_sitemap_product_urls(
    document: str,
    *,
    product_name: str,
    product_model: str,
    storage_gb: str | None,
    allowed_host: str,
    product_path_markers: tuple[str, ...] = ("/produto/",),
) -> list[str]:
    """Pick the product pages a sitemap publishes for one canonical capacity.

    A sitemap carries no visible link text, so the URL slug is the only
    evidence available at selection time — which is why every page selected
    here is still parsed by the retailer's own product extractor before any
    offer is recorded. This is the route for retailers whose robots.txt
    forbids the search path while leaving product pages public.
    """
    identity = _CatalogUrlFilter(
        product_name=product_name,
        product_model=product_model,
        storage_gb=storage_gb,
        host=allowed_host,
        product_path_markers=product_path_markers,
    )
    results: list[str] = []
    for location in extract_sitemap_locations(document, allowed_host=allowed_host):
        if not identity.matches(location, visible_text=""):
            continue
        results.append(location)
        if len(results) >= MAX_SEARCH_RESULTS_PER_CAPACITY:
            break
    return results


def _canonical_attributes(title: str) -> dict[str, str]:
    brand, model, _ = _catalog_identity(title)
    return {
        "brand": brand,
        "model": model,
        "region": "br",
        "storage_gb": _storage_from_text(title),
        "color": _color_from_text(title, model=model),
    }


def extract_amazon_listing(page_html: str, page_url: str) -> RetailListing:
    """Extract Amazon's selected buy-box offer from its visible product page.

    Amazon's Product JSON-LD can lag behind the rendered buy box. The adapter
    therefore reads the scoped visible price, stock and merchant blocks and
    fails closed when any of those commercial fields is absent.
    """
    selector = Selector(text=page_html)
    title = " ".join(selector.css("#productTitle::text").getall()).strip()
    price = (
        selector.css("#corePrice_feature_div .apex-pricetopay-value .a-offscreen::text").get()
        or selector.css("#corePrice_feature_div .a-offscreen::text").get()
    )
    seller_candidates = [
        value.strip()
        for value in selector.css(
            '[offer-display-feature-name="desktop-merchant-info"] '
            ".offer-display-feature-text-message::text"
        ).getall()
        if value.strip()
    ]
    seller_name = seller_candidates[0] if seller_candidates else ""
    asin_match = re.search(r"/dp/(?P<asin>[A-Z0-9]{10})(?:[/?]|$)", page_url, re.IGNORECASE)
    missing = [
        field
        for field, absent in (
            ("title", not title),
            ("price", price is None),
            ("merchant", not seller_name),
            ("asin", asin_match is None),
        )
        if absent
    ]
    if missing:
        raise ExtractionError(
            f"Amazon page is missing visible buy-box fields: {', '.join(missing)}"
        )
    assert price is not None and asin_match is not None

    availability_text = " ".join(selector.css("#availability ::text").getall()).casefold()
    visible_in_stock = any(
        marker in availability_text for marker in ("em estoque", "disponível", "in stock")
    )
    add_to_cart_available = bool(selector.css('#add-to-cart-button, [name="submit.add-to-cart"]'))
    product = next(iter_product_json_ld(page_html), None)
    json_ld_in_stock = False
    if product is not None:
        with suppress(ExtractionError):
            json_ld_in_stock = (
                parse_availability(str(_offer(product).get("availability") or ""))
                == Availability.IN_STOCK
            )
    if not visible_in_stock and not json_ld_in_stock and not add_to_cart_available:
        raise ExtractionError("Amazon buy box does not confirm the item is in stock")

    is_cash = bool(re.search(r"à vista no Pix(?: ou NuPay)?", page_html, re.IGNORECASE))
    return RetailListing(
        external_listing_id=asin_match.group("asin").upper(),
        url=page_url,
        raw_title=title,
        gtin=None,
        attributes=_canonical_attributes(title),
        seller_external_id=_external_id(seller_name),
        seller_display_name=seller_name,
        price_amount=_brl_amount(price),
        currency="BRL",
        availability=Availability.IN_STOCK,
        condition=Condition.NEW,
        payment_terms=PaymentTerms(
            price_basis=PriceBasis.CASH if is_cash else PriceBasis.ADVERTISED,
            condition_summary="à vista via Pix ou NuPay" if is_cash else None,
        ),
        shipping=ShippingTerms(known=False),
    )


def extract_carrefour_listing(page_html: str, page_url: str) -> RetailListing:
    """Extract Carrefour marketplace identity plus the visible Pix price."""
    product = next(iter_product_json_ld(page_html), None)
    if product is None:
        raise ExtractionError("no Product JSON-LD found on Carrefour page")
    offer = _offer(product)
    title = html_module.unescape(str(product.get("name") or "")).strip()
    sku = str(product.get("sku") or offer.get("sku") or "").strip()
    price_match = re.search(
        r"(?P<price>R\$\s*[\d.]+,\d{2})</span>.{0,600}?à vista no Pix",
        page_html,
        re.IGNORECASE | re.DOTALL,
    )
    seller_match = re.search(
        r"Vendido\s+e\s+entregue\s+por(?:\s|<!--.*?-->)*"
        r"<a\b[^>]*>(?P<seller>.*?)</a>",
        page_html,
        re.IGNORECASE | re.DOTALL,
    )
    if not sku or price_match is None or seller_match is None:
        raise ExtractionError("Carrefour page is missing SKU, Pix price or marketplace seller")
    seller_name = _plain_text(seller_match.group("seller"))
    if not seller_name:
        raise ExtractionError("Carrefour page contains an empty marketplace seller")
    availability = parse_availability(str(offer.get("availability") or ""))
    condition = parse_condition(str(offer.get("itemCondition") or ""))
    if availability == Availability.UNKNOWN or condition == Condition.UNKNOWN:
        raise ExtractionError("Carrefour JSON-LD does not confirm stock and condition")
    return RetailListing(
        external_listing_id=sku,
        url=page_url,
        raw_title=title,
        gtin=None,
        attributes=_canonical_attributes(title),
        seller_external_id=_external_id(seller_name),
        seller_display_name=seller_name,
        price_amount=_brl_amount(price_match.group("price")),
        currency=str(offer.get("priceCurrency") or "BRL"),
        availability=availability,
        condition=condition,
        payment_terms=PaymentTerms(
            price_basis=PriceBasis.CASH,
            condition_summary="à vista via Pix",
        ),
        shipping=ShippingTerms(known=False),
    )


def extract_americanas_listing(page_html: str, page_url: str) -> RetailListing:
    """Extract the first positive, in-stock marketplace offer from Americanas."""
    product = next(iter_product_json_ld(page_html), None)
    if product is None:
        raise ExtractionError("no Product JSON-LD found on Americanas page")
    title = html_module.unescape(str(product.get("name") or "")).strip()
    sku = str(product.get("sku") or "").strip()
    offers = product.get("offers")
    if not sku or not isinstance(offers, list):
        raise ExtractionError("Americanas Product JSON-LD is missing SKU or offers")

    selected_offer: dict | None = None
    for candidate in offers[:MAX_AGGREGATE_OFFERS]:
        if not isinstance(candidate, dict):
            continue
        seller_value = candidate.get("seller")
        seller = seller_value if isinstance(seller_value, dict) else {}
        try:
            price = _price(candidate)
        except ExtractionError:
            continue
        if (
            price > 0
            and parse_availability(str(candidate.get("availability") or ""))
            == Availability.IN_STOCK
            and str(seller.get("name") or "").strip()
        ):
            selected_offer = candidate
            break
    if selected_offer is None:
        raise ExtractionError("Americanas page has no positive in-stock marketplace offer")

    seller_value = selected_offer.get("seller")
    seller = seller_value if isinstance(seller_value, dict) else {}
    seller_name = str(seller.get("name") or "").strip()
    return RetailListing(
        external_listing_id=sku,
        url=page_url,
        raw_title=title,
        gtin=None,
        attributes=_canonical_attributes(title),
        seller_external_id=_external_id(seller_name),
        seller_display_name=seller_name,
        price_amount=_price(selected_offer),
        currency=str(selected_offer.get("priceCurrency") or "BRL"),
        availability=Availability.IN_STOCK,
        # The adapter is enabled only for the reviewed new-device product URL.
        condition=Condition.NEW,
        payment_terms=PaymentTerms(price_basis=PriceBasis.ADVERTISED),
        shipping=ShippingTerms(known=False),
    )


class TwoAFinderMarkdownParser:
    """Parse the public, robot-friendly offer table without following lead URLs."""

    _title = re.compile(r"^#\s+(?P<title>.+?)\s*$", re.MULTILINE)
    _active_offers = re.compile(
        r"^Onde comprar .+?:\s+\d+\s+ofertas ativas\b",
        re.IGNORECASE | re.MULTILINE,
    )
    _row = re.compile(
        r"^\|\s*(?P<rank>\d+)\s*"
        r"\|\s*(?P<price>R\$[^|]+?)\s*"
        r"\|\s*(?P<channel>[^|]+?)\s*"
        r"\|\s*(?P<seller>[^|]+?)\s*"
        r"\|\s*(?P<condition>[^|]+?)\s*"
        r"\|\s*(?P<freight>[^|]+?)\s*"
        r"\|\s*(?P<variant>.*?)\s*"
        r"\|\s*(?P<verified>\d{4}-\d{2}-\d{2}T[^|]+?)\s*"
        r"\|\s*`(?P<offer_id>[0-9a-fA-F-]{36})`\s*"
        r"\|\s*(?P<next_step>https://2afinder\.com/produto/[^|\s]+)\s*\|$",
        re.MULTILINE,
    )

    def parse(self, page_markdown: str, page_url: str) -> list[RetailListing]:
        title_match = self._title.search(page_markdown)
        if title_match is None:
            raise ExtractionError("2aFinder Markdown is missing the canonical product heading")
        if self._active_offers.search(page_markdown) is None:
            raise ExtractionError("2aFinder Markdown does not confirm active offers")
        title = title_match.group("title").strip()
        brand, model, _ = _catalog_identity(title)
        attributes = {
            "brand": brand,
            "model": model,
            "region": "br",
            "storage_gb": _storage_from_text(title),
            "color": _color_from_text(title, model=model),
        }

        listings: list[RetailListing] = []
        for match in self._row.finditer(page_markdown):
            if len(listings) >= MAX_AGGREGATE_OFFERS:
                break
            condition_text = match.group("condition").strip().casefold()
            seller_name = match.group("seller").strip()
            channel = match.group("channel").strip()
            if not seller_name or not channel:
                continue
            listings.append(
                RetailListing(
                    external_listing_id=match.group("offer_id").lower(),
                    # The public comparison document is the immutable audit
                    # target. Affiliate/lead URLs are intentionally ignored.
                    url=page_url,
                    raw_title=title,
                    gtin=None,
                    attributes=attributes,
                    seller_external_id=_external_id(f"{channel}-{seller_name}"),
                    seller_display_name=f"{seller_name} · {channel}",
                    price_amount=_brl_amount(match.group("price")),
                    currency="BRL",
                    availability=Availability.IN_STOCK,
                    condition=Condition.NEW if condition_text == "novo" else Condition.UNKNOWN,
                    payment_terms=PaymentTerms(price_basis=PriceBasis.ADVERTISED),
                    shipping=self._shipping(match.group("freight")),
                )
            )
        if not listings:
            raise ExtractionError("no offers found in 2aFinder Markdown table")
        return listings

    @staticmethod
    def _shipping(value: str) -> ShippingTerms:
        normalized = value.strip().casefold()
        if normalized in {"grátis", "gratis"}:
            return ShippingTerms(known=True, cost_minor_units=0, cost_currency="BRL")
        if normalized.startswith("r$"):
            cost = _brl_amount(value)
            return ShippingTerms(
                known=True,
                cost_minor_units=int(cost * 100),
                cost_currency="BRL",
            )
        return ShippingTerms(known=False)


@dataclass(frozen=True, slots=True)
class BuscapeOfferPage:
    """One page of Buscapé's public offer document.

    ``hit_count`` is the number of raw entries the page carried, before
    catalog filtering. Pagination has to key off that rather than off the
    listings actually kept: a page can be full of offers for other models
    and still be followed by a page holding the retailer we need.
    """

    listings: tuple[RetailListing, ...]
    hit_count: int

    @property
    def is_full(self) -> bool:
        return self.hit_count >= BUSCAPE_OFFER_PAGE_SIZE


class BuscapeOfferParser:
    """Parse the bounded offer payload used by Buscapé's public product page."""

    _product_id = re.compile(r'"prodId"\s*:\s*"?(?P<id>\d+)"?')

    def product_id(self, page_html: str) -> str:
        identifiers = {match.group("id") for match in self._product_id.finditer(page_html)}
        if len(identifiers) != 1:
            raise ExtractionError("Buscapé page does not expose one unambiguous product id")
        return identifiers.pop()

    def parse_page(
        self, payload_text: str, evidence_url: str, *, skips: SkipLog | None = None
    ) -> BuscapeOfferPage:
        """Parse one offer page without requiring it to yield canonical offers.

        A malformed document is still an error, but an page that simply holds
        no catalog match is a legitimate outcome while paginating.
        """
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise ExtractionError("Buscapé offer response is not valid JSON") from exc
        hits = payload.get("hits") if isinstance(payload, dict) else None
        if not isinstance(hits, list):
            raise ExtractionError("Buscapé offer response is missing hits")

        skips = skips if skips is not None else SkipLog()
        listings: list[RetailListing] = []
        for hit in hits[:MAX_AGGREGATE_OFFERS]:
            if not isinstance(hit, dict):
                continue
            listing = self._listing(hit, evidence_url, skips)
            if listing is not None:
                listings.append(listing)
        return BuscapeOfferPage(listings=tuple(listings), hit_count=len(hits))

    def parse(self, payload_text: str, evidence_url: str) -> list[RetailListing]:
        page = self.parse_page(payload_text, evidence_url)
        if not page.listings:
            raise ExtractionError("no canonical offers found in Buscapé response")
        return list(page.listings)

    @staticmethod
    def _listing(hit: dict, evidence_url: str, skips: SkipLog) -> RetailListing | None:
        title = str(hit.get("name") or "").strip()
        seller = hit.get("seller")
        sales_condition = hit.get("sales_condition")
        if not title or not isinstance(seller, dict) or not isinstance(sales_condition, dict):
            skips.record(title, "offer is missing its title, retailer or sales condition")
            return None
        seller_name = str(seller.get("name") or "").strip()
        external_id = str(hit.get("offer_id") or "").strip()
        if not seller_name or not external_id:
            skips.record(title, "offer is missing its retailer name or offer id")
            return None
        try:
            brand, model, _ = _catalog_identity(title)
            storage = _storage_from_text(title)
            color = _color_from_text(title, model=model)
            price = Decimal(str(sales_condition.get("price")))
        except (ExtractionError, InvalidOperation, TypeError) as exc:
            skips.record(title, str(exc) or "offer does not resolve to a canonical variant")
            return None
        if price <= 0:
            skips.record(title, "offer price is not positive")
            return None

        installments = sales_condition.get("installments")
        installment_count = None
        if isinstance(installments, list) and installments and isinstance(installments[0], dict):
            raw_count = installments[0].get("amount_months")
            if isinstance(raw_count, int) and raw_count > 0:
                installment_count = raw_count
        stock = sales_condition.get("stock")
        if isinstance(stock, int) and not isinstance(stock, bool):
            availability = Availability.IN_STOCK if stock > 0 else Availability.OUT_OF_STOCK
        else:
            availability = Availability.UNKNOWN
        return RetailListing(
            external_listing_id=external_id,
            url=evidence_url,
            raw_title=title,
            gtin=None,
            attributes={
                "brand": brand,
                "model": model,
                "region": "br",
                "storage_gb": storage,
                "color": color,
            },
            seller_external_id=_external_id(f"{seller.get('id', '')}-{seller_name}"),
            seller_display_name=seller_name,
            price_amount=price,
            currency="BRL",
            availability=availability,
            condition=(Condition.NEW if hit.get("condition") == "NEW" else Condition.UNKNOWN),
            payment_terms=PaymentTerms(
                installment_count=installment_count,
                price_basis=PriceBasis.CASH,
                condition_summary="preço à vista informado pelo comparador",
            ),
            shipping=ShippingTerms(known=False),
        )


def _commercial_text(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _commercial_text(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if key not in {"url", "image", "@id"}:
                yield from _commercial_text(item)


def _payment_terms(offer: dict) -> PaymentTerms:
    raw_text = " ".join(_commercial_text(offer))
    normalized = "".join(
        character
        for character in unicodedata.normalize("NFKD", raw_text.casefold())
        if not unicodedata.combining(character)
    )
    installment_match = _INSTALLMENTS.search(normalized)

    for marker, summary in _CONDITIONAL_TERMS.items():
        if marker in normalized:
            return PaymentTerms(
                installment_count=(int(installment_match.group(1)) if installment_match else None),
                price_basis=PriceBasis.CONDITIONAL,
                is_conditional=True,
                condition_summary=summary,
            )

    is_cash = "pix" in normalized or "à vista" in normalized or "a vista" in normalized
    return PaymentTerms(
        installment_count=int(installment_match.group(1)) if installment_match else None,
        price_basis=PriceBasis.CASH if is_cash else PriceBasis.ADVERTISED,
        condition_summary="pagamento à vista" if is_cash else None,
    )


def extract_iplace_listings(
    page_html: str, page_url: str, *, skips: SkipLog | None = None
) -> list[RetailListing]:
    skips = skips if skips is not None else SkipLog()
    listings: list[RetailListing] = []
    for product in iter_product_json_ld(page_html):
        if len(listings) >= MAX_PRODUCT_VARIANTS:
            break
        name = str(product.get("name", "")).strip()
        try:
            attributes = _canonical_attributes(name)
        except ExtractionError as exc:
            skips.record(name, str(exc))
            continue
        offer = _offer(product)
        sku = str(product.get("sku") or offer.get("sku") or "").strip()
        if not sku:
            raise ExtractionError("iPlace Product JSON-LD is missing a SKU")
        seller_value = offer.get("seller")
        seller: dict = seller_value if isinstance(seller_value, dict) else {}
        listings.append(
            RetailListing(
                external_listing_id=sku,
                url=str(product.get("url") or offer.get("url") or page_url),
                raw_title=name,
                # iPlace identifiers remain attribute-matched until each GTIN is
                # independently verified against the canonical catalog.
                gtin=None,
                attributes=attributes,
                seller_external_id="iplace",
                seller_display_name=str(seller.get("name") or "iPlace"),
                price_amount=_price(offer),
                currency=str(offer.get("priceCurrency") or "BRL"),
                availability=parse_availability(str(offer.get("availability") or "")),
                condition=parse_condition(str(offer.get("itemCondition") or "")),
                payment_terms=_payment_terms(offer),
                shipping=ShippingTerms(known=False),
            )
        )
    if not listings:
        raise ExtractionError("no canonical iPhone variants found in iPlace JSON-LD")
    return listings


def extract_fast_shop_listing(page_html: str, page_url: str) -> RetailListing:
    product = next(iter_product_json_ld(page_html), None)
    if product is None:
        raise ExtractionError("no Product JSON-LD found on Fast Shop page")
    offer = _offer(product)
    name = str(product.get("name", "")).strip()
    description = html_module.unescape(str(product.get("description") or ""))
    plain_description = re.sub(r"<[^>]+>", "|", description)
    combined_text = f"{name} | {plain_description}"
    brand, canonical_model, _ = _catalog_identity(name)
    storage = _STORAGE.search(combined_text)
    color = _COLOR.search(plain_description)
    model = _MODEL.search(plain_description)
    try:
        canonical_color = _color_from_text(
            color.group(1) if color else combined_text,
            model=canonical_model,
        )
    except ExtractionError as exc:
        raise ExtractionError("Fast Shop product is missing a supported color") from exc
    if not storage:
        raise ExtractionError("Fast Shop product is missing iPhone storage or color")
    sku = str(product.get("sku") or (model.group(1) if model else "")).strip()
    if not sku:
        raise ExtractionError("Fast Shop Product JSON-LD is missing a SKU")
    attributes = {
        "brand": brand,
        "model": canonical_model,
        "region": "br",
        "storage_gb": storage.group(1),
        "color": canonical_color,
    }
    # The evidence keeps retailer-provided identifiers. They are not used for
    # matching because marketplace sellers have published inconsistent EANs
    # for the same Apple variant; the full canonical signature is safer.
    seller_value = offer.get("seller")
    seller: dict = seller_value if isinstance(seller_value, dict) else {}
    return RetailListing(
        external_listing_id=sku,
        url=str(product.get("url") or offer.get("url") or page_url),
        raw_title=name,
        gtin=None,
        attributes=attributes,
        seller_external_id="fast-shop",
        seller_display_name=str(seller.get("name") or "Fast Shop"),
        price_amount=_price(offer),
        currency=str(offer.get("priceCurrency") or "BRL"),
        availability=parse_availability(str(offer.get("availability") or "")),
        condition=parse_condition(str(offer.get("itemCondition") or "")),
        payment_terms=_payment_terms(offer),
        shipping=ShippingTerms(known=False),
    )


def extract_kabum_listing(page_html: str, page_url: str) -> RetailListing:
    """Extract one canonical offer and its visible marketplace seller from KaBuM!."""
    product = next(iter_product_json_ld(page_html), None)
    if product is None:
        raise ExtractionError("no Product JSON-LD found on KaBuM! page")

    offer = _offer(product)
    name = html_module.unescape(str(product.get("name") or "")).strip()
    description = html_module.unescape(str(product.get("description") or ""))
    brand, model, _ = _catalog_identity(name)
    sku = str(product.get("sku") or offer.get("sku") or "").strip()
    if not sku:
        raise ExtractionError("KaBuM! Product JSON-LD is missing a SKU")

    seller_block = re.search(
        r"Vendido\s+e\s+entregue\s+por:\s*</[^>]+>(?P<block>.{0,600}?)</div>",
        page_html,
        re.IGNORECASE | re.DOTALL,
    )
    if seller_block is None:
        raise ExtractionError("KaBuM! page is missing the visible marketplace seller")
    seller_element = re.search(
        r"<(?:b|button)[^>]*>(?P<seller>.*?)</(?:b|button)>",
        seller_block.group("block"),
        re.IGNORECASE | re.DOTALL,
    )
    if seller_element is None:
        raise ExtractionError("KaBuM! page is missing the visible marketplace seller")
    seller_name = re.sub(r"<[^>]+>", "", seller_element.group("seller"))
    seller_name = html_module.unescape(seller_name).strip()
    if not seller_name:
        raise ExtractionError("KaBuM! page contains an empty marketplace seller")

    combined_text = f"{name} | {description}"
    return RetailListing(
        external_listing_id=sku,
        url=str(product.get("url") or offer.get("url") or page_url),
        raw_title=name,
        gtin=None,
        attributes={
            "brand": brand,
            "model": model,
            "region": "br",
            "storage_gb": _storage_from_text(combined_text),
            "color": _color_from_text(combined_text, model=model),
        },
        seller_external_id=re.sub(r"[^a-z0-9]+", "-", seller_name.casefold()).strip("-"),
        seller_display_name=seller_name,
        price_amount=_price(offer),
        currency=str(offer.get("priceCurrency") or "BRL"),
        availability=parse_availability(str(offer.get("availability") or "")),
        # KaBuM!'s JSON-LD currently omits itemCondition on these new-device
        # pages. The adapter is deliberately scoped to the reviewed, seeded
        # new-product URLs rather than inferring condition from arbitrary URLs.
        condition=Condition.NEW,
        payment_terms=_payment_terms(offer),
        shipping=ShippingTerms(known=False),
    )


def extract_samsung_shop_listings(
    page_html: str, page_url: str, *, skips: SkipLog | None = None
) -> list[RetailListing]:
    """Extract every purchasable SKU published in Samsung Shop ProductGroup JSON-LD."""
    skips = skips if skips is not None else SkipLog()
    listings: list[RetailListing] = []
    for product in iter_product_json_ld(page_html):
        if len(listings) >= MAX_PRODUCT_VARIANTS:
            break
        name = str(product.get("name", "")).strip()
        color = str(product.get("color") or "").strip()
        try:
            attributes = _canonical_attributes(f"{name} {color}")
        except ExtractionError as exc:
            skips.record(f"{name} {color}".strip(), str(exc))
            continue
        offer = _offer(product)
        sku = str(product.get("sku") or product.get("mpn") or "").strip()
        if not sku or not color:
            # The VTEX page also emits one summary Product block without a
            # color. Only ProductGroup variants identify a canonical SKU.
            continue
        seller_value = offer.get("seller")
        seller: dict = seller_value if isinstance(seller_value, dict) else {}
        listings.append(
            RetailListing(
                external_listing_id=sku,
                url=str(product.get("url") or offer.get("url") or page_url),
                raw_title=name,
                # Keep the upstream GTIN in the immutable evidence HTML, but
                # attribute-match until a separate catalog enrichment step has
                # verified and persisted every Samsung SKU/GTIN pair.
                gtin=None,
                attributes=attributes,
                seller_external_id="samsung-shop-brasil",
                seller_display_name=str(seller.get("name") or "Samsung Shop Brasil"),
                price_amount=_price(offer),
                currency=str(offer.get("priceCurrency") or "BRL"),
                availability=parse_availability(str(offer.get("availability") or "")),
                condition=parse_condition(str(offer.get("itemCondition") or "")),
                payment_terms=_payment_terms(offer),
                shipping=ShippingTerms(known=False),
            )
        )
    if not listings:
        raise ExtractionError("no canonical Galaxy variants found in Samsung Shop JSON-LD")
    return listings


def extract_zoom_listings(
    page_html: str, page_url: str, *, skips: SkipLog | None = None
) -> list[RetailListing]:
    """Extract the bounded retailer sample published in Zoom AggregateOffer JSON-LD.

    Zoom remains the evidence channel; ``offeredBy`` is retained as the actual
    retailer so the UI can report both domain coverage and seller diversity.
    """
    product = next(iter_product_json_ld(page_html), None)
    if product is None:
        raise ExtractionError("no Product JSON-LD found on Zoom page")
    brand, model, _ = _catalog_identity(str(product.get("name") or ""))
    aggregate = product.get("offers")
    if not isinstance(aggregate, dict) or not isinstance(aggregate.get("offers"), list):
        raise ExtractionError("Zoom Product JSON-LD is missing AggregateOffer entries")

    skips = skips if skips is not None else SkipLog()
    listings: list[RetailListing] = []
    for offer in aggregate["offers"][:MAX_AGGREGATE_OFFERS]:
        if not isinstance(offer, dict):
            continue
        title = str(offer.get("name") or product.get("name") or "").strip()
        external_id = str(offer.get("id") or "").strip()
        seller_name = str(offer.get("offeredBy") or "").strip()
        if not external_id or not seller_name:
            skips.record(title, "aggregate offer is missing its id or retailer")
            continue
        try:
            storage = _storage_from_text(title)
            color = _color_from_text(title, model=model)
        except ExtractionError as exc:
            skips.record(title, str(exc))
            continue
        listings.append(
            RetailListing(
                external_listing_id=external_id,
                # Lead URLs are deliberately not followed. The public product
                # comparison page is the auditable evidence URL.
                url=page_url,
                raw_title=title,
                gtin=None,
                attributes={
                    "brand": brand,
                    "model": model,
                    "region": "br",
                    "storage_gb": storage,
                    "color": color,
                },
                seller_external_id=re.sub(r"[^a-z0-9]+", "-", seller_name.casefold()).strip("-"),
                seller_display_name=seller_name,
                price_amount=_price(offer),
                currency=str(offer.get("priceCurrency") or "BRL"),
                availability=Availability.IN_STOCK,
                condition=Condition.NEW,
                payment_terms=PaymentTerms(
                    price_basis=PriceBasis.CASH,
                    condition_summary="preço à vista informado pelo comparador",
                ),
                shipping=ShippingTerms(known=False),
            )
        )
    if not listings:
        raise ExtractionError("no canonical offers found in Zoom Product JSON-LD")
    return listings
