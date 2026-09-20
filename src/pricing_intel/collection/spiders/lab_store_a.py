import os

import scrapy

from pricing_intel.collection.spiders.base import LabStoreSpider


class LabStoreASpider(LabStoreSpider):
    name = "lab_store_a"
    product_link_css = "a.product-card::attr(href)"
    next_page_css = "a.pagination-next::attr(href)"

    def start_requests(self):
        base_url = os.environ.get("LAB_STORE_A_BASE_URL", "http://lab-store-a:8000")
        yield scrapy.Request(f"{base_url}/categoria/smartphones", callback=self.parse_category)
