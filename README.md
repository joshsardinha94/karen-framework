\# Karen — An Agent Framework for White-Label Customer Service



\*\*Live demo:\*\* \[https://karendemo.com](https://karendemo.com)



Karen is a customer service agent framework with a clean separation between core identity and deployment context. The core — how Karen talks, how she holds a conversation, how she escalates — is defined once. Company-specific resolution flows, policies, and operational procedures live in swappable deployment contexts. Onboarding a new customer means writing a new context file; the core code does not change.



The production deployment serves a family-owned Dunkin' Donuts franchise. The resolution flows are drawn from four years of real franchise management experience rather than speculation about what customer service "should" look like.



\---



\## What's interesting about how it's built



The architecturally notable decision is that identity and context are written in different mediums.



Identity is prose, because posture, tone, and worldview live in connotation and natural language is the right vehicle. It lives in `core/identity.py`.



Resolution flows are \*\*pseudocode state machines\*\* with explicit states, explicit transitions, and parameterized sub-procedures. They live in `deployments/<company>/context.py`. I arrived at this medium because I discovered by building that models follow state machines much more reliably than they follow numbered steps in prose, especially as the prompt grows in complexity.



Several flows — refunds, exchanges, and employee complaints — all terminate in the same downstream procedure (collect contact info, offer a final check, draft an email, handle approval). Rather than duplicate that logic, it's extracted as a shared `email\_escalation\_flow` that invoking flows call by name with a parameter:



```

GOTO email\_escalation\_flow(request\_type="Refund Request")

GOTO email\_escalation\_flow(request\_type="Exchange Request")

```



The parameter controls the email subject line. The model interprets this routing reliably even though the syntax isn't standard — it's pseudocode invented for this project.



\---



\## Project structure



```

karen-framework/

├── core/

│   ├── identity.py             # KAREN\_CORE — universal identity prompt

│   ├── escalation.py           # Tag detection / stripping

│   ├── conversation.py         # Conversation class — wraps API calls + history

│   └── capabilities/

│       └── email\_draft.py      # Reusable email-draft extraction

├── deployments/

│   └── dunkin/

│       ├── context.py          # DUNKIN\_CONTEXT — state-machine resolution flows

│       ├── app.py              # Flask backend (stateless, frontend holds history)

│       └── index.html          # Dunkin-branded chat UI with email card rendering

├── evals/

│   ├── judge.py                # LLM-as-judge (per-criterion, per-turn)

│   ├── runner.py               # Multi-turn eval harness

│   └── dunkin\_cases.py         # Multi-turn test cases drawn from real scenarios

├── .env                        # Not committed — your OpenAI API key goes here

├── requirements.txt

└── README.md

```



\---



\## Resolution flows (Dunkin deployment)



The Dunkin deployment defines four flows as state machines:



| Flow | Triggered by | Terminates at |

|---|---|---|

| `refund\_request` | Customer wants their money back | Email escalation to manager |

| `exchange\_request` | Customer wants product replaced | In-store visit OR email escalation |

| `employee\_complaint` | Customer reports staff misconduct | Email escalation to manager |

| `mobile\_app\_issue` | Customer reports app problems | Redirect to in-store resolution |



Universal rules handle cross-flow behaviors: low-information responses ("yes", "sure") are interpreted against Karen's most recent question; explicit manager requests preempt any flow; mid-flow preference changes (refund → exchange or exchange → refund) transition cleanly with context preserved.



\---



\## Evaluation



The eval suite tests Karen across ten multi-turn scenarios covering all four flows. Each turn is judged by an LLM against per-turn behavioral criteria; structural outcomes (escalation fired, email draft generated) are verified by deterministic Python.



The split between LLM-judged behavioral criteria and Python-checked structural outcomes was a deliberate architectural decision. LLM-as-judge has specific failure modes — particularly with negative criteria and compound contrastive claims — where the judge's reasoning correctly identifies the right behavior but the verdict flips. Delegating structural outcomes to Python removes that failure mode from the equation and reserves the LLM for what only an LLM can evaluate: tone, empathy, and conversational appropriateness.



Run the eval suite for a specific flow:



```bash

python -m evals.runner --flow refund\_request

python -m evals.runner --flow exchange\_request

python -m evals.runner --flow employee\_complaint

python -m evals.runner --flow mobile\_app\_issue

```



\---



\## Running Karen locally



\*\*Prerequisites:\*\* Python 3.10+, an OpenAI API key with GPT-4o access.



\*\*Setup:\*\*



```bash

\# Clone the repo

git clone https://github.com/joshsardinha94/karen-framework.git

cd karen-framework



\# Create a virtual environment

python -m venv .venv

source .venv/bin/activate   # macOS/Linux

\# or

.venv\\Scripts\\activate      # Windows PowerShell



\# Install dependencies

pip install -r requirements.txt



\# Set up your API key

echo "OPENAI\_API\_KEY=your-key-here" > .env

```



\*\*Run the Dunkin web interface:\*\*



```bash

python -m deployments.dunkin.app

```



Then open `http://127.0.0.1:5000` in your browser.



\*\*Run the eval suite:\*\*



```bash

python -m evals.runner --flow refund\_request

```



\---



\## Model configuration



Karen runs on `gpt-4o`. This was a deliberate choice after testing — the procedural complexity of the state-machine contexts exceeds what `gpt-4o-mini` can reliably hold, and behavioral degradation on the smaller model looked like prompt bugs but wasn't. Model selection is centralized in `core/conversation.py` and can be overridden per deployment.



\---



\## Architectural decisions worth naming



\*\*Identity in prose, procedure in pseudocode.\*\* Different cognitive purposes, different mediums. Mixing them — putting procedural steps in prose or posture directives in pseudocode — produces measurably worse agent behavior than clean separation.



\*\*Parameterized sub-procedures over duplicated flows.\*\* Shared downstream logic (like email escalation) is defined once and invoked by name with parameters. Cleaner architecture, smaller prompt footprint, and correctly differentiated output per caller.



\*\*Stateless Flask backend with frontend-held history.\*\* The web deployment stores no session state server-side. The frontend holds conversation history in JavaScript and sends it with each request. The server rebuilds a Conversation hydrated with that history, processes the new turn, returns.



\*\*Delegating structural checks to Python, behavioral checks to LLM.\*\* Structural outcomes (escalation flag, email draft generation) are checked deterministically. Subjective outcomes (tone, empathy, appropriateness) are checked by LLM. The split prevents LLM-as-judge failure modes from polluting the structural signal.



\---



\## License



MIT

