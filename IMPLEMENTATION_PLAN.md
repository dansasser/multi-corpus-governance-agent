# Multi-Corpus Governance Agent - Complete Implementation Plan

## 🚨 CRITICAL COMPLIANCE REQUIREMENT
This implementation plan MUST be followed exactly as written. Every component, every API call limit, every failure pattern, every governance rule specified in the documentation must be implemented precisely. No deviations, no interpretations, no shortcuts.

## 📚 Documentation Authority
This implementation is governed by these documents in order of precedence:
1. `agents.md` - Primary orientation and architecture
2. `routing-matrix.md` - Flow control, API limits, failure patterns
3. `governance.md` - Agent roles, responsibilities, constraints
4. `context-assembly.md` - Context handling and voice fingerprinting
5. `docs/security/protocols/governance-protocol.md` - **CRITICAL** Runtime governance enforcement
6. `docs/security/architecture/security-architecture.md` - **CRITICAL** Zero Trust security architecture
7. `docs/security/compliance/deployment-security.md` - **CRITICAL** Production deployment security
8. `personal-search.md` - Personal corpus search specifications
9. `social-search.md` - Social corpus search specifications  
10. `published-search.md` - Published corpus search specifications

**⚠️ SECURITY SUITE COMPLIANCE MANDATORY**: All implementation must comply with the comprehensive security documentation suite under `docs/security/` created in this session.

## 🎯 Architecture Overview

The system follows this exact flow per routing-matrix.md:
```
User Prompt → Classification → Multi-Corpus Retrieval → Context Assembly → 
Ideator (max 2 API) → Drafter (max 1 API) → Critic (max 2 API) → 
Revisor (MVLM preferred, 1 API fallback) → Summarizer (MVLM only) → Final Output
```

## 📋 Phase 1: Security Foundation & PydanticAI Core Infrastructure (Priority: CRITICAL)

### 1.1 PydanticAI Agent Orchestration Framework
**Purpose**: Implement PydanticAI as the PRIMARY agent orchestration framework
**Documentation Reference**: agents.md lines 13, 16, 216, 218, docs/security/protocols/governance-protocol.md

**PydanticAI Requirements** (FIRST PRIORITY):
- PydanticAI agent framework as core orchestration system
- Agent governance rules enforced through PydanticAI runtime
- Tool-based corpus access through PydanticAI tools
- Runtime governance validation that cannot be bypassed
- Agent role-based permissions enforced by framework

**Files to Create FIRST**:
- `src/mcg_agent/pydantic_ai/agent_base.py` - PydanticAI agent base classes
- `src/mcg_agent/pydantic_ai/tools.py` - Corpus access tools with governance
- `src/mcg_agent/pydantic_ai/governance.py` - Runtime governance enforcement

### 1.2 Security Architecture Implementation (Zero Trust)
**Purpose**: Implement comprehensive security architecture per docs/security/
**Documentation Reference**: docs/security/architecture/security-architecture.md, docs/security/protocols/governance-protocol.md

**Security Architecture Requirements** (exact from security suite):
- Zero Trust Architecture with governance-enforced security
- WAF integration for internet boundary protection
- FastAPI Gateway with JWT Auth + Rate Limiting
- Input validation through Pydantic schemas
- TLS 1.3 for all connections
- Database encryption at rest and in transit
- Redis session store with TLS + AUTH

**Files to Create**:
- `src/mcg_agent/security/zero_trust.py` - Zero Trust implementation
- `src/mcg_agent/security/waf_integration.py` - WAF integration layer
- `src/mcg_agent/security/governance_enforcer.py` - Runtime governance enforcement
- `src/mcg_agent/security/audit_trail.py` - Immutable audit logging

### 1.3 CLI Tool Implementation
**Purpose**: Implement CLI tool per agents.md requirements  
**Documentation Reference**: agents.md lines 91, 109, 331, 349

**CLI Tool Requirements**:
- `mcg-agent serve --reload` - Development server with hot reload
- `mcg-agent serve --workers 4` - Production server with multiple workers
- CLI integration with existing scripts
- Command-line argument parsing and validation

**Files to Create**:
- `src/mcg_agent/cli/__init__.py` - CLI module initialization
- `src/mcg_agent/cli/main.py` - Main CLI entry point
- `src/mcg_agent/cli/commands.py` - CLI command implementations
- `src/mcg_agent/cli/config.py` - CLI configuration management
- `scripts/setup.sh` - ✅ Already exists - automated setup
- `scripts/init-db.sh` - ✅ Already exists - database initialization  
- `scripts/start-dev.sh` - ✅ Already exists - development server
- `scripts/start-prod.sh` - ✅ Already exists - production server
- `scripts/health-check.sh` - ✅ Already exists - health monitoring with format support
- `scripts/run-tests.sh` - ✅ Already exists - test execution

### 1.4 Requirements & Setup Integration  
**Purpose**: Integrate with existing requirements.txt and setup.py
**Documentation Reference**: agents.md lines 59, 62, 280, 283

**Integration Requirements**:
- Validate `pip install -e .[dev]` setup works with PydanticAI
- Ensure requirements.txt includes pydantic-ai
- Verify setup.py configuration matches agents.md specs
- Test both development and production installation paths

### 1.5 Existing Scripts Integration

**none**


### 1.6 Environment Variables Security Implementation
**Purpose**: Implement complete environment variable security per agents.md  
**Documentation Reference**: agents.md lines 291-311

**Required Environment Variables** (EXACT from documentation):
```bash
# Database Configuration
DATABASE_URL=sqlite:///./mcg_agent.db

# Redis Configuration (session management)
REDIS_URL=redis://localhost:6379/0

# Security Keys (generate secure values!)
JWT_SECRET_KEY=your-jwt-secret-key-here
ENCRYPTION_KEY=your-32-byte-encryption-key

# API Keys - BOTH required
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# Server Configuration
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

**Implementation Requirements**:
- Secure 32-byte encryption key generation
- Environment variable validation on startup
- Support for both OpenAI AND Anthropic API keys
- DEBUG and ENVIRONMENT flag handling
- LOG_LEVEL configuration integration

### 1.7 API Call Tracking System Implementation
**Purpose**: Implement complete API call tracking per governance protocol
**Documentation Reference**: docs/security/protocols/governance-protocol.md lines 117-143

**Files to Create**:
- `src/mcg_agent/governance/call_tracker.py` - API call tracking system
- `src/mcg_agent/governance/api_limits.py` - API limit enforcement
- `src/mcg_agent/utils/security_logger.py` - Security violation logging

**API Call Tracking Implementation** (EXACT from governance protocol):
```python
class APICallGovernance:
    AGENT_LIMITS = {
        'ideator': 2,
        'drafter': 1, 
        'critic': 2,
        'revisor': 1,     # fallback only when MVLM fails
        'summarizer': 0   # emergency fallback only
    }
    
    @staticmethod
    async def validate_api_call(agent_name: str, task_id: str) -> bool:
        current_calls = await CallTracker.get_call_count(agent_name, task_id)
        max_calls = APICallGovernance.AGENT_LIMITS.get(agent_name, 0)
        
        if current_calls >= max_calls:
            await SecurityLogger.log_governance_violation(
                violation_type="api_call_limit_exceeded",
                agent_name=agent_name,
                current_calls=current_calls,
                max_calls=max_calls,
                task_id=task_id
            )
            raise APICallLimitExceededError(agent_name, max_calls, current_calls + 1)
        
        return True
```

### 1.8 PydanticAI Governance Tool Pattern Implementation
**Purpose**: Implement PydanticAI tool governance pattern per security protocols
**Documentation Reference**: docs/security/protocols/governance-protocol.md lines 147-222

**Files to Create**:
- `src/mcg_agent/pydantic_ai/secure_tools.py` - Governance tool decorator
- `src/mcg_agent/pydantic_ai/governance_validation.py` - Runtime validation

**Secure Tool Pattern Implementation** (EXACT from governance protocol):
```python
from pydantic_ai import Agent, RunContext

class SecureAgentTool:
    @staticmethod
    def governance_tool(
        required_permissions: List[str],
        corpus_access: Optional[List[str]] = None,
        max_calls_per_task: int = 0
    ):
        def decorator(func):
            async def wrapper(ctx: RunContext[AgentInput], *args, **kwargs):
                # 1. Validate agent permissions
                await GovernanceRules.validate_agent_permissions(
                    agent_name=ctx.deps.agent_role,
                    required_permissions=required_permissions,
                    task_id=ctx.deps.task_id
                )
                
                # 2. Check corpus access if required
                if corpus_access:
                    for corpus in corpus_access:
                        if not GovernanceRules.validate_corpus_access(
                            ctx.deps.agent_role, corpus
                        ):
                            raise UnauthorizedCorpusAccessError(
                                ctx.deps.agent_role, corpus
                            )
                
                # 3. Validate API call limits
                if max_calls_per_task > 0:
                    await APICallGovernance.validate_api_call(
                        ctx.deps.agent_role, ctx.deps.task_id
                    )
                
                # 4. Execute with logging
                result = await func(ctx, *args, **kwargs)
                
                # 5. Log successful execution
                await AuditLogger.log_tool_execution(
                    agent_role=ctx.deps.agent_role,
                    tool_name=func.__name__,
                    task_id=ctx.deps.task_id,
                    input_params=kwargs,
                    success=True
                )
                
                return result
            
            return wrapper
        return decorator
```

### 1.9 Multi-Corpus Database Schema Implementation
**Purpose**: Implement exact database schemas per corpus search documentation
**Documentation Reference**: personal-search.md lines 13-24, social-search.md lines 24-34, published-search.md lines 23-33

**Database Schema Requirements** (EXACT from original documentation):

**Personal Corpus Schema** (personal-search.md):
```sql
-- Tables
messages(id PK, thread_id, role, content, ts, source, channel, meta JSONB)
threads(thread_id PK, title, participants, tags TEXT[], started_at)
attachments(id PK, message_id FK, kind, url, meta JSONB)

-- Indexes
-- SQLite: messages_fts (FTS5 on content) with trigram optional
-- Postgres: GIN on to_tsvector('english', content), btree on ts, thread_id
```

**Social Corpus Schema** (social-search.md):
```sql
-- Tables  
posts(id PK, platform, content, ts, url, hashtags TEXT[], mentions TEXT[], engagement INT, meta JSONB)
comments(id PK, post_id FK, author, content, ts, engagement INT)

-- Indexes
-- SQLite: posts_fts (FTS5 on content); btree on platform, ts
-- Postgres: GIN on to_tsvector('english', content); GIN on hashtags; btree on engagement
```

**Published Corpus Schema** (published-search.md):
```sql
-- Tables
articles(id PK, title, content, ts, author, url, tags TEXT[], meta JSONB)
sources(id PK, domain, authority_score)

-- Indexes  
-- SQLite: FTS5 on articles.content; btree on ts, author
-- Postgres: GIN on to_tsvector('english', content); btree on ts; GIN on tags
```

### 1.10 Corpus Search Tool Implementation
**Purpose**: Implement exact PydanticAI tool signatures per corpus documentation
**Documentation Reference**: personal-search.md lines 60-65, social-search.md lines 69-74, published-search.md lines 66-71

**PydanticAI Tool Signatures** (EXACT from documentation):
```python
# Personal Search Tool
@tool("personal_search")
def personal_search(query: str, filters: PersonalSearchFilters, limit: int = 20) -> PersonalSearchResult: ...

# Social Search Tool  
@tool("social_search")
def social_search(query: str, filters: SocialSearchFilters, limit: int = 30) -> SocialSearchResult: ...

# Published Search Tool
@tool("published_search") 
def published_search(query: str, filters: PublishedSearchFilters, limit: int = 20) -> PublishedSearchResult: ...
```

**Corpus Models** (EXACT from documentation):
```python
# Personal Search Models
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
```

### 1.11 Corpus Ranking Algorithms Implementation
**Purpose**: Implement exact ranking algorithms per corpus documentation
**Documentation Reference**: personal-search.md lines 75-82, social-search.md lines 173-180, published-search.md lines 76-82

**Personal Search Ranking** (personal-search.md):
```python
# Score = BM25 + recency_decay(ts) + role_boost(assistant ≈ your authored tone) + thread_focus(if thread_id filter)
# Example recency decay: exp(-Δdays / 180)
```

**Social Search Ranking** (social-search.md):
```python
# Score = BM25 + recency_decay(ts, faster) + engagement_weight(log1p(engagement)) + hashtag_match_boost
# Tune decay faster than Personal, since social freshness matters more
```

**Published Search Ranking** (published-search.md):
```python
# Score = BM25 + authority_weight(from domain/author) + recency_decay(ts)
# Authority weight from sources.authority_score
```

### 1.12 Voice Fingerprinting Algorithm Implementation
**Purpose**: Implement voice fingerprinting algorithm per context-assembly.md
**Documentation Reference**: context-assembly.md lines 43-53

**Voice Fingerprinting Requirements** (EXACT from documentation):
- Build per-corpus dictionaries of **top N collocations and cadence markers**
- Separate fingerprints for:
  - **Personal corpus** → conversational tone and phrasing
  - **Social corpus** → short-form cadence, colloquial style  
  - **Published corpus** → formal structures, article-level phrasing
- Use fingerprints to calculate **tone scores** during draft evaluation
- Keep fingerprints lightweight and local: simple frequency counts sufficient
- Update fingerprints periodically as new data is added

### 1.13 Scoring Thresholds System Implementation  
**Purpose**: Implement scoring thresholds per context-assembly.md
**Documentation Reference**: context-assembly.md lines 87-112

**Scoring System Requirements** (EXACT from documentation):
```python
class ScoringThresholds(BaseModel):
    coverage_score_min: float  # T1 - % of prompt concepts present in selected snippets
    tone_score_min: float      # T2 - overlap between draft text and voice fingerprints
    diversity_check: bool      # Ensures at least two corpora represented when possible
    banned_terms_max: int = 0  # Zero banned terms
    length_limits: Dict[str, int]  # Length within configured limits
```

**Coverage Score**: Calculated as % of prompt concepts present in selected snippets. Threshold: **≥ T1** (configurable)
**Tone Score**: Counts matching collocations and cadence markers. Threshold: **≥ T2** (configurable, corpus-specific)
**Diversity Check**: Ensures at least **two corpora** are represented when possible

### 1.14 MVLM Integration Interface
**Purpose**: Implement Minimum Viable Language Model interface as primary tool for Revisor/Summarizer
**Documentation Reference**: governance.md lines 196-199, 238-240, routing-matrix.md lines 319-321

**Files to Create**:
- `src/mcg_agent/mvlm/interface.py` - Abstract MVLM interface
- `src/mcg_agent/mvlm/local_mvlm.py` - Local MVLM implementation  
- `src/mcg_agent/mvlm/fallback.py` - API fallback when MVLM fails

**Requirements**:
- Abstract interface with `process()` method
- Local MVLM for tone enforcement and compression
- API fallback with governance permission checks
- Usage tracking and logging
- Error handling for MVLM failures

**Implementation Details**:
```python
class MVLMInterface(ABC):
    @abstractmethod
    async def process(self, input_text: str, task_type: str, governance_rules: Dict) -> MVLMResult
    
class MVLMResult(BaseModel):
    output_text: str
    success: bool
    token_usage: Dict[str, int]
    processing_time: float
    fallback_used: bool = False
```

### 1.2 Multi-Corpus Search Infrastructure
**Purpose**: Implement Personal, Social, Published corpus search per documentation specs
**Documentation Reference**: personal-search.md, social-search.md, published-search.md, context-assembly.md

**Files to Create**:
- `src/mcg_agent/corpus/base_search.py` - Abstract search interface
- `src/mcg_agent/corpus/personal_search.py` - Personal corpus implementation
- `src/mcg_agent/corpus/social_search.py` - Social corpus implementation  
- `src/mcg_agent/corpus/published_search.py` - Published corpus implementation
- `src/mcg_agent/corpus/models.py` - Pydantic models for all corpus types

**Database Schema** (per documentation):
```sql
-- Personal Corpus
CREATE TABLE messages(id PK, thread_id, role, content, ts, source, channel, meta JSONB);
CREATE TABLE threads(thread_id PK, title, participants, tags TEXT[], started_at);
CREATE TABLE attachments(id PK, message_id FK, kind, url, meta JSONB);

-- Social Corpus  
CREATE TABLE posts(id PK, platform, content, ts, url, hashtags TEXT[], mentions TEXT[], engagement INT, meta JSONB);
CREATE TABLE comments(id PK, post_id FK, author, content, ts, engagement INT);

-- Published Corpus
CREATE TABLE articles(id PK, title, content, ts, author, url, tags TEXT[], meta JSONB);
CREATE TABLE sources(id PK, domain, authority_score);
```

**Search Tool Contracts** (exact from documentation):
```python
@tool("personal_search")
def personal_search(query: str, filters: PersonalSearchFilters, limit: int = 20) -> PersonalSearchResult

@tool("social_search")  
def social_search(query: str, filters: SocialSearchFilters, limit: int = 30) -> SocialSearchResult

@tool("published_search")
def published_search(query: str, filters: PublishedSearchFilters, limit: int = 20) -> PublishedSearchResult
```

### 1.3 Context Assembly System
**Purpose**: Build context packs with attribution and voice fingerprinting
**Documentation Reference**: context-assembly.md lines 42-135

**Files to Create**:
- `src/mcg_agent/context/assembly.py` - Main context assembly logic
- `src/mcg_agent/context/voice_fingerprint.py` - Voice fingerprinting system
- `src/mcg_agent/context/scoring.py` - Coverage and tone scoring
- `src/mcg_agent/context/models.py` - Context pack data models

**Context Pack Structure** (exact from documentation):
```python
class ContextSnippet(BaseModel):
    snippet: str
    source: Literal["Personal", "Social", "Published", "External"]
    date: str  
    tags: List[str]
    voice_terms: List[str]
    attribution: str
    notes: str
    
class ContextPack(BaseModel):
    snippets: List[ContextSnippet]
    coverage_score: float
    tone_score: float  
    diversity_check: bool
    voice_fingerprint: Dict[str, List[str]]
```

**Voice Fingerprinting Requirements**:
- Per-corpus dictionaries of top N collocations
- Frequency-based collocation extraction
- Separate fingerprints for Personal (conversational), Social (short-form), Published (formal)
- Lightweight local processing only

### 1.4 Scoring and Threshold System
**Purpose**: Implement configurable thresholds for governance decisions
**Documentation Reference**: routing-matrix.md lines 115-124, context-assembly.md lines 87-112

**Files to Create**:
- `src/mcg_agent/scoring/thresholds.py` - Configurable threshold management
- `src/mcg_agent/scoring/evaluator.py` - Score calculation logic
- `src/mcg_agent/scoring/models.py` - Scoring result models

**Threshold Implementation**:
```python
class GovernanceThresholds(BaseModel):
    tone_score_min: float = 0.7  # T1 from documentation
    coverage_score_min: float = 0.8  # T2 from documentation
    banned_terms_max: int = 0
    length_limits: Dict[str, int]
    
class ScoreResult(BaseModel):
    tone_score: float
    coverage_score: float
    guardrails_passed: bool
    threshold_status: Literal["pass", "minor_fail", "major_fail", "critical_fail"]
```

### 1.10 Governed Agent Pipeline Implementation  
**Purpose**: Implement complete governed pipeline orchestration per security protocols
**Documentation Reference**: docs/security/protocols/governance-protocol.md lines 224-362

**Files to Create**:
- `src/mcg_agent/pipeline/governed_pipeline.py` - Main pipeline orchestration
- `src/mcg_agent/pipeline/stage_executor.py` - Individual stage execution
- `src/mcg_agent/pipeline/failure_handler.py` - Critical failure handling

**GovernedAgentPipeline Implementation** (EXACT from governance protocol):
```python
class GovernedAgentPipeline:
    async def process_request(self, user_prompt: str) -> AgentOutput:
        task_id = str(uuid4())
        
        # Initialize governance context
        governance_context = GovernanceContext(
            task_id=task_id,
            user_prompt=user_prompt,
            classification=await self.classify_prompt(user_prompt)
        )
        
        # Stage 1: Ideator (max 2 API calls)
        # Stage 2: Drafter (max 1 API call)  
        # Stage 3: Critic (max 2 API calls + RAG)
        # Stage 4: Revisor (MVLM preferred, API fallback)
        # Stage 5: Summarizer (MVLM only)
        
        # Each stage includes:
        # - Pre-execution governance validation
        # - 5-minute timeout per agent
        # - Post-execution validation
        # - Critical failure handling
```

### 1.11 Violation Classification & Response Implementation
**Purpose**: Implement violation response protocols per security suite
**Documentation Reference**: docs/security/protocols/governance-protocol.md lines 366-457

**Files to Create**:
- `src/mcg_agent/governance/violation_handler.py` - Violation classification and response
- `src/mcg_agent/governance/containment.py` - Automated containment actions
- `src/mcg_agent/governance/alerting.py` - Security team alerting

**Violation Classification** (EXACT from governance protocol):
```yaml
Critical_Violations:
  - Unauthorized corpus access attempt
  - RAG access by non-Critic agent  
  - API call limit exceeded by >100%
  - Attempt to modify immutable data
  Response: Immediate pipeline termination + security alert

High_Violations:
  - API call limit exceeded by <100%
  - Invalid input format detected
  - Authentication token issues
  Response: Request rejection + warning log

Medium_Violations:
  - Rate limiting triggered
  - Input validation failures
  - Non-critical configuration errors
  Response: Graceful error handling + monitoring alert
```

## 📋 Phase 2: Agent Architecture Compliance (Priority: CRITICAL)

### 2.1 API Call Limit Enforcement
**Purpose**: Enforce exact API call limits per agent per routing-matrix.md
**Documentation Reference**: routing-matrix.md lines 572-577, governance.md lines 220-230

**Implementation Requirements**:
- Ideator: Maximum 2 API calls (1 initial + 1 revise)
- Drafter: Maximum 1 API call per task
- Critic: Maximum 2 API calls per task  
- Revisor: MVLM preferred, 1 API fallback maximum
- Summarizer: MVLM only, API fallback only with governance permission

**Files to Create**:
- `src/mcg_agent/agents/base_agent.py` - Add API call tracking and limits
- All agent implementations - Enforce specific limits

**Tracking Implementation**:
```python
class APICallTracker:
    def __init__(self, agent_role: AgentRole, max_calls: int):
        self.agent_role = agent_role
        self.max_calls = max_calls
        self.calls_made = 0
        
    async def track_call(self) -> bool:
        if self.calls_made >= self.max_calls:
            raise APICallLimitExceededError(f"{self.agent_role} exceeded {self.max_calls} API calls")
        self.calls_made += 1
        return True
```

### 2.2 RAG Access Rules Implementation
**Purpose**: Implement RAG access rules per corpus search documentation  
**Documentation Reference**: social-search.md lines 98-107, published-search.md lines 95-104

**RAG Access Rules** (EXACT from documentation):
- **Social Search RAG**: Critic (always), Ideator (conditionally when coverage gaps)
- **Published Search RAG**: Critic (always), Ideator (conditionally when coverage gaps)
- **Personal Search**: No RAG access (DB-only per personal-search.md)

**RAG Implementation Requirements**:
```python
class RAGAccessValidator:
    ALLOWED_RAG_AGENTS = {
        'social': ['critic', 'ideator'],  # Ideator conditionally
        'published': ['critic', 'ideator'],  # Ideator conditionally  
        'personal': []  # No RAG access
    }
    
    def validate_rag_access(self, agent_role: str, corpus: str) -> bool:
        if corpus == 'personal':
            return False  # Personal is DB-only
        return agent_role in self.ALLOWED_RAG_AGENTS.get(corpus, [])
```

**Snippet Processing Requirements**:
- **Personal Search**: Window hits to ±240 chars (personal-search.md line 70)
- **Social Search**: Keep snippets short, 1-2 sentences max (social-search.md line 82)
- **Published Search**: Concise snippets, 1-3 sentences (published-search.md line 90)
- **Voice Terms Extraction**: Top collocations from hits for tone anchoring

### 2.3 Failure Pattern Implementation
**Purpose**: Implement Minor/Major/Critical fail patterns exactly per routing-matrix.md
**Documentation Reference**: routing-matrix.md lines 410-431

**Failure Definitions** (exact from documentation):
- **Minor Fail**: One threshold slightly below target → local tweak using corpus phrases
- **Major Fail**: Multiple thresholds missed → exactly one revise API call with delta prompt  
- **Critical Fail**: Unsafe/unverifiable/contradictory → pipeline stops, flag for human review

**Files to Create**:
- `src/mcg_agent/governance/failure_handler.py` - Failure pattern logic
- `src/mcg_agent/governance/recovery.py` - Local tweak and revise call logic

**Implementation Requirements**:
```python
class FailureHandler:
    async def handle_failure(self, scores: ScoreResult, agent_role: AgentRole) -> FailureAction:
        if scores.threshold_status == "minor_fail":
            return LocalTweakAction(corpus_phrases=self.get_corpus_phrases())
        elif scores.threshold_status == "major_fail":  
            return ReviseCallAction(delta_prompt=self.build_delta_prompt(scores))
        elif scores.threshold_status == "critical_fail":
            return StopPipelineAction(reason="Critical failure - human review required")
```

### 2.4 Agent Role Differentiation & Naming Convention
**Purpose**: Implement exact agent responsibilities per governance.md with correct naming
**Documentation Reference**: governance.md lines 254-472, agents.md lines 174

**Agent Naming Convention** (EXACT from agents.md line 174):
- `IdeatorAgent` - NOT IdeatorAgent class
- `DrafterAgent` - NOT DrafterAgent class  
- `CriticAgent` - NOT CriticAgent class
- `RevisorAgent` - NOT RevisorAgent class
- `SummarizerAgent` - NOT SummarizerAgent class

**IdeatorAgent Requirements** (governance.md lines 254-298):
- Classify intent and retrieve corpus snippets
- Build compact context pack with attribution
- Generate outline via API (max 2 calls)
- Score against governance thresholds (tone, coverage, guardrails)
- Apply local tweaks for minor fails, revise call for major fails
- Hand off structured outline (5–7 bullets + headline) to Drafter

**DrafterAgent Requirements** (governance.md lines 300-335):
- Expand Ideator outline into full draft
- Use multi-corpus voice samples for tone anchoring
- Apply SEO hints in writing mode (keywords, readability, headers)
- Maximum 1 API call per task
- No fact-checking (belongs to Critic)
- Must include corpus voice samples in API prompt

**CriticAgent Requirements** (governance.md lines 337-392):
- Voice check against corpus samples
- Truth/accuracy check with RAG access (ONLY agent with RAG)
- SEO check when in writing mode
- Maximum 2 API calls per task
- Cross-check claims against corpora + external RAG when needed
- Annotate findings with attribution (cannot overwrite entire draft)

**RevisorAgent Requirements** (governance.md lines 394-430):
- Apply Critic corrections using MVLM primarily
- Preserve tone and style from corpus samples
- 1 API fallback allowed if MVLM fails (must use MVLM first)
- No new retrieval or fact-checking
- Document all changes applied with before/after snippets

**SummarizerAgent Requirements** (governance.md lines 432-472):
- Use MVLM for compression and packaging (MVLM only by default)
- Extract long-tail keywords for metadata
- No new claims or vocabulary beyond connectors (and, the, commas, hyphens)
- API fallback only with governance permission
- Maintain exact meaning from Revisor draft

## 📋 Phase 3: Routing Matrix Compliance (Priority: HIGH)

### 3.1 Classification System Implementation
**Purpose**: Implement user prompt classification per routing-matrix.md
**Documentation Reference**: routing-matrix.md lines 44-53

**Classification Types** (exact from documentation):
- **Chat**: conversational answers
- **Writing**: content drafting, article generation, SEO-anchored work  
- **Voice/Answering**: real-time or telephony use cases
- **Retrieval-only**: purely factual lookup

**Files to Create**:
- `src/mcg_agent/classification/classifier.py` - Prompt classification logic
- `src/mcg_agent/classification/models.py` - Classification result models

### 3.2 Multi-Corpus Blending Rules
**Purpose**: Implement corpus weighting and blending per routing-matrix.md
**Documentation Reference**: routing-matrix.md lines 460-506

**Corpus Access Rules** (EXACT from agents.md lines 244-248):
- **Ideator**: May call all three corpora; RAG allowed for Social/Published only if coverage gaps
- **Drafter**: May use Personal + Social for tone anchoring; NO RAG access
- **Critic**: Full access to all corpora; always permitted to invoke RAG  
- **Revisor**: NO new queries; works with provided snippets only
- **Summarizer**: NO queries of any kind

**Blending Rules** (exact from routing-matrix.md):
- **Ideator**: Queries all three corpora by default
- **Drafter**: Works with Ideator's context, may request additional Personal/Social  
- **Critic**: Always allowed to re-query, may trigger RAG fallback
- **Revisor**: No new corpus queries, uses inherited snippets
- **Summarizer**: No corpus queries, compression only

**Corpus Weighting** (exact from documentation):
- **Personal**: Highest priority for conversational tone
- **Social**: Supplements tone with cadence and colloquial phrasing
- **Published**: Provides factual grounding and authority

### 3.3 Revise Call Template Implementation  
**Purpose**: Implement exact revise call template from routing-matrix.md
**Documentation Reference**: routing-matrix.md lines 126-148

**Template Implementation** (exact from documentation):
```python
REVISE_CALL_TEMPLATE = """System: You are the Ideator. Produce an outline only. No prose.  
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
Output: bullet outline, 5–7 bullets, 1 short headline."""
```

## 📋 Phase 4: Metadata Schema Compliance (Priority: HIGH)

### 4.1 Complete Metadata Bundle Implementation
**Purpose**: Implement exact metadata schema from governance.md with full field validation
**Documentation Reference**: governance.md lines 124-188

**Complete Metadata Schema** (EXACT from governance.md lines 129-173):
```python  
class InputSource(BaseModel):
    corpus: Literal["Personal", "Social", "Published"]
    snippet_id: str
    source_text: str
    timestamp: str  # ISO-8601 format

class Attribution(BaseModel):
    claim_id: str
    source: str
    timestamp: str  # ISO-8601 format

class ToneFlags(BaseModel):
    voice_match_score: float
    seo_keywords: List[str]
    safety_flags: List[str]

class ChangeLog(BaseModel):
    change_id: str
    original_text: str
    revised_text: str
    reason: str
    applied_by: Literal["Critic", "Revisor"]

class TokenStats(BaseModel):
    input_tokens: int
    output_tokens: int

class MetadataBundle(BaseModel):
    task_id: str                    # unique ID for this user request
    role: str                       # which agent produced this output
    input_sources: List[InputSource] # corpora and retrieval details
    attribution: List[Attribution]   # citations tied to claims
    tone_flags: ToneFlags           # tone/style governance checks
    change_log: List[ChangeLog]     # applied by Critic/Revisor
    long_tail_keywords: List[str]   # extracted by Summarizer
    token_stats: TokenStats         # tracking usage
    trimmed_sections: List[str]     # Summarizer log
    final_output: str               # text as delivered to user
```

**Metadata Persistence Requirements** (governance.md lines 177-183):
- `task_id` stays constant across the whole volley
- `input_sources` and `attribution` ensure provenance is never lost
- `change_log` is the Critic/Revisor record of what was modified and why
- `long_tail_keywords` are always logged, but only surfaced in writing mode
- `trimmed_sections` documents what the Summarizer removed

### 4.2 Attribution Persistence
**Purpose**: Ensure attribution persists through entire pipeline
**Documentation Reference**: governance.md lines 115-121, context-assembly.md lines 26-35

**Requirements**:
- Every snippet must include source type, timestamp, author
- Attribution must persist through every pipeline stage
- Claims from corpus/RAG must include source and timestamp metadata
- Fallback connectors must be logged when corpus fails

## 📋 Phase 5: Testing Strategy (Priority: MEDIUM)

### 5.1 Governance Compliance Tests
**Purpose**: Validate every governance rule is enforced

**Test Categories**:
- API call limit enforcement per agent
- MVLM preference in Revisor/Summarizer
- Failure pattern handling (minor/major/critical)
- Attribution persistence through pipeline
- Scoring threshold validation
- Agent role responsibility compliance

### 5.2 Integration Tests
**Purpose**: Validate complete pipeline flow

**Test Scenarios**:
- Full pipeline execution with all agent handoffs
- Multi-corpus retrieval and context assembly
- Voice fingerprinting and tone scoring
- Metadata bundle completeness
- Error handling and recovery

## 📋 Phase 6: Production Deployment & Monitoring (Priority: HIGH)

### 6.1 Security Constraints Enforcement
**Purpose**: Implement mandatory security requirements from agents.md
**Documentation Reference**: agents.md lines 419-425, 182-187

**Security Requirements** (exact from documentation):
- API keys in environment variables only
- No raw SQL - ORM or parameterized queries only  
- No bypassing governance checks
- Attribution and logging are mandatory
- No hardcoding - configurations from .env or settings.py

**Files to Create**:
- `src/mcg_agent/security/validator.py` - Security constraint validation
- `src/mcg_agent/security/sql_guard.py` - SQL injection prevention
- `src/mcg_agent/security/env_manager.py` - Environment variable management

**Implementation Requirements**:
```python
class SecurityValidator:
    def validate_sql_query(self, query: str) -> bool:
        # Ensure only parameterized queries, no raw SQL
        if "DROP" in query.upper() or "DELETE" in query.upper():
            raise SecurityValidationError("Raw SQL operations not permitted")
        return True
        
    def validate_api_key_usage(self, key_source: str) -> bool:
        # Ensure API keys only from environment variables
        if key_source != "environment":
            raise SecurityValidationError("API keys must come from environment variables")
        return True
```

### 6.2 Production Server Configuration  
**Purpose**: Implement production-ready server setup per agents.md
**Documentation Reference**: agents.md lines 102-110, 342-350

**Production Requirements**:
- Gunicorn ASGI server with multiple workers
- Health checks for Kubernetes (live/ready probes)
- Monitoring endpoints with metrics
- Error handling with proper HTTP status codes
- Request logging and security headers middleware

**Files to Create**:
- `scripts/start-prod.sh` - Production server startup script
- `src/mcg_agent/middleware/security.py` - Security headers middleware
- `src/mcg_agent/middleware/monitoring.py` - Request monitoring middleware
- `gunicorn.conf.py` - Gunicorn configuration

**Production Startup Script** (per agents.md):
```bash
#!/bin/bash
# Production server startup
gunicorn src.mcg_agent.api.app:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

### 6.3 Health Check Implementation
**Purpose**: Implement comprehensive health monitoring per agents.md  
**Documentation Reference**: agents.md lines 368-380, 457-463

**Health Check Endpoints** (exact from documentation):
- `GET /health` - Comprehensive system health check
- `GET /health/live` - Kubernetes liveness probe  
- `GET /health/ready` - Kubernetes readiness probe
- `GET /monitoring/metrics` - System performance metrics
- `GET /monitoring/violations` - Governance violation tracking

**Implementation Requirements**:
```python
@router.get("/health/live")
async def liveness_probe():
    """Kubernetes liveness probe - basic service availability"""
    return {"status": "alive", "timestamp": datetime.utcnow()}

@router.get("/health/ready")  
async def readiness_probe():
    """Kubernetes readiness probe - service ready for traffic"""
    # Check database, Redis, corpus connections
    checks = await perform_readiness_checks()
    if all(checks.values()):
        return {"status": "ready", "checks": checks}
    raise HTTPException(status_code=503, detail="Service not ready")
```

### 6.4 Governance Violation Tracking
**Purpose**: Implement mandatory governance violation monitoring
**Documentation Reference**: agents.md lines 462-463, governance.md lines 220-230

**Violation Tracking Requirements**:
- Log all governance check failures
- Track API call limit violations
- Monitor attribution compliance
- Record security constraint violations
- Generate violation reports for monitoring

**Files to Create**:
- `src/mcg_agent/monitoring/violations.py` - Violation tracking system
- `src/mcg_agent/monitoring/reports.py` - Violation reporting

### 6.5 Authentication & Authorization Security
**Purpose**: Implement JWT security with Redis session management
**Documentation Reference**: agents.md lines 441-470

**Security Implementation Requirements**:
- JWT tokens with secure secret keys
- Redis session management and token revocation
- Request validation using Pydantic models  
- Governance enforcement at API layer
- Comprehensive audit logging

**Security Middleware Requirements**:
```python
class SecurityMiddleware:
    async def __call__(self, request: Request, call_next):
        # Add security headers
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY" 
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response
```

### 6.6 Database Security & ORM Compliance
**Purpose**: Enforce no raw SQL constraint from agents.md
**Documentation Reference**: agents.md line 184, personal-search.md lines 86-88

**Database Security Requirements**:
- SQLAlchemy ORM for all database operations
- Parameterized queries only - no raw SQL
- SQL injection prevention validation
- Database connection security
- Query logging for audit trails

**SQL Guard Implementation**:
```python  
class SQLGuard:
    FORBIDDEN_KEYWORDS = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE"]
    
    def validate_query(self, query_text: str) -> bool:
        upper_query = query_text.upper()
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in upper_query:
                raise SecurityValidationError(f"Raw SQL keyword '{keyword}' not permitted")
        return True
```

## 📋 Phase 7: Code Quality & Testing (Priority: HIGH)

### 7.1 Code Quality Standards
**Purpose**: Implement mandatory code quality per agents.md
**Documentation Reference**: agents.md lines 382-396, 171-178

**Quality Requirements** (exact from documentation):
- Black code formatting: `black src/ tests/`
- Import sorting: `isort src/ tests/`  
- Linting: `flake8 src/ tests/`
- Type checking: `mypy src/`
- Pydantic BaseModel for all type safety

**Quality Scripts** (per agents.md):
```bash
# Format code
black src/ tests/

# Sort imports  
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### 7.2 Comprehensive Testing Strategy
**Purpose**: Implement testing suite per agents.md requirements
**Documentation Reference**: agents.md lines 354-366

**Test Categories** (exact from documentation):
- Unit tests: `./scripts/run-tests.sh --unit`
- Integration tests: `./scripts/run-tests.sh --integration`
- API tests: `./scripts/run-tests.sh --api`  
- Fast mode: `./scripts/run-tests.sh --fast`
- Coverage: `pytest tests/ -v --cov=src/mcg_agent`

### 7.3 Environment Configuration Security
**Purpose**: Implement secure environment management per agents.md
**Documentation Reference**: agents.md lines 288-312

**Environment Variables** (exact from documentation):
```bash
# Database Configuration
DATABASE_URL=sqlite:///./mcg_agent.db

# Redis Configuration (session management)
REDIS_URL=redis://localhost:6379/0

# Security Keys (generate secure values!)
JWT_SECRET_KEY=your-jwt-secret-key-here
ENCRYPTION_KEY=your-32-byte-encryption-key

# API Keys
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# Server Configuration
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

## 📋 Phase 8: Deployment Configuration (Priority: MEDIUM)

### 8.1 Configuration Management
**Purpose**: Implement configurable thresholds and settings

**Configuration Files**:
- Scoring thresholds (T1, T2 values)
- API call limits per agent
- MVLM fallback permissions  
- Corpus access rules
- Voice fingerprint parameters

### 8.2 Monitoring and Metrics
**Purpose**: Track compliance and performance

**Metrics to Track**:
- API calls per agent per task
- MVLM vs API usage ratios
- Failure pattern frequencies
- Attribution completion rates
- Pipeline success/failure rates
- Security violation rates
- Authentication/authorization failures

## ⚠️ CRITICAL SUCCESS CRITERIA

### Implementation Validation Checklist:

**PydanticAI Framework Compliance:**
- [ ] PydanticAI implemented as PRIMARY agent orchestration framework
- [ ] All agents built using PydanticAI agent classes with correct naming (IdeatorAgent, DrafterAgent, etc.)
- [ ] Corpus access implemented through PydanticAI tools with @SecureAgentTool.governance_tool decorator
- [ ] Runtime governance enforcement cannot be bypassed via RunContext validation
- [ ] Agent permissions enforced by PydanticAI framework with tool-level validation

**Core Architecture Compliance:**
- [ ] API call limits enforced exactly per routing-matrix.md
- [ ] MVLM interface implemented with proper fallback logic
- [ ] All three corpus search modules implemented per documentation
- [ ] Context assembly with voice fingerprinting working
- [ ] Minor/Major/Critical failure patterns implemented  
- [ ] Agent responsibilities differentiated per governance.md
- [ ] Complete metadata schema implemented with all fields (input_sources, attribution, tone_flags, change_log, token_stats, trimmed_sections)
- [ ] Attribution persists through entire pipeline
- [ ] Scoring thresholds configurable and enforced
- [ ] Revise call template matches documentation exactly

**Security Suite Compliance (docs/security/):**
- [ ] Zero Trust Architecture implemented per docs/security/architecture/security-architecture.md
- [ ] Governance protocol enforced per docs/security/protocols/governance-protocol.md  
- [ ] PydanticAI governance tool pattern implemented (@SecureAgentTool.governance_tool)
- [ ] GovernedAgentPipeline with sequential processing and 5-minute timeouts
- [ ] API call tracking system (CallTracker.get_call_count, SecurityLogger.log_governance_violation)
- [ ] Violation classification and response (Critical/High/Medium with automated containment)
- [ ] Deployment security checklist completed per docs/security/compliance/deployment-security.md
- [ ] WAF integration operational
- [ ] TLS 1.3 configured for all connections
- [ ] Database encryption at rest and in transit
- [ ] Redis TLS + AUTH configured
- [ ] Immutable audit trail implemented
- [ ] Governance violation monitoring active
- [ ] Pre-deployment security validation checklist completed

**Existing Infrastructure Integration:**
- [ ] CLI tool implemented (mcg-agent serve --reload, mcg-agent serve --workers 4)
- [ ] Requirements.txt and setup.py integration working (pip install -e .[dev])
- [ ] All existing scripts in /scripts/ validated and integrated
- [ ] Health check format support (--format json, --format prometheus)
- [ ] Environment variables complete (ANTHROPIC_API_KEY, ENCRYPTION_KEY, ENVIRONMENT, DEBUG, LOG_LEVEL)
- [ ] setup.sh works with new PydanticAI architecture  
- [ ] Production scripts (start-prod.sh) security validated
- [ ] Test scripts cover governance protocol compliance

**Production Security Requirements:**
- [ ] No raw SQL - ORM/parameterized queries only
- [ ] API keys from environment variables only
- [ ] Governance checks cannot be bypassed via any method
- [ ] Attribution and logging mandatory and enforced
- [ ] JWT authentication with Redis session management
- [ ] Security headers middleware implemented
- [ ] SQL injection prevention active
- [ ] Production server configuration ready (Gunicorn + workers)

**Code Quality Standards:**  
- [ ] Black formatting enforced
- [ ] Import sorting (isort) enforced
- [ ] Linting (flake8) passes
- [ ] Type checking (mypy) passes  
- [ ] Comprehensive test suite covering all governance rules
- [ ] Environment configuration secured
- [ ] Complete docs/security/ documentation compliance verified

### Implementation Order:
1. **Phase 1**: PydanticAI foundation + Zero Trust security (PydanticAI agents, security architecture, existing scripts integration, MVLM, corpus search, context assembly)
2. **Phase 2**: Governance protocol enforcement (API limits, failure patterns, runtime governance validation per docs/security/)  
3. **Phase 3**: Agent role compliance (exact corpus access rules, routing matrix compliance, classification, templates)
4. **Phase 4**: Metadata schema compliance (complete bundle, attribution, audit trail)
5. **Phase 5**: Security validation (deployment security checklist compliance, governance protocol testing)
6. **Phase 6**: Production deployment & monitoring (health checks, metrics, existing production scripts)
7. **Phase 7**: Code quality & testing (formatting, linting, comprehensive test suite)
8. **Phase 8**: Pre-deployment security validation & future work preparation (mandatory validation checklist, extensibility preparation)

## 🚨 FINAL WARNING

This implementation plan MUST be followed exactly. Every API call limit, every failure pattern, every governance rule, every data structure specified in the documentation must be implemented precisely as documented. No creative interpretations, no shortcuts, no "improvements" that deviate from the specifications.

**CRITICAL**: This implementation MUST comply with the comprehensive security documentation suite under `docs/security/` that was created in this session. The Zero Trust Architecture, governance protocol enforcement, and deployment security requirements are MANDATORY.

**PydanticAI REQUIREMENT**: PydanticAI is the PRIMARY framework - not FastAPI, not custom classes. All agents MUST use PydanticAI as the core orchestration system with governance rules enforced at runtime.

**EXISTING INFRASTRUCTURE**: DO NOT recreate the scripts in `/scripts/` - they already exist and are production-ready. Integrate with them, don't replace them.

The documentation is the law. The security suite is mandatory. Follow it to the letter.