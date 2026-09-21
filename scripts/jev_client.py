"""Minimal client for TypeSafe's System One API (the Jev model).

Standard library only, so the runner has no dependency beyond Playwright.

    POST https://api.typesafe.ai/v1/systemone
    Authorization: Bearer $TYPESAFE_API_KEY
    {"state": ..., "model": "jev-latest", "questions": {...}}

Environment variables:
    TYPESAFE_API_KEY   required
    TYPESAFE_MODEL     optional, default "jev-latest"
    TYPESAFE_BASE_URL  optional, default https://api.typesafe.ai/v1/systemone
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://api.typesafe.ai/v1/systemone"


class JevError(RuntimeError):
    """Raised when the API cannot be reached or returns an error."""


def choice(instructions: str, criteria: dict[str, str]) -> dict:
    """Build a Choice question: pick one label from `criteria` (label -> description)."""
    return {"type": "choice", "instructions": instructions, "criteria": criteria}


def score(instructions: str, criteria: list[str]) -> dict:
    """Build a Score question: position on an ordered rubric (index 0..n-1)."""
    return {"type": "score", "instructions": instructions, "criteria": criteria}


def noul(instructions: str) -> dict:
    """Build a Noul question: probability (0-1) that the statement is true of the state."""
    return {"type": "noul", "instructions": instructions}


class JevClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 20.0,
        retries: int = 2,
    ) -> None:
        self.api_key = api_key or os.environ.get("TYPESAFE_API_KEY", "")
        if not self.api_key:
            raise JevError(
                "TYPESAFE_API_KEY is not set. Create a key at https://console.typesafe.ai/keys "
                "and export it (or put it in a .env file in the directory the runner is started from)."
            )
        self.model = model or os.environ.get("TYPESAFE_MODEL", "jev-latest")
        self.base_url = base_url or os.environ.get("TYPESAFE_BASE_URL", DEFAULT_BASE_URL)
        self.timeout = timeout
        self.retries = retries
        self.requests = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.last_model: str | None = None

    def system_one(self, state, questions: dict[str, dict]) -> dict:
        """Evaluate all `questions` against `state` in one call.

        Returns {"answers": {...}, "usage": {...}, "model": str, "latency_ms": int}.
        Answer shapes (per TypeSafe docs):
          choice -> {"type": "choice", "choice": label, "confidence": 0-1, "probabilities": {label: p}}
          score  -> {"type": "score", "score": float, "confidence": 0-1, "probabilities": {...}}
          noul   -> {"type": "noul", "noul": 0-1}
        """
        body = json.dumps({"state": state, "model": self.model, "questions": questions}).encode()
        req = urllib.request.Request(
            self.base_url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "jev-browser-test/0.1",
            },
        )
        attempt = 0
        while True:
            t0 = time.perf_counter()
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode())
                break
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:500]
                retryable = e.code == 429 or e.code >= 500
                if retryable and attempt < self.retries:
                    attempt += 1
                    time.sleep(0.5 * 2**attempt)
                    continue
                raise JevError(f"TypeSafe API HTTP {e.code}: {detail}") from None
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                if attempt < self.retries:
                    attempt += 1
                    time.sleep(0.5 * 2**attempt)
                    continue
                raise JevError(f"TypeSafe API unreachable: {e}") from None
        latency_ms = int((time.perf_counter() - t0) * 1000)

        usage = data.get("usage") or {}
        self.requests += 1
        self.input_tokens += int(usage.get("input_tokens") or 0)
        self.output_tokens += int(usage.get("output_tokens") or 0)
        self.last_model = data.get("model")
        return {
            "answers": data.get("answers") or {},
            "usage": usage,
            "model": data.get("model"),
            "latency_ms": latency_ms,
        }

    def usage_summary(self) -> dict:
        return {
            "jev_requests": self.requests,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "model": self.last_model or self.model,
        }
