"""Central LLM client — ADR-127 Phase 1.

Single chokepoint for model selection via `.env`. Every LLM call site in the
codebase routes through this module so the model/endpoint can be governed in one
place instead of being re-rolled per module.

Phase 1 is **behaviour-neutral** on purpose:

- Each call site keeps its own thin wrapper (``_call_ollama`` / ``_call_gemma`` /
  ``_call_ollama_assistant`` / the reasoning block) and its own post-processing,
  return contract, and symbol name — only the transport/model lookup moves here.
- Each site **pins** its current backend. The 3 scanner/assistant sites are
  local-Ollama today; the reasoning node is Anthropic-cloud today. ``LLM_BACKEND``
  is therefore **not** consulted for dispatch yet (the active ``.env`` has
  ``LLM_BACKEND=local``, and honouring it for the reasoning node would flip its
  output cloud→local). Flipping reasoning to local-Gemma is **Phase 3**, when the
  node's function (free measure generation) is rebuilt.
- The literal ``claude-sonnet-4-6`` lives here as the api-backend default
  (centralized, not deleted) — so "0 hardcoded models outside ``src/llm/``" holds
  while output stays byte-identical.

HTTP transport is unified on ``httpx`` (the only HTTP lib in the client) so the
extractor's ``except httpx.HTTPError`` path keeps firing on transport/HTTP errors.
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

# Centralized default for the api backend (ADR-127 Phase 1: literal lives here).
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"


def resolve_ollama_endpoint(
    *,
    full_env: str | None = None,
    full_default: str | None = None,
    base_env: str | None = None,
    base_default: str | None = None,
    suffix: str = "",
) -> str:
    """Resolve an Ollama ``/api/generate`` POST endpoint.

    Centralizes the ``OLLAMA_URL`` (full, path included) vs ``OLLAMA_BASE_URL``
    (bare host:port, path appended) split **without merging them** — each call
    site declares which env var(s) it reads plus its own default, so the resolved
    endpoint is byte-identical to the pre-Phase-1 lookup. (The two groups resolve
    to different hosts on the active ``.env``; truly unifying them is a separate,
    behaviour-changing cleanup, not Phase 1.)

    Precedence: ``full_env`` (already includes the path) → ``base_env`` + ``suffix``
    → ``full_default`` → ``base_default`` + ``suffix``.
    """
    if full_env:
        value = os.getenv(full_env)
        if value:
            return value
    if base_env:
        value = os.getenv(base_env)
        if value:
            return value.rstrip("/") + suffix
    if full_default is not None:
        return full_default
    return (base_default or "").rstrip("/") + suffix


def complete_ollama(
    prompt: str,
    *,
    endpoint: str,
    model: str,
    options: dict,
    format: str | None = None,
    timeout: float,
) -> dict:
    """POST to Ollama ``/api/generate`` and return the parsed JSON response dict.

    Raises ``httpx.HTTPError`` (via ``raise_for_status``) on transport/HTTP errors
    so every caller's existing ``except`` path fires identically (the urllib sites
    catch broadly → ``None``; the extractor catches ``httpx.HTTPError`` for its
    "Ollama call failed" branch). Callers extract ``response`` / ``done`` / ``error``
    from the returned dict exactly as before.
    """
    body: dict = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": options,
    }
    if format is not None:
        body["format"] = format
    response = httpx.post(endpoint, json=body, timeout=timeout)
    response.raise_for_status()
    return response.json()


def resolve_anthropic_model(model: str | None = None) -> str:
    """Resolve the Anthropic model id: explicit arg → ``LLM_MODEL`` env → default.

    Default ``claude-sonnet-4-6`` keeps the reasoning node byte-neutral in Phase 1.
    """
    return model or os.getenv("LLM_MODEL", DEFAULT_ANTHROPIC_MODEL)


def complete_anthropic(prompt: str, *, model: str, max_tokens: int) -> str:
    """Call the Anthropic messages API and return the first text block.

    Exceptions (overload 529, missing key, etc.) propagate to the caller so the
    reasoning node's existing fallback handling is unchanged.
    """
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
