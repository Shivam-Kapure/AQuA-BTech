from __future__ import annotations


def app_context_block(app_context: str | None) -> str:
    """Format user-provided notes about app behaviour for inclusion in an LLM prompt."""
    text = (app_context or "").strip()
    if not text:
        return ""
    return (
        "\n### Application behaviour notes from the user\n"
        "These notes are authoritative. Follow them over your own assumptions about how the app behaves "
        "(redirects, what appears or disappears, limits, error display, which selectors to use).\n"
        f"{text}\n"
    )
