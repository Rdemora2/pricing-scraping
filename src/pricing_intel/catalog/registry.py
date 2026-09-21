"""Versioned canonical-device registry.

This module deliberately contains product identity and variants, not offers or
prices. Market evidence only enters the system through collectors and remains
traceable to its source. Official reference URLs document where each catalog
shape was reviewed.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product


@dataclass(frozen=True, slots=True)
class CatalogVariant:
    """One canonical combination that scraped offers may match."""

    attributes: dict[str, str]
    gtin: str | None = None


@dataclass(frozen=True, slots=True)
class CatalogProduct:
    """Reviewed device family and its supported Brazilian variants."""

    name: str
    brand: str
    model: str
    storages_gb: tuple[str, ...]
    colors: tuple[str, ...]
    reference_url: str | None
    category: str = "smartphone"
    gtins: tuple[tuple[str, str, str], ...] = ()
    variant_pairs: tuple[tuple[str, str], ...] = ()
    include_identity_attributes: bool = True

    @property
    def variants(self) -> tuple[CatalogVariant, ...]:
        gtin_by_variant = {(storage, color): gtin for storage, color, gtin in self.gtins}
        combinations = self.variant_pairs or tuple(product(self.storages_gb, self.colors))
        variants = []
        for storage, color in combinations:
            attributes = {"storage_gb": storage, "color": color}
            if self.include_identity_attributes:
                attributes = {
                    "brand": self.brand.lower(),
                    "model": self.model,
                    "region": "br",
                    **attributes,
                }
            variants.append(
                CatalogVariant(
                    attributes=attributes,
                    gtin=gtin_by_variant.get((storage, color)),
                )
            )
        return tuple(variants)


CATALOG_PRODUCTS = (
    CatalogProduct(
        name="Apple iPhone 16",
        brand="Apple",
        model="iphone_16",
        storages_gb=("128", "256", "512"),
        colors=("Preto", "Branco", "Rosa", "Verde-Acinzentado", "Ultramarino"),
        reference_url="https://www.apple.com/br/iphone-16/specs/",
    ),
    CatalogProduct(
        name="Apple iPhone 16 Plus",
        brand="Apple",
        model="iphone_16_plus",
        storages_gb=("128", "256", "512"),
        colors=("Preto", "Branco", "Rosa", "Verde-Acinzentado", "Ultramarino"),
        reference_url="https://www.apple.com/br/iphone-16/specs/",
    ),
    CatalogProduct(
        name="Apple iPhone 16 Pro",
        brand="Apple",
        model="iphone_16_pro",
        storages_gb=("128", "256", "512", "1024"),
        colors=("Titânio-Preto", "Titânio-Branco", "Titânio-Natural", "Titânio-Deserto"),
        reference_url="https://support.apple.com/pt-br/121031",
    ),
    CatalogProduct(
        name="Apple iPhone 16 Pro Max",
        brand="Apple",
        model="iphone_16_pro_max",
        storages_gb=("256", "512", "1024"),
        colors=("Titânio-Preto", "Titânio-Branco", "Titânio-Natural", "Titânio-Deserto"),
        reference_url="https://support.apple.com/pt-br/121032",
    ),
    CatalogProduct(
        name="Apple iPhone 17",
        brand="Apple",
        model="iphone_17",
        storages_gb=("256", "512"),
        colors=("Preto", "Branco", "Azul-Névoa", "Lavanda", "Sálvia"),
        reference_url="https://www.apple.com/br/newsroom/2025/09/apple-introduces-iphone-17/",
        gtins=(("256", "Preto", "195950643428"),),
    ),
    CatalogProduct(
        name="Apple iPhone Air",
        brand="Apple",
        model="iphone_air",
        storages_gb=("256", "512", "1024"),
        colors=("Preto-Espacial", "Branco-Nuvem", "Dourado-Claro", "Azul-Céu"),
        reference_url="https://www.apple.com/br/iphone-air/specs/",
    ),
    CatalogProduct(
        name="Apple iPhone 17 Pro",
        brand="Apple",
        model="iphone_17_pro",
        storages_gb=("256", "512", "1024"),
        colors=("Prateado", "Laranja-Cósmico", "Azul-Intenso"),
        reference_url="https://www.apple.com/pt/iphone-17-pro/specs/",
    ),
    CatalogProduct(
        name="Apple iPhone 17 Pro Max",
        brand="Apple",
        model="iphone_17_pro_max",
        storages_gb=("256", "512", "1024", "2048"),
        colors=("Prateado", "Laranja-Cósmico", "Azul-Intenso"),
        reference_url="https://www.apple.com/pt/iphone-17-pro/specs/",
    ),
    CatalogProduct(
        name="Apple iPhone 18 Pro",
        brand="Apple",
        model="iphone_18_pro",
        storages_gb=("256", "512", "1024", "2048"),
        colors=("Preto", "Prateado", "Glacial", "Bordô"),
        reference_url="https://www.apple.com/br/iphone-18-pro/specs/",
    ),
    CatalogProduct(
        name="Apple iPhone 18 Pro Max",
        brand="Apple",
        model="iphone_18_pro_max",
        storages_gb=("256", "512", "1024", "2048"),
        colors=("Preto", "Prateado", "Glacial", "Bordô"),
        reference_url="https://www.apple.com/br/iphone-18-pro/specs/",
    ),
    CatalogProduct(
        name="Samsung Galaxy S25",
        brand="Samsung",
        model="galaxy_s25",
        storages_gb=("128", "256", "512"),
        colors=("Azul-Gelo", "Azul-Marinho", "Prata", "Verde-Menta", "Preto-Azulado"),
        reference_url="https://www.samsung.com/br/smartphones/galaxy-s25/specs/",
    ),
    CatalogProduct(
        name="Samsung Galaxy S25+",
        brand="Samsung",
        model="galaxy_s25_plus",
        storages_gb=("256", "512"),
        colors=("Azul-Marinho", "Azul-Gelo", "Prata", "Preto-Azulado"),
        reference_url="https://www.samsung.com/br/smartphones/galaxy-s25/specs/",
    ),
    CatalogProduct(
        name="Samsung Galaxy S25 Ultra",
        brand="Samsung",
        model="galaxy_s25_ultra",
        storages_gb=("256", "512", "1024"),
        colors=(
            "Titânio-Azul",
            "Titânio-Preto",
            "Titânio-Cinza",
            "Titânio-Prata",
            "Titânio-Preto-Intenso",
        ),
        reference_url="https://www.samsung.com/br/smartphones/galaxy-s25/specs/",
    ),
    CatalogProduct(
        name="Samsung Galaxy S26",
        brand="Samsung",
        model="galaxy_s26",
        storages_gb=("256", "512"),
        colors=("Violeta", "Azul", "Preto", "Branco", "Prata", "Dourado"),
        reference_url="https://www.samsung.com/br/smartphones/galaxy-s26/specs/",
    ),
    CatalogProduct(
        name="Samsung Galaxy S26+",
        brand="Samsung",
        model="galaxy_s26_plus",
        storages_gb=("256", "512"),
        colors=("Violeta", "Azul", "Preto", "Branco", "Prata", "Dourado"),
        reference_url="https://www.samsung.com/br/smartphones/galaxy-s26/specs/",
    ),
    CatalogProduct(
        name="Samsung Galaxy S26 Ultra",
        brand="Samsung",
        model="galaxy_s26_ultra",
        storages_gb=("256", "512", "1024"),
        colors=("Violeta", "Azul", "Preto", "Branco", "Prata", "Dourado"),
        reference_url="https://www.samsung.com/br/smartphones/galaxy-s26/specs/",
    ),
    CatalogProduct(
        name="Motorola Edge 70 Pro",
        brand="Motorola",
        model="edge_70_pro",
        storages_gb=("256", "512"),
        colors=("Cocoa-Cream", "Titan", "Zinfandel", "Lily-White"),
        reference_url=("https://www.motorola.com.br/smartphone-motorola-edge-70-pro-5g-256gb/p"),
    ),
    CatalogProduct(
        name="Nimbus Phone X",
        brand="Nimbus",
        model="nimbus_phone_x",
        storages_gb=("128", "256"),
        colors=("Preto", "Azul"),
        reference_url=None,
        variant_pairs=(("128", "Preto"), ("256", "Preto"), ("128", "Azul")),
        include_identity_attributes=False,
        gtins=(
            ("128", "Preto", "7891234500018"),
            ("256", "Preto", "7891234500025"),
            ("128", "Azul", "7891234500032"),
        ),
    ),
)
