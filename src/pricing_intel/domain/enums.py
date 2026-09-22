from enum import StrEnum


class SourceKind(StrEnum):
    LAB_SIMULATED = "lab_simulated"
    REAL = "real"


class SourceStatus(StrEnum):
    """Lifecycle of a scraping source, per the candidate-to-enabled policy.

    A source never starts as ENABLED on its own — see docs/architecture.md
    ("Política de habilitação de fontes").
    """

    CANDIDATE = "candidate"
    ENABLED = "enabled"
    DISABLED = "disabled"


class PageType(StrEnum):
    CATEGORY = "category"
    PRODUCT = "product"


class DiscoveredPageStatus(StrEnum):
    PENDING = "pending"
    COLLECTED = "collected"
    FAILED = "failed"


class RunTrigger(StrEnum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class RunStatus(StrEnum):
    """Matches docs/architecture.md's job state machine.

    PARTIAL means the run finished but not every discovered page was
    collected successfully — it is a completion outcome, not a failure.
    """

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL = "partial"


class RejectionStage(StrEnum):
    """Where a scraped listing stopped short of becoming a comparable offer.

    ACCESS covers a page the source refused to serve; EXTRACTION covers a page
        or entry the adapter refused to read as an offer; MATCHING covers an offer
        that was read but corresponds to no canonical variant. Together they make
        the three ways a run loses a retailer distinguishable: the source blocked
        us, the source changed shape, or our catalog does not describe what the
        source is selling.
    """

    ACCESS = "access"
    EXTRACTION = "extraction"
    MATCHING = "matching"


class EvidenceType(StrEnum):
    DISCOVERY_PAGE = "discovery_page"
    LISTING_PAGE = "listing_page"


class Condition(StrEnum):
    NEW = "new"
    USED = "used"
    REFURBISHED = "refurbished"
    UNKNOWN = "unknown"


class Availability(StrEnum):
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    UNKNOWN = "unknown"


class PriceBasis(StrEnum):
    """Commercial meaning of the displayed price."""

    ADVERTISED = "advertised"
    CASH = "cash"
    INSTALLMENT = "installment"
    CONDITIONAL = "conditional"


class MatchMethod(StrEnum):
    RULE_GTIN_EXACT = "rule:gtin_exact"
    RULE_ATTRIBUTES = "rule:attributes"
    MANUAL = "manual"
