"""Configuration loaded from environment (and an optional, gitignored .env file).

Secrets are never printed or logged. Only presence of a key is ever reported.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: str | os.PathLike | None = None) -> None:
    """Minimal .env loader: KEY=VALUE lines, does not override existing env vars."""
    p = Path(path) if path else Path(__file__).resolve().parent.parent / ".env"
    if not p.is_file():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def _first(*names: str, default: str = "") -> str:
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return default


@dataclass
class Settings:
    mode: str  # "stub" or "live"
    base_url: str
    api_key: str
    model: str
    timeout: float = 60.0

    @property
    def live(self) -> bool:
        return self.mode == "live" and bool(self.api_key and self.base_url and self.model)

    def public(self) -> dict:
        """Safe-to-display summary (never includes the key)."""
        return {
            "mode": "live" if self.live else "stub",
            "model": self.model if self.live else "deterministic-stub",
            "key_present": bool(self.api_key),
        }


def get_settings(load_env: bool = True) -> Settings:
    if load_env:
        load_dotenv(os.environ.get("EVIDENCE_ENV_FILE") or None)
    api_key = _first("EVIDENCE_LLM_API_KEY", "OPENAI_API_KEY", "NEBIUS_API_KEY")
    base_url = _first("EVIDENCE_LLM_BASE_URL", "OPENAI_BASE_URL", "NEBIUS_BASE_URL")
    model = _first("EVIDENCE_LLM_MODEL", "OPENAI_MODEL", "NEBIUS_MODEL")
    mode = os.environ.get("EVIDENCE_MODE", "live" if api_key else "stub").lower()
    if mode not in ("stub", "live"):
        mode = "stub"
    return Settings(mode=mode, base_url=base_url.rstrip("/"), api_key=api_key, model=model)
