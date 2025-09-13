"""Voice consistency monitor for real-time voice quality assurance."""

import logging
import statistics
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque

from ..protocols.voice_monitoring_protocol import (
    VoiceMonitoringProtocol,
    ConsistencyMetrics,
    MonitoringLevel
)
from ...voice.voice_fingerprint_extractor import VoiceFingerprint

logger = logging.getLogger(__name__)


class VoiceConsistencyMonitor(VoiceMonitoringProtocol):
    """
    Voice consistency monitor that provides real-time monitoring
    of voice pattern consistency and quality.
    
    This monitor specializes in:
    - Real-time consistency checking across voice dimensions
    - Trend monitoring with configurable sensitivity
    - Quality score calculation with detailed breakdowns
    - Alert generation for consistency violations
    """
    
    def __init__(self, monitoring_level: MonitoringLevel = MonitoringLevel.STANDARD):
        """
        Initialize voice consistency monitor.
        
        Args:
            monitoring_level: Level of monitoring detail
        """
        self.monitoring_level = monitoring_level
        
        # Monitoring configuration based on level
        self.monitoring_configs = {
            MonitoringLevel.BASIC: {
                'check_frequency_seconds': 300,      # 5 minutes
                'history_window_hours': 24,          # 1 day
                'consistency_threshold': 0.6,        # Lower threshold
                'trend_sensitivity': 0.2,            # Less sensitive
                'max_history_size': 100
            },
            MonitoringLevel.STANDARD: {
                'check_frequency_seconds': 60,       # 1 minute
                'history_window_hours': 12,          # 12 hours
                'consistency_threshold': 0.7,        # Standard threshold
                'trend_sensitivity': 0.15,           # Standard sensitivity
                'max_history_size': 500
            },
            MonitoringLevel.COMPREHENSIVE: {
                'check_frequency_seconds': 30,       # 30 seconds
                'history_window_hours': 6,           # 6 hours
                'consistency_threshold': 0.8,        # High threshold
                'trend_sensitivity': 0.1,            # More sensitive
                'max_history_size': 1000
            },
            MonitoringLevel.REAL_TIME: {
                'check_frequency_seconds': 5,        # 5 seconds
                'history_window_hours': 2,           # 2 hours
                'consistency_threshold': 0.85,       # Very high threshold
                'trend_sensitivity': 0.05,           # Very sensitive
                'max_history_size': 2000
            }
        }
        
        self.config = self.monitoring_configs[monitoring_level]
        
        # Monitoring state
        self.consistency_history: deque = deque(maxlen=self.config['max_history_size'])
        self.last_check_time = datetime.now()
        self.baseline_fingerprint: Optional[VoiceFingerprint] = None
        
        # Consistency dimensions to monitor
        self.consistency_dimensions = {
            'vocabulary_consistency': self._check_vocabulary_consistency,
            'tone_consistency': self._check_tone_consistency,
            'style_consistency': self._check_style_consistency,
            'structure_consistency': self._check_structure_consistency,
            'formality_consistency': self._check_formality_consistency,
            'engagement_consistency': self._check_engagement_consistency
        }
        
        # Alert thresholds
        self.alert_thresholds = {
            'critical': 0.4,    # Critical consistency violation
            'warning': 0.6,     # Warning level
            'info': 0.8         # Information level
        }
        
        # Monitoring statistics
        self.monitoring_stats = {
            'total_checks': 0,
            'consistency_violations': 0,
            'alerts_generated': 0,
            'average_consistency': 0.0,
            'monitoring_uptime_hours': 0.0
        }
    
    async def monitor_consistency(
        self,
        current_fingerprint: VoiceFingerprint,
        baseline_fingerprint: Optional[VoiceFingerprint] = None
    ) -> ConsistencyMetrics:
        """
        Monitor voice consistency against baseline.
        
        Args:
            current_fingerprint: Current voice fingerprint
            baseline_fingerprint: Optional baseline for comparison
            
        Returns:
            Consistency metrics
        """
        try:
            # Set baseline if provided
            if baseline_fingerprint:
                self.baseline_fingerprint = baseline_fingerprint
            elif not self.baseline_fingerprint:
                # Use current as baseline if none set
                self.baseline_fingerprint = current_fingerprint
                logger.info("Baseline fingerprint established")
            
            # Check if monitoring is due
            time_since_last_check = (datetime.now() - self.last_check_time).total_seconds()
            if time_since_last_check < self.config['check_frequency_seconds']:
                # Return cached result if available
                if self.consistency_history:
                    return self.consistency_history[-1]
            
            # Perform consistency checks
            dimension_scores = {}
            for dimension, check_func in self.consistency_dimensions.items():
                score = await check_func(current_fingerprint, self.baseline_fingerprint)
                dimension_scores[dimension] = score
            
            # Calculate overall consistency
            overall_consistency = sum(dimension_scores.values()) / len(dimension_scores)
            
            # Check for violations
            violations = await self._identify_violations(dimension_scores)
            
            # Generate alerts if needed
            alerts = await self._generate_alerts(overall_consistency, violations)
            
            # Calculate trend
            trend = await self._calculate_consistency_trend()
            
            # Create consistency metrics
            consistency_metrics = ConsistencyMetrics(
                timestamp=datetime.now(),
                overall_consistency=overall_consistency,
                dimension_scores=dimension_scores,
                violations=violations,
                alerts=alerts,
                trend_direction=trend['direction'],
                trend_strength=trend['strength'],
                monitoring_level=self.monitoring_level.value
            )
            
            # Store in history
            self.consistency_history.append(consistency_metrics)
            
            # Update statistics
            self.monitoring_stats['total_checks'] += 1
            if violations:
                self.monitoring_stats['consistency_violations'] += 1
            if alerts:
                self.monitoring_stats['alerts_generated'] += len(alerts)
            
            # Update average consistency
            recent_scores = [m.overall_consistency for m in list(self.consistency_history)[-10:]]
            self.monitoring_stats['average_consistency'] = statistics.mean(recent_scores)
            
            # Update last check time
            self.last_check_time = datetime.now()
            
            logger.debug(f"Consistency check completed: {overall_consistency:.3f}")
            return consistency_metrics
            
        except Exception as e:
            logger.error(f"Consistency monitoring failed: {str(e)}")
            # Return minimal metrics on error
            return ConsistencyMetrics(
                timestamp=datetime.now(),
                overall_consistency=0.5,
                dimension_scores={'error': 0.0},
                violations=[f"Monitoring error: {str(e)}"],
                alerts=[],
                trend_direction='unknown',
                trend_strength=0.0,
                monitoring_level=self.monitoring_level.value
            )
    
    async def check_voice_health(
        self,
        current_fingerprint: VoiceFingerprint
    ) -> Dict[str, Any]:
        """
        Check overall voice health status.
        
        Args:
            current_fingerprint: Current voice fingerprint
            
        Returns:
            Voice health status
        """
        try:
            # Get recent consistency metrics
            consistency_metrics = await self.monitor_consistency(current_fingerprint)
            
            # Calculate health indicators
            health_indicators = await self._calculate_health_indicators(
                current_fingerprint, consistency_metrics
            )
            
            # Determine overall health status
            health_status = await self._determine_health_status(health_indicators)
            
            # Generate health recommendations
            recommendations = await self._generate_health_recommendations(
                health_indicators, health_status
            )
            
            health_report = {
                'health_check_id': f"health_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'timestamp': datetime.now().isoformat(),
                'overall_health_status': health_status,
                'health_score': health_indicators.get('overall_health_score', 0.5),
                'health_indicators': health_indicators,
                'consistency_metrics': {
                    'overall_consistency': consistency_metrics.overall_consistency,
                    'trend_direction': consistency_metrics.trend_direction,
                    'violations_count': len(consistency_metrics.violations)
                },
                'recommendations': recommendations,
                'monitoring_level': self.monitoring_level.value,
                'monitoring_stats': self.monitoring_stats.copy()
            }
            
            logger.info(f"Voice health check completed: {health_status}")
            return health_report
            
        except Exception as e:
            logger.error(f"Voice health check failed: {str(e)}")
            return {
                'health_check_id': f"health_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'timestamp': datetime.now().isoformat(),
                'overall_health_status': 'unknown',
                'error': str(e)
            }
    
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """
        Get current monitoring status.
        
        Returns:
            Monitoring status information
        """
        uptime = (datetime.now() - self.last_check_time).total_seconds() / 3600
        self.monitoring_stats['monitoring_uptime_hours'] = uptime
        
        recent_metrics = list(self.consistency_history)[-10:] if self.consistency_history else []
        
        return {
            'monitoring_level': self.monitoring_level.value,
            'configuration': self.config.copy(),
            'statistics': self.monitoring_stats.copy(),
            'status': {
                'is_active': True,
                'last_check': self.last_check_time.isoformat(),
                'baseline_set': self.baseline_fingerprint is not None,
                'history_size': len(self.consistency_history),
                'recent_average_consistency': (
                    statistics.mean([m.overall_consistency for m in recent_metrics])
                    if recent_metrics else 0.0
                )
            },
            'alert_thresholds': self.alert_thresholds.copy()
        }
    
    # Private helper methods
    
    async def _check_vocabulary_consistency(
        self,
        current_fingerprint: VoiceFingerprint,
        baseline_fingerprint: VoiceFingerprint
    ) -> float:
        """Check vocabulary pattern consistency."""
        current_vocab = current_fingerprint.personal_patterns.get('vocabulary_patterns', {})
        baseline_vocab = baseline_fingerprint.personal_patterns.get('vocabulary_patterns', {})
        
        if not current_vocab or not baseline_vocab:
            return 0.5  # Neutral score if patterns missing
        
        # Compare common words
        current_words = set(current_vocab.get('common_words', []))
        baseline_words = set(baseline_vocab.get('common_words', []))
        
        if not current_words or not baseline_words:
            return 0.5
        
        # Calculate overlap
        overlap = len(current_words.intersection(baseline_words))
        total = len(current_words.union(baseline_words))
        
        consistency = overlap / total if total > 0 else 0.5
        return consistency
    
    async def _check_tone_consistency(
        self,
        current_fingerprint: VoiceFingerprint,
        baseline_fingerprint: VoiceFingerprint
    ) -> float:
        """Check tone pattern consistency."""
        current_tone = current_fingerprint.personal_patterns.get('tone_patterns', {})
        baseline_tone = baseline_fingerprint.personal_patterns.get('tone_patterns', {})
        
        if not current_tone or not baseline_tone:
            return 0.5
        
        # Compare tone aspects
        tone_aspects = ['formality', 'warmth', 'directness', 'enthusiasm']
        consistency_scores = []
        
        for aspect in tone_aspects:
            current_value = current_tone.get(aspect, 0.5)
            baseline_value = baseline_tone.get(aspect, 0.5)
            
            if isinstance(current_value, (int, float)) and isinstance(baseline_value, (int, float)):
                # Calculate similarity (1 - absolute difference)
                similarity = 1 - abs(current_value - baseline_value)
                consistency_scores.append(similarity)
        
        return statistics.mean(consistency_scores) if consistency_scores else 0.5
    
    async def _check_style_consistency(
        self,
        current_fingerprint: VoiceFingerprint,
        baseline_fingerprint: VoiceFingerprint
    ) -> float:
        """Check style pattern consistency."""
        current_style = current_fingerprint.personal_patterns.get('style_patterns', {})
        baseline_style = baseline_fingerprint.personal_patterns.get('style_patterns', {})
        
        if not current_style or not baseline_style:
            return 0.5
        
        # Compare punctuation patterns
        current_punct = current_style.get('punctuation_patterns', {})
        baseline_punct = baseline_style.get('punctuation_patterns', {})
        
        if not current_punct or not baseline_punct:
            return 0.5
        
        consistency_scores = []
        for punct_type in ['exclamation', 'question', 'ellipsis', 'comma']:
            current_freq = current_punct.get(punct_type, 0)
            baseline_freq = baseline_punct.get(punct_type, 0)
            
            # Calculate relative consistency
            if baseline_freq > 0:
                relative_diff = abs(current_freq - baseline_freq) / baseline_freq
                consistency = max(0, 1 - relative_diff)
                consistency_scores.append(consistency)
        
        return statistics.mean(consistency_scores) if consistency_scores else 0.5
    
    async def _check_structure_consistency(
        self,
        current_fingerprint: VoiceFingerprint,
        baseline_fingerprint: VoiceFingerprint
    ) -> float:
        """Check structural pattern consistency."""
        current_structure = current_fingerprint.personal_patterns.get('structural_patterns', {})
        baseline_structure = baseline_fingerprint.personal_patterns.get('structural_patterns', {})
        
        if not current_structure or not baseline_structure:
            return 0.5
        
        # Compare sentence length
        current_length = current_structure.get('avg_sentence_length', 0)
        baseline_length = baseline_structure.get('avg_sentence_length', 0)
        
        if baseline_length > 0:
            relative_diff = abs(current_length - baseline_length) / baseline_length
            consistency = max(0, 1 - relative_diff)
            return consistency
        
        return 0.5
    
    async def _check_formality_consistency(
        self,
        current_fingerprint: VoiceFingerprint,
        baseline_fingerprint: VoiceFingerprint
    ) -> float:
        """Check formality level consistency."""
        current_formality = current_fingerprint.personal_patterns.get('formality_level', 0.5)
        baseline_formality = baseline_fingerprint.personal_patterns.get('formality_level', 0.5)
        
        if isinstance(current_formality, (int, float)) and isinstance(baseline_formality, (int, float)):
            consistency = 1 - abs(current_formality - baseline_formality)
            return consistency
        
        return 0.5
    
    async def _check_engagement_consistency(
        self,
        current_fingerprint: VoiceFingerprint,
        baseline_fingerprint: VoiceFingerprint
    ) -> float:
        """Check engagement pattern consistency."""
        current_engagement = current_fingerprint.personal_patterns.get('engagement_patterns', {})
        baseline_engagement = baseline_fingerprint.personal_patterns.get('engagement_patterns', {})
        
        if not current_engagement or not baseline_engagement:
            return 0.5
        
        # Compare engagement indicators
        engagement_aspects = ['question_frequency', 'exclamation_usage', 'personal_references']
        consistency_scores = []
        
        for aspect in engagement_aspects:
            current_value = current_engagement.get(aspect, 0)
            baseline_value = baseline_engagement.get(aspect, 0)
            
            if baseline_value > 0:
                relative_diff = abs(current_value - baseline_value) / baseline_value
                consistency = max(0, 1 - relative_diff)
                consistency_scores.append(consistency)
        
        return statistics.mean(consistency_scores) if consistency_scores else 0.5
    
    async def _identify_violations(self, dimension_scores: Dict[str, float]) -> List[str]:
        """Identify consistency violations."""
        violations = []
        threshold = self.config['consistency_threshold']
        
        for dimension, score in dimension_scores.items():
            if score < threshold:
                severity = 'critical' if score < 0.4 else 'warning' if score < 0.6 else 'minor'
                violations.append(f"{severity.upper()}: {dimension} below threshold ({score:.3f} < {threshold})")
        
        return violations
    
    async def _generate_alerts(
        self,
        overall_consistency: float,
        violations: List[str]
    ) -> List[Dict[str, Any]]:
        """Generate alerts based on consistency issues."""
        alerts = []
        
        # Overall consistency alert
        if overall_consistency < self.alert_thresholds['critical']:
            alerts.append({
                'level': 'critical',
                'type': 'overall_consistency',
                'message': f"Critical consistency violation: {overall_consistency:.3f}",
                'timestamp': datetime.now().isoformat(),
                'recommended_action': 'Immediate review and potential rollback required'
            })
        elif overall_consistency < self.alert_thresholds['warning']:
            alerts.append({
                'level': 'warning',
                'type': 'overall_consistency',
                'message': f"Consistency warning: {overall_consistency:.3f}",
                'timestamp': datetime.now().isoformat(),
                'recommended_action': 'Review recent changes and monitor closely'
            })
        
        # Violation-specific alerts
        for violation in violations:
            if 'CRITICAL' in violation:
                alerts.append({
                    'level': 'critical',
                    'type': 'dimension_violation',
                    'message': violation,
                    'timestamp': datetime.now().isoformat(),
                    'recommended_action': 'Investigate specific dimension issue'
                })
            elif 'WARNING' in violation:
                alerts.append({
                    'level': 'warning',
                    'type': 'dimension_violation',
                    'message': violation,
                    'timestamp': datetime.now().isoformat(),
                    'recommended_action': 'Monitor dimension for further degradation'
                })
        
        return alerts
    
    async def _calculate_consistency_trend(self) -> Dict[str, Any]:
        """Calculate consistency trend from recent history."""
        if len(self.consistency_history) < 3:
            return {'direction': 'unknown', 'strength': 0.0}
        
        # Get recent consistency scores
        recent_scores = [m.overall_consistency for m in list(self.consistency_history)[-10:]]
        
        # Calculate simple trend
        if len(recent_scores) >= 3:
            # Linear trend calculation
            x_values = list(range(len(recent_scores)))
            n = len(recent_scores)
            
            x_mean = sum(x_values) / n
            y_mean = sum(recent_scores) / n
            
            numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, recent_scores))
            denominator = sum((x - x_mean) ** 2 for x in x_values)
            
            if denominator > 0:
                slope = numerator / denominator
                
                # Determine direction and strength
                if slope > self.config['trend_sensitivity']:
                    direction = 'improving'
                elif slope < -self.config['trend_sensitivity']:
                    direction = 'declining'
                else:
                    direction = 'stable'
                
                strength = min(1.0, abs(slope) * 10)  # Scale slope to 0-1
                
                return {'direction': direction, 'strength': strength}
        
        return {'direction': 'stable', 'strength': 0.0}
    
    async def _calculate_health_indicators(
        self,
        current_fingerprint: VoiceFingerprint,
        consistency_metrics: ConsistencyMetrics
    ) -> Dict[str, Any]:
        """Calculate voice health indicators."""
        indicators = {}
        
        # Consistency health
        indicators['consistency_health'] = consistency_metrics.overall_consistency
        
        # Confidence health
        avg_confidence = sum(current_fingerprint.confidence_scores.values()) / len(current_fingerprint.confidence_scores)
        indicators['confidence_health'] = avg_confidence
        
        # Trend health
        trend_health = 1.0  # Default healthy
        if consistency_metrics.trend_direction == 'declining':
            trend_health = max(0.3, 1.0 - consistency_metrics.trend_strength)
        elif consistency_metrics.trend_direction == 'improving':
            trend_health = min(1.0, 0.7 + consistency_metrics.trend_strength * 0.3)
        
        indicators['trend_health'] = trend_health
        
        # Violation health
        violation_count = len(consistency_metrics.violations)
        violation_health = max(0.0, 1.0 - (violation_count * 0.2))
        indicators['violation_health'] = violation_health
        
        # Overall health score
        indicators['overall_health_score'] = (
            indicators['consistency_health'] * 0.4 +
            indicators['confidence_health'] * 0.3 +
            indicators['trend_health'] * 0.2 +
            indicators['violation_health'] * 0.1
        )
        
        return indicators
    
    async def _determine_health_status(self, health_indicators: Dict[str, Any]) -> str:
        """Determine overall health status."""
        overall_score = health_indicators.get('overall_health_score', 0.5)
        
        if overall_score >= 0.9:
            return 'excellent'
        elif overall_score >= 0.8:
            return 'good'
        elif overall_score >= 0.6:
            return 'fair'
        elif overall_score >= 0.4:
            return 'poor'
        else:
            return 'critical'
    
    async def _generate_health_recommendations(
        self,
        health_indicators: Dict[str, Any],
        health_status: str
    ) -> List[str]:
        """Generate health improvement recommendations."""
        recommendations = []
        
        if health_indicators.get('consistency_health', 1.0) < 0.7:
            recommendations.append("Review voice consistency patterns and consider baseline adjustment")
        
        if health_indicators.get('confidence_health', 1.0) < 0.7:
            recommendations.append("Improve voice pattern confidence through additional training data")
        
        if health_indicators.get('trend_health', 1.0) < 0.7:
            recommendations.append("Monitor voice evolution trends and consider intervention")
        
        if health_indicators.get('violation_health', 1.0) < 0.7:
            recommendations.append("Address specific consistency violations in voice patterns")
        
        if health_status in ['poor', 'critical']:
            recommendations.append("Consider voice pattern rollback or comprehensive review")
        
        if not recommendations:
            recommendations.append("Voice health is good - continue current monitoring")
        
        return recommendations
