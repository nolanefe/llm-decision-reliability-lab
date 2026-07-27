"""Failure explorer: surfaces every Run/Evaluation pair that did not
succeed outright, as bounded, sanitized ``FailureEntry`` records.

Only terminal Run/Evaluation data is considered (a Run always has exactly
one Evaluation once it reaches a terminal status). A Run counts as a
failure whenever its Evaluation has a ``failure_category`` set -- i.e.
everything except a schema-valid Run with both labels correct.

``Run.error_message`` is expected to already be short and provider-neutral
(see ``app.llm.provider.ProviderError``) -- but this module is the one
promising callers a "sanitized" message, so it does not simply trust that
upstream discipline held. Any traceback, absolute filesystem path, or
API-key-shaped token is stripped defensively before the message is
capped, independent of whatever produced it.
"""

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dataset_item import DatasetItem
from app.models.evaluation import Evaluation
from app.models.prompt_version import PromptVersion
from app.models.run import Run
from app.schemas.failure import FailureEntry

_RAW_RESPONSE_PREVIEW_MAX_CHARS = 200
_ERROR_MESSAGE_MAX_CHARS = 200

_TRACEBACK_MARKER = "Traceback (most recent call last):"
_SECRET_LIKE_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]{6,}")
_ABSOLUTE_PATH_PATTERN = re.compile(r"/(?:[\w.-]+/)+[\w.-]+")


def build_failure_entries(db: Session, experiment_id: int) -> list[FailureEntry]:
    rows = db.execute(
        select(Run, Evaluation, DatasetItem, PromptVersion)
        .join(Evaluation, Evaluation.run_id == Run.id)
        .join(DatasetItem, DatasetItem.id == Run.dataset_item_id)
        .join(PromptVersion, PromptVersion.id == Run.prompt_version_id)
        .where(
            Run.experiment_id == experiment_id,
            Evaluation.failure_category.is_not(None),
        )
        .order_by(Run.id)
    ).all()

    return [
        FailureEntry(
            run_id=run.id,
            dataset_item_id=dataset_item.id,
            dataset_item_name=dataset_item.name,
            prompt_version_id=prompt_version.id,
            prompt_version_name=prompt_version.name,
            model_name=run.model_name,
            repetition_index=run.repetition_index,
            run_status=run.status,
            failure_category=evaluation.failure_category,
            schema_valid=evaluation.schema_valid,
            category_correct=evaluation.category_correct,
            priority_correct=evaluation.priority_correct,
            sanitized_error_message=_sanitize_error_message(run.error_message),
            raw_response_preview=_truncate_preview(run.raw_response),
        )
        for run, evaluation, dataset_item, prompt_version in rows
    ]


def _truncate_preview(raw_response: str | None) -> str | None:
    if raw_response is None:
        return None
    return raw_response[:_RAW_RESPONSE_PREVIEW_MAX_CHARS]


def _sanitize_error_message(error_message: str | None) -> str | None:
    if error_message is None:
        return None
    message = error_message
    if _TRACEBACK_MARKER in message:
        # Everything from a traceback onward is provider/SDK internals by
        # definition -- drop it rather than try to redact piecemeal.
        message = message.split(_TRACEBACK_MARKER, 1)[0].rstrip()
    message = _SECRET_LIKE_PATTERN.sub("[redacted]", message)
    message = _ABSOLUTE_PATH_PATTERN.sub("[redacted-path]", message)
    return message[:_ERROR_MESSAGE_MAX_CHARS] or None
