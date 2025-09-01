# Multi-Corpus Governance Agent - Implementation Plan

## 🎯 Overview

This implementation plan details how to build the Multi-Corpus Governance Agent using **PydanticAI** as the core orchestration framework. The system will implement a five-agent pipeline with strict governance rules, multi-corpus retrieval, and comprehensive security from day one.

## 📋 Phase One: Core Backend Implementation

### 1. Foundation Layer (Week 1-2)

#### 1.1 Project Structure Setup
```
src/mcg_agent/
├── __init__.py
├── main.py                 # FastAPI entrypoint
├── config.py              # ✅ Already implemented
├── agents/
│   ├── __init__.py
│   ├── base.py            # Base PydanticAI agent class
│   ├── ideator.py         # Ideator agent
│   ├── drafter.py         # Drafter agent
│   ├── critic.py          # Critic agent
│   ├── revisor.py         # Revisor agent
│   └── summarizer.py      # Summarizer agent
├── governance/
│   ├── __init__.py
│   ├── rules.py           # Governance rule engine
│   ├── scoring.py         # Tone/coverage scoring
│   ├── validators.py      # Input/output validation
│   └── metadata.py        # Metadata schema
├── search/
│   ├── __init__.py
│   ├── base.py            # Base corpus connector
│   ├── personal.py        # Personal corpus connector
│   ├── social.py          # Social corpus connector
│   ├── published.py       # Published corpus connector
│   └── rag.py             # RAG/external search
├── context/
│   ├── __init__.py
│   ├── assembly.py        # Context pack builder
│   ├── fingerprint.py     # Voice fingerprinting
│   └── attribution.py     # Attribution tracking
├── database/
│   ├── __init__.py
│   ├── models.py          # SQLAlchemy models
│   ├── migrations/        # Alembic migrations
│   └── session.py         # DB session management
├── api/
│   ├── __init__.py
│   ├── routes.py          # FastAPI routes
│   ├── schemas.py         # Pydantic request/response models
│   └── auth.py            # JWT authentication
├── storage/
│   ├── __init__.py
│   ├── redis_client.py    # Redis session management
│   └── cache.py           # Caching layer
└── utils/
    ├── __init__.py
    ├── logging.py         # Structured logging
    ├── security.py        # Security utilities
    └── exceptions.py      # Custom exceptions
```

#### 1.2 Database Schema Design
**Tables for Multi-Corpus Storage:**

```sql
-- Personal Corpus
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    thread_id UUID NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    source VARCHAR(50) NOT NULL,
    channel VARCHAR(100),
    meta JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE threads (
    thread_id UUID PRIMARY KEY,
    title VARCHAR(500),
    participants TEXT[],
    tags TEXT[],
    started_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Social Corpus
CREATE TABLE social_posts (
    id UUID PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    post_id VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    author VARCHAR(200),
    timestamp TIMESTAMPTZ NOT NULL,
    engagement_metrics JSONB,
    hashtags TEXT[],
    meta JSONB,
    UNIQUE(platform, post_id)
);

-- Published Corpus
CREATE TABLE published_content (
    id UUID PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    url VARCHAR(1000),
    author VARCHAR(200),
    published_at TIMESTAMPTZ NOT NULL,
    content_type VARCHAR(50), -- article, blog, research
    seo_keywords TEXT[],
    meta JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Voice Fingerprints
CREATE TABLE voice_fingerprints (
    id UUID PRIMARY KEY,
    corpus_type VARCHAR(20) NOT NULL, -- personal, social, published
    collocations JSONB NOT NULL,
    cadence_markers JSONB NOT NULL,
    frequency_counts JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Task Execution Logs
CREATE TABLE task_logs (
    id UUID PRIMARY KEY,
    task_id UUID NOT NULL,
    agent_role VARCHAR(20) NOT NULL,
    input_data JSONB NOT NULL,
    output_data JSONB NOT NULL,
    metadata JSONB NOT NULL,
    execution_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2. PydanticAI Agent Architecture (Week 2-3)

#### 2.1 Base Agent Design
```python
# src/mcg_agent/agents/base.py
from pydantic_ai import Agent
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

class AgentInput(BaseModel):
    task_id: str
    content: str
    metadata: Dict[str, Any]
    context_pack: Optional[Dict[str, Any]] = None

class AgentOutput(BaseModel):
    agent_role: str
    task_id: str
    content: str
    metadata: Dict[str, Any]
    attribution: List[Dict[str, Any]]
    scores: Dict[str, float]

class BaseGovernanceAgent(ABC):
    def __init__(self, agent_name: str, model: str = "gpt-4"):
        self.agent = Agent(model=model, deps_type=AgentInput)
        self.agent_name = agent_name
        self.max_api_calls = self.get_max_api_calls()
        self.api_call_count = 0
    
    @abstractmethod
    def get_max_api_calls(self) -> int:
        pass
    
    @abstractmethod
    async def process(self, input_data: AgentInput) -> AgentOutput:
        pass
    
    async def validate_governance_rules(self, input_data: AgentInput) -> bool:
        # Implement governance validation
        pass
```

#### 2.2 Individual Agent Implementation Strategy

**Ideator Agent (Max 2 API calls)**
- Tool: Multi-corpus query access
- Responsibility: Build outlines with tone/coverage scoring
- Governance: Local tweaks vs revise call decision logic

**Drafter Agent (Max 1 API call)**
- Tool: Limited corpus access for voice anchoring
- Responsibility: Expand outline to full draft with SEO
- Governance: Single API call constraint

**Critic Agent (Max 2 API calls + RAG)**
- Tool: Full corpus access + RAG capabilities
- Responsibility: Truth validation, voice checking, safety
- Governance: Critical fail detection and stopping

**Revisor Agent (MVLM preferred, 1 API fallback)**
- Tool: MVLM + limited corpus for tone
- Responsibility: Apply Critic corrections deterministically
- Governance: No new content creation

**Summarizer Agent (MVLM only, API fallback optional)**
- Tool: MVLM for compression
- Responsibility: Package output + extract keywords
- Governance: No new vocabulary introduction

### 3. Context Assembly System (Week 3-4)

#### 3.1 Voice Fingerprinting Engine
```python
# src/mcg_agent/context/fingerprint.py
class VoiceFingerprint:
    def __init__(self, corpus_type: str):
        self.corpus_type = corpus_type
        self.collocations: Dict[str, int] = {}
        self.cadence_markers: Dict[str, float] = {}
    
    def build_fingerprint(self, texts: List[str]) -> None:
        # Extract n-grams, sentence patterns, vocabulary preferences
        pass
    
    def calculate_tone_score(self, text: str) -> float:
        # Compare text against fingerprint patterns
        pass
```

#### 3.2 Context Pack Builder
```python
# src/mcg_agent/context/assembly.py
class ContextPack(BaseModel):
    task_id: str
    snippets: List[Dict[str, Any]]
    attribution: List[Dict[str, Any]]
    voice_samples: Dict[str, List[str]]
    coverage_score: float
    tone_score: float
    diversity_check: bool

class ContextAssembly:
    async def build_context_pack(
        self, 
        user_prompt: str, 
        classification: str
    ) -> ContextPack:
        # Query all corpora
        # Apply selection rules
        # Build attribution
        # Calculate scores
        pass
```

### 4. Governance Rule Engine (Week 4-5)

#### 4.1 Rule Validation System
```python
# src/mcg_agent/governance/rules.py
class GovernanceRules:
    @staticmethod
    def validate_api_call_limit(agent_name: str, call_count: int) -> bool:
        limits = {
            "ideator": 2,
            "drafter": 1, 
            "critic": 2,
            "revisor": 1,  # fallback only
            "summarizer": 0  # MVLM preferred
        }
        return call_count <= limits.get(agent_name, 0)
    
    @staticmethod
    def validate_rag_access(agent_name: str) -> bool:
        return agent_name == "critic"
    
    @staticmethod
    def validate_corpus_access(agent_name: str, corpus: str) -> bool:
        # Define corpus access rules per agent
        pass
```

### 5. Security & Authentication Layer (Week 5-6)

#### 5.1 Redis Session Management
```python
# src/mcg_agent/storage/redis_client.py
class SecureRedisClient:
    def __init__(self):
        self.client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD.get_secret_value(),
            ssl=True,
            ssl_cert_reqs=ssl.CERT_REQUIRED
        )
    
    async def store_session_state(self, task_id: str, state: Dict) -> None:
        # Store ephemeral task state with TTL
        pass
    
    async def get_session_state(self, task_id: str) -> Optional[Dict]:
        # Retrieve task state
        pass
```

#### 5.2 JWT Authentication
```python
# src/mcg_agent/api/auth.py
class JWTAuth:
    @staticmethod
    def create_access_token(user_data: Dict) -> str:
        # Generate JWT with expiration
        pass
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict]:
        # Validate and decode JWT
        pass
```

## 📊 Implementation Timeline

### Week 1-2: Foundation
- [ ] Set up complete directory structure
- [ ] Implement database models and migrations
- [ ] Create base PydanticAI agent classes
- [ ] Set up Redis client with security

### Week 3-4: Core Agents
- [ ] Implement all five PydanticAI agents
- [ ] Build context assembly system
- [ ] Implement voice fingerprinting
- [ ] Create governance rule engine

### Week 5-6: Integration & Security
- [ ] Build FastAPI routes and authentication
- [ ] Implement comprehensive logging
- [ ] Add input/output validation
- [ ] Create error handling and recovery

### Week 7-8: Testing & Deployment Prep
- [ ] Unit tests for all components
- [ ] Integration tests for agent pipeline
- [ ] Performance testing and optimization
- [ ] Security audit and hardening

## 🔧 Key PydanticAI Implementation Details

### Agent Dependency Injection
```python
from pydantic_ai import Agent, RunContext

# Each agent will receive typed dependencies
@agent.system_prompt
def system_prompt(ctx: RunContext[AgentInput]) -> str:
    return f"You are the {ctx.deps.agent_role}. Follow governance rules strictly."

@agent.tool
async def query_corpus(ctx: RunContext[AgentInput], corpus: str, query: str) -> str:
    # Validate governance rules before corpus access
    if not GovernanceRules.validate_corpus_access(ctx.deps.agent_role, corpus):
        raise PermissionError(f"{ctx.deps.agent_role} cannot access {corpus}")
    
    # Perform corpus query with attribution
    return await corpus_connector.search(query)
```

### Multi-Agent Orchestration
```python
# src/mcg_agent/main.py
class MultiCorpusGovernanceSystem:
    def __init__(self):
        self.agents = {
            'ideator': IdeatorAgent(),
            'drafter': DrafterAgent(), 
            'critic': CriticAgent(),
            'revisor': RevisorAgent(),
            'summarizer': SummarizerAgent()
        }
    
    async def process_request(self, user_prompt: str) -> Dict[str, Any]:
        task_id = str(uuid4())
        
        # 1. Classification and context assembly
        context_pack = await self.context_assembly.build_context_pack(
            user_prompt, 
            classification
        )
        
        # 2. Sequential agent processing with governance
        result = context_pack
        for agent_name in ['ideator', 'drafter', 'critic', 'revisor', 'summarizer']:
            agent = self.agents[agent_name]
            result = await agent.process(result)
            
            # Log each step with attribution
            await self.log_agent_execution(task_id, agent_name, result)
            
            # Check for critical failures
            if result.metadata.get('critical_fail'):
                return self.handle_critical_failure(task_id, result)
        
        return result
```

## 🛡️ Security Implementation Priorities

1. **Input Validation**: All agent inputs validated via Pydantic schemas
2. **API Rate Limiting**: Enforce governance rules at runtime
3. **Attribution Tracking**: Mandatory source tracking through pipeline
4. **Session Security**: Redis with TLS, AUTH, and limited ACLs
5. **Audit Logging**: Complete execution trail for all decisions

## 🚀 Success Metrics

- [ ] All five agents implemented with PydanticAI
- [ ] Multi-corpus retrieval with attribution
- [ ] Voice fingerprinting and tone scoring
- [ ] Governance rules enforced at runtime
- [ ] Comprehensive test coverage (>80%)
- [ ] API security hardened (JWT + validation)
- [ ] Performance: <5s response time for chat mode

This implementation plan provides a clear roadmap for building a production-ready Multi-Corpus Governance Agent system using PydanticAI as the core orchestration framework.