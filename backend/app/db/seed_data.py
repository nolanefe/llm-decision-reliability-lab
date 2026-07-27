"""Built-in seed content: fixed dataset items and prompt versions.

All ticket text below is fictional and contains no personal information.
"""

DATASET_ITEMS: list[dict] = [
    {
        "name": "billing-duplicate-charge",
        "input_text": (
            "Hi, I just noticed I was charged twice for my monthly subscription "
            "on my last statement. Can you refund the duplicate charge? This is "
            "the second time this has happened and I'm getting frustrated."
        ),
        "expected_category": "billing",
        "expected_priority": "high",
        "reference_summary": "Customer was double-charged for their subscription and wants a refund.",
        "reference_action": "Verify the duplicate charge and issue a refund for the extra amount.",
    },
    {
        "name": "billing-invoice-copy",
        "input_text": (
            "Could someone send me a copy of last month's invoice? I need it "
            "for our expense report and can't find it in my account portal."
        ),
        "expected_category": "billing",
        "expected_priority": "low",
        "reference_summary": "Customer requests a copy of last month's invoice.",
        "reference_action": "Locate and email the requested invoice.",
    },
    {
        "name": "account-locked-out",
        "input_text": (
            "I'm completely locked out of my account after too many failed "
            "login attempts and I have a client presentation in one hour that "
            "requires the dashboard. Please help me get back in immediately."
        ),
        "expected_category": "account_access",
        "expected_priority": "urgent",
        "reference_summary": "Customer is locked out of their account before a time-sensitive presentation.",
        "reference_action": "Unlock the account and verify identity, prioritizing speed.",
    },
    {
        "name": "account-mfa-reset",
        "input_text": (
            "I lost my phone over the weekend and it had my authenticator app "
            "on it, so I can no longer get the two-factor codes to sign in. "
            "How do I reset my MFA?"
        ),
        "expected_category": "account_access",
        "expected_priority": "medium",
        "reference_summary": "Customer lost their MFA device and needs two-factor authentication reset.",
        "reference_action": "Verify identity through an alternate channel and reset MFA enrollment.",
    },
    {
        "name": "bug-export-crash",
        "input_text": (
            "Every time I click the CSV export button on the reports page, the "
            "whole app freezes and I have to reload the tab. This happens on "
            "both Chrome and Firefox and started after the latest update."
        ),
        "expected_category": "bug",
        "expected_priority": "high",
        "reference_summary": "CSV export on the reports page consistently crashes the app after a recent update.",
        "reference_action": "File a bug report for the reports export regression and escalate to engineering.",
    },
    {
        "name": "bug-settings-label-typo",
        "input_text": (
            "Small thing, but the label under Settings > Notifications says "
            "'Recieve emails' instead of 'Receive emails'. Not urgent, just "
            "wanted to flag it."
        ),
        "expected_category": "bug",
        "expected_priority": "low",
        "reference_summary": "Minor spelling error in the notifications settings label.",
        "reference_action": "Log a low-priority ticket to fix the copy typo.",
    },
    {
        "name": "bug-sync-data-missing",
        "input_text": (
            "A whole week of records I uploaded seems to have vanished from my "
            "account after last night's sync. This is critical data for our "
            "team and we need it restored as soon as possible."
        ),
        "expected_category": "bug",
        "expected_priority": "urgent",
        "reference_summary": "A week of uploaded data disappeared from the customer's account after a sync error.",
        "reference_action": "Escalate immediately to check backups and restore the missing data.",
    },
    {
        "name": "feature-request-dark-mode",
        "input_text": (
            "Would love to see a dark mode option added to the web app for "
            "late-night work sessions. Not a big deal if it's not planned, "
            "just wanted to put in the request."
        ),
        "expected_category": "feature_request",
        "expected_priority": "low",
        "reference_summary": "Customer requests a dark mode theme for the web application.",
        "reference_action": None,
    },
    {
        "name": "feature-request-bulk-export",
        "input_text": (
            "Right now I can only export one report at a time, which is slow "
            "when I need a dozen of them for a monthly review. It would help "
            "a lot if we could select multiple reports and export them together."
        ),
        "expected_category": "feature_request",
        "expected_priority": "medium",
        "reference_summary": "Customer wants the ability to bulk export multiple reports at once.",
        "reference_action": None,
    },
    {
        "name": "other-partnership-inquiry",
        "input_text": (
            "I work at a small analytics startup and we're interested in "
            "exploring an API integration partnership with your platform. "
            "Who would be the right person to talk to about this?"
        ),
        "expected_category": "other",
        "expected_priority": "low",
        "reference_summary": "A potential partner is inquiring about API integration opportunities.",
        "reference_action": "Route the inquiry to the partnerships or business development team.",
    },
]


PROMPT_VERSIONS: list[dict] = [
    {
        "name": "baseline-triage",
        "version": 1,
        "description": "Simple structured triage instruction.",
        "template_text": (
            "You are a support ticket triage assistant.\n\n"
            "Read the following support ticket and classify it.\n\n"
            "Ticket:\n{ticket_text}\n\n"
            "Respond with a JSON object with these fields: category, priority, "
            "summary, recommended_action."
        ),
    },
    {
        "name": "explicit-criteria-triage",
        "version": 1,
        "description": (
            "Explicit category and priority definitions with stronger output "
            "constraints."
        ),
        "template_text": (
            "You are a support ticket triage assistant. Classify the ticket "
            "below using these definitions.\n\n"
            "Category (choose exactly one):\n"
            "- billing: payments, charges, invoices, refunds, subscriptions\n"
            "- account_access: login, password, MFA, or account lockout issues\n"
            "- bug: something in the product is broken or behaving incorrectly\n"
            "- feature_request: a request for new or enhanced functionality\n"
            "- other: anything that does not fit the categories above\n\n"
            "Priority (choose exactly one):\n"
            "- low: no urgency, can be handled whenever\n"
            "- medium: should be addressed within a few business days\n"
            "- high: significant impact, should be addressed same day\n"
            "- urgent: blocking the customer right now, needs immediate attention\n\n"
            "Ticket:\n{ticket_text}\n\n"
            "Respond with a JSON object with exactly these fields: category, "
            "priority, summary, recommended_action. Use only the category and "
            "priority values defined above."
        ),
    },
    {
        "name": "defensive-json-triage",
        "version": 1,
        "description": (
            "Emphasizes exact JSON structure, forbids extra fields, and "
            "handles ambiguous tickets conservatively."
        ),
        "template_text": (
            "You are a support ticket triage assistant. You must respond with "
            "a single valid JSON object and nothing else — no markdown, no "
            "code fences, no explanation before or after it.\n\n"
            "The JSON object must contain exactly these four fields and no "
            "others: category, priority, summary, recommended_action.\n\n"
            "category must be exactly one of: billing, account_access, bug, "
            "feature_request, other.\n"
            "priority must be exactly one of: low, medium, high, urgent.\n\n"
            "If the ticket is ambiguous or you are uncertain, choose the "
            "closest matching category, default priority to \"low\" unless "
            "there is clear evidence of urgency, and note the ambiguity in the "
            "summary field. Never invent additional fields.\n\n"
            "Ticket:\n{ticket_text}"
        ),
    },
]
