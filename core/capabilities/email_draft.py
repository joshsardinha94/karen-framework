"""
Email Draft Capability

A reusable capability that extracts structured email drafts from Karen's
responses. Any deployment that needs Karen to draft emails — for refund
escalation, appointment confirmation, ticket creation, whatever — can
import this module rather than reimplementing the extraction logic.

Karen signals an email draft by wrapping it in [EMAIL DRAFT] ... [END EMAIL
DRAFT] markers. This module detects those markers, extracts the content,
and separates the draft from the rest of Karen's reply so deployments can
render them differently (e.g., the reply as chat text, the draft as a
structured preview the customer can approve or edit).

Deployments are responsible for:
  - Including email-drafting instructions in their context.py prompt.
  - Deciding what to do with the extracted draft (show it, send it, save it).

This module is responsible for:
  - Reliably detecting and extracting the draft.
  - Parsing the draft into structured fields (To / Subject / Body).
  - Providing a clean "reply text minus the draft" for display.
"""

import re
from dataclasses import dataclass
from typing import Optional


# Pattern is case-insensitive and tolerant of minor whitespace variation
# around the markers. re.DOTALL lets "." match newlines so the draft body
# can span multiple lines.
EMAIL_DRAFT_PATTERN = re.compile(
    r"\[\s*email[\s_]+draft\s*\](.*?)\[\s*end[\s_]+email[\s_]+draft\s*\]",
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class EmailDraft:
    """
    A parsed email draft extracted from Karen's response.

    to:      The recipient address (usually a deployment-configured inbox).
    subject: Karen's generated subject line.
    body:    The full email body, including greeting and sign-off.
    raw:     The original unparsed draft content, kept for debugging.
    """
    to: str
    subject: str
    body: str
    raw: str


def extract_email_draft(response: str) -> tuple[str, Optional[EmailDraft]]:
    """
    Extract an email draft from Karen's response, if one is present.

    Args:
        response: Karen's raw reply, potentially containing an
            [EMAIL DRAFT] ... [END EMAIL DRAFT] block.

    Returns:
        (cleaned_response, draft):
            cleaned_response is the reply with the draft block removed,
            suitable for displaying to the customer as chat text.
            draft is an EmailDraft object if one was found, otherwise None.

    If no draft is present, the response is returned unchanged and draft
    is None. Deployments should always check for None before using the draft.
    """
    match = EMAIL_DRAFT_PATTERN.search(response)
    if not match:
        return response, None

    raw_draft = match.group(1).strip()
    draft = _parse_draft(raw_draft)

    # Remove the draft block from the response and tidy whitespace.
    cleaned = response[: match.start()] + response[match.end():]
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    return cleaned, draft


def _parse_draft(raw: str) -> EmailDraft:
    """
    Parse the content of a draft block into structured fields.

    Expects the model to produce content roughly in the form:

        To: someone@example.com
        Subject: Something descriptive
        Body:
        Hi there,
        ...full email body...
        — Karen

    Missing fields are returned as empty strings rather than raising, so
    a partially-formed draft still surfaces useful information to the
    deployment rather than crashing the response.
    """
    to = _extract_field(raw, "to")
    subject = _extract_field(raw, "subject")
    body = _extract_body(raw)
    return EmailDraft(to=to, subject=subject, body=body, raw=raw)


def _extract_field(raw: str, field_name: str) -> str:
    """
    Pull a single-line field (To, Subject) out of the draft text.

    Matches "FieldName: value" case-insensitively, stopping at the next
    newline. Returns an empty string if the field is missing.
    """
    pattern = re.compile(
        rf"^\s*{field_name}\s*:\s*(.+)$",
        re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(raw)
    return match.group(1).strip() if match else ""


def _extract_body(raw: str) -> str:
    """
    Pull the Body field out of the draft text. The body spans multiple
    lines, so we match "Body:" and take everything after it to end of draft.
    """
    pattern = re.compile(
        r"^\s*body\s*:\s*(.*)",
        re.IGNORECASE | re.DOTALL | re.MULTILINE,
    )
    match = pattern.search(raw)
    return match.group(1).strip() if match else ""