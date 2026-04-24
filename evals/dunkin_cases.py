"""
evals/dunkin_cases.py

Multi-turn test cases for Karen — Dunkin' Putnam Valley deployment.

Each case represents a realistic customer interaction drawn from actual
franchise manager experience. Cases are organized by flow and designed
to test both the happy path and meaningful edge cases within each flow.

Case structure:
    {
        "id":    int — unique across all cases
        "flow":  str — matches a VALID_FLOWS entry in runner.py
        "turns": list of dicts, each with:
                    "user":     str — customer message this turn
                    "expected": list[str] — criteria the judge evaluates
                                Karen's response against this turn
        "final_expected_state": dict — structural outcomes expected after
                                all turns complete:
                    "escalated":             bool
                    "email_draft_generated": bool
    }

Criteria writing standard:
    Criteria test whether the conversation advanced correctly — not whether
    Karen used specific words or phrasing. The question is always: did the
    right thing happen? Not: did she say it exactly this way?

    Tone criteria are intentionally minimal. Karen is allowed to be warm,
    empathetic, and use natural language. Tone criteria only appear when
    there is a specific behavioral risk — e.g., matching hostility, or
    rushing past a customer's story in the employee_complaint flow.

Cases per flow:
    refund_request:     3 cases (polite, angry, edge case — mostly consumed)
    exchange_request:   3 cases (clean path, no receipt, mid-flow pivot)
    employee_complaint: 2 cases (broad opener, full story / serious conduct)
    mobile_app_issue:   2 cases (wrong store, frustrated customer)
"""

DUNKIN_CASES = [

    # ===========================================================
    # FLOW: refund_request
    # ===========================================================

    {
        "id": 1,
        "flow": "refund_request",
        "turns": [
            {
                "user": (
                    "Hi, I ordered a large iced coffee this morning and it tasted "
                    "completely off — like the milk had turned. I didn't finish it. "
                    "I was hoping to get a refund."
                ),
                "expected": [
                    "Karen explained that refunds are handled by the manager.",
                    "Karen offered to send the details to the manager by email "
                    "on the customer's behalf.",
                    "Karen did not promise the refund would be approved.",
                ],
            },
            {
                "user": "Yes, that works for me.",
                "expected": [
                    "Karen asked for the customer's full name and email address.",
                ],
            },
            {
                "user": "Sure, it's Maria Lopez, maria.lopez@gmail.com.",
                "expected": [
                    "Karen asked if there is anything else the customer would "
                    "like the manager to know before drafting the email.",
                ],
            },
            {
                "user": "No, that's everything.",
                "expected": [
                    "Karen produced an email draft.",
                    "The draft was addressed to refunds@dunkinputnamvalley.com.",
                    "The draft subject line referenced a refund request.",
                    "The draft included the customer's name and email address.",
                    "Karen asked the customer to confirm the draft before sending.",
                ],
            },
            {
                "user": "That looks good, go ahead and send it.",
                "expected": [
                    "Karen confirmed the email has been sent.",
                    "Karen told the customer to expect a response within "
                    "1 business day.",
                ],
            },
        ],
        "final_expected_state": {
            "escalated": False,
            "email_draft_generated": True,
        },
    },

    {
        "id": 2,
        "flow": "refund_request",
        "turns": [
            {
                "user": (
                    "I want my money back. I ordered a bacon egg and cheese and "
                    "there was NO egg on it. This is ridiculous, this happens every "
                    "time I come in. I want to talk to someone who can actually help me."
                ),
                "expected": [
                    "Karen remained calm and professional without matching the "
                    "customer's hostility or becoming defensive.",
                    "Karen did not promise the refund would be approved.",
                    "Karen explained that refunds are handled by the manager "
                    "and offered to send the details by email.",
                ],
            },
            {
                "user": "Fine. Whatever. Yes.",
                "expected": [
                    "Karen asked for the customer's full name and email address.",
                ],
            },
            {
                "user": "James Ruiz. james.ruiz@hotmail.com",
                "expected": [
                    "Karen asked if there is anything else the customer would "
                    "like the manager to know before drafting the email.",
                ],
            },
            {
                "user": (
                    "Yeah — tell them this isn't the first time this has happened "
                    "to me. I come in almost every week."
                ),
                "expected": [
                    "Karen produced an email draft.",
                    "The draft incorporated the detail that this has happened "
                    "before and that the customer is a frequent visitor.",
                    "Karen asked the customer to confirm the draft before sending.",
                ],
            },
            {
                "user": "Yes send it.",
                "expected": [
                    "Karen confirmed the email has been sent.",
                    "Karen told the customer to expect a response within "
                    "1 business day.",
                ],
            },
        ],
        "final_expected_state": {
            "escalated": False,
            "email_draft_generated": True,
        },
    },

    {
        "id": 3,
        "flow": "refund_request",
        "turns": [
            {
                "user": (
                    "Hey, I got a breakfast sandwich this morning and honestly it "
                    "was pretty bad — the bread was stale and it tasted like it had "
                    "been sitting out. I did eat most of it because I was hungry and "
                    "in a rush, but I still think I should get my money back."
                ),
                "expected": [
                    "Karen did not dismiss or challenge the customer's request "
                    "despite the product being mostly consumed.",
                    "Karen explained that refunds are handled by the manager.",
                    "Karen offered to send the details to the manager by email.",
                    "Karen did not promise the refund would be approved.",
                ],
            },
            {
                "user": "Yes please, I'd appreciate that.",
                "expected": [
                    "Karen asked for the customer's full name and email address.",
                ],
            },
            {
                "user": "Priya Nair, priya.nair@gmail.com.",
                "expected": [
                    "Karen asked if there is anything else the customer would "
                    "like the manager to know before drafting the email.",
                ],
            },
            {
                "user": "No that's it.",
                "expected": [
                    "Karen produced an email draft.",
                    "The draft was addressed to refunds@dunkinputnamvalley.com.",
                    "The draft accurately described the customer's complaint.",
                    "Karen asked the customer to confirm the draft before sending.",
                ],
            },
            {
                "user": "Looks good.",
                "expected": [
                    "Karen confirmed the email has been sent.",
                    "Karen told the customer to expect a response within "
                    "1 business day.",
                ],
            },
        ],
        "final_expected_state": {
            "escalated": False,
            "email_draft_generated": True,
        },
    },


    # ===========================================================
    # FLOW: exchange_request
    # ===========================================================

    {
        "id": 4,
        "flow": "exchange_request",
        "turns": [
            {
                "user": (
                    "I ordered a medium hot coffee this morning and it was way too "
                    "sweet — I think they put the wrong flavor shot in it. I didn't "
                    "drink much of it. Can I come in and swap it for the right one?"
                ),
                "expected": [
                    "Karen communicated both requirements for an in-store "
                    "exchange: the receipt and the unconsumed product.",
                    "Karen asked whether the customer can come in with both — "
                    "as a single question, not a checklist.",
                ],
            },
            {
                "user": "Yeah I have the receipt and most of the coffee is still there.",
                "expected": [
                    "Karen directed the customer to come into the store with "
                    "the receipt and the product.",
                    "Karen told them to speak with a manager or employee and "
                    "reference this conversation.",
                    "Karen reminded them to keep the receipt.",
                ],
            },
        ],
        "final_expected_state": {
            "escalated": False,
            "email_draft_generated": False,
        },
    },

    {
        "id": 5,
        "flow": "exchange_request",
        "turns": [
            {
                "user": (
                    "I got a dozen donuts this morning and at least three of them "
                    "were completely smashed — like they were dropped or something. "
                    "I want to exchange them for ones that aren't destroyed."
                ),
                "expected": [
                    "Karen communicated both requirements for an in-store "
                    "exchange: the receipt and the product.",
                    "Karen asked whether the customer can come in with both.",
                ],
            },
            {
                "user": "I don't have the receipt, I paid cash.",
                "expected": [
                    "Karen communicated that without a receipt, an in-store "
                    "exchange is not possible.",
                    "Karen offered the email route to the manager as an "
                    "alternative path forward.",
                ],
            },
            {
                "user": "Okay sure, let's do the email.",
                "expected": [
                    "Karen asked for the customer's full name and email address.",
                ],
            },
            {
                "user": "Tony Greco, tgreco@yahoo.com.",
                "expected": [
                    "Karen asked if there is anything else the customer would "
                    "like the manager to know before drafting the email.",
                ],
            },
            {
                "user": "Nope.",
                "expected": [
                    "Karen produced an email draft.",
                    "The draft was addressed to refunds@dunkinputnamvalley.com.",
                    "The draft included the customer's name and email address.",
                    "Karen asked the customer to confirm the draft before sending.",
                ],
            },
            {
                "user": "That's fine, send it.",
                "expected": [
                    "Karen confirmed the email has been sent.",
                    "Karen told the customer to expect a response within "
                    "1 business day.",
                ],
            },
        ],
        "final_expected_state": {
            "escalated": False,
            "email_draft_generated": True,
        },
    },

    {
        "id": 6,
        "flow": "exchange_request",
        "turns": [
            {
                "user": (
                    "My order was completely wrong this morning — I ordered an "
                    "everything bagel with cream cheese and got a plain bagel with "
                    "butter. I want to exchange it."
                ),
                "expected": [
                    "Karen communicated both requirements for an in-store "
                    "exchange: the receipt and the product.",
                    "Karen asked whether the customer can come in with both.",
                ],
            },
            {
                "user": (
                    "I have the receipt but I already ate it — I was starving. "
                    "Actually, you know what, can I just get a refund instead?"
                ),
                "expected": [
                    "Karen recognized the pivot from exchange to refund and "
                    "transitioned cleanly to the refund path.",
                    "Karen did not ask the customer to re-explain what happened — "
                    "she carried the complaint context forward.",
                    "Karen explained that refunds are handled by the manager "
                    "and offered to send the details by email.",
                ],
            },
            {
                "user": "Yes please.",
                "expected": [
                    "Karen asked for the customer's full name and email address.",
                ],
            },
            {
                "user": "Sandra Kim, sandrakim@gmail.com.",
                "expected": [
                    "Karen asked if there is anything else the customer would "
                    "like the manager to know before drafting the email.",
                ],
            },
            {
                "user": "No, that's all.",
                "expected": [
                    "Karen produced an email draft.",
                    "The draft was addressed to refunds@dunkinputnamvalley.com.",
                    "The draft included the customer's name and email address.",
                    "Karen asked the customer to confirm the draft before sending.",
                ],
            },
            {
                "user": "Looks good, send it.",
                "expected": [
                    "Karen confirmed the email has been sent.",
                    "Karen told the customer to expect a response within "
                    "1 business day.",
                ],
            },
        ],
        "final_expected_state": {
            "escalated": False,
            "email_draft_generated": True,
        },
    },

    # ===========================================================
    # FLOW: employee_complaint
    # ===========================================================

    {
        "id": 7,
        "flow": "employee_complaint",
        "turns": [
            {
                "user": "One of your employees was really rude to me this morning.",
                "expected": [
                    "Karen gave the customer space to share what happened rather "
                    "than immediately launching into information-gathering questions.",
                ],
            },
            {
                "user": (
                    "I was at the drive-through and I asked the cashier a question "
                    "about the menu and she literally rolled her eyes at me and "
                    "sighed like I was wasting her time. In front of other customers. "
                    "I've never been treated like that there before."
                ),
                "expected": [
                    "Karen affirmed that this kind of behavior is not acceptable "
                    "or representative of how the store operates.",
                ],
            },
            {
                "user": "I don't know her name. It was today around 8am.",
                "expected": [
                    "Karen asked for the customer's full name and email address, transitioning to the email escalation flow.",
                ],
            },
            {
                "user": "Denise Farrow, dfarrow@gmail.com.",
                "expected": [
                    "Karen asked if there is anything else the customer would "
                    "like the manager to know before drafting the email.",
                ],
            },
            {
                "user": "No, I think that covers it.",
                "expected": [
                    "The text '[EMAIL DRAFT]' appears in Karen's response.",
                    "The draft subject line referenced an employee complaint.",
                    "The draft accurately described the incident.",
                    "Karen's response contained a question that gave the customer a chance to add anything before the draft",
                ],
            },
            {
                "user": "Yes that's accurate. Send it.",
                "expected": [
                    "Karen confirmed the email has been sent.",
                    "Karen told the customer to expect a response within "
                    "1 business day.",
                ],
            },
        ],
        "final_expected_state": {
            "escalated": False,
            "email_draft_generated": True,
        },
    },

    {
        "id": 8,
        "flow": "employee_complaint",
        "turns": [
            {
                "user": (
                    "I need to report something serious. I was just at your store "
                    "and one of your employees — I think his name was Marco — "
                    "screamed at me in front of the whole store because I asked to "
                    "have my order corrected. He got right up in my face. I've never "
                    "been so humiliated in my life. This happened maybe 20 minutes ago."
                ),
                "expected": [
                    "Karen affirmed this is not how the store operates.",
                ],
            },
            {
                "user": "I don't have any other details to give.",
                "expected": [
                    "Karen asked for the customer's full name and email address.",
                ],
            },
            {
                "user": "Raymond Holt, raymond.holt@gmail.com.",
                "expected": [
                    "Karen asked if there is anything else the customer would "
                    "like the manager to know before drafting the email.",
                ],
            },
            {
                "user": "Just that I want a follow-up. I don't want this ignored.",
                "expected": [
                    "The text '[EMAIL DRAFT]' appears in Karen's response.",
                    "The draft incorporated the customer's request for a follow-up.",
                    "The draft accurately described the serious nature of the incident.",
                    "The draft subject line referenced an employee complaint.",
                    "Karen asked the customer to confirm the draft before sending.",
                ],
            },
            {
                "user": "Yes, send it.",
                "expected": [
                    "Karen confirmed the email has been sent.",
                    "Karen told the customer to expect a response within "
                    "1 business day.",
                ],
            },
        ],
        "final_expected_state": {
            "escalated": False,
            "email_draft_generated": True,
        },
    },

    # ===========================================================
    # FLOW: mobile_app_issue
    # ===========================================================

    {
        "id": 9,
        "flow": "mobile_app_issue",
        "turns": [
            {
                "user": (
                    "I placed a mobile order this morning but it went to the wrong "
                    "Dunkin' — I meant to order for Putnam Valley but it sent to "
                    "the one in Carmel. By the time I realized it I was already at "
                    "your store. The order was never picked up."
                ),
                "expected": [
                    "Karen explained that app-related issues are best handled "
                    "in person at the store where an employee or manager can "
                    "help directly.",
                    "Karen encouraged the customer to come in and speak with "
                    "any employee or manager.",
                    "Karen reminded the customer it is a family-owned location "
                    "and the team is happy to help.",
                ],
            },
        ],
        "final_expected_state": {
            "escalated": False,
            "email_draft_generated": False,
        },
    },

    {
        "id": 10,
        "flow": "mobile_app_issue",
        "turns": [
            {
                "user": (
                    "My DD Perks points from this morning's order never showed up. "
                    "I've been waiting all day and they're just gone. This is the "
                    "second time this month. I'm really frustrated — can you just "
                    "fix it or tell me who can?"
                ),
                "expected": [
                    "Karen explained that app and loyalty account issues are "
                    "best handled in person at the store.",
                    "Karen encouraged the customer to come in when convenient.",
                    "Karen reminded the customer it is a family-owned location "
                    "and the team is happy to help.",
                ],
            },
        ],
        "final_expected_state": {
            "escalated": False,
            "email_draft_generated": False,
        },
    },
]