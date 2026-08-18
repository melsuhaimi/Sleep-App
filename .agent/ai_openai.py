"""Minimal OpenAI Responses API provider for bounded engineering proposals."""
from __future__ import annotations

import json
import os
from pathlib import Path
import urllib.error
import urllib.request
from typing import Any

from bootstrap import fail, read_json


def _schema(repo: Path) -> dict[str, Any]:
    raw = read_json(repo / ".agent/schemas/result.schema.json")
    return {k: v for k, v in raw.items() if k not in {"$schema", "$id"}}


def _extract_output_text(response: dict[str, Any]) -> str:
    direct = response.get("output_text")
    if isinstance(direct, str) and direct:
        return direct
    parts: list[str] = []
    output = response.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, dict) and part.get("type") == "output_text" and isinstance(part.get("text"), str):
                    parts.append(part["text"])
    if not parts:
        fail("MODEL_OUTPUT_INVALID", "OpenAI response contained no output_text", request_attempted=True)
    return "".join(parts)


def request_proposal(prompt: str, cfg: dict[str, Any], repo: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        fail("MISSING_OPENAI_API_KEY", "OPENAI_API_KEY is required for live bounded AI execution", request_attempted=False)

    url = cfg.get("openai_responses_url")
    model = cfg.get("openai_model")
    max_tokens = cfg.get("max_ai_output_tokens")
    timeout = cfg.get("openai_timeout_seconds")
    response_limit = cfg.get("max_openai_response_bytes", 1048576)
    if not isinstance(url, str) or not url.startswith("https://"):
        fail("INVALID_CONFIG", "openai_responses_url must be an https URL")
    if not isinstance(model, str) or not model:
        fail("INVALID_CONFIG", "openai_model must be configured")
    if not isinstance(max_tokens, int) or max_tokens <= 0:
        fail("INVALID_CONFIG", "max_ai_output_tokens must be a positive integer")
    if not isinstance(timeout, int) or timeout <= 0:
        fail("INVALID_CONFIG", "openai_timeout_seconds must be a positive integer")
    if not isinstance(response_limit, int) or response_limit <= 0:
        fail("INVALID_CONFIG", "max_openai_response_bytes must be a positive integer")

    payload = {
        "model": model,
        "input": prompt,
        "store": False,
        "max_output_tokens": max_tokens,
        "reasoning": {"effort": "medium"},
        "text": {
            "format": {
                "type": "json_schema",
                "name": "bounded_ai_engineering_proposal",
                "schema": _schema(repo),
                "strict": True,
            }
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(response_limit + 1)
    except urllib.error.HTTPError as exc:
        fail("MODEL_UNAVAILABLE", "OpenAI Responses API returned an HTTP error", http_status=exc.code, request_attempted=True)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        fail("MODEL_UNAVAILABLE", "OpenAI Responses API request failed", error=type(exc).__name__, request_attempted=True)

    if len(body) > response_limit:
        fail("MODEL_OUTPUT_TOO_LARGE", "OpenAI response exceeded configured byte limit", limit=response_limit, request_attempted=True)
    try:
        response_obj = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        fail("MODEL_OUTPUT_INVALID", "OpenAI response was not valid UTF-8 JSON", request_attempted=True)
    if not isinstance(response_obj, dict):
        fail("MODEL_OUTPUT_INVALID", "OpenAI response root was not an object", request_attempted=True)

    text = _extract_output_text(response_obj)
    try:
        proposal = json.loads(text)
    except json.JSONDecodeError:
        fail("MODEL_OUTPUT_INVALID", "structured output text was not valid JSON", request_attempted=True)
    if not isinstance(proposal, dict):
        fail("MODEL_OUTPUT_INVALID", "structured output root was not an object", request_attempted=True)
    return proposal, {
        "request_attempted": True,
        "response_id": response_obj.get("id") if isinstance(response_obj.get("id"), str) else None,
        "model": model,
    }
