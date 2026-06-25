"""
Chat clients.

The pipeline talks to LLMs through a narrow :class:`ChatClient` protocol so the
generator and judge never depend on a concrete SDK or vendor. Every live provider
exposes an OpenAI-compatible endpoint, so a single :class:`OpenAICompatibleClient`
serves them all — only the base URL and API key differ, chosen per provider:

  - ``nvidia``     — NVIDIA Build (``NVIDIA_API_KEY``)
  - ``gemini``     — Google AI Studio / Gemini (``GEMINI_API_KEY`` or ``GOOGLE_API_KEY``)
  - ``openrouter`` — OpenRouter, one key across many models (``OPENROUTER_API_KEY``)

A model id may carry a ``provider:`` prefix (e.g. ``gemini:gemini-2.5-flash``); a
bare id (e.g. ``deepseek-ai/deepseek-v4-flash``) defaults to ``nvidia`` so existing
commands keep working. :class:`MockClient` returns canned output with no network.

Free tiers are rate-limited, so the client paces call *starts* with a
:class:`RateLimiter` and retries transient errors with backoff.
"""
from __future__ import annotations

import os
import time
from typing import Protocol, runtime_checkable

from .ratelimit import RateLimiter

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

# provider name -> (OpenAI-compatible base URL, candidate API-key env var names)
PROVIDERS: dict[str, tuple[str, tuple[str, ...]]] = {
    "nvidia": (NVIDIA_BASE_URL, ("NVIDIA_API_KEY",)),
    "gemini": (
        "https://generativelanguage.googleapis.com/v1beta/openai",
        ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    ),
    "openrouter": ("https://openrouter.ai/api/v1", ("OPENROUTER_API_KEY",)),
}
DEFAULT_PROVIDER = "nvidia"


def parse_model(spec: str) -> tuple[str, str]:
    """Split ``"provider:model"`` into ``(provider, model)``.

    A bare id maps to the default provider. Only splits when the text before the
    first ``:`` is a *registered* provider, so model ids that themselves contain a
    colon (e.g. OpenRouter's ``…:free``) are never misparsed.
    """
    if ":" in spec:
        head, rest = spec.split(":", 1)
        if head in PROVIDERS:
            return head, rest
    return DEFAULT_PROVIDER, spec


def _resolve_key(provider: str) -> str:
    """First non-empty env var among the provider's candidates, or a clear error."""
    _, envs = PROVIDERS[provider]
    for env in envs:
        val = os.environ.get(env)
        if val:
            return val
    raise RuntimeError(
        f"No API key for provider '{provider}'. Set one of {', '.join(envs)} in your "
        f"environment or .env. (Gemini: get a free key at https://aistudio.google.com/apikey)"
    )


@runtime_checkable
class ChatClient(Protocol):
    """Minimal chat interface shared by every model the pipeline calls."""

    def complete(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Return the assistant's text response for a single-turn exchange."""
        ...


class OpenAICompatibleClient:
    """OpenAI-SDK client for any OpenAI-compatible endpoint (NVIDIA, Gemini, …).

    The provider is fixed at construction (it sets ``base_url`` + ``api_key``); the
    model is chosen per request. A ``provider:`` prefix on the model id is stripped
    before the call, so the same id can flow through provenance and routing.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        max_retries: int = 4,
        backoff_base: float = 1.5,
        timeout: float = 90.0,
        rate_limit_wait: float = 12.0,
        calls_per_minute: float = 36.0,
    ) -> None:
        # Imported lazily so the package (and MockClient) work without `openai`.
        from openai import OpenAI

        if not api_key:
            raise RuntimeError("OpenAICompatibleClient requires an api_key")
        # Per-request timeout so a cold-starting or hung model fails fast and the
        # caller can retry/skip rather than blocking. max_retries=0 disables the
        # SDK's own retry loop so it can't silently multiply our timeout; our loop
        # below is the only one.
        self._client = OpenAI(
            api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0,
        )
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._rate_limit_wait = rate_limit_wait
        # Proactive throttle shared across this client's calls (and so across all
        # worker threads in a batch, which reuse one client).
        self._limiter = RateLimiter(calls_per_minute)

    def complete(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        _, model = parse_model(model)  # strip any 'provider:' routing prefix
        last_err: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                self._limiter.acquire()  # pace call starts under the rate cap
                resp = self._client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content or ""
            except Exception as err:  # noqa: BLE001 — retry any transient API error
                last_err = err
                if attempt < self._max_retries - 1:
                    # Rate limits (429) need a real cool-off, not a 1-2s backoff,
                    # or every retry burns inside the same throttle window.
                    is_rate_limit = (
                        type(err).__name__ == "RateLimitError" or "429" in str(err)
                    )
                    time.sleep(self._rate_limit_wait if is_rate_limit
                               else self._backoff_base ** attempt)
        raise RuntimeError(
            f"API call to {model} failed after {self._max_retries} attempts: {last_err}"
        ) from last_err


class NvidiaClient(OpenAICompatibleClient):
    """Back-compat shim: NVIDIA Build is just one provider of the generic client.

    Reads ``NVIDIA_API_KEY`` when no key is passed. One account-level key
    authenticates every NVIDIA model — the model is chosen per request.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = NVIDIA_BASE_URL,
        **kwargs,
    ) -> None:
        super().__init__(
            base_url=base_url, api_key=api_key or _resolve_key("nvidia"), **kwargs
        )


class MockClient:
    """Deterministic stand-in for an LLM — no network, no API key.

    Returns a JSON object shaped like what the generator's templates ask for, so
    the full generate→parse→serialize path can be exercised offline.
    """

    def __init__(self, canned_prompt: str = "[mock target-language output]") -> None:
        self._canned_prompt = canned_prompt

    def complete(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        # Mirror the JSON contract the generator expects. ``expected`` is left
        # empty; the generator treats an empty string as "no answer".
        import json

        return json.dumps(
            {"prompt": self._canned_prompt, "expected": ""},
            ensure_ascii=False,
        )


def build_client(name: str, **kwargs) -> ChatClient:
    """Factory: ``"mock"`` -> :class:`MockClient`; otherwise resolve the provider.

    ``name`` is a model id, optionally ``provider:`` prefixed. The prefix (or the
    default ``nvidia``) selects the base URL and API key; the model itself is sent
    per request. ``api_key`` / ``base_url`` may be overridden via kwargs.
    """
    if name == "mock":
        return MockClient()
    provider, _ = parse_model(name)
    if provider not in PROVIDERS:
        provider = DEFAULT_PROVIDER
    base_url, _envs = PROVIDERS[provider]
    api_key = kwargs.pop("api_key", None) or _resolve_key(provider)
    base_url = kwargs.pop("base_url", base_url)
    return OpenAICompatibleClient(base_url=base_url, api_key=api_key, **kwargs)
