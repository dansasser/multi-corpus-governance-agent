from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from mcg_agent.db.base import Base
from mcg_agent.db.session import engine, get_session
from mcg_agent.db.models_social import Post, Comment


def _to_dt(val: Optional[str | float | int]) -> Optional[datetime]:
    if val is None:
        return None
    # Try epoch numeric first
    try:
        return datetime.fromtimestamp(float(val), tz=timezone.utc)
    except Exception:
        pass
    # Try ISO8601 strings
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except Exception:
        return None


def ensure_tables() -> None:
    Base.metadata.create_all(bind=engine)


def import_posts_json(path: str, platform: Optional[str] = None) -> dict:
    """Import social posts from a JSON file.

    Expected JSON layout: array of objects with keys
    {id?, platform?, content, ts, url?, hashtags?, mentions?, engagement?, meta?, comments?[]}
    """
    path = os.path.abspath(path)
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    if "../" in path or "..\\" in path:
        raise Exception("Invalid file path")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Expected top-level JSON array")

    ensure_tables()
    created = 0
    with get_session() as s:
        for item in data:
            content = item.get("content") or ""
            if not content:
                continue
            ts = _to_dt(item.get("ts")) or datetime.now(timezone.utc)
            post = Post(
                platform=item.get("platform") or platform,
                content=content,
                ts=ts,
                url=item.get("url"),
                hashtags=item.get("hashtags") or [],
                mentions=item.get("mentions") or [],
                engagement=int(item.get("engagement") or 0),
                meta=item.get("meta") or {},
            )
            s.add(post)
            created += 1
            for c in item.get("comments") or []:
                s.add(
                    Comment(
                        post=post,
                        author=c.get("author"),
                        content=c.get("content") or "",
                        ts=_to_dt(c.get("ts")) or ts,
                        engagement=int(c.get("engagement") or 0),
                    )
                )

    return {"posts": created}


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Social posts into corpus")
    parser.add_argument("--path", required=True, help="Path to JSON array of posts")
    parser.add_argument("--platform", default=None, help="Override platform field for all posts")
    args = parser.parse_args()
    stats = import_posts_json(args.path, args.platform)
    print({"import_social": {"path": args.path, **stats}})


if __name__ == "__main__":
    main()

