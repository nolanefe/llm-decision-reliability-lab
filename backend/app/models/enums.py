import enum


class ExperimentStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FailureCategory(str, enum.Enum):
    INVALID_JSON = "invalid_json"
    SCHEMA_ERROR = "schema_error"
    PROVIDER_ERROR = "provider_error"
    TIMEOUT = "timeout"
    CONTENT_MISMATCH = "content_mismatch"
    OTHER = "other"
