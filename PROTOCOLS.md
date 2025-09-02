# Protocol-Driven Architecture Manifest

This repository implements a protocol-driven architecture. The authoritative
contracts live in code as Pydantic models and constants under
`src/mcg_agent/protocols/`, derived from root documentation:

- `governance.md`
- `routing-matrix.md`
- `context-assembly.md`
- `docs/security/protocols/governance-protocol.md`

## Protocol Modules

- `protocols/governance_protocol.py`
  - `APICallLimits`: Agent API call ceilings (ideator=2, drafter=1, critic=2, revisor=1, summarizer=0)
  - `CorpusAccessMatrix`: Corpus access by role (Personal, Social, Published)
  - `RAGAccessPolicy`: RAG permissions (Critic always; Ideator conditional on coverage for Social/Published)

- `protocols/routing_protocol.py`
  - `ClassificationType`: `chat|writing|voice|retrieval-only`
  - `PipelineOrder`: Stage order `ideator→drafter→critic→revisor→summarizer`
  - `REVISE_CALL_TEMPLATE`: Exact revise template for Ideator

- `protocols/context_protocol.py`
  - `ContextSnippet`: Canonical snippet structure with attribution and voice terms
  - `ContextPack`: Assembled pack with optional scoring fields

- `protocols/punctuation_protocol.py`
  - `PunctuationPolicy`: Canonical punctuation/output control rules
  - `DEFAULT_PUNCTUATION_POLICY`: Repository default policy

- `metadata/models.py`
  - `MetadataBundle` and related models mirrored from `governance.md`

## Usage Rules

1. Never hardcode policy in feature modules. Import from `mcg_agent.protocols.*`.
2. Governance checks must consult `APICallLimits`, `CorpusAccessMatrix`, and `RAGAccessPolicy`.
3. Routing logic and revise flows must use `PipelineOrder` and `REVISE_CALL_TEMPLATE`.
4. Context assembly must produce `ContextPack` of `ContextSnippet`s.
5. Metadata must conform to `MetadataBundle` exactly.

## Change Management

All protocol changes must update:
- Root docs and `docs/security/protocols/governance-protocol.md`
- The corresponding `src/mcg_agent/protocols/*` module(s)
- Tests validating governance and routing behavior
