"""Gemini tutoring service.

Wraps the Google GenAI client so the Flask layer never has to know how a
document is uploaded or how a chat session is created.

The client is created lazily, so importing this module (e.g. from tests) does
not require an API key.
"""

import time
from pathlib import Path
from typing import Optional

from google import genai
from google.api_core.exceptions import ResourceExhausted

from config import (
    MODEL_NAME,
    SESSION_GREETING,
    SYSTEM_INSTRUCTION,
    get_api_key,
)

_client: Optional[genai.Client] = None


def get_client() -> genai.Client:
    """Return a cached GenAI client, creating it on first use."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=get_api_key())
    return _client


def _upload_and_wait(file_path: Path):
    """Upload a PDF to Gemini and block until the server finished processing."""
    client = get_client()
    uploaded = client.files.upload(file=str(file_path))
    while client.files.get(name=uploaded.name).state.name == "PROCESSING":
        time.sleep(1)
    return uploaded


def create_tutor_session(file_path: Path):
    """Start a tutoring chat session grounded on ``file_path``.

    Returns a ready-to-use ``chat_session`` (the greeting has already been sent).
    """
    client = get_client()
    uploaded = _upload_and_wait(Path(file_path))

    chat_session = client.chats.create(
        model=MODEL_NAME,
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION
        ),
    )
    chat_session.send_message([uploaded, SESSION_GREETING])
    return chat_session


def ask(chat_session, message: str) -> str:
    """Send ``message`` to an existing session and return the reply text."""
    response = chat_session.send_message(message)
    return response.text


def is_context_exhausted(error: Exception) -> bool:
    """True when Gemini rejected the request because the context window is full."""
    return isinstance(error, ResourceExhausted)


def is_transient(error: Exception) -> bool:
    """True for the "model overloaded" errors that are worth retrying."""
    text = str(error)
    return "503" in text or "UNAVAILABLE" in text