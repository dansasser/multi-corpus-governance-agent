from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

from sqlalchemy.exc import SQLAlchemyError

from mcg_agent.db.base import Base
from mcg_agent.db.session import engine, get_session
from mcg_agent.db.models_published import Article, Source


def _to_dt(val: Optional[str | float | int]) -> Optional[datetime]:
    if val is None:
        return None
    try:
        return datetime.fromtimestamp(float(val), tz=timezone.utc)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except Exception:
        return None


def _domain(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        return urlparse(url).netloc.lower() or None
    except Exception:
        return None


def ensure_tables() -> None:
    Base.metadata.create_all(bind=engine)


def import_articles_json(path: str, default_authority: float = 0.0) -> dict:
    """Import published articles from a JSON file.

    Expected JSON layout: array of objects with keys
    {id?, title, content, ts, author?, url?, tags?, meta?, source?: {domain, authority_score?}}
    """
    path = os.path.abspath(path)
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Expected top-level JSON array")

    ensure_tables()
    created = 0
    with get_session() as s:
        sources_cache: dict[str, Source] = {}
        for item in data:
            title = item.get("title") or ""
            content = item.get("content") or ""
            if not content:
                continue
            ts = _to_dt(item.get("ts")) or datetime.now(timezone.utc)
            url = item.get("url")
            domain = (item.get("source") or {}).get("domain") or _domain(url)
            authority = float((item.get("source") or {}).get("authority_score") or default_authority)
            source_obj: Optional[Source] = None
            if domain:
                source_obj = sources_cache.get(domain)
                if source_obj is None:
                    # Look up existing or create
                    res = s.execute(
                        Source.__table__.select().where(Source.domain == domain)
                    ).first()
                    if res:
                        source_obj = s.get(Source, res.id)  # type: ignore[attr-defined]
                    if source_obj is None:
                        source_obj = Source(domain=domain, authority_score=authority)
                        s.add(source_obj)
                        sources_cache[domain] = source_obj

            art = Article(
                title=title,
                content=content,
                ts=ts,
                author=item.get("author"),
                url=url,
                tags=item.get("tags") or [],
                meta=item.get("meta") or {},
                source=source_obj,
            )
            s.add(art)
            created += 1

    return {"articles": created}


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Published articles into corpus")
    parser.add_argument("--path", required=True, help="Path to JSON array of articles")
    parser.add_argument("--default-authority", default=0.0, type=float, help="Default authority score for unknown domains")
    args = parser.parse_args()
    stats = import_articles_json(args.path, args.default_authority)
    print({"import_published": {"path": args.path, **stats}})


if __name__ == "__main__":
    main()

