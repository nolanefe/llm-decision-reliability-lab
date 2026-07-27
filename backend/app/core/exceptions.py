class NotFoundError(Exception):
    """Raised when a requested resource does not exist."""


class ConflictError(Exception):
    """Raised when a create operation would violate a uniqueness constraint."""


class UnprocessableEntityError(Exception):
    """Raised when request data references other resources that do not exist."""


class ProviderUnavailableError(Exception):
    """Raised when the configured LLM provider cannot be used (e.g. no API key)."""


class OrchestrationError(Exception):
    """Raised when experiment execution fails for a reason outside normal
    per-run provider/output handling (e.g. an unrecoverable database or
    programming error mid-execution)."""
