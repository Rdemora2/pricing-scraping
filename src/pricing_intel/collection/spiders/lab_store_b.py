import os

import scrapy

from pricing_intel.collection.spiders.base import LabStoreSpider


class LabStoreBSpider(LabStoreSpider):
    name = "lab_store_b"
    product_link_css = "a.offer-tile::attr(href)"
    next_page_css = 'a[rel="next"]::attr(href)'

    def start_requests(self):
        base_url = os.environ.get("LAB_STORE_B_BASE_URL", "http://lab-store-b:8000")
        yield scrapy.Request(f"{base_url}/c/celulares", callback=self.parse_category)
