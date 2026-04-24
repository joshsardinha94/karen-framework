"""
Escalation Detection

Karen signals that a conversation should be escalated to a human by ending her
response with the tag [ESCALATION TRIGGERED]. This module handles detecting
that tag robustly (tolerant of case, spacing, and minor formatting variation)
and stripping it cleanly from the response before the customer sees it.

Every deployment should import from here rather than implementing its own tag
detection, so that any future change to the escalation protocol is a one-file
update.
"""

import re

# The pattern matches [ESCALATION TRIGGERED] in a forgiving way:
#   - case-insensitive
#   - tolerates spaces or underscores between the two words
#   - tolerates surrounding whitespace inside the brackets
ESCALATION_PATTERN = re.compile(
    r"\[\s*escalation[\s_]+triggered\s*\]",
    re.IGNORECASE,
)


def detect_escalation(response: str) -> bool:
    """
    Returns True if Karen's response contains the escalation tag.

    Used by deployments to decide whether to route the conversation to a
    human, lock the UI, send a notification, etc.
    """
    return bool(ESCALATION_PATTERN.search(response))


def strip_escalation_tag(response: str) -> str:
    """
    Removes the escalation tag from Karen's response so the customer never
    sees it, and cleans up any leftover whitespace around where the tag was.

    Always call this before displaying Karen's response, regardless of whether
    escalation was triggered — it's a no-op if no tag is present.
    """
    cleaned = ESCALATION_PATTERN.sub("", response)
    return cleaned.strip()


def process_response(response: str) -> tuple[str, bool]:
    """
    Convenience function that does both checks in one call.

    Returns a tuple of (cleaned_response, escalated) where:
      - cleaned_response is the customer-safe version with the tag removed
      - escalated is a boolean indicating whether the tag was present

    This is the function deployments should usually call — it's one line
    instead of two and guarantees you never forget to strip the tag.
    """
    escalated = detect_escalation(response)
    cleaned = strip_escalation_tag(response)
    return cleaned, escalated