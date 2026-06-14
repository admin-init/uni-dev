"""ChatModal — LLM-powered issue drafting dialog.

Uses deepseek-v4-flash for fast conversational issue creation.
User describes what they want; the LLM drafts a structured issue.
"""

from __future__ import annotations

import os
from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static, TextArea


CHAT_SYSTEM_PROMPT = """\
You help draft well-structured software issues for a backend development
pipeline. Your goal is to extract requirements from the user's description
and produce a clear, actionable issue.

Format your response like this:
[TITLE]: A concise title summarizing the feature/bug
[BODY]: Detailed description with:
- What needs to be built or fixed
- Acceptance criteria
- Any constraints or edge cases
- Preferred approach (if the user mentioned one)

Ask clarifying questions when requirements are ambiguous.
Be concise and developer-focused. Do NOT include markdown formatting.
"""


class ChatModal(ModalScreen[dict[str, Any] | None]):
    """Modal dialog for LLM-powered issue drafting.

    Returns a dict with 'title' and 'body' on submit, or None on cancel.
    """

    def __init__(self) -> None:
        super().__init__()
        self._messages: list[dict[str, str]] = [
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        ]

    def compose(self) -> ComposeResult:
        with Vertical(id="chat-container"):
            yield Label("New Issue Chat", id="chat-title")
            yield Static(
                "LLM: What would you like to build or fix?",
                id="chat-history",
            )
            yield Input(placeholder="Describe what you need...", id="chat-input")
            with Vertical(id="chat-draft", classes="hidden"):
                yield Label("Draft Issue", id="draft-label")
                yield TextArea(id="draft-text", language=None)
            yield Static("", id="chat-status")
            with Vertical(id="chat-actions"):
                yield Button("Submit", variant="primary", id="submit-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_mount(self) -> None:
        self.query_one("#chat-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        user_text = event.value.strip()
        if not user_text:
            return

        history = self.query_one("#chat-history", Static)
        current = history.renderable
        history.update(
            f"{current}\n\nYou: {user_text}"
        )

        event.input.clear()
        event.input.disabled = True
        self.query_one("#chat-status", Static).update("Thinking...")

        self._messages.append({"role": "user", "content": user_text})

        try:
            response = self._call_llm()
            self._messages.append({"role": "assistant", "content": response})

            title, body = self._parse_response(response)

            draft = self.query_one("#draft-text", TextArea)
            draft.load_text(body or response)
            draft_container = self.query_one("#chat-draft", Vertical)
            draft_container.remove_class("hidden")

            history.update(
                f"{current}\n\nYou: {user_text}\n\nLLM: {response}"
            )

            self._current_title = title
            self._current_body = body or response

            submit_btn = self.query_one("#submit-btn", Button)
            submit_btn.focus()

        except Exception as exc:
            history.update(f"{current}\n\nError: {exc}")
        finally:
            event.input.disabled = False
            self.query_one("#chat-status", Static).update("")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit-btn":
            title = getattr(self, "_current_title", "")
            body = getattr(self, "_current_body", "")
            draft = self.query_one("#draft-text", TextArea)
            if draft.text:
                title = title or "Untitled"
                body = draft.text
            self.dismiss({"title": title, "body": body})
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def _call_llm(self) -> str:
        """Call DeepSeek v4-flash for chat response."""
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key or api_key.startswith("your_"):
            return (
                "[TITLE]: Feature Request\n"
                "[BODY]: "
                "Please describe what you need in more detail. "
                "I'll help draft a proper issue from your description."
            )

        from langchain_openai import ChatOpenAI

        model = ChatOpenAI(
            model="deepseek-v4-flash",
            base_url="https://api.deepseek.com",
            api_key=api_key,
            temperature=0.7,
        )

        result = model.invoke(
            [
                {"role": m["role"], "content": m["content"]}
                for m in self._messages
            ]
        )
        content = getattr(result, "content", "")
        return str(content) if content else ""

    def _parse_response(self, text: str) -> tuple[str, str]:
        """Parse [TITLE] and [BODY] from LLM response."""
        title = ""
        body = text

        if "[TITLE]:" in text:
            parts = text.split("[BODY]:", 1)
            title_part = parts[0].replace("[TITLE]:", "").strip()
            body_part = parts[1].strip() if len(parts) > 1 else ""
            title = title_part
            body = body_part

        return title, body
