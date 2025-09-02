from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from mcg_agent.db.base import Base
from mcg_agent.db.session import engine, get_session
from mcg_agent.db.models_personal import Thread, Message


def _epoch_to_dt(ts: Optional[float]) -> Optional[datetime]:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    except Exception:
        return None


def _message_text(message: Dict[str, Any]) -> str:
    content = message.get("content") or {}
    if isinstance(content, dict):
        # Newer export: {content: {content_type: 'text', parts: [...]}}
        parts = content.get("parts")
        if isinstance(parts, list):
            return "\n".join(str(p) for p in parts if p is not None)
        text = content.get("text")
        if isinstance(text, str):
            return text
    # Fallbacks
    return str(content) if content else ""


def _iter_messages(mapping: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for node in (mapping or {}).values():
        msg = (node or {}).get("message")
        if not msg:
            continue
        yield msg


def ensure_tables() -> None:
    Base.metadata.create_all(bind=engine)


def import_conversations_json(path: str, source_label: str = "openai_chatgpt") -> dict:
    """Import conversations.json (ChatGPT export) into personal corpus tables.

    - Threads: one per conversation id/title
    - Messages: flattened from mapping, ordered by create_time
    """
    path = os.path.abspath(path)
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    ensure_tables()
    threads = 0
    messages = 0
    with get_session() as s:
        for conv in data:
            conv_id = conv.get("id") or conv.get("conversation_id") or conv.get("uuid")
            title = conv.get("title") or "Untitled"
            started_at = _epoch_to_dt(conv.get("create_time"))
            participants = {"authors": []}

            thr = s.get(Thread, conv_id)
            if thr is None:
                thr = Thread(
                    thread_id=str(conv_id),
                    title=title,
                    participants=participants,
                    tags=[],
                    started_at=started_at,
                )
                s.add(thr)
                threads += 1

            mapping = conv.get("mapping") or {}
            msgs = list(_iter_messages(mapping))
            # Track authors
            for m in msgs:
                author = (m.get("author") or {}).get("role")
                if author and author not in participants["authors"]:
                    participants["authors"].append(author)
            # Sort by create_time
            msgs.sort(key=lambda m: m.get("create_time") or 0)
            for m in msgs:
                role = (m.get("author") or {}).get("role") or "assistant"
                content = _message_text(m)
                if not content:
                    continue
                ts = _epoch_to_dt(m.get("create_time")) or started_at or datetime.now(timezone.utc)
                s.add(
                    Message(
                        thread_id=str(conv_id),
                        role=role,
                        content=content,
                        ts=ts,
                        source=source_label,
                        channel="chatgpt",
                        meta={
                            "model": (m.get("metadata") or {}).get("model_slug"),
                            "recipient": m.get("recipient"),
                        },
                    )
                )
                messages += 1

    return {"threads": threads, "messages": messages}


def main() -> None:
    parser = argparse.ArgumentParser(description="Import ChatGPT conversations into personal corpus")
    parser.add_argument("--path", required=True, help="Path to conversations.json")
    parser.add_argument("--source", default="openai_chatgpt", help="Source label for provenance")
    args = parser.parse_args()
    stats = import_conversations_json(args.path, args.source)
    print({"import_personal": {"path": args.path, **stats}})


if __name__ == "__main__":
    main()

