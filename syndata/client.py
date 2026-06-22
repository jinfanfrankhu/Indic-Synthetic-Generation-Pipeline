"""
Chat clients.

The pipeline talks to LLMs through a narrow :class:`ChatClient` protocol so the
generator (and, later, the judge) never depends on a concrete SDK. Two
implementations ship today:

  - :class:`NvidiaClient` — wraps the OpenAI SDK pointed at NVIDIA Build's
    OpenAI-compatible endpoint. Teacher (Qwen3) and judge (Llama 3.3) both live
    there; they differ only by model id.
  - :class:`MockClient` — returns canned, deterministic output with no network
    call. Used by the test suite and for fast iteration on the CLI/plumbing.

NVIDIA Build's free tier is rate-limited, so :class:`NvidiaClient` retries on
transient errors with exponential backoff.
"""
from __future__ import annotations

import os
import time
from typing import Protocol, runtime_checkable

from .ratelimit import RateLimiter

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


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


class NvidiaClient:
    """OpenAI-compatible client for NVIDIA Build models.

    Reads ``NVIDIA_API_KEY`` from the environment (or ``api_key`` if passed). One
    account-level key authenticates every model in the catalog — the model is
    chosen per request, not by the key — so a single ``NVIDIA_API_KEY`` covers
    teacher and all judges.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = NVIDIA_BASE_URL,
        max_retries: int = 4,
        backoff_base: float = 1.5,
        timeout: float = 90.0,
        rate_limit_wait: float = 12.0,
        calls_per_minute: float = 36.0,
    ) -> None:
        # Imported lazily so the package (and MockClient) work without `openai`.
        from openai import OpenAI

        key = api_key or os.environ.get("NVIDIA_API_KEY")
        if not key:
            raise RuntimeError(
                "NVIDIA_API_KEY is not set (env or .env). Get a free key at "
                "https://build.nvidia.com — one key works for all models."
            )
        # Per-request timeout so a cold-starting or hung model fails fast and
        # the caller can retry/skip rather than blocking the whole run.
        # max_retries=0 disables the SDK's own retry loop (default 2): otherwise
        # it silently multiplies our timeout (timeout × 3 × our retries), which
        # turned a hung model into 20+ minute blocks. Our retry loop is the only
        # one.
        self._client = OpenAI(
            api_key=key, base_url=base_url, timeout=timeout, max_retries=0,
        )
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._rate_limit_wait = rate_limit_wait
        # Proactive throttle shared across this client's calls (and so across all
        # worker threads in a batch, which reuse one client). Keeps starts under
        # the account-level 40/min cap; the 429 backoff above is the safety net.
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
            f"NVIDIA API call failed after {self._max_retries} attempts: {last_err}"
        ) from last_err


class MockClient:
    """Deterministic stand-in for an LLM — no network, no API key.

    Returns a JSON object shaped like what the generator's templates ask for, so
    the full generate→parse→serialize path can be exercised offline. The echoed
    ``user`` prompt lets tests assert that templating ran.
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
    """Factory: ``"mock"`` -> :class:`MockClient`, anything else -> NVIDIA.

    All NVIDIA models use the single ``NVIDIA_API_KEY``; the model id (``name``)
    only selects which model the request targets.
    """
    if name == "mock":
        return MockClient()
    return NvidiaClient(**kwargs)
