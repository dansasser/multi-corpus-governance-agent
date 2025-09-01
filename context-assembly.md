# Context Assembly

## 🎯 Purpose

The purpose of context assembly is to take data from multiple corpora and shape it into a **usable context pack**. This ensures that every agent in the governance chain works from consistent, attributed, and tone-aligned input. Context assembly is responsible for selection, attribution, and compression before information enters the pipeline.

---

## 🗂️ Sources

* **Personal corpus** → chat history, notes, raw drafts, and one-off ideas.
* **Social corpus** → public posts, microcontent, conversational tone data.
* **Published corpus** → long-form articles, blogs, research pieces, professional outputs.
* **External retrievals** (optional) → RAG queries, web snippets, or API lookups to supplement coverage.

---

## 🏗️ Assembly Rules

### Selection

* Pull only the most relevant snippets to the classified user prompt.
* Prioritize **freshness** for Social corpus and **authority** for Published corpus.
* Ensure minimum coverage from at least two corpora when available.

### Attribution

* Every snippet must include:

  * Source type (Personal, Social, Published, External).
  * Timestamp.
  * Author (if known).
* Attribution must persist through every stage of the pipeline.

### Compression

* Trim snippets to essential phrases or sentences.
* Remove duplication and redundant phrasing.
* Preserve identifiers, tags, and attribution metadata.

---

## 🔊 Voice Fingerprinting

* Build per-corpus dictionaries of **top n collocations and cadence markers**.
* Maintain separate fingerprints for:

  * **Personal corpus** → conversational tone and phrasing.
  * **Social corpus** → short-form cadence, colloquial style.
  * **Published corpus** → formal structures, article-level phrasing.
* Use fingerprints to calculate **tone scores** during draft evaluation.
* Keep fingerprints lightweight and local: simple frequency counts are sufficient.
* Update fingerprints periodically as new data is added.

---

## 📦 Context Pack Structure

Each context pack bundles selected snippets and metadata into a portable package for agents.

### Required Fields

* **Snippet text**: trimmed phrase or sentence.
* **Source**: Personal, Social, Published, or External.
* **Date**: timestamp of original snippet.
* **Tags**: keywords tied to snippet relevance.
* **Voice terms**: fingerprinted collocations for tone alignment.
* **Attribution**: link to source location or identifier.
* **Usage notes**: why this snippet was selected.

### Example (JSON)

```json
{
  "snippet": "AI-assisted workflows streamline creative output.",
  "source": "Published",
  "date": "2024-03-18",
  "tags": ["AI", "workflow", "content"],
  "voice_terms": ["streamline", "creative output"],
  "attribution": "dansasser.me/blog/ai-workflows",
  "notes": "Anchor for writing mode, matches brand tone"
}
```

---

## ⚖️ Scoring and Thresholds

### Coverage Score

* Measures how well the context pack represents the user prompt.
* Calculated as % of prompt concepts present in selected snippets.
* Threshold: **≥ T1** (configurable).

### Tone Score

* Measures overlap between draft text and **voice fingerprints**.
* Counts matching collocations and cadence markers.
* Threshold: **≥ T2** (configurable, corpus-specific).

### Diversity Check

* Ensures at least **two corpora** are represented when possible.
* Prevents over-reliance on a single source.

### Guardrails

* Zero banned terms.
* Length within configured limits.
* Attribution preserved on every snippet.

---

## 📝 Logging

### Required Log Data

* Snippets included (with full attribution).
* Fingerprints applied.
* Coverage score, tone score, diversity check results.
* Guardrail pass/fail notes.

### Structure

* All logs stored as **structured metadata** (JSON recommended).
* Each entry tied to a unique **prompt ID** for traceability.

### Usage

* Enables auditing of snippet selection.
* Provides explainability for downstream agents.
* Supports feedback loops for improving fingerprint accuracy.



