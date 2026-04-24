"""
evals/runner.py

Eval harness for Karen — Dunkin' deployment.

Loads test cases filtered by flow, runs each case turn by turn through
Karen using the same Conversation class and code paths as production,
judges each turn with the LLM-as-judge from judge.py, checks final
conversation state, and prints a readable report.

Usage:
    python -m evals.runner --flow refund_request
    python -m evals.runner --flow exchange_request
    python -m evals.runner --flow employee_complaint
    python -m evals.runner --flow mobile_app_issue

Valid flow names:
    refund_request
    exchange_request
    employee_complaint
    mobile_app_issue

Design principles:
    - Always runs all turns in a case, even if Karen fails early. Stopping
      mid-case hides information about whether she recovers.
    - One Conversation instance per case. Each case starts fresh — no
      history bleeds between cases.
    - The runner calls the same code paths as production: Conversation.send()
      then extract_email_draft(). It does not call process_response()
      directly — Conversation.send() already does that internally.
    - Judge calls are per-criterion, per-turn. One API call per criterion.
    - Final state is checked with judge_final_state() — pure Python, no API.
"""

import argparse
import sys
from core.conversation import Conversation
from core.capabilities.email_draft import extract_email_draft
from deployments.dunkin.context import DUNKIN_CONTEXT
from evals.judge import judge_turn, judge_final_state
from evals.dunkin_cases import DUNKIN_CASES

# ------------------------------------------------------------
# Valid flows — used for CLI validation and case filtering
# ------------------------------------------------------------

VALID_FLOWS = [
    "refund_request",
    "exchange_request",
    "employee_complaint",
    "mobile_app_issue",
]


# ------------------------------------------------------------
# Case runner
# ------------------------------------------------------------

def run_case(case: dict) -> dict:
    """
    Run a single multi-turn test case through Karen end to end.

    Creates a fresh Conversation, loops through all turns, judges each
    criterion on each turn, tracks escalation and email draft state,
    then judges final state.

    Args:
        case: A test case dict with keys:
            id          — int, unique identifier
            flow        — str, which flow this case exercises
            turns       — list of dicts, each with:
                            user      — str, customer message
                            expected  — list[str], criteria to judge this turn
            final_expected_state — dict, e.g.:
                            {"escalated": False, "email_draft_generated": True}

    Returns a result dict:
        {
            "case_id":        int,
            "flow":           str,
            "turn_results":   list of per-turn verdict dicts,
            "state_result":   judge_final_state() return dict,
            "total_criteria": int,
            "criteria_passed": int,
            "case_passed":    bool,  # True only if all criteria + state pass
        }
    """
    flow = case["flow"]
    turns = case["turns"]
    final_expected_state = case.get("final_expected_state", {})

    # Fresh conversation per case — no history from previous cases
    convo = Conversation(deployment_context=DUNKIN_CONTEXT)

    turn_results = []
    email_draft_generated = False
    escalated_ever = False

    for turn_index, turn in enumerate(turns):
        user_message = turn["user"]
        criteria = turn.get("expected", [])

        # Same code path as production: send() then extract_email_draft()
        reply, escalated = convo.send(user_message)
        cleaned_reply, draft = extract_email_draft(reply)

        # Track state across turns
        if escalated:
            escalated_ever = True
        if draft is not None:
            email_draft_generated = True

        # Judge each criterion for this turn.
        # The judge receives the full reply (before email draft extraction)
        # so it can evaluate draft-related criteria. cleaned_reply is used
        # only for display in the printed report.
        criteria_results = []
        for criterion in criteria:
            verdict = judge_turn(
                response_text=reply,
                criterion=criterion,
                flow=flow,
                turn_index=turn_index,
            )
            criteria_results.append(verdict)

        turn_results.append({
            "turn_index": turn_index,
            "user_message": user_message,
            "karen_reply": cleaned_reply,
            "escalated_this_turn": escalated,
            "email_draft_this_turn": draft is not None,
            "criteria_results": criteria_results,
        })

    # Build actual state and judge it
    actual_state = {
        "escalated": escalated_ever,
        "email_draft_generated": email_draft_generated,
    }
    state_result = judge_final_state(actual_state, final_expected_state)

    # Aggregate counts
    all_criteria = [
        verdict
        for turn in turn_results
        for verdict in turn["criteria_results"]
    ]
    total_criteria = len(all_criteria)
    criteria_passed = sum(1 for v in all_criteria if v["passed"])

    case_passed = (criteria_passed == total_criteria) and state_result["passed"]

    return {
        "case_id": case["id"],
        "flow": flow,
        "turn_results": turn_results,
        "state_result": state_result,
        "total_criteria": total_criteria,
        "criteria_passed": criteria_passed,
        "case_passed": case_passed,
    }


# ------------------------------------------------------------
# Report printer
# ------------------------------------------------------------

def print_report(result: dict) -> None:
    """
    Print a readable report for a single case result.

    Shows pass/fail per criterion with judge reasoning on failures,
    final state check, and an overall case verdict.
    """
    case_id = result["case_id"]
    flow = result["flow"]
    case_passed = result["case_passed"]
    criteria_passed = result["criteria_passed"]
    total_criteria = result["total_criteria"]

    print()
    print(f"{'=' * 60}")
    print(f"  CASE {case_id} — {flow}")
    print(f"{'=' * 60}")

    for turn in result["turn_results"]:
        turn_num = turn["turn_index"] + 1
        print()
        print(f"  Turn {turn_num}")
        print(f"  Customer: {turn['user_message']}")
        print(f"  Karen:    {turn['karen_reply'][:120]}{'...' if len(turn['karen_reply']) > 120 else ''}")

        if not turn["criteria_results"]:
            print("  (no criteria for this turn)")
            continue

        print()
        for verdict in turn["criteria_results"]:
            icon = "✓" if verdict["passed"] else "✗"
            print(f"    {icon} {verdict['criterion']}")
            if not verdict["passed"]:
                print(f"      → {verdict['reasoning']}")

    # Final state
    print()
    print("  Final State")
    state = result["state_result"]
    if state["passed"]:
        print("    ✓ All state checks passed")
        for key, val in state["expected"].items():
            print(f"      {key}: {val}")
    else:
        for key, val in state["expected"].items():
            actual_val = state["actual"].get(key)
            if actual_val == val:
                print(f"    ✓ {key}: {val}")
            else:
                print(f"    ✗ {key}: expected {val}, got {actual_val}")

    # Case verdict
    print()
    verdict_label = "PASSED" if case_passed else "FAILED"
    print(f"  CASE RESULT: {verdict_label} ({criteria_passed}/{total_criteria} criteria passed)")
    print()


def print_summary(results: list[dict], flow: str) -> None:
    """
    Print a summary across all cases for this flow run.
    """
    total_cases = len(results)
    cases_passed = sum(1 for r in results if r["case_passed"])
    total_criteria = sum(r["total_criteria"] for r in results)
    criteria_passed = sum(r["criteria_passed"] for r in results)

    print(f"{'=' * 60}")
    print(f"  SUMMARY — {flow}")
    print(f"{'=' * 60}")
    print(f"  Cases:    {cases_passed}/{total_cases} passed")
    print(f"  Criteria: {criteria_passed}/{total_criteria} passed")

    failed = [r for r in results if not r["case_passed"]]
    if failed:
        print()
        print("  Failed cases:")
        for r in failed:
            print(f"    Case {r['case_id']}: {r['criteria_passed']}/{r['total_criteria']} criteria, "
                  f"state {'✓' if r['state_result']['passed'] else '✗'}")
    print()


# ------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run Karen evals for a specific flow.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join([
            "Examples:",
            "  python -m evals.runner --flow refund_request",
            "  python -m evals.runner --flow employee_complaint",
        ]),
    )
    parser.add_argument(
        "--flow",
        required=True,
        choices=VALID_FLOWS,
        help="Which flow to evaluate. One of: " + ", ".join(VALID_FLOWS),
    )
    args = parser.parse_args()

    # Filter cases to the requested flow
    cases = [c for c in DUNKIN_CASES if c["flow"] == args.flow]

    if not cases:
        print(f"No cases found for flow: {args.flow}")
        print(f"Check evals/dunkin_cases.py — make sure cases have flow='{args.flow}'")
        sys.exit(1)

    print()
    print(f"Running {len(cases)} case(s) for flow: {args.flow}")
    print(f"Model: gpt-4o-mini")

    results = []
    for case in cases:
        print(f"\nRunning case {case['id']}...", end="", flush=True)
        result = run_case(case)
        results.append(result)
        print(" done.")
        print_report(result)

    print_summary(results, args.flow)


if __name__ == "__main__":
    main()