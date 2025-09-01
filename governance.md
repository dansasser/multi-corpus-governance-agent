# Multi-Corpus Governance Agent

## Governance Quick Reference

| **Role**       | **Inputs**                             | **Tools**                              | **Responsibilities**                            | **Outputs**                           |
| -------------- | -------------------------------------- | -------------------------------------- | ----------------------------------------------- | ------------------------------------- |
| **Ideator**    | User prompt, multi-corpus snippets     | API (1–2 calls), corpora               | Outline ideas, tone/coverage scoring, annotate  | Structured outline + notes            |
| **Drafter**    | Ideator outline + notes, voice samples | API (1 call), limited corpora          | Expand outline into draft, apply SEO + style    | Draft + metadata (voice/SEO samples)  |
| **Critic**     | Draft + outline, corpora, governance   | API (≤2 calls), corpora, RAG           | Voice, truth, SEO, safety checks, annotate      | Feedback notes + optional corrections |
| **Revisor**    | Drafter draft + Critic notes, corpora  | MVLM (preferred), limited API, corpora | Apply Critic’s notes, preserve tone, fix errors | Corrected draft + change log          |
| **Summarizer** | Revisor draft + metadata               | MVLM (preferred), API fallback         | Condense/package, extract long-tail keywords    | Summary + metadata (keywords, trims)  |

---

⚡ This table does not replace the detailed role definitions, but it gives any coding agent or reader the **entire workflow in one glance**.

Do you want me to also create a **sequence diagram (ASCII)** right under this table so the flow is visual as well?


```
User Prompt
    |
    v
+----------------+
| Classification |
+----------------+
        |
        v
+-----------------+
| Routing Matrix  |-----> Multi-Corpus Retrieval (Personal | Social | Published)
+-----------------+
        |
        v
+-------------------+
| Context Assembly  |
+-------------------+
        |
        v
+-------------------+
|      Ideator      |---(API + corpora, 1–2 calls, tone check)
+-------------------+
        |
        v
+-------------------+
|      Drafter      |---(API + limited corpora, 1 call)
+-------------------+
        |
        v
+-------------------+
|      Critic       |---(API + corpora + RAG, ≤2 calls, full check)
+-------------------+
        |
        v
+-------------------+
|      Revisor      |---(MVLM, corpus, API fallback once)
+-------------------+
        |
        v
+-------------------+
|    Summarizer     |---(MVLM only, API fallback optional)
+-------------------+
        |
        v
+-------------------+
|   Final Output    |---(Chat reply, Draft+Brief, Metadata)
+-------------------+
```

This diagram makes it crystal clear:

* Where API calls are permitted.
* Where RAG is permitted (Critic only).
* Where MVLMs act as firebreaks.
* How information flows from prompt → final output without looping.

```
                     ┌─────────────────────────┐
                     │     User Prompt Input    │
                     └─────────────┬───────────┘
                                   │
                                   ▼
                     ┌─────────────────────────┐
                     │  Routing + Corpora Pull │
                     └─────────────┬───────────┘
                                   │
             ┌─────────────────────┼─────────────────────┐
             ▼                     ▼                     ▼
      Attribution Logs       Corpus Metadata        Voice Samples
 (source, timestamp)       (tags, keywords)         (style anchors)

                                   │
                                   ▼
                ┌────────────────────────────────┐
                │       Ideator → Drafter →       │
                │       Critic → Revisor →        │
                │        Summarizer chain         │
                └────────────────┬────────────────┘
                                 │
             ┌───────────────────┼───────────────────┐
             ▼                   ▼                   ▼
     Change Logs            Long-tail Keywords     Tone/SEO Flags
 (who changed what)        (from Summarizer)       (carried down)

                                 │
                                 ▼
                      ┌─────────────────────┐
                      │     Final Output     │
                      └─────────────────────┘
                                 │
                                 ▼
        ┌─────────────────────────────────────────────────┐
        │   Logged package = Output + Metadata bundle:    │
        │   - Attribution (citations, sources)            │
        │   - Long-tail keywords (hidden/shown per mode)  │
        │   - Change log (Critic/Revisor notes)           │
        │   - Tone/SEO flags                              │
        └─────────────────────────────────────────────────┘
```

### Key points

* **Attribution** is attached at the very start (from corpora) and must persist through the chain.
* **Change logs** track what Critic and Revisor did.
* **Long-tail keywords** are produced at the Summarizer stage and only displayed in writing mode.
* **Final output = text + metadata bundle.**

---

## Metadata Schema

All outputs are delivered with an attached **metadata bundle**. This bundle persists from Ideator through Summarizer, with fields added or updated at each stage.

```json
{
  "task_id": "string",                // unique ID for this user request
  "role": "string",                   // which agent produced this output
  "input_sources": [                  // corpora and retrieval details
    {
      "corpus": "Personal|Social|Published",
      "snippet_id": "string",
      "source_text": "string",
      "timestamp": "ISO-8601"
    }
  ],
  "attribution": [                    // citations tied to claims
    {
      "claim_id": "string",
      "source": "string",
      "timestamp": "ISO-8601"
    }
  ],
  "tone_flags": {                     // tone/style governance checks
    "voice_match_score": "float",
    "seo_keywords": ["string"],
    "safety_flags": ["string"]
  },
  "change_log": [                     // applied by Critic/Revisor
    {
      "change_id": "string",
      "original_text": "string",
      "revised_text": "string",
      "reason": "string",
      "applied_by": "Critic|Revisor"
    }
  ],
  "long_tail_keywords": [             // extracted by Summarizer
    "string"
  ],
  "token_stats": {                    // tracking usage
    "input_tokens": "int",
    "output_tokens": "int"
  },
  "trimmed_sections": [               // Summarizer log
    "string"
  ],
  "final_output": "string"            // text as delivered to user
}
```

---

### Notes

* **task\_id** stays constant across the whole volley.
* **input\_sources** and **attribution** ensure provenance is never lost.
* **change\_log** is the Critic/Revisor record of what was modified and why.
* **long\_tail\_keywords** are always logged, but only surfaced in writing mode.
* **trimmed\_sections** documents what the Summarizer removed.

---

✅ This schema keeps everything deterministic, auditable, and agent-friendly.

---

## Global Governance Rules

### API and MVLM Access

* Only **Ideator, Drafter, and Critic** may call external API endpoints.
* **Revisor and Summarizer** must default to MVLMs.
* Revisor may fall back to the API once per task if MVLM fails.
* Summarizer may only fall back to the API if governance explicitly allows.

### RAG Access

* Only **Critic** may use RAG (multi-corpus and optional external/web).
* Ideator and Drafter may access corpora but not external RAG.
* Revisor and Summarizer may not retrieve additional context of any kind.

### Multi-Corpus Rules

* All roles have access to the assembled corpus context, but:

  * Ideator and Drafter use it for style and content generation.
  * Critic uses it for validation and accuracy checks.
  * Revisor uses it for tone anchoring when applying corrections.
  * Summarizer uses no new retrieval — only what is passed in.

### Attribution

* Any claim that comes from a corpus or RAG result must include source and timestamp metadata.
* If a corpus fails to return results, fallback connectors must be logged.

### Guardrails on Calls

* No role may loop indefinitely. Maximum two API calls per role per task.
* Repeated failure must be escalated as an error, not retried.
* All API calls must inject governance headers:

  * Tone rules.
  * Attribution requirements.
  * “Do not invent beyond provided context.”

### Output Integrity

* **No role may introduce new claims.**
* Revisor and Summarizer must only insert connector tokens (and, the, commas, hyphens, etc.) when restructuring.
* Summarizer must not expand vocabulary; it may only condense or rearrange.

### MVLM Placement

* Revisor MVLM = tone and accuracy enforcement, applies Critic’s notes.
* Summarizer MVLM = compression and packaging, extracts long-tail keywords.
* These MVLMs serve as a **double firebreak** against hallucination and tone drift.

### Logging and Metadata

* Each role must log:

  * Inputs received.
  * Tools used (API, MVLM, RAG, corpora).
  * Decisions made (pass/fail scores, corrections applied).
  * Outputs delivered.
* Summarizer must additionally log long-tail keywords even if not displayed.

---

## Role: Ideator

### Inputs

* User prompt.
* Multi-corpus snippets (Personal, Social, Published).
* Governance rules (tone, coverage thresholds, banned terms).

### Tools

* **API access**: up to two calls per task (one initial, one revise if needed).
* **Multi-corpus access**: yes, for assembling context packs and tone anchors.
* **No RAG** access.

### Responsibilities

1. Classify intent and retrieve relevant corpus snippets.
2. Build a compact context pack with attribution.
3. Generate an outline or seed ideas via API.
4. Score output against governance thresholds:

   * **Tone score** (voice fingerprint match).
   * **Coverage score** (concept coverage from corpora).
   * **Guardrails** (no banned words, length limits).
5. Decide:

   * Pass if scores meet thresholds.
   * Apply local tweaks if minor misses.
   * Make one revise API call if major misses.
6. Annotate results: log corpus snippets used, scores, and corrections.
7. Hand off outline and notes to Drafter.

### Guardrails

* Maximum two API calls (one initial, one revise).
* Must stop after revise call, no loops.
* Must log all scoring and corrections.
* May not invent beyond corpus + user prompt.

### Outputs

* Structured outline (5–7 bullets + headline).
* Notes on corpus snippets used, scores, and fixes.
* Context pack passed to Drafter.

---

## Role: Drafter

### Inputs

* Ideator outline and notes.
* Multi-corpus samples (small slice from Published + Social for voice, optional Personal for phrasing).
* Governance rules (tone, SEO guidelines, length, formatting).

### Tools

* **API access**: one call per task.
* **Multi-corpus access**: limited — for style/SEO anchoring only.
* **No RAG** access.

### Responsibilities

1. Expand the Ideator’s outline into a full draft.
2. Use multi-corpus voice samples to anchor tone and cadence.
3. Apply SEO hints if writing mode is active (keywords, readability, headers).
4. Respect governance rules for format, attribution, and length.
5. Produce a clean draft without attempting fact-checking (that belongs to the Critic).

### Guardrails

* Maximum one API call per handoff.
* Must include corpus voice samples in the API prompt.
* Must echo attribution notes if provided by Ideator.
* May not invent outside of provided outline + context.

### Outputs

* Drafted text (article draft, chat reply draft, etc.).
* Metadata: which voice samples were used, what SEO constraints applied.
* Hand off cleanly to Critic for validation.

---

## Role: Critic

### Inputs

* Draft from Drafter.
* Notes and outline from Ideator.
* Multi-corpus access (Personal, Social, Published).
* Governance rules (truthfulness, tone, SEO, safety).

### Tools

* **API access**: up to two calls per task.
* **Multi-corpus access**: full — can query all connectors as needed.
* **RAG access**: allowed — local corpora + external search/scraping when governance permits.

### Responsibilities

1. **Voice check**

   * Compare draft against corpus voice samples.
   * Flag or correct mismatches in style and cadence.

2. **Truth/accuracy check**

   * Cross-check claims against corpora.
   * Use RAG or web when corpora are insufficient.
   * Annotate findings with attribution.

3. **SEO check** (when in writing mode)

   * Ensure keywords, readability, headers, and overall structure meet SEO rules.

4. **Governance enforcement**

   * Apply tone and safety rules.
   * Flag redactions or sensitive info.
   * Log all checks and decisions.

### Guardrails

* Maximum of two API calls per task.
* RAG usage restricted to Critic role only.
* Must return annotated notes with sources for each claim.
* May not overwrite the entire draft — changes must be tied to identified issues.

### Outputs

* Annotated feedback document with:

  * Voice analysis results.
  * Truth/accuracy findings.
  * SEO/tone adjustments.
* Optional corrected draft (if governance rules allow).
* Full handoff to Revisor with all notes, sources, and recommended changes.

---

## Role: Revisor

### Inputs

* Annotated feedback and notes from Critic.
* Draft from Drafter.
* Multi-corpus voice/SEO samples (Personal, Social, Published).
* Governance rules (tone, attribution, corrections to apply).

### Tools

* **Primary:** MVLM access (apply Critic’s notes deterministically, low-noise rewrite).
* **Optional fallback:** API access with strict constraints (only when MVLM fails).
* **Multi-corpus access:** yes, for tone anchoring and corrections.
* **No RAG** access.

### Responsibilities

1. Apply Critic’s corrections and feedback to the draft.
2. Preserve Drafter’s tone and style, anchored by corpus samples.
3. Ensure corrected draft still respects attribution and formatting rules.
4. Avoid introducing new claims, reasoning, or hallucinations.

### Guardrails

* Must use MVLM as the first tool.
* If MVLM fails, may use API **once** with Critic’s notes and corpus samples injected.
* May not perform new retrieval or fact-checking.
* Must document changes made and which Critic notes were applied.

### Outputs

* Finalized draft that reflects Critic’s corrections and keeps the intended voice.
* Metadata: what changes were applied, what corpus samples were used.
* Passes corrected draft to Summarizer for packaging.

---

## Role: Summarizer

### Inputs

* Final draft from Revisor.
* Metadata and notes from Critic and Revisor (attribution, SEO flags, tone).
* Governance rules (length, format, attribution).

### Tools

* **Primary:** MVLM (condense, clean, package).
* **Fallback:** API once, only if MVLM fails.
* **No RAG.**
* **No direct multi-corpus retrieval.**

### Responsibilities

1. Produce a condensed version of the Revisor’s draft (chat answer, brief, abstract).
2. Preserve exact meaning.
3. Extract **long-tail keywords** for metadata. These are logged with the output, but only displayed in writing projects.
4. Only insert new words/tokens as connectors (and, the, commas, hyphens). No new claims, no new vocabulary.
5. Maintain tone/voice exactly as received.

### Guardrails

* Must not introduce new ideas or claims.
* All keywords must originate from the draft or corpora — never invented.
* Must flag if content was trimmed due to token limits.
* MVLM is default; API fallback only when governance permits.

### Outputs

* Condensed, formatted final text.
* Metadata: long-tail keywords, token count, what sections were trimmed.
* Final handoff to user/application.

---




