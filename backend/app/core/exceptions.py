class NotFoundError(Exception):
    """Raised when a requested resource does not exist."""


class ConflictError(Exception):
    """Raised when a create operation would violate a uniqueness constraint."""


class UnprocessableEntityError(Exception):
    """Raised when request data references other resources that do not exist."""
