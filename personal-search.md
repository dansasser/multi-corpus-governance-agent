# Personal Search

## Purpose

Query your **Personal corpus**: exported chat histories, notes, drafts. Return attributed snippets for context packs.

## Inputs

* `query`: string
* `filters` (optional): `{ date_from, date_to, role(user|assistant), source(app), thread_id, tags[] }`
* `limit`: int (default 20)

## Storage Model

**Tables**

* `messages(id PK, thread_id, role, content, ts, source, channel, meta JSONB)`
* `threads(thread_id PK, title, participants, tags TEXT[], started_at)`
* `attachments(id PK, message_id FK, kind, url, meta JSONB)`

**Indexes**

* SQLite: `messages_fts` (FTS5 on `content`) with trigram optional
* Postgres: `GIN` on `to_tsvector('english', content)`, btree on `ts`, `thread_id`

## Access (PydanticAI)

* Provide a **Tool** that runs parameterized SQL or FTS queries.
* Disallow raw SQL from prompts. Inputs map to whitelisted queries.

### Pydantic models (contract)

```python
from pydantic import BaseModel
from typing import List, Optional, Literal

class PersonalSearchFilters(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    role: Optional[Literal["user","assistant"]] = None
    source: Optional[str] = None
    thread_id: Optional[str] = None
    tags: Optional[List[str]] = None

class PersonalSnippet(BaseModel):
    snippet: str
    source: Literal["Personal"] = "Personal"
    date: str
    tags: List[str] = []
    voice_terms: List[str] = []
    attribution: str  # e.g., "gpt_export/chat_2024-02-11.json#msg_48192"
    notes: str = ""
    thread_id: Optional[str] = None
    message_id: Optional[str] = None

class PersonalSearchResult(BaseModel):
    items: List[PersonalSnippet]
```

### Tool signature

```python
@tool("personal_search")
def personal_search(query: str, filters: PersonalSearchFilters, limit: int = 20) -> PersonalSearchResult: ...
```

## Responsibilities

* Run FTS/BM25 over `messages.content`.
* Window the hit to a **concise snippet** (e.g., ±240 chars).
* Add **attribution**: file or DB ids, timestamps, thread ids.
* Extract simple **voice\_terms** for tone anchoring (top collocations from the hit).
* Deduplicate near-identical hits. Respect `limit`.

## Ranking

Score = `BM25`
`+ recency_decay(ts)`
`+ role_boost(assistant ≈ your authored tone)`
`+ thread_focus(if thread_id filter)`.

Example recency decay: `exp(-Δdays / 180)`.

## Guardrails

* No raw SQL. Parameterized only.
* No rewriting of content. Only trim.
* Always include `attribution`, `date`.
* Respect filters strictly.

## Outputs

List of `PersonalSnippet` objects for **Context Assembly**.

## Logging

Store: query, filters, SQL plan name, counts, and the snippet ids returned. Link to `task_id`.

---

# `social-search.md`

## Purpose

Query your **Social corpus**: Facebook, Instagram, LinkedIn, X, etc. Return short-form, cadence-heavy snippets.

## Inputs

* `query`: string
* `filters` (optional): `{ platform, date_from, date_to, hashtags[], mentions[], min_engagement }`
* `limit`: int (default 30)

## Storage Model

**Tables**

* `posts(id PK, platform, content, ts, url, hashtags TEXT[], mentions TEXT[], engagement INT, meta JSONB)`
* `comments(id PK, post_id FK, author, content, ts, engagement INT)`

**Indexes**

* SQLite: FTS5 on `posts.content`; btree on `ts`, `platform`
* Postgres: GIN on `to_tsvector('english', content)`, GIN on `hashtags`, btree on `engagement`

## Access (PydanticAI)

Expose a **Tool** for safe queries with ranking and filters.

### Pydantic models (contract)

```python
from pydantic import BaseModel
from typing import List, Optional

class SocialSearchFilters(BaseModel):
    platform: Optional[str] = None   # "facebook" | "instagram" | "linkedin" | "x"
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    hashtags: Optional[List[str]] = None
    mentions: Optional[List[str]] = None
    min_engagement: Optional[int] = None

class SocialSnippet(BaseModel):
    snippet: str
    source: str  # "Social"
    date: str
    tags: List[str] = []
    voice_terms: List[str] = []
    attribution: str  # e.g., "linkedin:post/123456"
    notes: str = ""
    platform: Optional[str] = None
    post_id: Optional[str] = None

class SocialSearchResult(BaseModel):
    items: List[SocialSnippet]
```

### Tool signature

```python
@tool("social_search")
def social_search(query: str, filters: SocialSearchFilters, limit: int = 30) -> SocialSearchResult: ...
```

## Responsibilities

* FTS/BM25 on `posts.content`.
* Keep snippets short. Respect platform style.
* Preserve `platform`, `url`, `engagement` in metadata.
* Extract `voice_terms` aligned with social cadence.
* Optionally include top comments if they strengthen tone.

## Ranking

Score = `BM25`
`+ recency_decay(ts, faster)`
`+ engagement_weight(log1p(engagement))`
`+ hashtag_match_boost`.

Tune decay faster than Personal, since social freshness matters more.

## Guardrails

* No synthetic engagement.
* No cross-platform mixing unless requested.
* Always include `attribution` and `platform`.
* Do not rewrite content. Only trim.

## Outputs

List of `SocialSnippet` objects for **Context Assembly**.

## Logging

Store: query, filters, platforms touched, count, and snippet ids. Link to `task_id`.

---

## Notes on **Published Search** parity

Update `published-search.md` to match this pattern:

* DB tables: `articles(id, title, content, ts, url, author, tags[])`.
* FTS/BM25 with **authority\_weight** from domain/author.
* Longer snippet window than Social.

---

## How PydanticAI plugs into **Context Assembly**

* **Ideator** and **Critic** call these tools by policy.
* Tools return **typed snippets** that already match the **Context Pack** schema.
* `context-assembly.md` scores coverage, tone, and diversity across these results.
* No vectors required. You can add embeddings later if desired.
