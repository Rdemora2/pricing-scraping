import scrapy

from pricing_intel.collection.spiders.base import LabStoreSpider


class LabStoreASpider(LabStoreSpider):
    name = "lab_store_a"
    allowed_domains = ("lab-store-a",)
    product_link_css = "a.product-card::attr(href)"
    next_page_css = "a.pagination-next::attr(href)"

    async def start(self):
        yield scrapy.Request(f"{self.base_url}/categoria/smartphones", callback=self.parse_category)
