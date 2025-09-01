# Governance Protocol Specification

**Document Version**: 1.0  
**Last Updated**: 2024-09-01  
**Status**: APPROVED  
**Classification**: INTERNAL USE  

---

## 🎯 Purpose and Scope

This document specifies the formal governance protocols that enforce security, access control, and behavioral constraints throughout the Multi-Corpus Governance Agent system. These protocols are implemented as **runtime-enforced rules** within the PydanticAI agent framework and cannot be bypassed through any normal system operation.

### Governance Objectives
1. **Ensure Agent Compliance**: Every agent operates within strict behavioral boundaries
2. **Enforce Access Control**: Corpus and tool access strictly controlled by role
3. **Prevent Security Violations**: No agent can exceed its defined capabilities  
4. **Maintain Audit Trail**: Every action logged with complete attribution
5. **Enable Safe Scaling**: Rules scale consistently across all system components

---

## 🤖 Agent Governance Matrix

### Agent Roles and Constraints

| Agent | Max API Calls | Corpus Access | RAG Access | MVLM Access | Primary Responsibility |
|-------|---------------|---------------|------------|-------------|----------------------|
| **Ideator** | 2 | Personal, Social, Published | ❌ | ✅ | Outline generation + scoring |
| **Drafter** | 1 | Social (limited), Published (limited) | ❌ | ✅ | Draft expansion + tone anchoring |
| **Critic** | 2 | Personal, Social, Published | ✅ | ✅ | Truth validation + safety checks |
| **Revisor** | 1 (fallback) | Inherited context only | ❌ | ✅ Primary | Apply corrections deterministically |
| **Summarizer** | 0 (fallback) | No new queries | ❌ | ✅ Only | Compression + keyword extraction |

---

## 🔐 Access Control Protocols

### 1. Corpus Access Governance

#### Personal Corpus Access Rules
```yaml
Personal_Corpus_Access:
  Authorized_Agents: [Ideator, Critic]
  Access_Type: READ_ONLY
  Validation_Required: true
  Logging_Level: DETAILED
  
  Restrictions:
    - No raw message content export
    - Must include attribution metadata
    - Query rate limited to 10/minute per agent
    - Personal data anonymization required for non-Critic agents
```

#### Social Corpus Access Rules  
```yaml
Social_Corpus_Access:
  Authorized_Agents: [Ideator, Drafter, Critic]
  Access_Type: READ_ONLY
  Validation_Required: true
  Logging_Level: STANDARD
  
  Agent_Specific_Rules:
    Drafter:
      - Limited to voice samples only
      - Max 5 snippets per request
      - No engagement metrics access
    Ideator:
      - Full metadata access allowed
      - Hashtag and trend analysis permitted
    Critic:
      - Complete access for fact-checking
      - External correlation allowed
```

#### Published Corpus Access Rules
```yaml
Published_Corpus_Access:
  Authorized_Agents: [Ideator, Drafter, Critic]
  Access_Type: READ_ONLY
  Validation_Required: true
  Logging_Level: STANDARD
  
  Content_Restrictions:
    - Must preserve original attribution
    - Cannot modify SEO metadata
    - Research citations must be validated
    - Copyright compliance mandatory
```

### 2. RAG Access Governance

#### External RAG Protocol (Critic Only)
```yaml
RAG_Access_Protocol:
  Authorized_Agent: [Critic]
  Max_Queries_Per_Task: 3
  Timeout: 30 seconds
  
  Validation_Requirements:
    - Query must relate to claims in current draft
    - External sources must be from whitelist
    - Results must include source attribution
    - No personal data queries to external systems
  
  Prohibited_Actions:
    - Queries containing PII
    - Requests to non-whitelisted domains
    - Bulk data extraction
    - Automated scraping beyond single queries
```

### 3. API Call Governance

#### Call Limit Enforcement
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

---

## 📋 PydanticAI Implementation Protocols

### 1. Agent Tool Governance

#### Secure Tool Implementation Pattern
```python
from pydantic_ai import Agent, RunContext
from mcg_agent.governance.rules import GovernanceRules
from mcg_agent.utils.exceptions import GovernanceViolationError

class SecureAgentTool:
    """Base class for all governance-enforced agent tools"""
    
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

# Example Usage in Agent Implementation
@agent.tool
@SecureAgentTool.governance_tool(
    required_permissions=['corpus_query'],
    corpus_access=['social', 'published'],
    max_calls_per_task=1
)
async def drafter_query_corpus(
    ctx: RunContext[AgentInput], 
    corpus: str, 
    query: str
) -> str:
    """Drafter-specific corpus query with governance enforcement"""
    return await CorpusConnector.query(corpus, query)
```

### 2. Agent Pipeline Governance

#### Sequential Processing with Governance
```python
class GovernedAgentPipeline:
    """Orchestrates the five-agent pipeline with strict governance"""
    
    async def process_request(self, user_prompt: str) -> AgentOutput:
        task_id = str(uuid4())
        pipeline_state = PipelineState(task_id=task_id)
        
        # Initialize governance context
        governance_context = GovernanceContext(
            task_id=task_id,
            user_prompt=user_prompt,
            classification=await self.classify_prompt(user_prompt)
        )
        
        try:
            # Stage 1: Ideator (max 2 API calls)
            ideator_input = AgentInput(
                task_id=task_id,
                agent_role="ideator",
                content=user_prompt,
                context_pack=await self.assemble_context(user_prompt)
            )
            ideator_result = await self.execute_agent_stage(
                agent=self.ideator_agent,
                input_data=ideator_input,
                governance_context=governance_context
            )
            
            # Stage 2: Drafter (max 1 API call)
            drafter_input = AgentInput(
                task_id=task_id,
                agent_role="drafter", 
                content=ideator_result.content,
                context_pack=ideator_result.context_pack
            )
            drafter_result = await self.execute_agent_stage(
                agent=self.drafter_agent,
                input_data=drafter_input,
                governance_context=governance_context
            )
            
            # Stage 3: Critic (max 2 API calls + RAG)
            critic_input = AgentInput(
                task_id=task_id,
                agent_role="critic",
                content=drafter_result.content,
                metadata=drafter_result.metadata
            )
            critic_result = await self.execute_agent_stage(
                agent=self.critic_agent,
                input_data=critic_input,
                governance_context=governance_context
            )
            
            # Check for critical failures
            if critic_result.metadata.get('critical_failure'):
                return await self.handle_critical_failure(
                    task_id, critic_result
                )
            
            # Stage 4: Revisor (MVLM preferred, API fallback)
            revisor_input = AgentInput(
                task_id=task_id,
                agent_role="revisor",
                content=drafter_result.content,
                metadata=critic_result.metadata
            )
            revisor_result = await self.execute_agent_stage(
                agent=self.revisor_agent,
                input_data=revisor_input,
                governance_context=governance_context
            )
            
            # Stage 5: Summarizer (MVLM only)
            summarizer_input = AgentInput(
                task_id=task_id,
                agent_role="summarizer",
                content=revisor_result.content,
                metadata=revisor_result.metadata
            )
            final_result = await self.execute_agent_stage(
                agent=self.summarizer_agent,
                input_data=summarizer_input,
                governance_context=governance_context
            )
            
            return final_result
            
        except GovernanceViolationError as e:
            await self.handle_governance_violation(task_id, e)
            raise
        except Exception as e:
            await self.handle_pipeline_error(task_id, e)
            raise
    
    async def execute_agent_stage(
        self, 
        agent: Agent, 
        input_data: AgentInput,
        governance_context: GovernanceContext
    ) -> AgentOutput:
        """Execute single agent stage with full governance validation"""
        
        # Pre-execution governance check
        await GovernanceValidator.validate_stage_execution(
            agent_role=input_data.agent_role,
            governance_context=governance_context
        )
        
        # Execute agent with timeout
        start_time = time.time()
        result = await asyncio.wait_for(
            agent.run(input_data),
            timeout=300  # 5 minute timeout per agent
        )
        execution_time = time.time() - start_time
        
        # Post-execution validation
        await GovernanceValidator.validate_stage_output(
            agent_role=input_data.agent_role,
            output=result,
            governance_context=governance_context
        )
        
        # Log stage completion
        await AuditLogger.log_stage_completion(
            task_id=input_data.task_id,
            agent_role=input_data.agent_role,
            execution_time=execution_time,
            input_tokens=result.metadata.get('input_tokens', 0),
            output_tokens=result.metadata.get('output_tokens', 0)
        )
        
        return result
```

---

## 🚨 Violation Response Protocols

### 1. Governance Violation Classification

#### Severity Levels
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

### 2. Automated Response Actions

#### Violation Response Pipeline
```python
class GovernanceViolationHandler:
    
    async def handle_violation(
        self, 
        violation: GovernanceViolationError,
        context: Dict[str, Any]
    ) -> ViolationResponse:
        
        # 1. Classify violation severity
        severity = self.classify_violation_severity(violation)
        
        # 2. Immediate containment actions
        await self.execute_containment_actions(severity, context)
        
        # 3. Log violation with full context
        await SecurityLogger.log_governance_violation(
            violation_type=violation.__class__.__name__,
            severity=severity,
            agent_context=context,
            timestamp=datetime.utcnow(),
            remediation_actions=[]
        )
        
        # 4. Alert security team if critical
        if severity == ViolationSeverity.CRITICAL:
            await SecurityAlerter.send_critical_alert(violation, context)
        
        # 5. Return appropriate response
        return ViolationResponse(
            severity=severity,
            message=violation.message,
            remediation_required=severity >= ViolationSeverity.HIGH
        )
    
    async def execute_containment_actions(
        self, 
        severity: ViolationSeverity, 
        context: Dict[str, Any]
    ) -> None:
        """Execute immediate containment based on violation severity"""
        
        if severity == ViolationSeverity.CRITICAL:
            # Immediate pipeline termination
            await PipelineController.terminate_task(context['task_id'])
            
            # Revoke session tokens if auth-related
            if 'user_id' in context:
                await AuthManager.revoke_user_tokens(context['user_id'])
        
        elif severity == ViolationSeverity.HIGH:
            # Graceful request rejection
            await PipelineController.reject_request(
                context['task_id'], 
                reason="Governance violation detected"
            )
        
        # Always increment violation counter
        await ViolationTracker.increment_violation_count(
            context.get('user_id', 'anonymous'),
            severity
        )
```

---

## ✅ Governance Validation Checklist

### Pre-Deployment Validation
- [ ] All agent API call limits enforced and tested
- [ ] Corpus access permissions validated for each agent role  
- [ ] RAG access restricted to Critic agent only
- [ ] MVLM fallback logic working correctly for Revisor/Summarizer
- [ ] Governance violation detection and response tested
- [ ] Audit logging capturing all required governance events
- [ ] Security alerts configured for critical violations
- [ ] Pipeline termination working for critical failures

### Runtime Monitoring Requirements
- [ ] Real-time governance rule compliance monitoring
- [ ] API call limit tracking per agent per task
- [ ] Corpus access logging with attribution
- [ ] Violation trend analysis and alerting
- [ ] Performance impact monitoring of governance checks

---

## 🔄 Governance Protocol Updates

### Change Management Process
1. **Security Impact Assessment**: All governance changes require security review
2. **Testing Requirements**: Comprehensive testing of governance logic changes  
3. **Phased Rollout**: Gradual deployment with monitoring and rollback capability
4. **Documentation Updates**: All protocol changes documented and communicated

### Version Control
- Protocol version tracked in git with semantic versioning
- Breaking changes require major version increment
- All changes reviewed and approved by security team
- Backward compatibility maintained for at least 2 versions

---

**Document Approval:**
- Security Team Lead: [Name] - [Date]
- Development Team Lead: [Name] - [Date]
- Agent Architecture Lead: [Name] - [Date]

**Next Review Date**: 2024-12-01