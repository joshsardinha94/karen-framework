"""
evals/judge.py

LLM-as-judge logic for Karen eval suite.

Two public functions:
    judge_turn(response_text, criterion, flow, turn_index) -> dict
    judge_final_state(actual_state, expected_state) -> dict

judge_turn   — uses GPT-4o-mini to evaluate a single criterion against a
               single Karen response. One API call per criterion. Returns a
               verdict dict with score, passed, reasoning, and metadata.

judge_final_state — pure Python. Compares actual system state (escalated,
                    email_draft_generated) against expected state. No API call.

Design note:
    The judge receives only Karen's identity (abbreviated), the criterion,
    and the response. Flow-specific behavioral rules have been intentionally
    removed. They were redundant with the criteria in dunkin_cases.py and
    were causing the judge to evaluate the entire flow instead of the single
    criterion in front of it. The criterion is self-contained — it already
    contains everything the judge needs to make a call.
"""

import json
from openai import OpenAI

client = OpenAI()

# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------

JUDGE_MODEL = "gpt-4o-mini"
PASS_THRESHOLD = 1.0  # criterion must be fully met to pass

# ------------------------------------------------------------
# Karen's core identity — abbreviated for the judge.
# Gives the judge enough to recognize genuine failures of
# posture and tone without providing a parallel flow spec
# that tempts it to evaluate beyond the criterion.
# ------------------------------------------------------------

KAREN_IDENTITY_FOR_JUDGE = """
Karen is an AI customer service specialist for a family-owned Dunkin' franchise
in Putnam Valley, NY. Key characteristics the judge should know:

- She is warm and professional. Empathetic openings like "I'm sorry to hear
  that" or "I apologize for the experience" are acceptable and expected.
  Only flag tone failures if Karen is genuinely cold, robotic, or dismissive.
- She is operationally honest. She never promises a refund will be approved.
  She escalates on the customer's behalf.
- Conversational continuity is non-negotiable. Short confirmations ("yes",
  "okay", "sure", "fine", "whatever, yes") are treated as agreement.
  After agreement, collecting name and email is the correct next step.
  She never asks the customer to re-explain themselves.
- She treats every customer as an adult with a legitimate concern.
- She never matches hostility with hostility.
- She is the customer's advocate to the manager, not a gatekeeper.
""".strip()

# ------------------------------------------------------------
# Judge prompt template
# ------------------------------------------------------------

JUDGE_PROMPT_TEMPLATE = """
You are evaluating one response from Karen, an AI customer service agent,
within a multi-turn customer service conversation.

============================
CRITICAL RULES — READ FIRST
============================

1. EVALUATE ONLY THIS CRITERION. Do not bring in requirements from other
   criteria or other turns. Each criterion is judged in isolation.

2. EVALUATE ONLY THIS RESPONSE. Do not penalize Karen for things that
   should have happened in earlier turns. Only what is in this response
   is relevant.

3. DO NOT RE-EVALUATE EARLIER TURNS. If the criterion is about something
   in this response — a draft, a question, a confirmation — look only at
   this response. Do not ask whether Karen handled any earlier turn
   correctly. That is not what is being evaluated.

4. TEXT PRESENCE CHECKS ARE LITERAL. If the criterion says a specific
   string or phrase appears in Karen's response, look for that text and
   return met: true if it exists. Do not evaluate anything else.

5. ON TONE: Karen is allowed to be warm and polite, including phrases like
   "I'm sorry to hear that" or "I apologize for the experience." Do NOT
   fail a tone criterion because Karen opened with empathy. Only fail a
   tone criterion if Karen was genuinely cold, robotic, or dismissive.

6. ON FLOW SEQUENCE: When a customer says "yes", "sure", "okay", "fine",
   or any short confirmation, that IS agreement to proceed. Karen asking
   for name and email immediately after is CORRECT — do not penalize her.

7. ON EMAIL DRAFT APPROVAL: The customer agreeing to "send an email"
   earlier in the conversation is NOT the same as approving the draft.
   Karen showing the draft and asking for confirmation is correct and
   required behavior. Never penalize Karen for this.

8. JUDGE WHAT KAREN DID. If the criterion asks whether Karen did something
   and she did it, mark it met — even if her response also included other
   things. Do not fail Karen for doing more than the criterion requires.

============================
KAREN'S CORE IDENTITY
============================
{identity}

============================
CURRENT FLOW: {flow}
============================

============================
CRITERION TO EVALUATE
============================
{criterion}

============================
KAREN'S RESPONSE
============================
{response_text}

============================
YOUR TASK
============================
Evaluate whether Karen's response meets the criterion above.
Apply the critical rules above before forming any judgment.

Respond with a JSON object and nothing else. No preamble, no markdown fences.
Use exactly this structure:

{{"met": true or false, "reasoning": "One or two sentences explaining your verdict. Be specific — reference what Karen said or failed to say."}}
""".strip()


def _build_judge_prompt(response_text: str, criterion: str, flow: str) -> str:
    """
    Build the full judge prompt for a single criterion evaluation.

    Uses a plain string template (not an f-string) to avoid conflicts
    with the JSON braces in the response format instructions.

    The flow name is passed for metadata context only. Flow-specific
    behavioral rules are intentionally excluded — the criterion is
    self-contained and adding a parallel flow spec caused the judge
    to evaluate the entire flow instead of the single criterion.
    """
    return JUDGE_PROMPT_TEMPLATE.format(
        identity=KAREN_IDENTITY_FOR_JUDGE,
        flow=flow,
        criterion=criterion,
        response_text=response_text,
    )


# ------------------------------------------------------------
# Public: judge a single turn against a single criterion
# ------------------------------------------------------------

def judge_turn(
    response_text: str,
    criterion: str,
    flow: str,
    turn_index: int = 0,
) -> dict:
    """
    Evaluate a single Karen response against a single criterion.

    Args:
        response_text:  Karen's full response including any email draft block.
                        The judge needs the full text to evaluate draft-related
                        criteria accurately.
        criterion:      A plain-English behavioral expectation, e.g.
                        "Karen offered to send the details to the manager by email."
        flow:           One of: refund_request, exchange_request,
                        employee_complaint, mobile_app_issue.
                        Passed for metadata only — not used to inject flow rules.
        turn_index:     Which turn in the conversation this is (0-indexed).
                        Used for metadata only, does not affect judgment.

    Returns a dict:
        {
            "turn": int,
            "criterion": str,
            "flow": str,
            "met": bool,
            "score": float,       # 1.0 if met, 0.0 if not
            "passed": bool,       # True if score >= PASS_THRESHOLD
            "reasoning": str,
        }
    """
    prompt = _build_judge_prompt(response_text, criterion, flow)

    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        temperature=0,  # deterministic — we want consistent verdicts
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise evaluator. You respond only with valid JSON. "
                    "No preamble. No explanation outside the JSON object."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    raw = response.choices[0].message.content.strip()

    try:
        verdict = json.loads(raw)
    except json.JSONDecodeError:
        # Judge returned malformed JSON. Record the failure cleanly rather
        # than crashing the runner. The runner should surface this as an
        # error, not a false negative.
        verdict = {
            "met": False,
            "reasoning": f"[JUDGE ERROR] Could not parse judge response: {raw}",
        }

    met = bool(verdict.get("met", False))
    score = 1.0 if met else 0.0

    return {
        "turn": turn_index,
        "criterion": criterion,
        "flow": flow,
        "met": met,
        "score": score,
        "passed": score >= PASS_THRESHOLD,
        "reasoning": verdict.get("reasoning", "[No reasoning returned]"),
    }


# ------------------------------------------------------------
# Public: judge final conversation state (no API call)
# ------------------------------------------------------------

def judge_final_state(actual_state: dict, expected_state: dict) -> dict:
    """
    Compare actual system state against expected state after all turns complete.

    This is a deterministic Python check — no LLM involved. The state values
    tracked are structural outcomes, not behavioral ones.

    Args:
        actual_state:   Dict of observed outcomes from the runner, e.g.
                        {"escalated": False, "email_draft_generated": True}
        expected_state: Dict from the test case definition, same shape.

    Returns a dict:
        {
            "passed": bool,
            "mismatches": list[dict],   # empty if fully passed
            "actual": dict,
            "expected": dict,
        }

    Each mismatch entry looks like:
        {"key": str, "expected": value, "actual": value}
    """
    mismatches = []

    for key, expected_value in expected_state.items():
        actual_value = actual_state.get(key)
        if actual_value != expected_value:
            mismatches.append({
                "key": key,
                "expected": expected_value,
                "actual": actual_value,
            })

    return {
        "passed": len(mismatches) == 0,
        "mismatches": mismatches,
        "actual": actual_state,
        "expected": expected_state,
    }