"""JSON helpers for LLM output."""

from __future__ import annotations

import json
import re
from typing import Any


def clean_json(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return text


def parse_json(raw: str) -> dict[str, Any]:
    return json.loads(clean_json(raw))
