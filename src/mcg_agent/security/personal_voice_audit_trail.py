"""
Personal Voice Audit Trail Module

Tracks all access to personal voice patterns with immutable audit trails.
Provides comprehensive logging of how personal data influences AI outputs.
"""

import json
import hashlib
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from pydantic import BaseModel, Field

from mcg_agent.pydantic_ai.agent_base import AgentRole
from mcg_agent.config import get_settings
from mcg_agent.utils.exceptions import AuditTrailError


class VoiceInfluenceLevel(str, Enum):
    """Level of voice influence on output"""
    MINIMAL = "minimal"      # <10% of output influenced by voice patterns
    MODERATE = "moderate"    # 10-50% of output influenced by voice patterns  
    SIGNIFICANT = "significant"  # 50-80% of output influenced by voice patterns
    DOMINANT = "dominant"    # >80% of output influenced by voice patterns


class VoicePatternUsage(BaseModel):
    """Record of voice pattern usage"""
    pattern_id: str = Field(description="Unique identifier for the voice pattern")
    pattern_type: str = Field(description="Type of voice pattern used")
    corpus_source: str = Field(description="Source corpus (personal, social, published)")
    pattern_content: str = Field(description="The actual voice pattern content")
    usage_context: str = Field(description="How the pattern was used")
    influence_score: float = Field(description="0-1 score of pattern influence on output")


class PersonalDataInfluence(BaseModel):
    """Record of how personal data influenced an output"""
    task_id: str = Field(description="Unique task identifier")
    agent_role: AgentRole = Field(description="Agent that used the personal data")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Voice pattern usage
    voice_patterns_used: List[VoicePatternUsage] = Field(default_factory=list)
    overall_influence_level: VoiceInfluenceLevel = Field(description="Overall influence level")
    influence_percentage: float = Field(description="Estimated percentage of output influenced")
    
    # Output information
    output_length: int = Field(description="Length of generated output")
    output_hash: str = Field(description="Hash of the output for integrity")
    
    # Context information
    user_query: str = Field(description="Original user query")
    context_summary: str = Field(description="Summary of context used")
    
    # Metadata
    processing_duration_ms: float = Field(description="Time taken to process")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuditTrailEntry(BaseModel):
    """Immutable audit trail entry"""
    entry_id: str = Field(description="Unique entry identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: str = Field(description="Type of audit event")
    
    # Personal data access information
    personal_data_influence: Optional[PersonalDataInfluence] = None
    
    # Security information
    agent_role: AgentRole
    task_id: str
    user_id: Optional[str] = None
    
    # Integrity information
    previous_entry_hash: Optional[str] = None
    entry_hash: str = Field(description="Hash of this entry for integrity")
    
    # Additional data
    details: Dict[str, Any] = Field(default_factory=dict)


class PersonalVoiceAuditTrail:
    """
    Track all access to personal voice patterns with immutable audit trails.
    
    Provides comprehensive logging of:
    - Which voice patterns were accessed by which agents
    - How personal data influenced AI outputs
    - Complete traceability of personal data usage
    - Immutable audit trail for compliance
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._audit_entries: List[AuditTrailEntry] = []
        self._audit_file_path = Path(self.settings.AUDIT_TRAIL_PATH) / "personal_voice_audit.jsonl"
        self._ensure_audit_setup()
        self._load_existing_audit_trail()
        
    def _ensure_audit_setup(self) -> None:
        """Ensure audit trail directory and files are properly set up"""
        audit_dir = self._audit_file_path.parent
        audit_dir.mkdir(parents=True, exist_ok=True)
        
        if not self._audit_file_path.exists():
            self._audit_file_path.touch()
            
    def _load_existing_audit_trail(self) -> None:
        """Load existing audit trail entries from file"""
        try:
            if self._audit_file_path.exists() and self._audit_file_path.stat().st_size > 0:
                with open(self._audit_file_path, 'r') as f:
                    for line in f:
                        if line.strip():
                            entry_data = json.loads(line.strip())
                            entry = AuditTrailEntry(**entry_data)
                            self._audit_entries.append(entry)
                            
        except Exception as e:
            raise AuditTrailError(f"Failed to load existing audit trail: {str(e)}")
            
    def _calculate_entry_hash(self, entry: AuditTrailEntry) -> str:
        """Calculate hash for audit trail entry integrity"""
        # Create deterministic string representation
        entry_dict = entry.dict()
        entry_dict.pop('entry_hash', None)  # Remove hash field itself
        
        entry_json = json.dumps(entry_dict, sort_keys=True, separators=(',', ':'), default=str)
        return hashlib.sha256(entry_json.encode('utf-8')).hexdigest()
        
    def _get_previous_entry_hash(self) -> Optional[str]:
        """Get hash of the previous audit trail entry"""
        if self._audit_entries:
            return self._audit_entries[-1].entry_hash
        return None
        
    def _append_to_audit_file(self, entry: AuditTrailEntry) -> None:
        """Append audit entry to file (immutable append-only)"""
        try:
            with open(self._audit_file_path, 'a') as f:
                entry_json = entry.json(separators=(',', ':'), default=str)
                f.write(entry_json + '\n')
                f.flush()  # Ensure immediate write
                
        except Exception as e:
            raise AuditTrailError(f"Failed to append to audit trail: {str(e)}")
            
    def log_voice_access(
        self, 
        agent_role: AgentRole, 
        corpus: str, 
        voice_patterns: List[str],
        task_id: str,
        context: Optional[str] = None
    ) -> str:
        """
        Log access to voice patterns.
        
        Args:
            agent_role: Agent accessing voice patterns
            corpus: Corpus being accessed
            voice_patterns: List of voice patterns accessed
            task_id: Task identifier
            context: Optional context information
            
        Returns:
            str: Entry ID of the audit log
        """
        try:
            entry_id = f"voice_access_{datetime.utcnow().isoformat()}_{task_id}"
            
            entry = AuditTrailEntry(
                entry_id=entry_id,
                event_type="voice_pattern_access",
                agent_role=agent_role,
                task_id=task_id,
                previous_entry_hash=self._get_previous_entry_hash(),
                entry_hash="",  # Will be calculated
                details={
                    "corpus": corpus,
                    "voice_patterns": voice_patterns,
                    "pattern_count": len(voice_patterns),
                    "context": context or "No context provided"
                }
            )
            
            # Calculate and set hash
            entry.entry_hash = self._calculate_entry_hash(entry)
            
            # Add to memory and file
            self._audit_entries.append(entry)
            self._append_to_audit_file(entry)
            
            return entry_id
            
        except Exception as e:
            raise AuditTrailError(f"Failed to log voice access: {str(e)}")
            
    def log_personal_data_influence(
        self,
        task_id: str,
        agent_role: AgentRole,
        voice_patterns_used: List[VoicePatternUsage],
        output_text: str,
        user_query: str,
        context_summary: str,
        processing_duration_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log how personal data influenced an AI output.
        
        Args:
            task_id: Task identifier
            agent_role: Agent that generated the output
            voice_patterns_used: Voice patterns that influenced the output
            output_text: The generated output text
            user_query: Original user query
            context_summary: Summary of context used
            processing_duration_ms: Processing time
            metadata: Additional metadata
            
        Returns:
            str: Entry ID of the audit log
        """
        try:
            entry_id = f"influence_{datetime.utcnow().isoformat()}_{task_id}"
            
            # Calculate influence metrics
            total_influence = sum(pattern.influence_score for pattern in voice_patterns_used)
            influence_percentage = min(total_influence * 100, 100.0)
            
            # Determine influence level
            if influence_percentage < 10:
                influence_level = VoiceInfluenceLevel.MINIMAL
            elif influence_percentage < 50:
                influence_level = VoiceInfluenceLevel.MODERATE
            elif influence_percentage < 80:
                influence_level = VoiceInfluenceLevel.SIGNIFICANT
            else:
                influence_level = VoiceInfluenceLevel.DOMINANT
                
            # Create personal data influence record
            personal_data_influence = PersonalDataInfluence(
                task_id=task_id,
                agent_role=agent_role,
                voice_patterns_used=voice_patterns_used,
                overall_influence_level=influence_level,
                influence_percentage=influence_percentage,
                output_length=len(output_text),
                output_hash=hashlib.sha256(output_text.encode('utf-8')).hexdigest(),
                user_query=user_query,
                context_summary=context_summary,
                processing_duration_ms=processing_duration_ms,
                metadata=metadata or {}
            )
            
            entry = AuditTrailEntry(
                entry_id=entry_id,
                event_type="personal_data_influence",
                agent_role=agent_role,
                task_id=task_id,
                personal_data_influence=personal_data_influence,
                previous_entry_hash=self._get_previous_entry_hash(),
                entry_hash="",  # Will be calculated
                details={
                    "influence_level": influence_level,
                    "influence_percentage": influence_percentage,
                    "patterns_used_count": len(voice_patterns_used),
                    "output_length": len(output_text)
                }
            )
            
            # Calculate and set hash
            entry.entry_hash = self._calculate_entry_hash(entry)
            
            # Add to memory and file
            self._audit_entries.append(entry)
            self._append_to_audit_file(entry)
            
            return entry_id
            
        except Exception as e:
            raise AuditTrailError(f"Failed to log personal data influence: {str(e)}")
            
    def get_voice_usage_summary(
        self, 
        time_range_hours: int = 24,
        agent_role: Optional[AgentRole] = None
    ) -> Dict[str, Any]:
        """
        Get summary of voice pattern usage over a time range.
        
        Args:
            time_range_hours: Hours to look back
            agent_role: Optional agent role filter
            
        Returns:
            Dict[str, Any]: Usage summary
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=time_range_hours)
        
        # Filter entries
        relevant_entries = [
            entry for entry in self._audit_entries
            if (entry.timestamp >= cutoff_time and
                (agent_role is None or entry.agent_role == agent_role))
        ]
        
        # Analyze voice access entries
        voice_access_entries = [
            entry for entry in relevant_entries
            if entry.event_type == "voice_pattern_access"
        ]
        
        # Analyze influence entries
        influence_entries = [
            entry for entry in relevant_entries
            if entry.event_type == "personal_data_influence"
        ]
        
        # Calculate statistics
        total_voice_accesses = len(voice_access_entries)
        total_influences = len(influence_entries)
        
        corpus_usage = {}
        for entry in voice_access_entries:
            corpus = entry.details.get("corpus", "unknown")
            corpus_usage[corpus] = corpus_usage.get(corpus, 0) + 1
            
        influence_levels = {}
        for entry in influence_entries:
            if entry.personal_data_influence:
                level = entry.personal_data_influence.overall_influence_level
                influence_levels[level] = influence_levels.get(level, 0) + 1
                
        return {
            "time_range_hours": time_range_hours,
            "agent_role": agent_role,
            "total_voice_accesses": total_voice_accesses,
            "total_influences": total_influences,
            "corpus_usage": corpus_usage,
            "influence_levels": influence_levels,
            "entries_analyzed": len(relevant_entries)
        }
        
    def get_task_audit_trail(self, task_id: str) -> List[AuditTrailEntry]:
        """
        Get complete audit trail for a specific task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            List[AuditTrailEntry]: All audit entries for the task
        """
        return [
            entry for entry in self._audit_entries
            if entry.task_id == task_id
        ]
        
    def verify_audit_trail_integrity(self) -> Dict[str, Any]:
        """
        Verify the integrity of the audit trail.
        
        Returns:
            Dict[str, Any]: Integrity verification results
        """
        integrity_results = {
            "total_entries": len(self._audit_entries),
            "integrity_valid": True,
            "broken_chains": [],
            "hash_mismatches": []
        }
        
        previous_hash = None
        
        for i, entry in enumerate(self._audit_entries):
            # Verify hash chain
            if entry.previous_entry_hash != previous_hash:
                integrity_results["broken_chains"].append({
                    "entry_index": i,
                    "entry_id": entry.entry_id,
                    "expected_previous_hash": previous_hash,
                    "actual_previous_hash": entry.previous_entry_hash
                })
                integrity_results["integrity_valid"] = False
                
            # Verify entry hash
            calculated_hash = self._calculate_entry_hash(entry)
            if calculated_hash != entry.entry_hash:
                integrity_results["hash_mismatches"].append({
                    "entry_index": i,
                    "entry_id": entry.entry_id,
                    "expected_hash": entry.entry_hash,
                    "calculated_hash": calculated_hash
                })
                integrity_results["integrity_valid"] = False
                
            previous_hash = entry.entry_hash
            
        return integrity_results
        
    def export_audit_trail(
        self, 
        output_path: Path,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        Export audit trail to a file.
        
        Args:
            output_path: Path to export file
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            int: Number of entries exported
        """
        try:
            # Filter entries by date range
            entries_to_export = self._audit_entries
            
            if start_date:
                entries_to_export = [e for e in entries_to_export if e.timestamp >= start_date]
            if end_date:
                entries_to_export = [e for e in entries_to_export if e.timestamp <= end_date]
                
            # Export to file
            with open(output_path, 'w') as f:
                for entry in entries_to_export:
                    f.write(entry.json(separators=(',', ':'), default=str) + '\n')
                    
            return len(entries_to_export)
            
        except Exception as e:
            raise AuditTrailError(f"Failed to export audit trail: {str(e)}")


__all__ = [
    "PersonalVoiceAuditTrail",
    "PersonalDataInfluence", 
    "VoicePatternUsage",
    "AuditTrailEntry",
    "VoiceInfluenceLevel"
]
