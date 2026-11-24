"""Thin wrapper around the Anthropic SDK used by the picker and generator."""
from __future__ import annotations

import anthropic

from .config import FALLBACK_BETA, MODEL

_client: anthropic.Anthropic | None = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        # Reads ANTHROPIC_API_KEY (or an `ant auth login` profile) from the environment.
        _client = anthropic.Anthropic(max_retries=4)
    return _client


class RefusedError(RuntimeError):
    pass


def check_stop(response) -> None:
    if response.stop_reason == "refusal":
        details = getattr(response, "stop_details", None)
        raise RefusedError(f"Model declined: {getattr(details, 'category', None)} {getattr(details, 'explanation', '')}")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Response hit max_tokens before finishing; raise max_tokens.")


def parse(*, system, messages, output_format, effort: str = "high", max_tokens: int = 32000):
    """Structured-output call. Streams so long generations don't hit HTTP timeouts."""
    with client().beta.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
        output_format=output_format,
        output_config={"effort": effort},
        betas=[FALLBACK_BETA],
        fallbacks="default",
    ) as stream:
        response = stream.get_final_message()
    check_stop(response)
    return response.parsed_output, response


def text_with_web_search(*, system, prompt: str, effort: str = "medium", max_searches: int = 8,
                         max_tokens: int = 32000, max_continuations: int = 5):
    """Run a research turn with the server-side web search tool.

    Returns (text, sources) where sources are the URLs the search tool actually returned.
    """
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": max_searches,
              "user_location": {"type": "approximate", "country": "IN"}}]
    messages = [{"role": "user", "content": prompt}]
    assistant_content: list = []
    sources: dict[str, str] = {}
    for _ in range(max_continuations + 1):
        with client().beta.messages.stream(
            model=MODEL, max_tokens=max_tokens, system=system, messages=messages, tools=tools,
            output_config={"effort": effort}, betas=[FALLBACK_BETA], fallbacks="default",
        ) as stream:
            response = stream.get_final_message()
        assistant_content.extend(response.content)
        for block in response.content:
            if block.type == "web_search_tool_result" and isinstance(block.content, list):
                for r in block.content:
                    if getattr(r, "url", None):
                        sources.setdefault(r.url, getattr(r, "title", "") or r.url)
        if response.stop_reason == "pause_turn":
            # Resume the server-side loop: resend the turn so far; the API picks up where it paused.
            messages = [messages[0], {"role": "assistant", "content": assistant_content}]
            continue
        check_stop(response)
        text = "\n".join(b.text for b in assistant_content if b.type == "text")
        return text, sources
    raise RuntimeError("Web research did not finish after several continuations.")
