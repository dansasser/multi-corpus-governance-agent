# Personal Corpus Ingestion (ChatGPT Export)

This importer loads a ChatGPT `conversations.json` export into the Personal
corpus tables (`threads`, `messages`).

## Requirements
- `DATABASE_URL` set to your Postgres (recommended) or SQLite URL
- Alembic configured (provided in repo)

## Steps
1) Migrate schema
```
python -m mcg_agent.ingest.seed --upgrade-db
```

2) Import conversations
```
python -m mcg_agent.ingest.seed \
  --personal-path "db/chat data/conversations.json" \
  --source openai_chatgpt
```

Output prints JSON with counts of threads/messages imported.

## Notes
- Timestamps stored in UTC.
- Message `meta` includes model slug when present.
- No synthetic data is created; messages lacking content are skipped.

