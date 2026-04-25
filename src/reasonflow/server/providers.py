"""Provider catalog — Claude / OpenAI / Ollama presets for the UI."""

from __future__ import annotations

import os
from typing import Any

import httpx


PROVIDERS: list[dict[str, Any]] = [
    {
        "id": "anthropic",
        "label": "Claude (Anthropic)",
        "env": "ANTHROPIC_API_KEY",
        "prefix": "",
        "models": [
            "claude-opus-4-7",
            "claude-sonnet-4-6",
            "claude-haiku-4-5",
            "claude-sonnet",
        ],
    },
    {
        "id": "openai",
        "label": "OpenAI",
        "env": "OPENAI_API_KEY",
        "prefix": "",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1", "o1-mini"],
    },
    {
        "id": "gemini",
        "label": "Google Gemini",
        "env": "GEMINI_API_KEY",
        "prefix": "gemini/",
        "models": ["gemini/gemini-1.5-pro", "gemini/gemini-1.5-flash"],
    },
    {
        "id": "ollama",
        "label": "Ollama (local)",
        "env": None,
        "prefix": "ollama/",
        "models": [],  # populated dynamically
    },
]


def list_providers() -> list[dict[str, Any]]:
    """Return providers with key_present flags."""
    out = []
    for p in PROVIDERS:
        out.append({
            **p,
            "key_present": p["env"] is None or bool(os.environ.get(p["env"])),
        })
    return out


async def list_ollama_models(base_url: str = "http://localhost:11434") -> list[str]:
    """Fetch installed Ollama models, prefixed for litellm."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{base_url}/api/tags")
            r.raise_for_status()
            data = r.json()
            return [f"ollama/{m['name']}" for m in data.get("models", [])]
    except Exception:
        return []


async def test_model(model: str) -> dict[str, Any]:
    """Fire a tiny completion to verify a model works."""
    try:
        from litellm import acompletion
        resp = await acompletion(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        return {"ok": True, "model": model, "response": str(resp.choices[0].message.content)[:50]}
    except Exception as e:
        return {"ok": False, "model": model, "error": str(e)}
