import scrapy


class DiscoveredPageItem(scrapy.Item):
    source_id = scrapy.Field()
    url = scrapy.Field()
    canonical_url = scrapy.Field()
    page_type = scrapy.Field()


class ListingItem(scrapy.Item):
    source_id = scrapy.Field()
    run_id = scrapy.Field()
    url = scrapy.Field()
    canonical_url = scrapy.Field()
    http_status = scrapy.Field()
    raw_html = scrapy.Field()
    extractor_name = scrapy.Field()
    extractor_version = scrapy.Field()
    external_listing_id = scrapy.Field()
    seller_external_id = scrapy.Field()
    seller_display_name = scrapy.Field()
    raw_title = scrapy.Field()
    gtin = scrapy.Field()
    attributes = scrapy.Field()
    price_amount = scrapy.Field()
    currency = scrapy.Field()
    availability = scrapy.Field()
    condition = scrapy.Field()
    payment_terms = scrapy.Field()
    shipping = scrapy.Field()
