from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict

from alembic import command
from alembic.config import Config

from mcg_agent.ingest.personal_chatgpt_export import import_conversations_json


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def upgrade_db(database_url: str | None = None) -> None:
    cfg_path = _repo_root() / "alembic.ini"
    if not cfg_path.exists():
        raise FileNotFoundError(cfg_path)
    cfg = Config(str(cfg_path))
    # override from env or argument
    url = database_url or os.environ.get("DATABASE_URL")
    if url:
        cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


def main() -> None:
    parser = argparse.ArgumentParser(description="DB migration + seed utilities")
    parser.add_argument("--upgrade-db", action="store_true", help="Run alembic upgrade head")
    parser.add_argument("--database-url", default=None, help="Override DATABASE_URL for alembic")
    parser.add_argument("--personal-path", default=None, help="Path to conversations.json for personal corpus import")
    parser.add_argument("--source", default="openai_chatgpt", help="Source label for personal import")
    args = parser.parse_args()

    result: Dict[str, Any] = {}

    if args.upgrade_db:
        upgrade_db(args.database_url)
        result["alembic"] = "upgraded"

    if args.personal_path:
        stats = import_conversations_json(args.personal_path, args.source)
        result["personal_import"] = stats

    if not result:
        result["noop"] = True

    print(json.dumps(result))


if __name__ == "__main__":
    main()

