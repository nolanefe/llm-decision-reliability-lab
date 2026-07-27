"""Prompt template rendering.

``PromptVersion.template_text`` is validated at creation time to contain the
literal ``{ticket_text}`` placeholder (see
``app.schemas.prompt_version.TICKET_TEXT_PLACEHOLDER``), so a persisted
prompt version can never be missing it. Rendering is a plain substring
replacement rather than ``str.format`` so that any other literal ``{``/``}``
characters in a template (e.g. describing a JSON shape) are left untouched.
"""

from app.schemas.prompt_version import TICKET_TEXT_PLACEHOLDER


def render_prompt(template_text: str, ticket_text: str) -> str:
    return template_text.replace(TICKET_TEXT_PLACEHOLDER, ticket_text)
