import scrapy

from pricing_intel.collection.spiders.base import LabStoreSpider


class LabStoreBSpider(LabStoreSpider):
    name = "lab_store_b"
    allowed_domains = ("lab-store-b",)
    product_link_css = "a.offer-tile::attr(href)"
    next_page_css = 'a[rel="next"]::attr(href)'

    async def start(self):
        yield scrapy.Request(f"{self.base_url}/c/celulares", callback=self.parse_category)
