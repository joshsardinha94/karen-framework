"""
Dunkin' Putnam Valley Karen — Flask Backend

Serves the Dunkin' Karen web interface. Provides two routes:

  GET  /      — serves the frontend HTML.
  POST /chat  — accepts a user message plus conversation history,
                routes through Karen, and returns her reply, any
                extracted email draft, and the escalation flag.

This deployment is stateless: the frontend holds the message history
in the browser and sends it with each request. The server rebuilds a
Conversation from that history, processes the new turn, and returns.
No session state is stored server-side.

To run:
    python -m deployments.dunkin.app

Then open http://127.0.0.1:5000 in a browser.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path

from core.conversation import Conversation
from core.capabilities.email_draft import extract_email_draft
from deployments.dunkin.context import DUNKIN_CONTEXT


# Flask needs to know where to find static files (index.html).
# __file__ resolves to this app.py; its parent is deployments/dunkin/.
STATIC_DIR = Path(__file__).resolve().parent

app = Flask(__name__, static_folder=str(STATIC_DIR))
CORS(app)


@app.route("/")
def index():
    """Serve the chat frontend."""
    return send_from_directory(str(STATIC_DIR), "index.html")


@app.route("/chat", methods=["POST"])
def chat():
    """
    Handle a single chat turn.

    Expects a JSON payload of the form:
        {
            "messages": [
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."},
                ...
            ]
        }

    The final message in the list is treated as the new user turn to
    respond to. Prior messages are treated as conversation history.

    Returns JSON:
        {
            "reply":        cleaned Karen reply (tag and email block stripped),
            "escalated":    bool — was the escalation tag present?,
            "email_draft":  dict or null — structured email draft if one was
                            produced this turn, else null
        }
    """
    data = request.get_json(silent=True) or {}
    messages = data.get("messages", [])

    if not messages:
        return jsonify({"error": "messages array is required"}), 400

    # The final message is the new user turn. Everything before it is history.
    new_user_message = messages[-1]
    prior_history = messages[:-1]

    if new_user_message.get("role") != "user":
        return jsonify({"error": "final message must be from user"}), 400

    # Rebuild a Conversation from the prior history, then send the new turn.
    convo = Conversation(
        deployment_context=DUNKIN_CONTEXT,
        history=prior_history,
    )
    reply, escalated = convo.send(new_user_message["content"])

    # Check the reply for an email draft and extract if present.
    cleaned_reply, draft = extract_email_draft(reply)

    # Serialize the draft for JSON. None stays None; an EmailDraft becomes
    # a plain dict the frontend can render.
    draft_payload = None
    if draft is not None:
        draft_payload = {
            "to": draft.to,
            "subject": draft.subject,
            "body": draft.body,
        }

    return jsonify({
        "reply": cleaned_reply,
        "escalated": escalated,
        "email_draft": draft_payload,
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5000)