# Routing Matrix

The **routing matrix** defines how prompts move through the **Multi-Corpus Governance Agent**. It provides the decision logic that governs:

* How incoming prompts are classified by type.
* How multi-corpus context is assembled and passed forward.
* How each agent hands off work to the next in sequence.
* What happens when thresholds or guardrails fail.

This document is **about flow** — the rules of movement and decision-making.
For the duties of each agent, see [`governance.md`](./governance.md).

---

## Purpose

The purpose of this routing matrix is to:

* Ensure consistency in how all prompts are processed.
* Prevent loops or undefined states in the pipeline.
* Provide transparent documentation of how governance rules are enforced.
* Make it easy for coding agents (or human contributors) to follow the exact steps in routing and retry logic.

---

## Scope

This matrix covers:

* **Classification** of prompts at entry.
* **Retrieval** of multi-corpus data (Personal, Social, Published).
* **Agent handoff logic** from Ideator → Drafter → Critic → Revisor → Summarizer.
* **Failure and retry rules** (local tweak, revise call, stop conditions).
* **Logging requirements** at each stage.

It does not define **role responsibilities** (see `governance.md`) or **context building details** (see `context-assembly.md`).

---

## Flow Overview

The routing matrix ensures that every prompt follows a consistent entry path before reaching the agent chain. The flow begins with **classification**, continues with **multi-corpus retrieval**, and then moves into the **agent handoff sequence**.

### 1. User Prompt Classification

* Every incoming prompt is first classified by type:

  * **Chat** → conversational answers.
  * **Writing** → content drafting, article generation, SEO-anchored work.
  * **Voice/Answering** → real-time or telephony use cases.
  * **Retrieval-only** → when the request is purely factual lookup.
* Classification determines the downstream constraints (tone, length, attribution rules).

### 2. Multi-Corpus Retrieval

* Once classified, the system pulls snippets from:

  * **Personal corpus** (chat history, notes).
  * **Social corpus** (Facebook, LinkedIn, short-form content).
  * **Published corpus** (blog posts, articles).
* These snippets form the **context pack**, with attribution preserved.
* The context pack is passed into the Ideator for shaping the first outline.

### 3. Agent Handoff Sequence

* After context is assembled, the request flows through the governance chain:

  * **Ideator** → constructs and validates the first outline.
  * **Drafter** → expands into a draft.
  * **Critic** → checks for truth, tone, SEO, and attribution.
  * **Revisor** → applies corrections with MVLM enforcement.
  * **Summarizer** → compresses and extracts metadata.
* Each handoff is logged and subject to guardrails to prevent loops or drift.

---

## Ideator

### Role in Routing

The Ideator is the entry point into the agent chain. It takes the user prompt and the multi-corpus context pack, shapes them into an outline, and ensures the first draft direction is aligned with tone and governance rules.

---

### Routing Logic

1. **Prep**

   * Classify intent (chat, writing, voice, retrieval-only).
   * Retrieve multi-corpus snippets (Personal, Social, Published).
   * Build a compact context pack with attribution.

2. **Generate**

   * Construct a governed API prompt (user prompt + context pack + tone rules + length limits).
   * Call the API once to produce an outline or seed ideas.

3. **Score**

   * Run light, local checks without extra API.
   * **Tone score**: overlap with “voice fingerprint” (collocations from Published + Social).
   * **Coverage score**: key concepts from context pack must appear.
   * **Guardrails**: no banned words, no length violations.

4. **Decide**

   * If all scores pass → hand off to Drafter.
   * If minor miss → apply rule-based tweak using corpus phrases.
   * If major miss → perform exactly **one revise API call** with delta prompt. Stop after that.

---

### Decision Rules

* **Acceptance thresholds**:

  * Tone score ≥ T1
  * Coverage score ≥ T2
  * Zero banned terms
* **Failure handling**:

  * Small margin miss → local tweak.
  * Hard fail → single revise call.
  * No third API call, no loop.

#### Revise Call Template

```
System: You are the Ideator. Produce an outline only. No prose.  
Rules: Match this voice and style. Do not invent beyond context. Respect length.  
Voice samples:  
- {{published_sample_1}}  
- {{social_sample_1}}  

Context (attributed):  
- {{snippet_1}} [Personal, 2024-11-02]  
- {{snippet_2}} [Published, 2024-03-18]  

User prompt: {{user_prompt}}  

Current outline failed these checks:  
- Tone: {{tone_issue}}  
- Coverage: {{coverage_issue}}  

Revise the outline to fix ONLY these issues. Keep all valid points.  
Output: bullet outline, 5–7 bullets, 1 short headline.  
```

---

### Logging

* Context pack used (with attribution).
* Scores: tone, coverage, guardrails.
* Any local tweaks applied.
* Whether revise call was triggered.

---

### Handoff

* Passes structured outline + annotations to the Drafter.
* Includes the same context pack, so the Drafter inherits all attribution and style anchors.

---

## Drafter

### Role in Routing

The Drafter expands the Ideator’s outline into a coherent draft. It anchors tone with multi-corpus samples and ensures structure and SEO alignment, while leaving fact-checking for the Critic.

---

### Routing Logic

1. **Receive Outline**

   * Takes Ideator’s structured outline and notes.
   * Inherits the same context pack with attribution.

2. **Expand Draft**

   * Construct a governed API prompt: outline + context pack + voice samples + SEO hints.
   * Make **one API call** to generate a full draft.

3. **Anchor Tone**

   * Insert corpus voice samples (Published + Social) into the API prompt.
   * Match cadence, collocations, and phrasing.

4. **Apply SEO (if writing mode)**

   * Ensure use of target keywords.
   * Respect readability and section formatting rules.

---

### Decision Rules

* **Maximum API calls**: one per handoff.
* **Coverage**: must reflect all outline points.
* **Tone**: must align with provided corpus samples.
* **Guardrails**: may not invent outside outline + context pack.

Failure handling:

* If API output drifts (tone mismatch or missed coverage), return draft with annotations for Critic rather than retrying.

---

### Logging

* Voice samples injected into the API prompt.
* Which SEO constraints were applied.
* Attribution echoes from the context pack.

---

### Handoff

* Passes drafted text (chat reply, article draft, etc.) to Critic.
* Includes metadata: voice samples used, SEO tags applied, and attribution carried forward.

---

## Critic

### Role in Routing

The Critic is the validator. It checks the Drafter’s work for truth, accuracy, tone alignment, SEO compliance, and overall governance integrity. It has the broadest access of any agent, since it must verify and cross-reference.

---

### Routing Logic

1. **Receive Draft**

   * Takes Drafter’s full draft, notes, and context pack.
   * Inherits attribution and voice samples used.

2. **Check Voice and Tone**

   * Compare draft against corpus voice fingerprint (Published + Social).
   * Flag deviations from established tone.

3. **Validate Content**

   * Cross-check factual claims using **RAG access**.
   * Query multi-corpus snippets and external sources for verification.
   * Flag unsupported or contradictory statements.

4. **SEO and Safety Review**

   * Ensure keyword coverage (if writing mode).
   * Verify compliance with banned terms, safety flags, and readability.

5. **Annotate**

   * Mark issues (voice drift, factual gaps, SEO misses).
   * Provide correction suggestions without rewriting the draft.

---

### Decision Rules

* **Maximum API calls**: up to two (one for initial validation, one targeted recheck).
* **RAG access**: unrestricted but scoped to relevant claims.
* **Failure handling**:

  * Minor issues → annotate only, let Revisor handle.
  * Major factual or safety issues → mark draft as **critical fail**, stop pipeline.

---

### Logging

* Citations for fact-checked claims.
* Voice match scores and SEO keyword coverage.
* Any flagged issues with type and severity.
* Notes for Revisor on what requires correction.

---

### Handoff

* Passes annotated draft and notes to Revisor.
* Provides clear metadata bundle: citations, tone scores, SEO coverage, flagged issues.

---

## Revisor

### Role in Routing

The Revisor takes the Critic’s annotated draft and applies the corrections. Its primary role is **implementation**, not invention. It enforces tone and structure while keeping attribution intact, with minimal API involvement.

---

### Routing Logic

1. **Receive Annotations**

   * Takes the Drafter’s draft plus Critic’s feedback notes.
   * Inherits attribution and context pack.

2. **Apply Corrections**

   * Integrate Critic’s notes deterministically (no new ideas).
   * Use corpus snippets only to adjust tone, cadence, or phrasing.

3. **Tone and Style Enforcement**

   * Compare draft against voice fingerprint to ensure alignment.
   * Adjust for consistency in readability, cadence, and SEO if flagged.

4. **Minimal API Usage**

   * Prefer **MVLM** for corrections.
   * One API fallback allowed if Critic’s corrections cannot be satisfied locally.

---

### Decision Rules

* **Maximum API calls**: zero by default, one fallback if needed.
* **Corrections only**: may not add new claims or content beyond Critic’s notes.
* **Tone enforcement**: must match corpus and governance thresholds.
* **Stop conditions**:

  * If corrections cannot be applied without inventing → flag and stop pipeline.

---

### Logging

* Changes applied, with before/after snippets.
* Whether MVLM or API was used.
* Attribution updates, if any.
* Flags raised if corrections were impossible.

---

### Handoff

* Passes revised draft to Summarizer.
* Provides change log and confirmation that Critic’s notes were addressed.

---

## Summarizer

### Role in Routing

The Summarizer is the closer. It compresses the Revisor’s draft into a concise output and extracts metadata such as long-tail keywords. It does not add new ideas — its role is packaging and metadata generation only.

---

### Routing Logic

1. **Receive Final Draft**

   * Takes the Revisor’s revised draft and change log.
   * Inherits full attribution and context pack.

2. **Compress Draft**

   * Use **MVLM** by default for minimal reasoning.
   * Reduce to a summary, preserving core meaning.
   * Only insert connector words (e.g., *and, the, with*) to keep flow.

3. **Extract Metadata**

   * Identify long-tail keywords for SEO and indexing.
   * Bundle keywords into a metadata object.
   * Keywords are stored even if not displayed (depends on mode: writing vs chat).

---

### Decision Rules

* **Reasoning**: Minimal, only for breaking sentences into summary form.
* **New words**: Not permitted beyond connectors.
* **Output**: Must remain faithful to Revisor’s draft — no re-interpretation.
* **Stop conditions**:

  * If summary drifts or keywords cannot be derived → flag pipeline error.

---

### Logging

* Summary produced.
* Long-tail keywords extracted.
* Any flagged issues or dropped sections.

---

### Handoff

* Passes final summary to user (chat mode) or stores it with metadata (writing mode).
* Provides keyword bundle to indexing/storage system.

---

## Routing Decisions

The routing matrix defines how the system responds when an agent’s checks fail.

### Minor Fail

* Definition: One threshold slightly below target (tone drift, small coverage gap).
* Action: Agent applies **local tweak** using corpus phrases or rules.
* Result: Passes corrected output forward without extra API calls.

### Major Fail

* Definition: Multiple thresholds missed or critical issues in one category.
* Action: Agent makes exactly **one revise API call** with a delta prompt.
* Result: Revised output replaces the failed one. No third call allowed.

### Critical Fail

* Definition: Unsafe, unverifiable, or contradictory output.
* Action: Pipeline stops. Output is flagged with notes and returned as error.
* Result: Requires human review before resuming.

### Escalation

* If the **Critic** flags a safety or truth failure that cannot be fixed by the Revisor, the draft is terminated and logged as a hard stop.

---

## Global Logging

Logging ensures every step is auditable and traceable.

### What to Log

* **Inputs**: user prompt, context pack, annotations received.
* **Outputs**: drafts, outlines, summaries.
* **Scores**: tone, coverage, SEO, factual checks.
* **Decisions**: local tweak applied, revise call triggered, stop condition.
* **Citations**: for all external facts validated by Critic.

### Aggregation

* Logs are stored as structured metadata objects (JSON preferred).
* Each agent appends its own entry, creating a sequential trace.
* A unique identifier ties all logs to the originating user prompt.

### Usage

* Debugging pipeline decisions.
* Auditing attribution and voice alignment.
* Feeding back into training or refinement cycles.

---

## Multi-Corpus Blending Rules

### Goal

Ensure responses reflect both **tone** (Personal + Social) and **authority** (Published), without forcing the system to pick just one corpus.

### Default Behavior

* **Ideator**:

  * Queries **all three corpora** by default.
  * Uses Personal + Social for **voice fingerprinting**.
  * Uses Published for **coverage anchors**.
* **Drafter**:

  * Works primarily with what Ideator passes down.
  * May request additional **Personal or Social** snippets for style anchoring.
* **Critic**:

  * Always allowed to re-query across corpora.
  * May trigger **RAG fallback** for Social and Published if coverage is missing or freshness is required.
* **Revisor**:

  * Inherits snippets already selected; no new corpus queries.
* **Summarizer**:

  * Never queries corpora directly; only compresses what it is given.

### Corpus Weighting

* **Personal**: Highest priority for conversational tone.
* **Social**: Supplements tone with cadence and colloquial phrasing.
* **Published**: Provides factual grounding and authority.

### Blending Logic

1. **Query All** → Ideator always starts broad, requesting top-N from each corpus.
2. **Assemble Pack** → Context Assembly merges snippets into a unified context pack.
3. **Filter & Score** → Coverage score, tone score, and diversity check ensure at least two corpora contribute.
4. **Governance** → Critic verifies attribution, truth, and balance between tone vs authority.

### Special Cases

* If **prompt intent = personal reflection/chat**, lean heavier on **Personal + Social**.
* If **prompt intent = factual/article/blog**, lean heavier on **Published**, but still inject Social tone markers.
* If **prompt intent = mixed/unclear**, balance evenly across all corpora.

---

```
User Prompt
    │
    ▼
+--------------------+
| Classification     |
| (Chat / Writing /  |
|  Voice / Retrieval)|
+--------------------+
    │
    ▼
+--------------------+
| Multi-Corpus       |
| Retrieval &        |
| Context Pack Build |
+--------------------+
    │
    ▼
+--------------------+       Minor Fail → Local Tweak
| Ideator            |------ Major Fail → Revise Call (1x)
| (Outline, tone,    |------ Critical Fail → STOP
| thresholds)        |
+--------------------+
    │
    ▼
+--------------------+
| Drafter            |
| (Expand outline,   |
| tone anchor, SEO)  |
+--------------------+
    │
    ▼
+--------------------+       Critical Fail → STOP
| Critic             |
| (Voice, truth, SEO,|
| RAG check)         |
+--------------------+
    │
    ▼
+--------------------+
| Revisor            |
| (Apply Critic’s    |
| notes, MVLM,       |
| minimal API)       |
+--------------------+
    │
    ▼
+--------------------+
| Summarizer         |
| (Compress,         |
| metadata extract)  |
+--------------------+
    │
    ▼
 Final Output + Logs
```

---

## Routing Matrix (Compact View)

| Agent          | Inputs                         | Actions                                                            | Outputs                     | Special Notes                           |
| -------------- | ------------------------------ | ------------------------------------------------------------------ | --------------------------- | --------------------------------------- |
| **Ideator**    | User prompt + context pack     | Build outline, tone/coverage scoring, local tweak or 1 revise call | Structured outline + notes  | Max 2 API calls, no loops, no invention |
| **Drafter**    | Ideator outline + context pack | Expand to draft, anchor tone, apply SEO                            | Full draft + metadata       | Max 1 API call, no fact-checking        |
| **Critic**     | Drafter draft + metadata       | Voice check, fact-check (RAG), SEO & safety                        | Annotated draft + citations | Max 2 API calls, full RAG access        |
| **Revisor**    | Critic annotations + draft     | Apply corrections deterministically, enforce tone                  | Revised draft + changelog   | MVLM preferred, 1 API fallback allowed  |
| **Summarizer** | Revisor draft + changelog      | Compress draft, extract keywords                                   | Summary + metadata bundle   | MVLM only, no new ideas                 |

---
