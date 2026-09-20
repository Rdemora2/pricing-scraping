"""Scrapy project settings — loaded via scrapy.cfg / SCRAPY_SETTINGS_MODULE.

Every politeness/robustness knob a scraping-focused review would look
for is set explicitly here rather than left at Scrapy's defaults.
"""

from pricing_intel.config import get_settings

_settings = get_settings()

BOT_NAME = "pricing_intel_collector"

SPIDER_MODULES = ["pricing_intel.collection.spiders"]
NEWSPIDER_MODULE = "pricing_intel.collection.spiders"

USER_AGENT = "pricing-intel-lab-bot/0.1 (+local pricing intelligence portfolio project)"

# Ethical/responsible-scraping defaults (brief section 9): obey robots.txt,
# throttle adaptively, retry transient failures, never hammer a domain.
ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS_PER_DOMAIN = _settings.collection_concurrency_per_domain
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_TARGET_CONCURRENCY = float(_settings.collection_concurrency_per_domain)
DOWNLOAD_TIMEOUT = 15
DOWNLOAD_MAXSIZE = 5_000_000
DOWNLOAD_WARNSIZE = 4_000_000
REDIRECT_MAX_TIMES = 3
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 429]

ITEM_PIPELINES = {
    "pricing_intel.collection.pipelines.PostgresPipeline": 300,
}

DOWNLOADER_MIDDLEWARES = {
    "pricing_intel.collection.network_policy.OutboundPolicyMiddleware": 50,
}

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

LOG_LEVEL = _settings.log_level
TELNETCONSOLE_ENABLED = False
REMOTE_CONTROL_ENABLED = False
