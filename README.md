# 📚 Multi-Corpus Governance Agent

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE.md)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/) 
[![PydanticAI](https://img.shields.io/badge/powered%20by-PydanticAI-green)](https://docs.pydantic.dev/latest/ai/)
[![Docker](https://img.shields.io/badge/docker-image-blue?logo=docker)](https://hub.docker.com/r/your-org/multi-corpus-governance-agent)
[![License: Commercial](https://img.shields.io/badge/License-Commercial-red.svg)](LICENSE.md)
[![Governance](https://img.shields.io/badge/Governance-Multi--Agent-green.svg)](governance.md)
[![Docs](https://img.shields.io/badge/Docs-README-lightgrey.svg)](README.md)
[![Status](https://img.shields.io/badge/Status-Phase%20Zero-orange.svg)](#)
[![Security Policy](https://img.shields.io/badge/Security-Policy-yellow.svg)](SECURITY.md)
[![Contributions Welcome](https://img.shields.io/badge/Contributions-Welcome-brightgreen.svg)](CONTRIBUTING.md)


A governed AI assistant that connects to multiple corpora (personal, social, published) and routes them through a **five-agent pipeline**: Ideator → Drafter → Critic → Revisor → Summarizer.

Unlike prompt-tuned chatbots, reasoning and validation are handled in the **governance layer**. Heavy lifting (idea generation, drafting, validation) uses API backends, while **Minimum Viable Language Models (MVLMs)** act as firebreaks at the end of the chain to enforce tone, reduce noise, and package results.

This design produces **accurate, auditable, and voice-aligned outputs** that can scale from content writing to chat answering and eventually real-time voice or telephony integration.

---

## ✨ Features

* 🔗 **Multi-corpus retrieval** from Personal, Social, and Published data.
* 🧩 **Five-agent governance pipeline** for checks and balances.
* 🔍 **Critic with full RAG powers** to validate truth, accuracy, and SEO.
* 🛡 **MVLM firebreaks** (Revisor + Summarizer) to lock tone and prevent drift.
* 📊 **Metadata logging**: attribution, long-tail keywords, change logs, and token usage.
* 🗣 **Persona alignment** for consistent voice across chat, writing, and publishing.

---

## 🗂 Quick Reference

| **Role**       | **Inputs**                             | **Tools**                              | **Responsibilities**                            | **Outputs**                           |
| -------------- | -------------------------------------- | -------------------------------------- | ----------------------------------------------- | ------------------------------------- |
| **Ideator**    | User prompt, multi-corpus snippets     | API (1–2 calls), corpora               | Outline ideas, tone/coverage scoring, annotate  | Structured outline + notes            |
| **Drafter**    | Ideator outline + notes, voice samples | API (1 call), limited corpora          | Expand outline into draft, apply SEO + style    | Draft + metadata (voice/SEO samples)  |
| **Critic**     | Draft + outline, corpora, governance   | API (≤2 calls), corpora, RAG           | Voice, truth, SEO, safety checks, annotate      | Feedback notes + optional corrections |
| **Revisor**    | Drafter draft + Critic notes, corpora  | MVLM (preferred), limited API, corpora | Apply Critic’s notes, preserve tone, fix errors | Corrected draft + change log          |
| **Summarizer** | Revisor draft + metadata               | MVLM (preferred), API fallback         | Condense/package, extract long-tail keywords    | Summary + metadata (keywords, trims)  |

---

## 📈 Sequence Flow

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

---

## 🗄 Metadata Flow

```
Routing + Corpora Pull
        |
        v
 Attribution ───────► Voice Samples ───────► Corpus Metadata
        |                                  |
        v                                  v
   Ideator → Drafter → Critic → Revisor → Summarizer
        |
        v
   Change Logs ───► Long-tail Keywords ───► Tone/SEO Flags
        |
        v
   Final Output + Metadata Bundle
```

---

## 📝 Metadata Schema

```json
{
  "task_id": "string",
  "role": "string",
  "input_sources": [
    {
      "corpus": "Personal|Social|Published",
      "snippet_id": "string",
      "source_text": "string",
      "timestamp": "ISO-8601"
    }
  ],
  "attribution": [
    {
      "claim_id": "string",
      "source": "string",
      "timestamp": "ISO-8601"
    }
  ],
  "tone_flags": {
    "voice_match_score": "float",
    "seo_keywords": ["string"],
    "safety_flags": ["string"]
  },
  "change_log": [
    {
      "change_id": "string",
      "original_text": "string",
      "revised_text": "string",
      "reason": "string",
      "applied_by": "Critic|Revisor"
    }
  ],
  "long_tail_keywords": ["string"],
  "token_stats": {
    "input_tokens": "int",
    "output_tokens": "int"
  },
  "trimmed_sections": ["string"],
  "final_output": "string"
}
```

---

## ⚖️ Governance Rules

* Only **Ideator, Drafter, Critic** may call APIs.
* Only **Critic** may use RAG.
* **Revisor + Summarizer** must use MVLMs as default.
* No role may loop original prompts. Max two API calls per role.
* All outputs must preserve attribution.
* Revisor and Summarizer may only add connector tokens (and, the, commas).
* Summarizer must extract long-tail keywords, logged even if hidden.

---

## 🚀 Roadmap

* [ ] Phase 1: Writing assistant + chat answering.
* [ ] Phase 2: Real-time voice with OpenAI Realtime API.
* [ ] Phase 3: Telephony integration (Twilio).
* [ ] Phase 4: Expand MVLMs for multiple personas (neutral, casual, worldview).

---

## 💡 Use Cases

* ✍️ Draft LinkedIn posts or blog entries in your exact voice.
* 💬 Deploy as a chatbot on your site with governance filters.
* 📞 Extend to real-time answering with voice APIs.
* 🔒 Maintain consistent tone, accuracy, and attribution across all channels.

---

## 🌟 Contributing

Contributions are welcome! Please open issues and PRs to improve documentation, expand connectors, or refine governance rules.

