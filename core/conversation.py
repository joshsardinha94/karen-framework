"""
Conversation Management

This module defines the Conversation class, which wraps all the logic for
talking to the language model: building the system prompt, managing message
history, calling the API, and processing the response for escalation.

Every Karen deployment — terminal, Streamlit, Flask, future deployments —
instantiates a Conversation and calls .send(user_message) on it. That's it.
The class handles everything else.

Changing models, swapping providers, adding retry logic, logging, or token
tracking is now a one-file change rather than a three-file hunt.
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

from core.identity import KAREN_CORE
from core.escalation import process_response

# Load environment variables once at module import time.
# .env is expected to live at the project root.
load_dotenv()


class Conversation:
    """
    A single Karen conversation session.

    Holds the system prompt (Karen's identity + deployment context), the
    running message history, and the OpenAI client. Exposes a .send() method
    that takes a user message and returns Karen's cleaned response plus an
    escalation flag.
    """

    def __init__(
            self,
            deployment_context: str,
            model: str = "gpt-4o",
            history: list[dict] | None = None,
    ):
        """
        Create a new conversation.

        Args:
            deployment_context: The company-specific context string for this
                deployment (e.g., DUNKIN_CONTEXT or SAAS_CONTEXT). Appended
                to KAREN_CORE to form the full system prompt.
            model: Which model to use. Defaults to gpt-4o.
            history: Optional existing message history to hydrate from.
                Used by stateless deployments (e.g., Flask) that rebuild
                a Conversation on each request from frontend-held history.
        """
        self.system_prompt = KAREN_CORE + "\n\n" + deployment_context
        self.model = model
        self.history: list[dict] = list(history) if history else []
        self.escalated = any(
            msg.get("role") == "assistant" and "[ESCALATION" in msg.get("content", "").upper()
            for msg in self.history
        )
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def send(self, user_message: str) -> tuple[str, bool]:
        """
        Send a user message to Karen and get her response.

        Appends the user message to history, calls the API with the full
        message stack (system prompt + history), appends Karen's response to
        history, processes the response for escalation, and returns the
        cleaned response plus the escalation flag.

        Args:
            user_message: What the customer said.

        Returns:
            (cleaned_response, escalated):
                cleaned_response is the customer-safe reply with the
                escalation tag stripped.
                escalated is True if the escalation tag was present.
        """
        self.history.append({"role": "user", "content": user_message})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": self.system_prompt}]
                     + self.history,
        )

        raw_reply = response.choices[0].message.content

        # Store the raw reply (with tag intact) in history so the model sees
        # its own escalation signal on subsequent turns. Only strip the tag
        # from what we return to the caller for display.
        self.history.append({"role": "assistant", "content": raw_reply})

        cleaned_reply, escalated = process_response(raw_reply)
        if escalated:
            self.escalated = True

        return cleaned_reply, escalated

    def reset(self) -> None:
        """
        Clear the conversation history and escalation state.

        Useful for the Streamlit 'Reset Conversation' button or for eval
        runners that want to start fresh between test cases.
        """
        self.history = []
        self.escalated = False