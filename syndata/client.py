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

    Reads the API key from ``api_key`` if passed, else from the first of
    ``NVIDIA_API_KEY`` / ``NVIDIA_QWEN_API_KEY`` set in the environment. All
    hosted NVIDIA Build models share one key, so a single value works for both
    teacher and judge.
    """

    _KEY_ENV_VARS = ("NVIDIA_API_KEY", "NVIDIA_QWEN_API_KEY")

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = NVIDIA_BASE_URL,
        max_retries: int = 4,
        backoff_base: float = 1.5,
        timeout: float = 90.0,
    ) -> None:
        # Imported lazily so the package (and MockClient) work without `openai`.
        from openai import OpenAI

        key = api_key or next(
            (os.environ[v] for v in self._KEY_ENV_VARS if os.environ.get(v)), None
        )
        if not key:
            raise RuntimeError(
                f"No API key found. Set one of {self._KEY_ENV_VARS} (env or .env), "
                "or pass api_key=... (get a free key at https://build.nvidia.com)."
            )
        # Per-request timeout so a cold-starting or hung model fails fast and
        # the caller can retry/skip rather than blocking the whole run.
        self._client = OpenAI(api_key=key, base_url=base_url, timeout=timeout)
        self._max_retries = max_retries
        self._backoff_base = backoff_base

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
                    time.sleep(self._backoff_base ** attempt)
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


# Vendor prefix (the part before "/" in a model id) -> preferred key env var.
# Each NVIDIA Build model can carry its own key; fall back to a shared key.
_VENDOR_KEY_ENV: dict[str, str] = {
    "qwen": "NVIDIA_QWEN_API_KEY",
    "deepseek-ai": "NVIDIA_DEEPSEEK_API_KEY",
    "sarvamai": "NVIDIA_SARVAM_API_KEY",
}


def resolve_api_key(model_id: str) -> str | None:
    """Pick the API key for ``model_id`` by vendor prefix.

    Tries the vendor-specific env var first (e.g. ``deepseek-ai/...`` ->
    ``NVIDIA_DEEPSEEK_API_KEY``), then a shared ``NVIDIA_API_KEY``, then any
    other ``NVIDIA_*_API_KEY`` present. Returns ``None`` if nothing is set, so
    the caller can raise a clear error.
    """
    vendor = model_id.split("/", 1)[0]
    preferred = _VENDOR_KEY_ENV.get(vendor)
    candidates = [preferred, "NVIDIA_API_KEY", *_VENDOR_KEY_ENV.values()]
    for var in candidates:
        if var and os.environ.get(var):
            return os.environ[var]
    return None


def build_client(name: str, **kwargs) -> ChatClient:
    """Factory: ``"mock"`` -> :class:`MockClient`, anything else -> NVIDIA.

    Resolves the API key from the model id's vendor unless ``api_key`` is
    already provided in ``kwargs``.
    """
    if name == "mock":
        return MockClient()
    if "api_key" not in kwargs:
        kwargs["api_key"] = resolve_api_key(name)
    return NvidiaClient(**kwargs)
