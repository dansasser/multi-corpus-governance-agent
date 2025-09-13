# MCG Agent API

## Authentication

- Protected endpoints require `Authorization: Bearer <JWT>`
- Mint a token for development:

```
mcg-agent mint-token --user-id alice --minutes 120
```

## Endpoints

### `GET /health`
- Returns: `{ status, database, error?, memory }`

### `GET /status`
- Returns: `{ environment, validation }`

### `POST /query` (auth)
- Body: `{ "prompt": "..." }`
- Returns: `{ task_id, agent_role, content, metadata }`
  - Metadata includes `request_id`, `task_id`, and `user_id` when available
- Example:

```
curl -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"prompt":"Write a short note."}' http://localhost:8000/query
```

### `GET /pipeline/summary` (auth)
- Returns: `{ summary: { stage: { success, fail } } }`

### `GET /metrics` (optional)
- Exposed when `METRICS_ENABLED=true`.

## Configuration Notes

- Provider swap: `GEN_PROVIDER=punctuation_only|openai|mvlm`, with `OPENAI_API_KEY` for dev.
- Optimizer: `FEATURE_RESPONSE_OPTIMIZER=true` to enable; config via `OPTIMIZATION_*` env vars.
- Caching & memory: see `.env.example` for cache backend and memory pressure behavior.

