# Incident Response Playbook

**Document Version**: 1.0  
**Last Updated**: 2024-09-01  
**Status**: APPROVED  
**Classification**: CONFIDENTIAL  

---

## 🚨 Emergency Response Overview

This playbook provides step-by-step procedures for responding to security incidents in the Multi-Corpus Governance Agent system. All incidents must be handled according to these procedures to ensure consistent, effective response and proper evidence preservation.

### 📞 Emergency Contacts
- **Security Incident Hotline**: `security-incidents@mcg-agent.com`
- **Primary Security Lead**: [Name] - [Phone] - [Email]
- **Backup Security Lead**: [Name] - [Phone] - [Email]  
- **Development Team Lead**: [Name] - [Phone] - [Email]
- **DevOps/Infrastructure**: [Name] - [Phone] - [Email]

---

## 🎯 Incident Classification System

### Severity Levels

#### 🔴 **CRITICAL (P0)** - Immediate Response Required (<15 minutes)
**Characteristics:**
- Governance rules bypassed or circumvented
- Unauthorized access to restricted corpora confirmed
- Data breach or exfiltration detected
- System compromise with root/admin access
- Complete service outage affecting all users

**Examples:**
- Agent accessing corpus without proper authorization
- External attacker gained access to database
- Personal corpus data exposed publicly
- Authentication system completely compromised

#### 🟠 **HIGH (P1)** - Urgent Response Required (<1 hour)
**Characteristics:**
- Authentication bypass attempts detected
- Rate limiting completely failing
- Abnormal agent behavior suggesting compromise
- Partial service degradation affecting multiple users
- Security control failures with potential for escalation

**Examples:**
- Multiple failed authentication attempts from single source
- Agent exceeding API limits without governance intervention
- Suspicious patterns in corpus queries
- Redis or database connection security failures

#### 🟡 **MEDIUM (P2)** - Response Required (<4 hours)
**Characteristics:**
- Configuration errors affecting security posture
- Performance anomalies that could indicate attack
- Non-critical security warnings requiring investigation
- Individual user account security issues

**Examples:**
- TLS certificate approaching expiration
- Unusual but not necessarily malicious access patterns
- Single user reporting account access issues
- Non-critical monitoring alerts

#### 🟢 **LOW (P3)** - Response Required (<24 hours)
**Characteristics:**
- Information security policy violations
- Minor configuration drift
- Non-urgent security improvements needed

---

## 🚨 Critical Incident Response (P0)

### Phase 1: Immediate Response (0-15 minutes)

#### Step 1: Incident Detection and Confirmation
```bash
# If automated alert triggered:
1. Acknowledge alert in monitoring system
2. Verify incident is not false positive
3. Gather initial evidence from logs

# If manually discovered:
1. Document discovery time and method
2. Take screenshots of evidence
3. Note any immediate impact observed
```

#### Step 2: Immediate Containment
```bash
# For governance rule bypass:
kubectl scale deployment mcg-agent --replicas=0  # Stop all agents
redis-cli FLUSHALL  # Clear session state (if compromised)

# For database compromise:
# Rotate database credentials immediately
# Block suspicious IP addresses at firewall

# For authentication compromise:
# Revoke all active JWT tokens
# Disable affected user accounts
```

#### Step 3: Stakeholder Notification
```markdown
**CRITICAL INCIDENT NOTIFICATION**

Incident ID: INC-2024-[NUMBER]
Severity: P0 - CRITICAL
Detection Time: [UTC TIMESTAMP]
Affected Systems: [LIST]
Initial Impact Assessment: [DESCRIPTION]

Immediate Actions Taken:
- [ ] System containment actions executed
- [ ] Evidence preservation initiated
- [ ] Investigation team assembled

Response Team Assigned:
- Incident Commander: [Name]
- Security Analyst: [Name]  
- Technical Lead: [Name]
- Communications Lead: [Name]

Next Update: [TIME + 30 minutes]
```

### Phase 2: Investigation and Analysis (15-60 minutes)

#### Evidence Collection Protocol
```bash
# System logs
kubectl logs -l app=mcg-agent --since=2h > incident-logs.txt

# Database query logs
psql -c "SELECT * FROM audit_logs WHERE timestamp > NOW() - INTERVAL '2 hours'" > db-audit.csv

# Redis access logs  
redis-cli --latency-history > redis-access.log

# Network traffic (if available)
tcpdump -w incident-network.pcap host [suspicious-ip]
```

#### Root Cause Analysis Framework
```markdown
## Investigation Checklist

### Technical Analysis
- [ ] Review system logs for anomalies
- [ ] Analyze database access patterns
- [ ] Check governance rule execution logs
- [ ] Validate agent API call patterns
- [ ] Review authentication and session logs

### Attack Vector Analysis
- [ ] Identify initial compromise method
- [ ] Map attacker progression through system
- [ ] Assess data accessed or modified
- [ ] Determine persistence mechanisms used
- [ ] Evaluate potential insider threat indicators

### Impact Assessment
- [ ] Quantify data potentially accessed
- [ ] Identify affected user accounts
- [ ] Assess system integrity status
- [ ] Determine business process impact
- [ ] Evaluate regulatory compliance implications
```

### Phase 3: Eradication and Recovery (1-4 hours)

#### Eradication Actions
```bash
# Remove attacker access
# Patch identified vulnerabilities
# Update governance rules if bypassed
# Rebuild compromised systems from clean backups

# Governance-specific eradication:
# 1. Review and strengthen agent permission validation
# 2. Update corpus access control rules
# 3. Enhance API call limit enforcement
# 4. Strengthen input validation routines
```

#### System Recovery Protocol
```yaml
Recovery_Checklist:
  Pre-Recovery:
    - [ ] Confirm threat eradicated
    - [ ] Validate system integrity
    - [ ] Test governance rules functioning
    - [ ] Verify security controls operational
  
  Recovery_Process:
    - [ ] Restore from clean backups if needed
    - [ ] Redeploy application with security patches
    - [ ] Reset all authentication credentials
    - [ ] Validate agent pipeline functioning correctly
    
  Post-Recovery:
    - [ ] Monitor for signs of re-compromise
    - [ ] Validate all security controls
    - [ ] Confirm normal system operation
    - [ ] Document lessons learned
```

---

## ⚠️ High Priority Incident Response (P1)

### Governance Violation Response

#### Automated Detection Triggers
```python
# Example: Unauthorized corpus access detection
async def detect_unauthorized_corpus_access():
    violations = await AuditLogger.query_violations(
        violation_types=['unauthorized_corpus_access'],
        time_window='last_hour'
    )
    
    if len(violations) > 0:
        await incident_manager.create_incident(
            severity='P1',
            type='governance_violation',
            description=f'Unauthorized corpus access detected: {len(violations)} violations'
        )
```

#### Response Actions (< 1 Hour)
1. **Validate Alert**: Confirm unauthorized access actually occurred
2. **Immediate Containment**: Disable affected agent or user session
3. **Evidence Collection**: Gather logs showing violation attempt
4. **Impact Assessment**: Determine what data may have been accessed
5. **Remediation**: Fix configuration or code issue that allowed violation
6. **Monitoring Enhancement**: Add additional detection for similar violations

---

## 📊 Incident Documentation and Reporting

### Required Documentation

#### Incident Report Template
```markdown
# Incident Report: INC-2024-[NUMBER]

## Executive Summary
- **Incident Type**: [Governance Violation | Data Breach | System Compromise]
- **Detection Time**: [UTC]
- **Resolution Time**: [UTC]  
- **Total Duration**: [Hours]
- **Impact**: [Description]

## Timeline of Events
| Time (UTC) | Event | Actor | Action Taken |
|------------|-------|-------|--------------|
| | | | |

## Technical Details
### Root Cause
[Detailed technical explanation]

### Attack Vector
[How the incident occurred]

### Systems Affected
[List of affected components]

### Data Involved
[What data was accessed/modified/stolen]

## Response Actions
### Immediate Response
- [List containment actions]

### Investigation Findings  
- [Key discoveries]

### Remediation Steps
- [Actions taken to fix root cause]

## Lessons Learned
### What Worked Well
- [Effective response elements]

### Areas for Improvement
- [Process improvements needed]

### Recommendations
- [Specific action items with owners]

## Appendices
- A: Log excerpts
- B: Network traffic analysis
- C: System configuration changes
```

### Post-Incident Activities

#### Immediate (Within 24 hours)
- [ ] Complete incident report
- [ ] Notify affected stakeholders
- [ ] Document lessons learned
- [ ] Update incident response procedures if needed

#### Short-term (Within 1 week)
- [ ] Implement security improvements identified
- [ ] Conduct tabletop exercise of incident response
- [ ] Update security training materials
- [ ] Review and update monitoring alerting

#### Long-term (Within 1 month)
- [ ] Conduct thorough security posture review
- [ ] Update threat model based on incident
- [ ] Implement additional preventive controls
- [ ] Schedule third-party security assessment

---

## 🛡️ Governance-Specific Incident Scenarios

### Scenario 1: Agent API Limit Bypass Detected

#### Detection Indicators
- Agent exceeding defined API call limits
- Suspicious patterns in agent execution logs
- Rate limiting failures in monitoring systems

#### Response Actions
```bash
# 1. Immediate containment
kubectl scale deployment [agent-name] --replicas=0

# 2. Investigation
grep "api_call_limit_exceeded" /var/log/mcg-agent/governance.log
psql -c "SELECT * FROM task_logs WHERE agent_role='[agent]' AND execution_time > normal_range"

# 3. Remediation  
# Review and strengthen API call validation in PydanticAI tools
# Update governance rules if necessary
# Redeploy with enhanced limits
```

### Scenario 2: Unauthorized RAG Access Attempt

#### Detection Indicators
- Non-Critic agent attempting RAG queries
- External API calls from unauthorized agents
- Governance violation logs showing RAG access attempts

#### Response Actions
```bash
# 1. Block external API access immediately
iptables -A OUTPUT -p tcp --dport 443 -j DROP  # Emergency block

# 2. Investigate agent behavior
grep "rag_access_violation" /var/log/mcg-agent/security.log

# 3. Code review and patching
# Review PydanticAI tool implementations
# Strengthen RAG access validation
# Test governance enforcement
```

### Scenario 3: Corpus Data Exfiltration Detected

#### Detection Indicators
- Unusual corpus query patterns
- Large data transfers from database
- Authentication anomalies combined with data access

#### Response Actions
```bash
# 1. Immediate database isolation
# Block database access from application layer
# Preserve database state for forensics

# 2. Evidence collection
pg_dump forensic_backup
grep -r "corpus_query" /var/log/mcg-agent/ > corpus-access.log

# 3. Impact assessment
# Identify which corpora accessed
# Determine scope of data potentially exfiltrated
# Assess need for user notification
```

---

## 📋 Incident Response Readiness

### Team Training Requirements
- **Monthly**: Tabletop exercises for different incident types
- **Quarterly**: Full incident response simulation
- **Annually**: Crisis communication training
- **Continuous**: Security awareness training updates

### Tool and Resource Preparation
```bash
# Incident response toolkit
/opt/incident-response/
├── containment-scripts/
│   ├── emergency-shutdown.sh
│   ├── isolate-database.sh
│   └── block-suspicious-ips.sh
├── investigation-tools/
│   ├── log-analyzer.py
│   ├── governance-validator.py
│   └── forensic-collector.sh
└── recovery-procedures/
    ├── system-recovery.md
    ├── governance-rules-restore.sh
    └── post-incident-checklist.md
```

### Communication Templates
- Critical incident notification (internal)
- Stakeholder update template  
- User communication (if breach affects users)
- Regulatory notification (if required)
- Media statement template (if public disclosure needed)

---

## ✅ Incident Response Validation

### Quarterly Testing Requirements
- [ ] Test incident detection and alerting systems
- [ ] Validate containment procedures work correctly
- [ ] Verify communication channels and contact lists
- [ ] Practice evidence collection and preservation
- [ ] Test system recovery procedures
- [ ] Validate governance rule restoration processes

### Annual Assessment
- [ ] Full-scale incident response exercise
- [ ] Third-party assessment of incident response capability
- [ ] Review and update all incident response documentation
- [ ] Validate legal and regulatory compliance procedures

---

**Document Approval:**
- Security Incident Response Lead: [Name] - [Date]
- Development Team Lead: [Name] - [Date]
- Legal/Compliance: [Name] - [Date]

**Next Review Date**: 2024-12-01