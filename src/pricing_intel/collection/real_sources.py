"""Pure extractors for reviewed Brazilian retailer product pages.

Each adapter consumes structured data already published by the retailer.  It
does not attempt to defeat access controls, CAPTCHA or browser challenges.
"""

from __future__ import annotations

import html as html_module
import json
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from pricing_intel.collection.extraction import (
    ExtractionError,
    iter_product_json_ld,
    parse_availability,
    parse_condition,
)
from pricing_intel.domain.enums import Availability, Condition, PriceBasis
from pricing_intel.domain.models import PaymentTerms, ShippingTerms

MAX_PRODUCT_VARIANTS = 24
MAX_AGGREGATE_OFFERS = 20


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


_IPHONE_17_NAME = re.compile(
    r"iphone\s+17(?:\s+apple)?[^0-9]*(?P<storage>256|512)\s*gb(?:\s+|.*?cor\s+)(?P<color>[^,|]+)",
    re.IGNORECASE,
)
_GALAXY_S26_NAME = re.compile(
    r"galaxy\s+s26(?P<suffix>\+|\s*plus|\s*ultra)?.*?(?P<storage>256|512|1\s*tb|1024)\s*(?:gb)?",
    re.IGNORECASE,
)
_STORAGE = re.compile(r"(?:capacidade|armazenamento|mem[oó]ria)?\s*:?[ ]*(256|512)\s*gb", re.I)
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
        return Decimal(str(raw))
    except (InvalidOperation, TypeError) as exc:
        raise ExtractionError(f"unparseable retail price: {raw!r}") from exc


def _iphone_attributes(storage: str, color: str) -> dict[str, str]:
    return {
        "brand": "apple",
        "model": "iphone_17",
        "region": "br",
        "storage_gb": storage,
        "color": color.strip(),
    }


def _galaxy_attributes(*, model_suffix: str, storage: str, color: str) -> dict[str, str]:
    suffix = model_suffix.casefold().strip()
    model = (
        "galaxy_s26_ultra"
        if "ultra" in suffix
        else "galaxy_s26_plus"
        if suffix in {"+", "plus"}
        else "galaxy_s26"
    )
    normalized_storage = "1024" if "tb" in storage.casefold() else storage.strip()
    return {
        "brand": "samsung",
        "model": model,
        "region": "br",
        "storage_gb": normalized_storage,
        "color": color.strip(),
    }


def _catalog_identity(text: str) -> tuple[str, str, str]:
    normalized = "".join(
        character
        for character in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(character)
    )
    if "iphone 17 pro max" in normalized:
        return "apple", "iphone_17_pro_max", "Apple iPhone 17 Pro Max"
    if "iphone 17 pro" in normalized:
        return "apple", "iphone_17_pro", "Apple iPhone 17 Pro"
    if "iphone 17" in normalized:
        return "apple", "iphone_17", "Apple iPhone 17"
    if "galaxy s26 ultra" in normalized:
        return "samsung", "galaxy_s26_ultra", "Samsung Galaxy S26 Ultra"
    if "galaxy s26+" in normalized or "galaxy s26 plus" in normalized:
        return "samsung", "galaxy_s26_plus", "Samsung Galaxy S26+"
    if "galaxy s26" in normalized:
        return "samsung", "galaxy_s26", "Samsung Galaxy S26"
    raise ExtractionError("retail product is outside the canonical device catalog")


def _storage_from_text(text: str) -> str:
    match = re.search(r"\b(256|512|1024|2048)\s*gb\b|\b([12])\s*tb\b", text, re.I)
    if not match:
        raise ExtractionError("retail offer is missing storage capacity")
    if match.group(2):
        return str(int(match.group(2)) * 1024)
    return str(match.group(1))


def _color_from_text(text: str, *, model: str) -> str:
    folded = "".join(
        character
        for character in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(character)
    )
    folded = re.sub(r"[^a-z0-9]+", " ", folded)
    aliases = {
        "azul intenso": "Azul-Intenso",
        "laranja cosmico": "Laranja-Cósmico",
        "azul nevoa": "Azul-Névoa",
        "salvia": "Sálvia",
        "prateado": "Prateado",
        "prata": "Prateado" if model.startswith("iphone_17_pro") else "Prata",
        "lavanda": "Lavanda",
        "violeta": "Violeta",
        "dourado": "Dourado",
        "branco": "Branco",
        "preto": "Preto",
        "azul": "Azul-Intenso" if model.startswith("iphone_17_pro") else "Azul",
    }
    for marker, canonical in aliases.items():
        if marker in folded:
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


class BuscapeOfferParser:
    """Parse the bounded offer payload used by Buscapé's public product page."""

    _product_id = re.compile(r'"prodId"\s*:\s*"?(?P<id>\d+)"?')

    def product_id(self, page_html: str) -> str:
        identifiers = {match.group("id") for match in self._product_id.finditer(page_html)}
        if len(identifiers) != 1:
            raise ExtractionError("Buscapé page does not expose one unambiguous product id")
        return identifiers.pop()

    def parse(self, payload_text: str, evidence_url: str) -> list[RetailListing]:
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise ExtractionError("Buscapé offer response is not valid JSON") from exc
        hits = payload.get("hits") if isinstance(payload, dict) else None
        if not isinstance(hits, list):
            raise ExtractionError("Buscapé offer response is missing hits")

        listings: list[RetailListing] = []
        for hit in hits[:MAX_AGGREGATE_OFFERS]:
            if not isinstance(hit, dict):
                continue
            listing = self._listing(hit, evidence_url)
            if listing is not None:
                listings.append(listing)
        if not listings:
            raise ExtractionError("no canonical offers found in Buscapé response")
        return listings

    @staticmethod
    def _listing(hit: dict, evidence_url: str) -> RetailListing | None:
        title = str(hit.get("name") or "").strip()
        seller = hit.get("seller")
        sales_condition = hit.get("sales_condition")
        if not title or not isinstance(seller, dict) or not isinstance(sales_condition, dict):
            return None
        seller_name = str(seller.get("name") or "").strip()
        external_id = str(hit.get("offer_id") or "").strip()
        if not seller_name or not external_id:
            return None
        try:
            brand, model, _ = _catalog_identity(title)
            storage = _storage_from_text(title)
            color = _color_from_text(title, model=model)
            price = Decimal(str(sales_condition.get("price")))
        except ExtractionError, InvalidOperation, TypeError:
            return None
        if price <= 0:
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


def extract_iplace_listings(page_html: str, page_url: str) -> list[RetailListing]:
    listings: list[RetailListing] = []
    for product in iter_product_json_ld(page_html):
        if len(listings) >= MAX_PRODUCT_VARIANTS:
            break
        name = str(product.get("name", "")).strip()
        match = _IPHONE_17_NAME.search(name)
        if not match:
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
                attributes=_iphone_attributes(match.group("storage"), match.group("color")),
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
        raise ExtractionError("no iPhone 17 variants found in iPlace JSON-LD")
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


def extract_samsung_shop_listings(page_html: str, page_url: str) -> list[RetailListing]:
    """Extract every purchasable SKU published in Samsung Shop ProductGroup JSON-LD."""
    listings: list[RetailListing] = []
    for product in iter_product_json_ld(page_html):
        if len(listings) >= MAX_PRODUCT_VARIANTS:
            break
        name = str(product.get("name", "")).strip()
        match = _GALAXY_S26_NAME.search(name)
        if not match:
            continue
        offer = _offer(product)
        sku = str(product.get("sku") or product.get("mpn") or "").strip()
        color = str(product.get("color") or "").strip()
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
                attributes=_galaxy_attributes(
                    model_suffix=match.group("suffix") or "",
                    storage=match.group("storage"),
                    color=color,
                ),
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
        raise ExtractionError("no Galaxy S26 variants found in Samsung Shop JSON-LD")
    return listings


def extract_zoom_listings(page_html: str, page_url: str) -> list[RetailListing]:
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

    listings: list[RetailListing] = []
    for offer in aggregate["offers"][:MAX_AGGREGATE_OFFERS]:
        if not isinstance(offer, dict):
            continue
        title = str(offer.get("name") or product.get("name") or "").strip()
        external_id = str(offer.get("id") or "").strip()
        seller_name = str(offer.get("offeredBy") or "").strip()
        if not external_id or not seller_name:
            continue
        try:
            storage = _storage_from_text(title)
            color = _color_from_text(title, model=model)
        except ExtractionError:
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
