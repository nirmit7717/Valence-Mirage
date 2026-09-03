"""Shared helpers for OpenAI-compatible model responses."""


def extract_message_text(response) -> str:
    """Return the actual text payload from an OpenAI-compatible response.

    Newer reasoning-capable models sometimes populate `reasoning` or
    `reasoning_content` instead of a plain `content` string. Fall back to those
    fields so the app does not misclassify valid model output as empty.
    """
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""

    message = getattr(choices[0], "message", None)
    if message is None:
        return ""

    for field in ("content", "reasoning_content", "reasoning"):
        value = getattr(message, field, None)
        if value:
            text = str(value).strip()
            if text:
                return text

    return ""
