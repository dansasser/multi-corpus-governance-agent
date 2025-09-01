# Published Search

## 🎯 Purpose

This module retrieves long-form, authoritative text from the **Published corpus**.
Primary targets include blog posts, essays, articles, whitepapers, and research outputs.
Its role is to provide high-quality, attributed context for tone alignment, reasoning, and factual grounding.

---

## 🗂️ Inputs

* **query**: string (keywords or structured prompt).
* **filters** (optional):

  * Date range (e.g., last 6 months).
  * Author/domain filter.
  * Tags or categories.
* **limit**: integer (default 20).

---

## 🗄️ Storage Model

**Tables**

* `articles(id PK, title, content, ts, author, url, tags TEXT[], meta JSONB)`
* `sources(id PK, domain, authority_score)`

**Indexes**

* SQLite: FTS5 on `articles.content`; btree on `ts`, `author`.
* Postgres: GIN on `to_tsvector('english', content)`; btree on `ts`; GIN on `tags`.

---

## 🔧 Access (PydanticAI)

Agents interact through a **tool contract** with Pydantic models:

```python
from pydantic import BaseModel
from typing import List, Optional

class PublishedSearchFilters(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    author: Optional[str] = None
    domain: Optional[str] = None
    tags: Optional[List[str]] = None

class PublishedSnippet(BaseModel):
    snippet: str
    source: str = "Published"
    date: str
    tags: List[str] = []
    voice_terms: List[str] = []
    attribution: str  # e.g., "dansasser.me/article/slug"
    notes: str = ""
    article_id: Optional[str] = None

class PublishedSearchResult(BaseModel):
    items: List[PublishedSnippet]
```

**Tool signature**

```python
@tool("published_search")
def published_search(query: str, filters: PublishedSearchFilters, limit: int = 20) -> PublishedSearchResult: ...
```

---

## 📌 Responsibilities

* Run **FTS/BM25** over stored `articles.content`.
* Prioritize by **authority\_score** and recency.
* Return snippets in **context pack format** (see `context-assembly.md`).
* Extract **voice\_terms** for tone fingerprint alignment.
* Guarantee attribution (author, date, URL).
* Deduplicate near-identical hits.

---

## ⚖️ Guardrails

* **No fabricated text** — return only stored or externally retrieved content.
* **Attribution required** (URL, author, timestamp).
* Snippets must be concise (1–3 sentences).
* Clear separation of **DB content** vs **RAG results**.

---

## 🌐 RAG Extension

When DB coverage is insufficient, certain agents may invoke **external retrieval**:

* **Allowed Agents**: Critic (always), Ideator (conditionally).
* **External Sources**: web scraping, RSS feeds, or academic APIs.
* **Logging**: all RAG outputs must include URL + retrieval timestamp.
* **Blending Rule**: DB results are prioritized; RAG supplements with freshness or breadth.
* **Stop Condition**: if attribution cannot be verified, the snippet is discarded.

---

## 📤 Outputs

All results are normalized into `PublishedSnippet` objects and aggregated into a **context pack**.

Example:

```json
{
  "snippet": "Recent advances in PydanticAI simplify multi-agent orchestration.",
  "source": "Published",
  "date": "2024-10-12",
  "tags": ["AI", "agents", "python"],
  "voice_terms": ["multi-agent", "orchestration"],
  "attribution": "https://medium.com/example-post",
  "notes": "Use as authority anchor for governance article",
  "article_id": "A1234"
}
```

---

## 📝 Logging

* Record: query, filters, source (DB or RAG), IDs of snippets.
* Store: attribution details, authority score, relevance score.
* Link logs to **task\_id** for full traceability.
