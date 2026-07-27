from enum import Enum


class TicketCategory(str, Enum):
    BILLING = "billing"
    ACCOUNT_ACCESS = "account_access"
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    OTHER = "other"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
