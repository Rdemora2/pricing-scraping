"""Scrapy project settings — loaded via scrapy.cfg / SCRAPY_SETTINGS_MODULE.

Every politeness/robustness knob a scraping-focused review would look
for is set explicitly here rather than left at Scrapy's defaults.
"""

from pricing_intel.collection.browser import BROWSER_USER_AGENT, CHROME_MAJOR_VERSION
from pricing_intel.config import get_settings

_settings = get_settings()

BOT_NAME = "pricing_intel_collector"

SPIDER_MODULES = ["pricing_intel.collection.spiders"]
NEWSPIDER_MODULE = "pricing_intel.collection.spiders"

# Browser-realistic representation (decisions/0001): headers negotiate the
# same way current desktop Chrome on Windows would, including the low-entropy
# Client Hints Chrome sends unprompted. Accept-Encoding is intentionally left
# to Scrapy's HttpCompressionMiddleware, which only advertises codecs this
# process can actually decode.
USER_AGENT = BROWSER_USER_AGENT
DEFAULT_REQUEST_HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
    "Sec-CH-UA": (
        f'"Chromium";v="{CHROME_MAJOR_VERSION}", "Not_A Brand";v="24", '
        f'"Google Chrome";v="{CHROME_MAJOR_VERSION}"'
    ),
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

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

# Hard wall-clock ceiling per crawl. RetryAfterMiddleware lets a target host
# dictate up to MAX_DELAY_SECONDS of wait per retried request; without this,
# a host that keeps answering 429 with a large Retry-After could stall a
# single crawl — and, since the worker runs one collection job at a time
# (compose.yaml), the whole queue — far longer than any legitimate multi-page
# crawl needs.
CLOSESPIDER_TIMEOUT = 300

ITEM_PIPELINES = {
    "pricing_intel.collection.pipelines.PostgresPipeline": 300,
}

DOWNLOADER_MIDDLEWARES = {
    "pricing_intel.collection.network_policy.OutboundPolicyMiddleware": 50,
    # Priority above RetryMiddleware (550) so it inspects the 429 response and
    # annotates the request before RetryMiddleware clones it for the retry.
    "pricing_intel.collection.retry_policy.RetryAfterMiddleware": 560,
}

# Browser acquisition is opt-in through request metadata. Plain Scrapy requests
# continue through the same handler without launching Chromium.
DOWNLOAD_HANDLERS = {
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    # Chromium's internal user-namespace sandbox is unavailable under the
    # default Docker profile. The worker supplies the outer boundary instead:
    # non-root user, no capabilities, no-new-privileges and read-only rootfs.
    "chromium_sandbox": False,
    "timeout": 15_000,
}
PLAYWRIGHT_MAX_CONTEXTS = 1
PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 1
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 15_000

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

LOG_LEVEL = _settings.log_level
TELNETCONSOLE_ENABLED = False
REMOTE_CONTROL_ENABLED = False
