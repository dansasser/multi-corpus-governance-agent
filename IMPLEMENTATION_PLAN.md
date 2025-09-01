# Multi-Corpus Governance Agent - Implementation Plan (Revised)

**Document Version**: 2.0  
**Last Updated**: 2024-09-01  
**Status**: DRAFT - PENDING APPROVAL  

---

## 🎯 Overview

This implementation plan details how to build the Multi-Corpus Governance Agent using **protocol architecture over PydanticAI**. Rather than relying on prompt engineering, we implement **governance as an architectural constraint** that makes rule violations impossible through tool-level enforcement and runtime validation.

### Core Innovation: Governance Protocol Layer
- **Protocol-First Design**: Security and governance enforced at the architecture level, not prompt level
- **PydanticAI Integration**: Agent orchestration with governance-wrapped tools and dependency injection
- **MVLM Firebreaks**: Revisor and Summarizer use local models as primary, API as controlled fallback
- **Immutable Audit Trail**: Complete attribution and decision tracking through the five-agent pipeline

---

## 🛡️ Security Integration Requirements

> **Security Foundation**: All implementation must comply with security requirements defined in `docs/security/`

### Mandatory Security Compliance
- **Governance Rules**: Implement exact agent constraints from [`docs/security/protocols/governance-protocol.md`](docs/security/protocols/governance-protocol.md)
- **Security Architecture**: Follow trust boundaries defined in [`docs/security/architecture/security-architecture.md`](docs/security/architecture/security-architecture.md)  
- **Deployment Validation**: Meet all requirements in [`docs/security/compliance/deployment-security.md`](docs/security/compliance/deployment-security.md)
- **Incident Response**: Integrate monitoring per [`docs/security/incident-response/incident-response-playbook.md`](docs/security/incident-response/incident-response-playbook.md)

### Security Implementation Checkpoints
- [ ] **Week 2**: Validate governance tool implementation against protocol specification
- [ ] **Week 4**: Security architecture review using documented trust boundaries  
- [ ] **Week 6**: Pre-deployment security validation using compliance checklist
- [ ] **Week 8**: Incident response procedures tested and operational

---

## 🏗️ Protocol Architecture Strategy

### Governance-Wrapped Agent Pattern

```python
# Core pattern: Each agent is a PydanticAI instance wrapped with governance
class GovernedAgent:
    def __init__(self, agent_name: str, governance_config: GovernanceConfig):
        self.agent = Agent(model="gpt-4", deps_type=AgentContext)
        self.governance = GovernanceEngine(agent_name, governance_config)
        self.agent_name = agent_name
        
    # All tools wrapped with protocol enforcement
    @self.agent.tool
    @governance_enforced(permissions=['corpus_access'], max_calls=2)
    async def secured_corpus_query(
        ctx: RunContext[AgentContext], 
        corpus: str, 
        query: str
    ) -> CorpusResult:
        # Governance validation occurs BEFORE execution
        # Violations raise exceptions and terminate execution
        return await self.corpus_connector.secure_query(corpus, query, ctx.deps)
```

### Multi-Agent Pipeline with Protocol Checkpoints

```python
class ProtocolEnforcedPipeline:
    """Five-agent pipeline with governance validation at every handoff"""
    
    async def process_request(self, user_prompt: str) -> GovernedOutput:
        context = await self.initialize_governance_context(user_prompt)
        
        # Each stage validates protocol compliance before execution
        ideator_result = await self.execute_governed_stage(
            agent=self.ideator,
            input_data=context,
            governance_checkpoint="outline_generation"
        )
        
        drafter_result = await self.execute_governed_stage(
            agent=self.drafter,
            input_data=ideator_result,
            governance_checkpoint="draft_expansion"  
        )
        
        # Critic has RAG access - additional protocol validation
        critic_result = await self.execute_governed_stage(
            agent=self.critic,
            input_data=drafter_result,
            governance_checkpoint="truth_validation"
        )
        
        # Revisor: MVLM primary, API fallback with governance approval
        revisor_result = await self.execute_mvlm_stage(
            agent=self.revisor,
            input_data=critic_result,
            fallback_allowed=True
        )
        
        # Summarizer: MVLM only (no API fallback without emergency authorization)
        final_result = await self.execute_mvlm_stage(
            agent=self.summarizer,
            input_data=revisor_result,
            fallback_allowed=False
        )
        
        return final_result
```

---

## 📋 Phase One: Protocol Layer Implementation (8 Weeks)

### Week 1-2: Governance Protocol Foundation

#### Core Governance Engine
```python
# governance/protocol.py - Implements exact rules from security docs
class GovernanceProtocol:
    """
    Implements agent permission matrix from:
    docs/security/protocols/governance-protocol.md
    """
    
    AGENT_PERMISSIONS = {
        'ideator': {
            'max_api_calls': 2,
            'corpus_access': ['personal', 'social', 'published'],
            'rag_access': False,
            'mvlm_access': True
        },
        'drafter': {
            'max_api_calls': 1,
            'corpus_access': ['social', 'published'],  # limited
            'rag_access': False,
            'mvlm_access': True
        },
        'critic': {
            'max_api_calls': 2,
            'corpus_access': ['personal', 'social', 'published'],
            'rag_access': True,  # ONLY agent with RAG access
            'mvlm_access': True
        },
        'revisor': {
            'max_api_calls': 1,  # fallback only
            'corpus_access': [],  # inherited context only
            'rag_access': False,
            'mvlm_access': True,  # PRIMARY
            'mvlm_preferred': True
        },
        'summarizer': {
            'max_api_calls': 0,  # emergency fallback only
            'corpus_access': [],  # no new queries
            'rag_access': False,
            'mvlm_access': True,  # ONLY
            'mvlm_required': True
        }
    }
```

#### Tool-Level Protocol Enforcement
```python
# governance/decorators.py - Protocol enforcement decorators
def governance_enforced(
    permissions: List[str],
    max_calls: int = 0,
    corpus_restrictions: List[str] = None,
    requires_mvlm_primary: bool = False
):
    """Decorator that enforces governance rules at tool invocation"""
    def decorator(tool_func):
        async def wrapper(ctx: RunContext[AgentContext], *args, **kwargs):
            # 1. Validate agent permissions against protocol
            await GovernanceValidator.validate_tool_access(
                agent_name=ctx.deps.agent_role,
                tool_permissions=permissions,
                current_context=ctx.deps
            )
            
            # 2. Check API call limits
            if max_calls > 0:
                await CallLimitValidator.validate_api_call(
                    ctx.deps.agent_role, 
                    ctx.deps.task_id,
                    max_calls
                )
            
            # 3. Validate corpus access if applicable
            if corpus_restrictions:
                await CorpusAccessValidator.validate_access(
                    ctx.deps.agent_role,
                    corpus_restrictions
                )
            
            # 4. MVLM preference check
            if requires_mvlm_primary:
                if not await MVLMAvailabilityChecker.is_mvlm_available():
                    if not await GovernanceProtocol.can_fallback_to_api(ctx.deps.agent_role):
                        raise MVLMRequiredError(ctx.deps.agent_role)
            
            # 5. Execute with full audit logging
            result = await tool_func(ctx, *args, **kwargs)
            
            # 6. Log successful execution with attribution
            await ProtocolAuditor.log_tool_execution(
                agent_role=ctx.deps.agent_role,
                tool_name=tool_func.__name__,
                governance_validation_passed=True,
                execution_result_hash=hash(str(result)),
                task_id=ctx.deps.task_id
            )
            
            return result
        return wrapper
    return decorator
```

### Week 3-4: Agent Implementation with Protocol Integration

#### Ideator Agent (Max 2 API Calls, Full Corpus Access)
```python
# agents/ideator.py
class IdeatorAgent(GovernedAgent):
    def __init__(self):
        super().__init__(
            agent_name="ideator",
            governance_config=GovernanceConfig.for_ideator()
        )
        
    @self.agent.tool
    @governance_enforced(
        permissions=['corpus_access', 'outline_generation'],
        max_calls=2,
        corpus_restrictions=['personal', 'social', 'published']
    )
    async def build_context_outline(
        ctx: RunContext[AgentContext],
        user_prompt: str
    ) -> OutlineResult:
        """Build outline with multi-corpus context and tone scoring"""
        
        # Query all authorized corpora
        context_pack = await ContextAssembly.build_from_corpora(
            prompt=user_prompt,
            corpora=['personal', 'social', 'published'],
            agent_permissions=ctx.deps.permissions
        )
        
        # Generate outline with governance-approved prompt
        outline = await self.generate_governed_outline(user_prompt, context_pack)
        
        # Score against governance thresholds
        scores = await ToneScorer.evaluate_outline(outline, context_pack)
        
        # Decide: pass, local tweak, or revise call based on scores
        if scores.passes_all_thresholds():
            return OutlineResult(outline=outline, scores=scores, status="approved")
        elif scores.minor_issues_only():
            tweaked_outline = await self.apply_local_tweaks(outline, scores)
            return OutlineResult(outline=tweaked_outline, scores=scores, status="tweaked")
        else:
            # Use second API call for revision
            revised_outline = await self.revise_outline(outline, scores, context_pack)
            return OutlineResult(outline=revised_outline, scores=scores, status="revised")
```

#### Critic Agent (RAG Access + Full Validation)
```python
# agents/critic.py  
class CriticAgent(GovernedAgent):
    def __init__(self):
        super().__init__(
            agent_name="critic", 
            governance_config=GovernanceConfig.for_critic()
        )
    
    @self.agent.tool
    @governance_enforced(
        permissions=['corpus_access', 'rag_access', 'truth_validation'],
        max_calls=2,
        corpus_restrictions=['personal', 'social', 'published']
    )
    async def validate_draft_truth_and_safety(
        ctx: RunContext[AgentContext],
        draft_content: str,
        draft_metadata: Dict[str, Any]
    ) -> CriticResult:
        """Full truth, voice, SEO, and safety validation with RAG"""
        
        validation_results = ValidationResult()
        
        # 1. Voice/tone validation against corpus fingerprints
        voice_score = await VoiceValidator.validate_against_corpus(
            text=draft_content,
            voice_fingerprints=ctx.deps.context_pack.voice_samples
        )
        validation_results.voice_score = voice_score
        
        # 2. Truth validation using RAG (ONLY Critic allowed)
        fact_claims = await ClaimExtractor.extract_factual_claims(draft_content)
        for claim in fact_claims:
            rag_validation = await self.validate_claim_with_rag(claim)
            validation_results.add_fact_check(claim, rag_validation)
        
        # 3. Safety and content policy validation
        safety_result = await SafetyValidator.check_content_safety(draft_content)
        validation_results.safety_result = safety_result
        
        # 4. SEO validation (if writing mode)
        if ctx.deps.output_mode == "writing":
            seo_validation = await SEOValidator.validate_seo_compliance(
                draft_content, 
                draft_metadata
            )
            validation_results.seo_validation = seo_validation
        
        # 5. Determine if critical failure requires pipeline termination
        if validation_results.has_critical_failures():
            await SecurityLogger.log_critical_failure(
                agent="critic",
                task_id=ctx.deps.task_id,
                failure_reasons=validation_results.critical_failures
            )
            return CriticResult(
                status="critical_failure",
                validation_results=validation_results,
                pipeline_action="terminate"
            )
        
        return CriticResult(
            status="validation_complete",
            validation_results=validation_results,
            corrections=validation_results.generate_corrections(),
            pipeline_action="continue"
        )
    
    async def validate_claim_with_rag(self, claim: FactualClaim) -> RAGValidation:
        """RAG validation - only available to Critic agent"""
        # This method can only be called by Critic due to governance enforcement
        external_sources = await RAGConnector.query_external_sources(
            query=claim.text,
            whitelisted_domains=self.governance.rag_whitelist,
            max_sources=3
        )
        
        validation = await FactChecker.validate_claim_against_sources(
            claim=claim,
            sources=external_sources
        )
        
        return validation
```

#### Revisor Agent (MVLM Primary, Governed API Fallback)
```python
# agents/revisor.py
class RevisorAgent(GovernedAgent):
    def __init__(self):
        super().__init__(
            agent_name="revisor",
            governance_config=GovernanceConfig.for_revisor()
        )
    
    @self.agent.tool
    @governance_enforced(
        permissions=['correction_application', 'tone_preservation'],
        max_calls=1,  # API fallback only
        requires_mvlm_primary=True
    )
    async def apply_critic_corrections(
        ctx: RunContext[AgentContext],
        original_draft: str,
        critic_corrections: List[Correction],
        voice_samples: Dict[str, Any]
    ) -> RevisorResult:
        """Apply corrections using MVLM primarily, API fallback if needed"""
        
        try:
            # PRIMARY: Use MVLM for deterministic correction application
            mvlm_result = await MVLMProcessor.apply_corrections(
                original_text=original_draft,
                corrections=critic_corrections,
                voice_anchors=voice_samples,
                preserve_attribution=True
            )
            
            # Validate MVLM output meets governance requirements
            validation = await RevisorValidator.validate_mvlm_output(
                original=original_draft,
                revised=mvlm_result.text,
                corrections=critic_corrections
            )
            
            if validation.is_acceptable():
                return RevisorResult(
                    revised_text=mvlm_result.text,
                    processing_method="mvlm",
                    corrections_applied=mvlm_result.corrections_applied,
                    change_log=mvlm_result.change_log,
                    status="success"
                )
            else:
                raise MVLMOutputUnacceptableError(validation.issues)
                
        except (MVLMFailure, MVLMOutputUnacceptableError) as e:
            # FALLBACK: Single API call if MVLM fails and governance allows
            if await self.governance.can_use_api_fallback(ctx.deps.task_id):
                
                api_result = await self.api_correction_fallback(
                    original_draft=original_draft,
                    corrections=critic_corrections,
                    voice_samples=voice_samples,
                    mvlm_failure_reason=str(e)
                )
                
                return RevisorResult(
                    revised_text=api_result.text,
                    processing_method="api_fallback",
                    corrections_applied=api_result.corrections_applied,
                    change_log=api_result.change_log,
                    fallback_reason=str(e),
                    status="success"
                )
            else:
                # Cannot use API fallback - governance violation
                raise GovernanceViolationError(
                    f"MVLM failed and API fallback not permitted for task {ctx.deps.task_id}"
                )
```

#### Summarizer Agent (MVLM Only, Emergency API Fallback)
```python
# agents/summarizer.py
class SummarizerAgent(GovernedAgent):
    def __init__(self):
        super().__init__(
            agent_name="summarizer",
            governance_config=GovernanceConfig.for_summarizer()  
        )
    
    @self.agent.tool
    @governance_enforced(
        permissions=['content_compression', 'keyword_extraction'],
        max_calls=0,  # No API calls by default
        requires_mvlm_primary=True
    )
    async def compress_and_extract_metadata(
        ctx: RunContext[AgentContext],
        final_draft: str,
        pipeline_metadata: Dict[str, Any]
    ) -> SummarizerResult:
        """Compress content and extract keywords using MVLM only"""
        
        try:
            # MVLM ONLY: No API fallback without emergency authorization
            compression_result = await MVLMProcessor.compress_content(
                input_text=final_draft,
                target_length=ctx.deps.target_summary_length,
                preserve_meaning=True,
                extract_keywords=True,
                no_new_vocabulary=True  # Governance constraint
            )
            
            # Extract long-tail keywords for metadata
            keywords = await KeywordExtractor.extract_longtail_keywords(
                text=compression_result.compressed_text,
                original_text=final_draft,
                corpus_context=ctx.deps.context_pack
            )
            
            # Validate no new claims or vocabulary introduced
            validation = await ContentValidator.validate_compression(
                original=final_draft,
                compressed=compression_result.compressed_text,
                allowed_additions=["and", "the", "with", ",", "-"]  # Connectors only
            )
            
            if not validation.is_valid():
                raise CompressionViolationError(validation.violations)
            
            return SummarizerResult(
                compressed_text=compression_result.compressed_text,
                long_tail_keywords=keywords,
                compression_ratio=len(compression_result.compressed_text) / len(final_draft),
                trimmed_sections=compression_result.trimmed_sections,
                processing_method="mvlm",
                metadata_bundle=self.create_final_metadata_bundle(
                    pipeline_metadata, keywords, compression_result
                ),
                status="success"
            )
            
        except MVLMFailure as e:
            # Emergency API fallback requires special authorization
            if await EmergencyAuthorization.is_api_fallback_authorized(ctx.deps.task_id):
                # Log emergency API usage
                await SecurityLogger.log_emergency_api_usage(
                    agent="summarizer",
                    task_id=ctx.deps.task_id,
                    authorization_reason="mvlm_failure",
                    failure_details=str(e)
                )
                
                # Single emergency API call
                api_result = await self.emergency_api_compression(
                    final_draft, pipeline_metadata, mvlm_failure=str(e)
                )
                
                return api_result
            else:
                # No emergency authorization - fail gracefully
                raise CompressionFailureError(
                    f"MVLM compression failed and no emergency API authorization for task {ctx.deps.task_id}"
                )
```

### Week 5-6: Pipeline Orchestration and Context Management

#### Context Assembly with Attribution Tracking
```python
# context/assembly.py - Implements context-assembly.md requirements
class ProtocolEnforcedContextAssembly:
    """
    Builds context packs following exact specifications from:
    docs/security/protocols/governance-protocol.md
    """
    
    async def build_context_pack(
        self,
        user_prompt: str,
        agent_permissions: AgentPermissions,
        classification: PromptClassification
    ) -> ContextPack:
        """Build attributed context pack with governance validation"""
        
        context_pack = ContextPack(
            task_id=str(uuid4()),
            created_at=datetime.utcnow(),
            classification=classification,
            agent_permissions=agent_permissions
        )
        
        # Query corpora based on agent permissions
        if 'personal' in agent_permissions.corpus_access:
            personal_snippets = await PersonalCorpusConnector.secure_query(
                query=user_prompt,
                agent_role=agent_permissions.agent_name,
                max_snippets=10
            )
            context_pack.add_snippets(personal_snippets, corpus="personal")
        
        if 'social' in agent_permissions.corpus_access:
            social_snippets = await SocialCorpusConnector.secure_query(
                query=user_prompt,
                agent_role=agent_permissions.agent_name,
                max_snippets=15,
                include_engagement_data=agent_permissions.can_access_engagement_data
            )
            context_pack.add_snippets(social_snippets, corpus="social")
        
        if 'published' in agent_permissions.corpus_access:
            published_snippets = await PublishedCorpusConnector.secure_query(
                query=user_prompt,
                agent_role=agent_permissions.agent_name,
                max_snippets=20
            )
            context_pack.add_snippets(published_snippets, corpus="published")
        
        # Build voice fingerprints for tone scoring
        voice_fingerprints = await VoiceFingerprintEngine.build_fingerprints(
            context_pack.all_snippets(),
            agent_permissions.agent_name
        )
        context_pack.voice_fingerprints = voice_fingerprints
        
        # Calculate initial scores and validate diversity
        context_pack.coverage_score = await CoverageScorer.calculate_coverage(
            prompt=user_prompt,
            snippets=context_pack.all_snippets()
        )
        
        context_pack.diversity_check = await DiversityChecker.validate_diversity(
            context_pack.snippets_by_corpus(),
            min_corpora=2 if len(agent_permissions.corpus_access) > 1 else 1
        )
        
        # Ensure complete attribution chain
        await AttributionValidator.validate_complete_attribution(context_pack)
        
        return context_pack
```

#### Agent Context and Dependency Injection
```python
# governance/context.py - AgentContext for RunContext dependency injection
class AgentContext(BaseModel):
    """Typed context passed to all PydanticAI agents via RunContext"""
    
    # Core identification
    task_id: str
    agent_role: str  # ideator, drafter, critic, revisor, summarizer
    
    # Governance state
    permissions: AgentPermissions
    api_calls_made: int = 0
    governance_violations: List[str] = []
    
    # Content and context
    context_pack: Optional[ContextPack] = None
    input_content: str
    pipeline_metadata: Dict[str, Any] = {}
    
    # Attribution chain
    attribution_chain: List[Attribution] = []
    voice_fingerprints: Dict[str, VoiceFingerprint] = {}
    
    # Output configuration
    output_mode: str  # chat, writing, voice
    target_summary_length: Optional[int] = None
    
    # Security tracking
    created_at: datetime
    last_updated: datetime
    security_clearance: str = "standard"
    
    def add_attribution(self, attribution: Attribution) -> None:
        """Add attribution while preserving immutable chain"""
        self.attribution_chain.append(attribution)
        self.last_updated = datetime.utcnow()
    
    def increment_api_calls(self) -> None:
        """Track API usage for governance validation"""
        self.api_calls_made += 1
        self.last_updated = datetime.utcnow()
    
    def add_governance_violation(self, violation: str) -> None:
        """Record governance violations for audit trail"""
        self.governance_violations.append(violation)
        self.last_updated = datetime.utcnow()
```

### Week 7-8: Security Integration and Testing

#### Security Testing Framework
```python
# tests/security/test_governance_protocol.py
class TestGovernanceProtocolEnforcement:
    """
    Validates implementation against:
    docs/security/protocols/governance-protocol.md
    docs/security/compliance/deployment-security.md
    """
    
    async def test_ideator_api_call_limits(self):
        """Test that Ideator cannot exceed 2 API calls per task"""
        task_id = str(uuid4())
        ideator = IdeatorAgent()
        
        # First call should succeed
        result1 = await ideator.build_context_outline(
            AgentContext(task_id=task_id, agent_role="ideator", input_content="test")
        )
        assert result1.status == "success"
        
        # Second call should succeed
        result2 = await ideator.build_context_outline(
            AgentContext(task_id=task_id, agent_role="ideator", input_content="test")
        )
        assert result2.status == "success"
        
        # Third call should raise APICallLimitExceededError
        with pytest.raises(APICallLimitExceededError):
            await ideator.build_context_outline(
                AgentContext(task_id=task_id, agent_role="ideator", input_content="test")
            )
    
    async def test_drafter_cannot_access_personal_corpus(self):
        """Test that Drafter is blocked from Personal corpus access"""
        drafter = DrafterAgent()
        
        with pytest.raises(UnauthorizedCorpusAccessError) as exc_info:
            await drafter.query_corpus(
                AgentContext(agent_role="drafter", task_id=str(uuid4())),
                corpus="personal",
                query="test"
            )
        
        assert exc_info.value.agent_name == "drafter"
        assert exc_info.value.corpus == "personal"
    
    async def test_non_critic_rag_access_blocked(self):
        """Test that only Critic can access RAG endpoints"""
        ideator = IdeatorAgent()
        
        with pytest.raises(UnauthorizedRAGAccessError) as exc_info:
            await ideator.query_external_rag(
                AgentContext(agent_role="ideator", task_id=str(uuid4())),
                query="test external query"
            )
        
        assert exc_info.value.agent_name == "ideator"
    
    async def test_revisor_mvlm_preference_enforcement(self):
        """Test that Revisor uses MVLM primarily and API only as fallback"""
        revisor = RevisorAgent()
        
        # Mock MVLM success - should use MVLM
        with patch('MVLMProcessor.apply_corrections', return_value=mock_mvlm_result):
            result = await revisor.apply_critic_corrections(
                AgentContext(agent_role="revisor", task_id=str(uuid4())),
                original_draft="test",
                critic_corrections=[],
                voice_samples={}
            )
            assert result.processing_method == "mvlm"
        
        # Mock MVLM failure - should fall back to API (if governance allows)
        with patch('MVLMProcessor.apply_corrections', side_effect=MVLMFailure("test")):
            result = await revisor.apply_critic_corrections(
                AgentContext(agent_role="revisor", task_id=str(uuid4())),
                original_draft="test", 
                critic_corrections=[],
                voice_samples={}
            )
            assert result.processing_method == "api_fallback"
            assert result.fallback_reason == "test"
    
    async def test_summarizer_mvlm_only_enforcement(self):
        """Test that Summarizer cannot use API without emergency authorization"""
        summarizer = SummarizerAgent()
        
        # Mock MVLM failure without emergency authorization
        with patch('MVLMProcessor.compress_content', side_effect=MVLMFailure("test")):
            with patch('EmergencyAuthorization.is_api_fallback_authorized', return_value=False):
                with pytest.raises(CompressionFailureError):
                    await summarizer.compress_and_extract_metadata(
                        AgentContext(agent_role="summarizer", task_id=str(uuid4())),
                        final_draft="test content",
                        pipeline_metadata={}
                    )
```

#### Security Monitoring Integration
```python
# monitoring/security_monitor.py - Implements incident-response-playbook.md
class GovernanceViolationMonitor:
    """
    Real-time monitoring following:
    docs/security/incident-response/incident-response-playbook.md
    """
    
    async def monitor_governance_violations(self):
        """Continuous monitoring for governance rule violations"""
        
        async for violation_event in SecurityEventStream.listen():
            
            # Classify violation severity
            severity = self.classify_violation_severity(violation_event)
            
            # Immediate containment for critical violations
            if severity == ViolationSeverity.CRITICAL:
                await self.execute_critical_containment(violation_event)
            
            # Create incident ticket
            incident = await IncidentManager.create_incident(
                severity=severity,
                violation_type=violation_event.type,
                agent_context=violation_event.context,
                detection_time=datetime.utcnow()
            )
            
            # Alert security team
            await SecurityAlerter.send_alert(incident)
            
            # Log for audit trail
            await SecurityLogger.log_violation_response(
                incident_id=incident.id,
                violation=violation_event,
                containment_actions=incident.containment_actions,
                response_time_ms=incident.response_time_ms
            )
    
    async def execute_critical_containment(self, violation: SecurityViolation):
        """Immediate containment for critical governance violations"""
        
        # Terminate affected task immediately
        await PipelineController.emergency_terminate(violation.task_id)
        
        # Revoke session if user-related
        if violation.user_id:
            await SessionManager.revoke_user_session(violation.user_id)
        
        # Block IP if attack-like behavior
        if violation.appears_malicious():
            await NetworkSecurity.block_ip_temporarily(
                ip_address=violation.source_ip,
                duration_minutes=30
            )
        
        # Alert security team immediately
        await SecurityAlerter.send_critical_alert(
            message=f"Critical governance violation: {violation.type}",
            violation_details=violation.to_dict(),
            containment_actions=["task_terminated", "session_revoked"]
        )
```

---

## 📊 Revised Implementation Timeline

### **Week 1-2: Protocol Foundation**
- [ ] Governance engine implementing exact rules from security docs
- [ ] Tool-level enforcement decorators with violation detection  
- [ ] Agent context and dependency injection system
- [ ] **Security Checkpoint**: Validate governance protocol against [`docs/security/protocols/governance-protocol.md`](docs/security/protocols/governance-protocol.md)

### **Week 3-4: Agent Implementation**
- [ ] All five agents with protocol-enforced tools
- [ ] MVLM integration for Revisor and Summarizer
- [ ] Multi-corpus connectors with access control validation
- [ ] **Security Checkpoint**: Security architecture review using [`docs/security/architecture/security-architecture.md`](docs/security/architecture/security-architecture.md)

### **Week 5-6: Pipeline Orchestration**
- [ ] End-to-end pipeline with governance checkpoints
- [ ] Context assembly with attribution tracking
- [ ] Real-time monitoring and violation response
- [ ] **Security Checkpoint**: Pre-deployment validation using [`docs/security/compliance/deployment-security.md`](docs/security/compliance/deployment-security.md)

### **Week 7-8: Security Integration**
- [ ] Comprehensive security testing suite
- [ ] Incident response procedures integration
- [ ] Performance optimization and scaling preparation
- [ ] **Final Security Checkpoint**: All security requirements validated and operational per [`docs/security/incident-response/incident-response-playbook.md`](docs/security/incident-response/incident-response-playbook.md)

---

## ✅ Success Criteria

### Technical Requirements
- [ ] All five agents operational with protocol enforcement
- [ ] Zero governance rule bypasses possible (architecturally prevented)
- [ ] MVLM primary processing for Revisor/Summarizer with controlled API fallback
- [ ] Complete audit trail with immutable attribution chain
- [ ] Real-time security monitoring with automated violation response

### Security Compliance
- [ ] 100% compliance with all security documentation requirements
- [ ] All deployment security checklist items validated
- [ ] Incident response procedures tested and operational
- [ ] Governance protocol enforcement tested and verified

### Performance Targets
- [ ] <5s response time for chat mode
- [ ] <15s response time for writing mode  
- [ ] >80% voice fingerprint matching accuracy
- [ ] <1% critical failure rate with graceful recovery

---

**Document Approval Required Before Implementation:**
- [ ] Security Team Lead: Protocol security validation
- [ ] Development Team Lead: Technical architecture approval  
- [ ] Product Manager: Requirements alignment confirmation

**Next Steps:**
1. Review and approve this revised implementation plan
2. Begin Week 1-2 Protocol Foundation implementation
3. Regular security checkpoints per schedule above

---