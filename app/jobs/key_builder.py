"""Build coalescing keys from YAML so 'same resource' is tunable without code changes."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.core.config import settings


def _type_cfg(resource_type: str) -> dict[str, Any]:
    cfg = settings.job_coalescing
    types = cfg.get("resource_types") or {}
    return types.get(resource_type) or {}


def granularity_for(resource_type: str) -> str:
    cfg = settings.job_coalescing
    override = _type_cfg(resource_type).get("granularity")
    return str(override or cfg.get("default_granularity") or "country_pillar_question")


def build_key(
    resource_type: str,
    *,
    country_id: int | None = None,
    pillar_id: int | None = None,
    question_id: int | None = None,
    document_id: int | None = None,
    country_ids: list[int] | None = None,
    year: int | None = None,
    question_text: str | None = None,
) -> str:
    """
    Deterministic key. Granularity is YAML-driven:

      country                  → evaluation_full:country:12:2026
      country_pillar           → evaluation_pillars:country:12:pillar:3:2026
      country_pillar_question  → evaluation_questions:country:12:pillar:3:question:88:2026
    """
    cfg = _type_cfg(resource_type)
    grain = granularity_for(resource_type)
    parts: list[str] = [resource_type]

    if grain == "document" or document_id is not None and grain == "document":
        parts.append(f"document:{document_id}")
    elif grain == "global":
        parts.append("global")
    elif grain == "countries":
        ids = ",".join(str(i) for i in sorted(country_ids or []))
        parts.append(f"countries:{ids}")
    else:
        if country_id is not None:
            parts.append(f"country:{country_id}")
        if grain in ("country_pillar", "country_pillar_question") and pillar_id is not None:
            parts.append(f"pillar:{pillar_id}")
        if grain == "country_pillar_question" and question_id is not None:
            parts.append(f"question:{question_id}")

    if cfg.get("include_year") and year is not None:
        parts.append(f"year:{year}")

    if cfg.get("include_question_text") and question_text:
        digest = hashlib.sha256(question_text.strip().lower().encode("utf-8")).hexdigest()[:16]
        parts.append(f"q:{digest}")

    return ":".join(parts)


def snapshot_payload(resource_type: str, **kwargs: Any) -> str:
    return json.dumps({"resource_type": resource_type, **kwargs}, sort_keys=True, default=str)
