from app.llm.prompt import render_prompt


class TestRenderPrompt:
    def test_substitutes_ticket_text_placeholder(self) -> None:
        rendered = render_prompt(
            "Classify this ticket:\n{ticket_text}\n\nRespond with JSON.",
            "My account is locked.",
        )

        assert "My account is locked." in rendered
        assert "{ticket_text}" not in rendered

    def test_leaves_other_braces_untouched(self) -> None:
        # Templates that describe a JSON shape may contain other literal
        # braces; only the {ticket_text} placeholder should be substituted.
        template = "Ticket: {ticket_text}\nRespond as {\"category\": ..., \"priority\": ...}"

        rendered = render_prompt(template, "Refund please.")

        assert "Refund please." in rendered
        assert '{"category": ..., "priority": ...}' in rendered

    def test_missing_placeholder_cannot_occur_through_validated_records(self) -> None:
        # PromptVersionCreate rejects any template_text without the literal
        # {ticket_text} placeholder, so a persisted PromptVersion always has
        # it. render_prompt itself is a plain substitution with no special
        # handling required for a missing placeholder.
        from pydantic import ValidationError

        from app.schemas.prompt_version import PromptVersionCreate

        try:
            PromptVersionCreate(
                name="no-placeholder",
                version=1,
                template_text="Classify this ticket with no placeholder.",
            )
        except ValidationError:
            pass
        else:
            raise AssertionError("expected ValidationError for missing placeholder")
