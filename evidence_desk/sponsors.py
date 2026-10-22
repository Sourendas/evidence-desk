"""Sponsor-tech adapter slots (Zetaris data source, Meterless usage metering).

Status: documented slots only. No sponsor account, key or paid service is used. Both adapters are
OFF unless their env vars are set, and even then they refuse to make network calls until a real
client is implemented against the sponsor's official API docs. This keeps the agent zero-cost
while making the integration point explicit and testable.

Plugging in a source adapter
----------------------------
Any object with ``name`` and ``search(question, limit) -> list[Source]`` can be passed to
``EvidenceDesk(source_adapters=[...])``. Returned sources go through the same extract → verify
pipeline, so their quotes are verbatim-checked and cited like every other source.

Plugging in a meter
-------------------
Any object with ``record(event: dict)`` can be passed as ``EvidenceDesk(meter=...)``. The agent
emits one event per LLM call and one per run (stage, model, token usage, latency). ``LocalMeter``
keeps them in memory and is what the trace's ``usage`` summary is built from.
"""
from __future__ import annotations

import os
from typing import Protocol

from .retrieval import Source


class SourceAdapter(Protocol):
    name: str

    def search(self, question: str, limit: int = 3) -> list[Source]: ...


class Meter(Protocol):
    def record(self, event: dict) -> None: ...


class NotConfigured(RuntimeError):
    pass


class ZetarisAdapter:
    """Slot for Zetaris federated-data queries as an evidence source (ids ``Z1``, ``Z2``…).

    Enable with ZETARIS_ENDPOINT + ZETARIS_TOKEN once sponsor access exists. Implementation TODO:
    run a read-only federated SQL/semantic query for the question and wrap each returned
    row/document as ``Source(id=f"Z{i}", kind="zetaris", title=..., url=<dataset ref>, text=...)``.
    """

    name = "zetaris"

    def __init__(self, endpoint: str | None = None, token: str | None = None):
        self.endpoint = endpoint or os.environ.get("ZETARIS_ENDPOINT", "")
        self._token = token or os.environ.get("ZETARIS_TOKEN", "")

    @property
    def enabled(self) -> bool:
        return bool(self.endpoint and self._token)

    def search(self, question: str, limit: int = 3) -> list[Source]:
        if not self.enabled:
            raise NotConfigured("Zetaris adapter not configured (set ZETARIS_ENDPOINT and ZETARIS_TOKEN)")
        raise NotConfigured("Zetaris client not implemented yet (slot only; no sponsor access)")


class LocalMeter:
    """In-memory usage meter (always on, zero cost)."""

    def __init__(self):
        self.events: list[dict] = []

    def record(self, event: dict) -> None:
        self.events.append(dict(event))

    def summary(self) -> dict:
        calls = [e for e in self.events if e.get("type") == "llm_call"]
        return {
            "llm_calls": len(calls),
            "prompt_tokens": sum(int(e.get("prompt_tokens") or 0) for e in calls),
            "completion_tokens": sum(int(e.get("completion_tokens") or 0) for e in calls),
            "llm_ms": sum(int(e.get("ms") or 0) for e in calls),
        }


class MeterlessMeter(LocalMeter):
    """Slot for forwarding usage events to Meterless (per-run/per-token metering).

    Enable with METERLESS_API_KEY once sponsor access exists. Until a client is implemented against
    the official API, events are only kept locally (``forwarded`` stays 0) — nothing is sent.
    """

    def __init__(self, api_key: str | None = None):
        super().__init__()
        self._key = api_key or os.environ.get("METERLESS_API_KEY", "")
        self.forwarded = 0

    @property
    def enabled(self) -> bool:
        return bool(self._key)


def default_adapters() -> list:
    """Adapters enabled by environment. Empty by default."""
    z = ZetarisAdapter()
    return [z] if z.enabled else []


def default_meter():
    m = MeterlessMeter()
    return m if m.enabled else LocalMeter()


def sponsor_status() -> dict:
    """Safe-to-display status (never includes secrets)."""
    return {"zetaris": "configured (client pending)" if ZetarisAdapter().enabled else "slot (off)",
            "meterless": "configured (local only)" if MeterlessMeter().enabled else "slot (local meter)"}
