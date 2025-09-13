"""Voice drift detector for identifying and preventing voice pattern drift."""

import logging
import statistics
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque

from ..protocols.voice_monitoring_protocol import (
    DriftDetectionProtocol,
    VoiceDriftAlert,
    DriftSeverity
)
from ...voice.voice_fingerprint_extractor import VoiceFingerprint

logger = logging.getLogger(__name__)


class VoiceDriftDetector(DriftDetectionProtocol):
    """
    Voice drift detector that identifies gradual changes in voice patterns
    that may indicate unwanted drift from the user's authentic voice.
    
    This detector specializes in:
    - Gradual drift detection using statistical analysis
    - Sudden change detection for immediate alerts
    - Pattern-specific drift analysis across voice dimensions
    - Corrective action recommendations
    """
    
    def __init__(self):
        """Initialize voice drift detector."""
        # Drift detection configuration
        self.drift_config = {
            'baseline_window_days': 7,        # Days to establish baseline
            'detection_window_hours': 24,     # Hours for drift detection
            'gradual_drift_threshold': 0.15,  # Threshold for gradual drift
            'sudden_change_threshold': 0.25,  # Threshold for sudden changes
            'min_samples_for_detection': 5,   # Minimum samples needed
            'drift_confirmation_samples': 3,  # Samples to confirm drift
            'max_history_size': 1000          # Maximum history to maintain
        }
        
        # Pattern history for drift detection
        self.pattern_history: deque = deque(maxlen=self.drift_config['max_history_size'])
        self.baseline_patterns: Optional[Dict[str, Any]] = None
        self.baseline_established_at: Optional[datetime] = None
        
        # Drift tracking
        self.active_drifts: Dict[str, VoiceDriftAlert] = {}
        self.drift_history: List[VoiceDriftAlert] = []
        
        # Pattern analyzers for different drift types
        self.drift_analyzers = {
            'vocabulary_drift': self._analyze_vocabulary_drift,
            'tone_drift': self._analyze_tone_drift,
            'style_drift': self._analyze_style_drift,
            'formality_drift': self._analyze_formality_drift,
            'engagement_drift': self._analyze_engagement_drift,
            'confidence_drift': self._analyze_confidence_drift
        }
        
        # Drift statistics
        self.drift_stats = {
            'total_detections': 0,
            'gradual_drifts': 0,
            'sudden_changes': 0,
            'false_positives': 0,
            'corrections_applied': 0,
            'baseline_resets': 0
        }
    
    async def detect_drift(
        self,
        current_fingerprint: VoiceFingerprint,
        baseline_fingerprint: Optional[VoiceFingerprint] = None
    ) -> List[VoiceDriftAlert]:
        """
        Detect voice pattern drift.
        
        Args:
            current_fingerprint: Current voice fingerprint
            baseline_fingerprint: Optional baseline fingerprint
            
        Returns:
            List of drift alerts
        """
        try:
            # Establish or update baseline
            if baseline_fingerprint:
                await self._update_baseline(baseline_fingerprint)
            elif not self.baseline_patterns:
                await self._establish_baseline(current_fingerprint)
                return []  # No drift detection on first baseline
            
            # Add current patterns to history
            await self._add_to_history(current_fingerprint)
            
            # Check if we have enough data for detection
            if len(self.pattern_history) < self.drift_config['min_samples_for_detection']:
                return []
            
            # Perform drift analysis
            drift_alerts = []
            
            for analyzer_name, analyzer_func in self.drift_analyzers.items():
                alerts = await analyzer_func(current_fingerprint)
                drift_alerts.extend(alerts)
            
            # Update active drifts
            await self._update_active_drifts(drift_alerts)
            
            # Filter and prioritize alerts
            significant_alerts = await self._filter_significant_alerts(drift_alerts)
            
            # Update statistics
            self.drift_stats['total_detections'] += len(significant_alerts)
            for alert in significant_alerts:
                if alert.drift_type == 'gradual':
                    self.drift_stats['gradual_drifts'] += 1
                elif alert.drift_type == 'sudden':
                    self.drift_stats['sudden_changes'] += 1
            
            # Store alerts in history
            self.drift_history.extend(significant_alerts)
            
            logger.info(f"Drift detection completed: {len(significant_alerts)} alerts generated")
            return significant_alerts
            
        except Exception as e:
            logger.error(f"Drift detection failed: {str(e)}")
            return []
    
    async def analyze_drift_patterns(
        self,
        time_window: Optional[Tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """
        Analyze drift patterns over time.
        
        Args:
            time_window: Optional time window for analysis
            
        Returns:
            Drift pattern analysis
        """
        try:
            # Filter alerts by time window
            if time_window:
                start_time, end_time = time_window
                filtered_alerts = [
                    alert for alert in self.drift_history
                    if start_time <= alert.timestamp <= end_time
                ]
            else:
                filtered_alerts = self.drift_history
            
            if not filtered_alerts:
                return {'no_data': True, 'message': 'No drift alerts in specified time window'}
            
            # Analyze drift frequency
            drift_frequency = await self._analyze_drift_frequency(filtered_alerts)
            
            # Analyze drift severity distribution
            severity_distribution = await self._analyze_severity_distribution(filtered_alerts)
            
            # Analyze drift patterns by type
            type_analysis = await self._analyze_drift_by_type(filtered_alerts)
            
            # Analyze drift trends
            drift_trends = await self._analyze_drift_trends(filtered_alerts)
            
            # Identify recurring patterns
            recurring_patterns = await self._identify_recurring_patterns(filtered_alerts)
            
            # Calculate drift impact
            drift_impact = await self._calculate_drift_impact(filtered_alerts)
            
            analysis = {
                'analysis_period': {
                    'start': time_window[0].isoformat() if time_window else filtered_alerts[0].timestamp.isoformat(),
                    'end': time_window[1].isoformat() if time_window else filtered_alerts[-1].timestamp.isoformat(),
                    'alerts_analyzed': len(filtered_alerts)
                },
                'drift_frequency': drift_frequency,
                'severity_distribution': severity_distribution,
                'type_analysis': type_analysis,
                'drift_trends': drift_trends,
                'recurring_patterns': recurring_patterns,
                'drift_impact': drift_impact,
                'recommendations': await self._generate_drift_recommendations(filtered_alerts),
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Drift pattern analysis completed: {len(filtered_alerts)} alerts analyzed")
            return analysis
            
        except Exception as e:
            logger.error(f"Drift pattern analysis failed: {str(e)}")
            return {'error': f'Analysis failed: {str(e)}'}
    
    async def recommend_corrections(
        self,
        drift_alerts: List[VoiceDriftAlert],
        current_fingerprint: VoiceFingerprint
    ) -> List[Dict[str, Any]]:
        """
        Recommend corrections for detected drift.
        
        Args:
            drift_alerts: List of drift alerts
            current_fingerprint: Current voice fingerprint
            
        Returns:
            List of correction recommendations
        """
        recommendations = []
        
        try:
            # Group alerts by pattern type
            alerts_by_pattern = defaultdict(list)
            for alert in drift_alerts:
                alerts_by_pattern[alert.pattern_affected].append(alert)
            
            # Generate recommendations for each pattern type
            for pattern_type, pattern_alerts in alerts_by_pattern.items():
                recommendation = await self._create_pattern_correction_recommendation(
                    pattern_type, pattern_alerts, current_fingerprint
                )
                recommendations.append(recommendation)
            
            # Add general recommendations based on severity
            high_severity_alerts = [a for a in drift_alerts if a.severity in [DriftSeverity.HIGH, DriftSeverity.CRITICAL]]
            if high_severity_alerts:
                general_recommendation = await self._create_general_correction_recommendation(
                    high_severity_alerts, current_fingerprint
                )
                recommendations.append(general_recommendation)
            
            # Sort by priority
            recommendations.sort(key=lambda x: x.get('priority_score', 0.5), reverse=True)
            
            logger.info(f"Correction recommendations generated: {len(recommendations)}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Correction recommendation failed: {str(e)}")
            return []
    
    # Private helper methods
    
    async def _establish_baseline(self, fingerprint: VoiceFingerprint) -> None:
        """Establish baseline patterns from fingerprint."""
        self.baseline_patterns = await self._extract_baseline_patterns(fingerprint)
        self.baseline_established_at = datetime.now()
        self.drift_stats['baseline_resets'] += 1
        logger.info("Baseline patterns established")
    
    async def _update_baseline(self, fingerprint: VoiceFingerprint) -> None:
        """Update baseline patterns with new fingerprint."""
        new_patterns = await self._extract_baseline_patterns(fingerprint)
        
        if self.baseline_patterns:
            # Blend with existing baseline (weighted average)
            blended_patterns = await self._blend_baseline_patterns(
                self.baseline_patterns, new_patterns, weight=0.3
            )
            self.baseline_patterns = blended_patterns
        else:
            self.baseline_patterns = new_patterns
        
        self.baseline_established_at = datetime.now()
        logger.debug("Baseline patterns updated")
    
    async def _extract_baseline_patterns(self, fingerprint: VoiceFingerprint) -> Dict[str, Any]:
        """Extract baseline patterns from fingerprint."""
        return {
            'vocabulary': fingerprint.personal_patterns.get('vocabulary_patterns', {}),
            'tone': fingerprint.personal_patterns.get('tone_patterns', {}),
            'style': fingerprint.personal_patterns.get('style_patterns', {}),
            'formality': fingerprint.personal_patterns.get('formality_level', 0.5),
            'engagement': fingerprint.personal_patterns.get('engagement_patterns', {}),
            'confidence': fingerprint.confidence_scores.copy(),
            'timestamp': datetime.now().isoformat()
        }
    
    async def _blend_baseline_patterns(
        self,
        existing_patterns: Dict[str, Any],
        new_patterns: Dict[str, Any],
        weight: float = 0.3
    ) -> Dict[str, Any]:
        """Blend baseline patterns with new patterns."""
        blended = existing_patterns.copy()
        
        # Blend numeric values
        for key in ['formality']:
            if key in existing_patterns and key in new_patterns:
                if isinstance(existing_patterns[key], (int, float)) and isinstance(new_patterns[key], (int, float)):
                    blended[key] = existing_patterns[key] * (1 - weight) + new_patterns[key] * weight
        
        # Blend confidence scores
        if 'confidence' in existing_patterns and 'confidence' in new_patterns:
            blended_confidence = {}
            for key in existing_patterns['confidence']:
                if key in new_patterns['confidence']:
                    blended_confidence[key] = (
                        existing_patterns['confidence'][key] * (1 - weight) +
                        new_patterns['confidence'][key] * weight
                    )
                else:
                    blended_confidence[key] = existing_patterns['confidence'][key]
            blended['confidence'] = blended_confidence
        
        blended['timestamp'] = datetime.now().isoformat()
        return blended
    
    async def _add_to_history(self, fingerprint: VoiceFingerprint) -> None:
        """Add fingerprint patterns to history."""
        patterns = await self._extract_baseline_patterns(fingerprint)
        self.pattern_history.append(patterns)
    
    async def _analyze_vocabulary_drift(self, current_fingerprint: VoiceFingerprint) -> List[VoiceDriftAlert]:
        """Analyze vocabulary drift."""
        alerts = []
        
        current_vocab = current_fingerprint.personal_patterns.get('vocabulary_patterns', {})
        baseline_vocab = self.baseline_patterns.get('vocabulary', {})
        
        if not current_vocab or not baseline_vocab:
            return alerts
        
        # Compare common words
        current_words = set(current_vocab.get('common_words', []))
        baseline_words = set(baseline_vocab.get('common_words', []))
        
        if current_words and baseline_words:
            overlap = len(current_words.intersection(baseline_words))
            total = len(current_words.union(baseline_words))
            similarity = overlap / total if total > 0 else 1.0
            
            drift_magnitude = 1 - similarity
            
            if drift_magnitude > self.drift_config['sudden_change_threshold']:
                alerts.append(VoiceDriftAlert(
                    timestamp=datetime.now(),
                    pattern_affected='vocabulary',
                    drift_type='sudden',
                    severity=DriftSeverity.HIGH if drift_magnitude > 0.4 else DriftSeverity.MEDIUM,
                    drift_magnitude=drift_magnitude,
                    description=f"Sudden vocabulary change detected: {drift_magnitude:.3f} drift",
                    recommended_actions=['Review vocabulary changes', 'Consider vocabulary pattern adjustment'],
                    confidence=0.8
                ))
            elif drift_magnitude > self.drift_config['gradual_drift_threshold']:
                alerts.append(VoiceDriftAlert(
                    timestamp=datetime.now(),
                    pattern_affected='vocabulary',
                    drift_type='gradual',
                    severity=DriftSeverity.MEDIUM if drift_magnitude > 0.25 else DriftSeverity.LOW,
                    drift_magnitude=drift_magnitude,
                    description=f"Gradual vocabulary drift detected: {drift_magnitude:.3f} drift",
                    recommended_actions=['Monitor vocabulary evolution', 'Consider baseline update'],
                    confidence=0.7
                ))
        
        return alerts
    
    async def _analyze_tone_drift(self, current_fingerprint: VoiceFingerprint) -> List[VoiceDriftAlert]:
        """Analyze tone drift."""
        alerts = []
        
        current_tone = current_fingerprint.personal_patterns.get('tone_patterns', {})
        baseline_tone = self.baseline_patterns.get('tone', {})
        
        if not current_tone or not baseline_tone:
            return alerts
        
        # Analyze tone aspects
        tone_aspects = ['formality', 'warmth', 'directness', 'enthusiasm']
        drift_scores = []
        
        for aspect in tone_aspects:
            current_value = current_tone.get(aspect, 0.5)
            baseline_value = baseline_tone.get(aspect, 0.5)
            
            if isinstance(current_value, (int, float)) and isinstance(baseline_value, (int, float)):
                drift = abs(current_value - baseline_value)
                drift_scores.append(drift)
        
        if drift_scores:
            avg_drift = statistics.mean(drift_scores)
            max_drift = max(drift_scores)
            
            if max_drift > self.drift_config['sudden_change_threshold']:
                alerts.append(VoiceDriftAlert(
                    timestamp=datetime.now(),
                    pattern_affected='tone',
                    drift_type='sudden',
                    severity=DriftSeverity.HIGH if max_drift > 0.4 else DriftSeverity.MEDIUM,
                    drift_magnitude=max_drift,
                    description=f"Sudden tone change detected: {max_drift:.3f} maximum drift",
                    recommended_actions=['Review tone calibration', 'Check context adaptation settings'],
                    confidence=0.8
                ))
            elif avg_drift > self.drift_config['gradual_drift_threshold']:
                alerts.append(VoiceDriftAlert(
                    timestamp=datetime.now(),
                    pattern_affected='tone',
                    drift_type='gradual',
                    severity=DriftSeverity.MEDIUM if avg_drift > 0.2 else DriftSeverity.LOW,
                    drift_magnitude=avg_drift,
                    description=f"Gradual tone drift detected: {avg_drift:.3f} average drift",
                    recommended_actions=['Monitor tone evolution', 'Consider tone pattern adjustment'],
                    confidence=0.7
                ))
        
        return alerts
    
    async def _analyze_style_drift(self, current_fingerprint: VoiceFingerprint) -> List[VoiceDriftAlert]:
        """Analyze style drift."""
        alerts = []
        
        current_style = current_fingerprint.personal_patterns.get('style_patterns', {})
        baseline_style = self.baseline_patterns.get('style', {})
        
        if not current_style or not baseline_style:
            return alerts
        
        # Analyze punctuation patterns
        current_punct = current_style.get('punctuation_patterns', {})
        baseline_punct = baseline_style.get('punctuation_patterns', {})
        
        if current_punct and baseline_punct:
            drift_scores = []
            
            for punct_type in ['exclamation', 'question', 'ellipsis']:
                current_freq = current_punct.get(punct_type, 0)
                baseline_freq = baseline_punct.get(punct_type, 0)
                
                if baseline_freq > 0:
                    relative_change = abs(current_freq - baseline_freq) / baseline_freq
                    drift_scores.append(relative_change)
            
            if drift_scores:
                avg_drift = statistics.mean(drift_scores)
                
                if avg_drift > self.drift_config['sudden_change_threshold']:
                    alerts.append(VoiceDriftAlert(
                        timestamp=datetime.now(),
                        pattern_affected='style',
                        drift_type='sudden',
                        severity=DriftSeverity.MEDIUM,
                        drift_magnitude=avg_drift,
                        description=f"Sudden style change detected: {avg_drift:.3f} punctuation drift",
                        recommended_actions=['Review style patterns', 'Check punctuation usage'],
                        confidence=0.7
                    ))
                elif avg_drift > self.drift_config['gradual_drift_threshold']:
                    alerts.append(VoiceDriftAlert(
                        timestamp=datetime.now(),
                        pattern_affected='style',
                        drift_type='gradual',
                        severity=DriftSeverity.LOW,
                        drift_magnitude=avg_drift,
                        description=f"Gradual style drift detected: {avg_drift:.3f} punctuation drift",
                        recommended_actions=['Monitor style evolution'],
                        confidence=0.6
                    ))
        
        return alerts
    
    async def _analyze_formality_drift(self, current_fingerprint: VoiceFingerprint) -> List[VoiceDriftAlert]:
        """Analyze formality drift."""
        alerts = []
        
        current_formality = current_fingerprint.personal_patterns.get('formality_level', 0.5)
        baseline_formality = self.baseline_patterns.get('formality', 0.5)
        
        if isinstance(current_formality, (int, float)) and isinstance(baseline_formality, (int, float)):
            drift = abs(current_formality - baseline_formality)
            
            if drift > self.drift_config['sudden_change_threshold']:
                alerts.append(VoiceDriftAlert(
                    timestamp=datetime.now(),
                    pattern_affected='formality',
                    drift_type='sudden',
                    severity=DriftSeverity.MEDIUM,
                    drift_magnitude=drift,
                    description=f"Sudden formality change detected: {drift:.3f} drift",
                    recommended_actions=['Review formality settings', 'Check context adaptation'],
                    confidence=0.8
                ))
            elif drift > self.drift_config['gradual_drift_threshold']:
                alerts.append(VoiceDriftAlert(
                    timestamp=datetime.now(),
                    pattern_affected='formality',
                    drift_type='gradual',
                    severity=DriftSeverity.LOW,
                    drift_magnitude=drift,
                    description=f"Gradual formality drift detected: {drift:.3f} drift",
                    recommended_actions=['Monitor formality evolution'],
                    confidence=0.7
                ))
        
        return alerts
    
    async def _analyze_engagement_drift(self, current_fingerprint: VoiceFingerprint) -> List[VoiceDriftAlert]:
        """Analyze engagement drift."""
        alerts = []
        
        current_engagement = current_fingerprint.personal_patterns.get('engagement_patterns', {})
        baseline_engagement = self.baseline_patterns.get('engagement', {})
        
        if not current_engagement or not baseline_engagement:
            return alerts
        
        # Analyze engagement aspects
        engagement_aspects = ['question_frequency', 'exclamation_usage', 'personal_references']
        drift_scores = []
        
        for aspect in engagement_aspects:
            current_value = current_engagement.get(aspect, 0)
            baseline_value = baseline_engagement.get(aspect, 0)
            
            if baseline_value > 0:
                relative_change = abs(current_value - baseline_value) / baseline_value
                drift_scores.append(relative_change)
        
        if drift_scores:
            avg_drift = statistics.mean(drift_scores)
            
            if avg_drift > self.drift_config['gradual_drift_threshold']:
                severity = DriftSeverity.MEDIUM if avg_drift > 0.25 else DriftSeverity.LOW
                drift_type = 'sudden' if avg_drift > self.drift_config['sudden_change_threshold'] else 'gradual'
                
                alerts.append(VoiceDriftAlert(
                    timestamp=datetime.now(),
                    pattern_affected='engagement',
                    drift_type=drift_type,
                    severity=severity,
                    drift_magnitude=avg_drift,
                    description=f"{drift_type.title()} engagement drift detected: {avg_drift:.3f} drift",
                    recommended_actions=['Review engagement patterns', 'Monitor interaction style'],
                    confidence=0.6
                ))
        
        return alerts
    
    async def _analyze_confidence_drift(self, current_fingerprint: VoiceFingerprint) -> List[VoiceDriftAlert]:
        """Analyze confidence drift."""
        alerts = []
        
        current_confidence = current_fingerprint.confidence_scores
        baseline_confidence = self.baseline_patterns.get('confidence', {})
        
        if not current_confidence or not baseline_confidence:
            return alerts
        
        # Calculate average confidence changes
        confidence_changes = []
        for key in current_confidence:
            if key in baseline_confidence:
                change = abs(current_confidence[key] - baseline_confidence[key])
                confidence_changes.append(change)
        
        if confidence_changes:
            avg_change = statistics.mean(confidence_changes)
            max_change = max(confidence_changes)
            
            if max_change > self.drift_config['sudden_change_threshold']:
                alerts.append(VoiceDriftAlert(
                    timestamp=datetime.now(),
                    pattern_affected='confidence',
                    drift_type='sudden',
                    severity=DriftSeverity.HIGH if max_change > 0.4 else DriftSeverity.MEDIUM,
                    drift_magnitude=max_change,
                    description=f"Sudden confidence change detected: {max_change:.3f} maximum change",
                    recommended_actions=['Review confidence patterns', 'Check data quality'],
                    confidence=0.8
                ))
            elif avg_change > self.drift_config['gradual_drift_threshold']:
                alerts.append(VoiceDriftAlert(
                    timestamp=datetime.now(),
                    pattern_affected='confidence',
                    drift_type='gradual',
                    severity=DriftSeverity.MEDIUM if avg_change > 0.2 else DriftSeverity.LOW,
                    drift_magnitude=avg_change,
                    description=f"Gradual confidence drift detected: {avg_change:.3f} average change",
                    recommended_actions=['Monitor confidence evolution', 'Consider pattern adjustment'],
                    confidence=0.7
                ))
        
        return alerts
    
    async def _update_active_drifts(self, new_alerts: List[VoiceDriftAlert]) -> None:
        """Update active drift tracking."""
        # Remove resolved drifts (no new alerts for same pattern)
        current_patterns = {alert.pattern_affected for alert in new_alerts}
        resolved_patterns = set(self.active_drifts.keys()) - current_patterns
        
        for pattern in resolved_patterns:
            del self.active_drifts[pattern]
        
        # Update active drifts with new alerts
        for alert in new_alerts:
            self.active_drifts[alert.pattern_affected] = alert
    
    async def _filter_significant_alerts(self, alerts: List[VoiceDriftAlert]) -> List[VoiceDriftAlert]:
        """Filter alerts to only include significant ones."""
        significant_alerts = []
        
        for alert in alerts:
            # Filter by severity
            if alert.severity in [DriftSeverity.MEDIUM, DriftSeverity.HIGH, DriftSeverity.CRITICAL]:
                significant_alerts.append(alert)
            # Include low severity if drift magnitude is significant
            elif alert.severity == DriftSeverity.LOW and alert.drift_magnitude > 0.2:
                significant_alerts.append(alert)
        
        return significant_alerts
    
    async def _analyze_drift_frequency(self, alerts: List[VoiceDriftAlert]) -> Dict[str, Any]:
        """Analyze drift frequency patterns."""
        if not alerts:
            return {'no_data': True}
        
        # Group by time periods
        daily_counts = defaultdict(int)
        hourly_counts = defaultdict(int)
        
        for alert in alerts:
            day_key = alert.timestamp.strftime('%Y-%m-%d')
            hour_key = alert.timestamp.strftime('%Y-%m-%d %H:00')
            daily_counts[day_key] += 1
            hourly_counts[hour_key] += 1
        
        return {
            'total_alerts': len(alerts),
            'daily_average': statistics.mean(daily_counts.values()) if daily_counts else 0,
            'peak_day': max(daily_counts.items(), key=lambda x: x[1]) if daily_counts else None,
            'hourly_average': statistics.mean(hourly_counts.values()) if hourly_counts else 0,
            'peak_hour': max(hourly_counts.items(), key=lambda x: x[1]) if hourly_counts else None
        }
    
    async def _analyze_severity_distribution(self, alerts: List[VoiceDriftAlert]) -> Dict[str, int]:
        """Analyze distribution of alert severities."""
        distribution = defaultdict(int)
        
        for alert in alerts:
            distribution[alert.severity.value] += 1
        
        return dict(distribution)
    
    async def _analyze_drift_by_type(self, alerts: List[VoiceDriftAlert]) -> Dict[str, Any]:
        """Analyze drift patterns by type."""
        type_analysis = defaultdict(lambda: {'count': 0, 'avg_magnitude': 0, 'severities': defaultdict(int)})
        
        for alert in alerts:
            pattern = alert.pattern_affected
            type_analysis[pattern]['count'] += 1
            type_analysis[pattern]['severities'][alert.severity.value] += 1
        
        # Calculate average magnitudes
        for pattern in type_analysis:
            pattern_alerts = [a for a in alerts if a.pattern_affected == pattern]
            if pattern_alerts:
                type_analysis[pattern]['avg_magnitude'] = statistics.mean([a.drift_magnitude for a in pattern_alerts])
        
        return dict(type_analysis)
    
    async def _analyze_drift_trends(self, alerts: List[VoiceDriftAlert]) -> Dict[str, Any]:
        """Analyze drift trends over time."""
        if len(alerts) < 3:
            return {'insufficient_data': True}
        
        # Sort by timestamp
        sorted_alerts = sorted(alerts, key=lambda x: x.timestamp)
        
        # Calculate trend in drift magnitude
        magnitudes = [alert.drift_magnitude for alert in sorted_alerts]
        
        # Simple linear trend
        n = len(magnitudes)
        x_values = list(range(n))
        x_mean = sum(x_values) / n
        y_mean = sum(magnitudes) / n
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, magnitudes))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator > 0:
            slope = numerator / denominator
            trend_direction = 'increasing' if slope > 0.01 else 'decreasing' if slope < -0.01 else 'stable'
        else:
            slope = 0
            trend_direction = 'stable'
        
        return {
            'trend_direction': trend_direction,
            'trend_slope': slope,
            'average_magnitude': statistics.mean(magnitudes),
            'magnitude_volatility': statistics.stdev(magnitudes) if len(magnitudes) > 1 else 0
        }
    
    async def _identify_recurring_patterns(self, alerts: List[VoiceDriftAlert]) -> List[Dict[str, Any]]:
        """Identify recurring drift patterns."""
        patterns = []
        
        # Group by pattern type and analyze frequency
        pattern_counts = defaultdict(int)
        for alert in alerts:
            pattern_counts[alert.pattern_affected] += 1
        
        # Identify patterns that occur frequently
        total_alerts = len(alerts)
        for pattern, count in pattern_counts.items():
            frequency = count / total_alerts
            if frequency > 0.3:  # Pattern occurs in >30% of alerts
                patterns.append({
                    'pattern': pattern,
                    'frequency': frequency,
                    'count': count,
                    'significance': 'high' if frequency > 0.5 else 'medium'
                })
        
        return sorted(patterns, key=lambda x: x['frequency'], reverse=True)
    
    async def _calculate_drift_impact(self, alerts: List[VoiceDriftAlert]) -> Dict[str, Any]:
        """Calculate overall impact of drift."""
        if not alerts:
            return {'no_impact': True}
        
        # Calculate severity-weighted impact
        severity_weights = {
            DriftSeverity.LOW: 0.2,
            DriftSeverity.MEDIUM: 0.5,
            DriftSeverity.HIGH: 0.8,
            DriftSeverity.CRITICAL: 1.0
        }
        
        total_impact = sum(severity_weights.get(alert.severity, 0.5) * alert.drift_magnitude for alert in alerts)
        average_impact = total_impact / len(alerts)
        
        # Calculate pattern diversity impact
        unique_patterns = len(set(alert.pattern_affected for alert in alerts))
        pattern_diversity_impact = min(1.0, unique_patterns / 6)  # 6 total pattern types
        
        return {
            'total_impact_score': total_impact,
            'average_impact_score': average_impact,
            'pattern_diversity_impact': pattern_diversity_impact,
            'overall_impact_level': (
                'critical' if average_impact > 0.7 else
                'high' if average_impact > 0.5 else
                'medium' if average_impact > 0.3 else
                'low'
            )
        }
    
    async def _generate_drift_recommendations(self, alerts: List[VoiceDriftAlert]) -> List[str]:
        """Generate recommendations based on drift analysis."""
        recommendations = []
        
        if not alerts:
            recommendations.append("No drift detected - continue current monitoring")
            return recommendations
        
        # High-level recommendations based on impact
        high_severity_count = len([a for a in alerts if a.severity in [DriftSeverity.HIGH, DriftSeverity.CRITICAL]])
        
        if high_severity_count > 0:
            recommendations.append("High-severity drift detected - consider immediate intervention")
        
        # Pattern-specific recommendations
        pattern_counts = defaultdict(int)
        for alert in alerts:
            pattern_counts[alert.pattern_affected] += 1
        
        for pattern, count in pattern_counts.items():
            if count > 1:
                recommendations.append(f"Multiple {pattern} drift alerts - review {pattern} patterns")
        
        # Trend-based recommendations
        if len(alerts) > 3:
            recent_alerts = sorted(alerts, key=lambda x: x.timestamp)[-3:]
            if all(a.severity in [DriftSeverity.HIGH, DriftSeverity.CRITICAL] for a in recent_alerts):
                recommendations.append("Escalating drift severity - consider baseline reset")
        
        return recommendations
    
    async def _create_pattern_correction_recommendation(
        self,
        pattern_type: str,
        pattern_alerts: List[VoiceDriftAlert],
        current_fingerprint: VoiceFingerprint
    ) -> Dict[str, Any]:
        """Create correction recommendation for specific pattern."""
        avg_magnitude = statistics.mean([alert.drift_magnitude for alert in pattern_alerts])
        max_severity = max([alert.severity for alert in pattern_alerts])
        
        return {
            'pattern_type': pattern_type,
            'priority_score': avg_magnitude * 0.7 + (max_severity.value / 4) * 0.3,
            'description': f"Correct {pattern_type} drift (avg magnitude: {avg_magnitude:.3f})",
            'specific_actions': [
                f"Review {pattern_type} patterns in baseline",
                f"Adjust {pattern_type} adaptation parameters",
                f"Monitor {pattern_type} evolution closely"
            ],
            'estimated_effort': 'medium' if avg_magnitude > 0.3 else 'low',
            'confidence': statistics.mean([alert.confidence for alert in pattern_alerts])
        }
    
    async def _create_general_correction_recommendation(
        self,
        high_severity_alerts: List[VoiceDriftAlert],
        current_fingerprint: VoiceFingerprint
    ) -> Dict[str, Any]:
        """Create general correction recommendation for high-severity issues."""
        return {
            'pattern_type': 'general',
            'priority_score': 0.9,
            'description': f"Address {len(high_severity_alerts)} high-severity drift issues",
            'specific_actions': [
                "Consider voice pattern rollback",
                "Review recent learning activities",
                "Increase monitoring frequency",
                "Validate baseline patterns"
            ],
            'estimated_effort': 'high',
            'confidence': 0.8
        }
    
    def get_drift_statistics(self) -> Dict[str, Any]:
        """Get drift detection statistics."""
        return {
            'drift_stats': self.drift_stats.copy(),
            'active_drifts': len(self.active_drifts),
            'total_history': len(self.drift_history),
            'baseline_age_hours': (
                (datetime.now() - self.baseline_established_at).total_seconds() / 3600
                if self.baseline_established_at else 0
            ),
            'pattern_history_size': len(self.pattern_history),
            'configuration': self.drift_config.copy()
        }
