from typing import TypeVar

T = TypeVar("T")


def require_non_blank(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("must not be blank")
    return stripped


def require_non_empty(values: list[T]) -> list[T]:
    if not values:
        raise ValueError("must contain at least one value")
    return values


def require_unique(values: list[T]) -> list[T]:
    if len(values) != len(set(values)):
        raise ValueError("duplicate values are not allowed")
    return values
