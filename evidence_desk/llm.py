"""Pluggable LLM layer: any OpenAI-compatible /chat/completions endpoint, or a deterministic stub."""
from __future__ import annotations

import json
import re
import urllib.request

from .config import Settings


class LLMError(RuntimeError):
    pass


def extract_json(text: str):
    """Pull the first JSON object/array out of a model reply (tolerates <think> blocks and fences)."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    text = re.sub(r"```(?:json)?", "", text)
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise LLMError("model reply did not contain valid JSON")


class OpenAICompatLLM:
    name = "openai-compatible"

    def __init__(self, settings: Settings):
        self.s = settings

    def chat_json(self, system: str, user: str, max_tokens: int = 1200):
        body = json.dumps(
            {
                "model": self.s.model,
                "temperature": 0.1,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
        ).encode()
        req = urllib.request.Request(
            f"{self.s.base_url}/chat/completions",
            data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.s.api_key}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.s.timeout) as r:
                data = json.loads(r.read().decode())
        except Exception as e:  # never include headers (key) in the message
            raise LLMError(f"LLM request failed: {type(e).__name__}") from None
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise LLMError("unexpected LLM response shape") from None
        try:
            return extract_json(content)
        except LLMError:
            raise LLMError(f"model reply did not contain valid JSON (finish_reason={choice.get('finish_reason')})") from None
