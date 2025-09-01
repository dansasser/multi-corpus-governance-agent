# Social Search

## 🎯 Purpose

This module retrieves conversational, short-form content from the **Social corpus**.
Targets include Facebook posts, LinkedIn updates, Instagram captions, and X (Twitter) threads.
Its role is to capture cadence, colloquial tone, and audience engagement signals.

---

## 🗂️ Inputs

* **query**: string (keywords, hashtags, mentions).
* **filters** (optional):

  * Platform (facebook, instagram, linkedin, x).
  * Date range.
  * Hashtags or mentions.
  * Minimum engagement score.
* **limit**: integer (default 30).

---

## 🗄️ Storage Model

**Tables**

* `posts(id PK, platform, content, ts, url, hashtags TEXT[], mentions TEXT[], engagement INT, meta JSONB)`
* `comments(id PK, post_id FK, author, content, ts, engagement INT)`

**Indexes**

* SQLite: `posts_fts` (FTS5 on `content`); btree on `platform`, `ts`.
* Postgres: `GIN` on `to_tsvector('english', content)`; GIN on `hashtags`; btree on `engagement`.

---

## 🔧 Access (PydanticAI)

Agents interact through a **tool contract**:

```python
from pydantic import BaseModel
from typing import List, Optional

class SocialSearchFilters(BaseModel):
    platform: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    hashtags: Optional[List[str]] = None
    mentions: Optional[List[str]] = None
    min_engagement: Optional[int] = None

class SocialSnippet(BaseModel):
    snippet: str
    source: str = "Social"
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

**Tool signature**

```python
@tool("social_search")
def social_search(query: str, filters: SocialSearchFilters, limit: int = 30) -> SocialSearchResult: ...
```

---

## 📌 Responsibilities

* Run **FTS/BM25** on `posts.content`.
* Prioritize by **engagement score** and recency.
* Return short snippets (1–2 sentences max).
* Extract hashtags/mentions for **voice\_terms**.
* Include `platform`, `url`, and `engagement` in attribution.
* Deduplicate reposts and near-identical entries.

---

## ⚖️ Guardrails

* No synthetic or fabricated content.
* Attribution must always include platform + URL.
* Preserve platform-specific style (don’t normalize to formal prose).
* Separate DB vs RAG results clearly.

---

## 🌐 RAG Extension

When DB coverage is insufficient, certain agents may use **RAG/web access**:

* **Allowed Agents**: Critic (always), Ideator (conditionally).
* **External Sources**: platform APIs, scraping, or search index results.
* **Metadata**: all RAG snippets must include URL, platform, retrieval timestamp.
* **Blending**: DB results prioritized; RAG used for freshness or missing coverage.
* **Stop Condition**: unverifiable content is discarded.

---

## 📤 Outputs

All results are normalized into `SocialSnippet` objects, then aggregated into a **context pack**.

Example:

```json
{
  "snippet": "Excited to announce my new AI project today!",
  "source": "Social",
  "date": "2024-12-01",
  "tags": ["AI", "announcement"],
  "voice_terms": ["excited", "announce"],
  "attribution": "https://linkedin.com/posts/12345",
  "notes": "High engagement post, matches upbeat tone",
  "platform": "LinkedIn",
  "post_id": "12345"
}
```

---

## 📝 Logging

* Record: query, filters, platform(s) accessed, snippet IDs.
* Store: engagement scores, retrieval method (DB or RAG).
* Link to **task\_id** for traceability across governance flow.

