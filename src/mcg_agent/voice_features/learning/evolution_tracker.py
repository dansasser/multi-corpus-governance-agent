"""Evolution tracker for monitoring voice pattern evolution and regression detection."""

import logging
import statistics
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from ..protocols.voice_learning_protocol import (
    EvolutionTrackingProtocol,
    VoiceEvolutionRecord
)
from ...voice.voice_fingerprint_extractor import VoiceFingerprint

logger = logging.getLogger(__name__)


class EvolutionTracker(EvolutionTrackingProtocol):
    """
    Evolution tracker that monitors voice pattern changes over time
    and detects potential regressions or improvements.
    
    This tracker specializes in:
    - Detailed evolution record creation and analysis
    - Trend analysis across multiple evolution records
    - Regression detection with configurable thresholds
    - Rollback recommendations for quality preservation
    """
    
    def __init__(self):
        """Initialize evolution tracker."""
        # Evolution tracking configuration
        self.tracking_config = {
            'min_change_threshold': 0.05,      # Minimum change to track
            'regression_threshold': 0.15,      # Performance drop threshold
            'trend_window_days': 30,           # Days for trend analysis
            'min_records_for_trend': 5,        # Minimum records for trend analysis
            'performance_weight': 0.7,         # Weight for performance metrics
            'confidence_weight': 0.3           # Weight for confidence metrics
        }
        
        # Evolution history storage (in production, this would be persistent)
        self.evolution_history: List[VoiceEvolutionRecord] = []
        
        # Performance tracking
        self.performance_metrics = {
            'total_evolutions_tracked': 0,
            'regressions_detected': 0,
            'improvements_detected': 0,
            'rollbacks_recommended': 0
        }
        
        # Pattern change analysis
        self.pattern_analyzers = {
            'vocabulary_changes': self._analyze_vocabulary_changes,
            'tone_changes': self._analyze_tone_changes,
            'structure_changes': self._analyze_structure_changes,
            'style_changes': self._analyze_style_changes
        }
    
    async def track_evolution(
        self,
        old_fingerprint: VoiceFingerprint,
        new_fingerprint: VoiceFingerprint,
        trigger_event: str
    ) -> VoiceEvolutionRecord:
        """
        Track voice pattern evolution.
        
        Args:
            old_fingerprint: Previous voice fingerprint
            new_fingerprint: Updated voice fingerprint
            trigger_event: Event that triggered evolution
            
        Returns:
            Evolution record
        """
        try:
            # Analyze pattern changes
            pattern_changes = await self._analyze_pattern_changes(
                old_fingerprint, new_fingerprint
            )
            
            # Calculate confidence change
            confidence_change = await self._calculate_confidence_change(
                old_fingerprint, new_fingerprint
            )
            
            # Analyze performance impact
            performance_impact = await self._analyze_performance_impact(
                old_fingerprint, new_fingerprint, pattern_changes
            )
            
            # Create rollback data
            rollback_data = await self._create_rollback_data(old_fingerprint)
            
            # Create evolution record
            evolution_record = VoiceEvolutionRecord(
                timestamp=datetime.now(),
                pattern_changes=pattern_changes,
                trigger_event=trigger_event,
                confidence_change=confidence_change,
                performance_impact=performance_impact,
                rollback_data=rollback_data
            )
            
            # Store evolution record
            self.evolution_history.append(evolution_record)
            
            # Update metrics
            self.performance_metrics['total_evolutions_tracked'] += 1
            
            # Detect if this is an improvement or regression
            overall_impact = await self._calculate_overall_impact(performance_impact)
            if overall_impact > 0.1:
                self.performance_metrics['improvements_detected'] += 1
                logger.info(f"Voice improvement detected: {overall_impact:.2f}")
            elif overall_impact < -0.1:
                self.performance_metrics['regressions_detected'] += 1
                logger.warning(f"Voice regression detected: {overall_impact:.2f}")
            
            logger.debug(f"Evolution tracked: {trigger_event}, confidence change: {confidence_change:.3f}")
            return evolution_record
            
        except Exception as e:
            logger.error(f"Evolution tracking failed: {str(e)}")
            # Return minimal evolution record
            return VoiceEvolutionRecord(
                timestamp=datetime.now(),
                pattern_changes={'error': str(e)},
                trigger_event=trigger_event,
                confidence_change=0.0,
                performance_impact={'error': True}
            )
    
    async def analyze_evolution_trends(
        self,
        evolution_history: List[VoiceEvolutionRecord],
        time_window: Optional[Tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """
        Analyze voice evolution trends.
        
        Args:
            evolution_history: Historical evolution records
            time_window: Optional time window filter
            
        Returns:
            Evolution trend analysis
        """
        try:
            # Filter by time window if provided
            if time_window:
                start_time, end_time = time_window
                filtered_history = [
                    record for record in evolution_history
                    if start_time <= record.timestamp <= end_time
                ]
            else:
                filtered_history = evolution_history
            
            if len(filtered_history) < self.tracking_config['min_records_for_trend']:
                return {
                    'insufficient_data': True,
                    'records_available': len(filtered_history),
                    'records_needed': self.tracking_config['min_records_for_trend']
                }
            
            # Analyze confidence trends
            confidence_trend = await self._analyze_confidence_trend(filtered_history)
            
            # Analyze performance trends
            performance_trend = await self._analyze_performance_trend(filtered_history)
            
            # Analyze pattern change frequency
            pattern_frequency = await self._analyze_pattern_change_frequency(filtered_history)
            
            # Analyze trigger event patterns
            trigger_patterns = await self._analyze_trigger_patterns(filtered_history)
            
            # Calculate trend stability
            stability_metrics = await self._calculate_stability_metrics(filtered_history)
            
            # Identify concerning trends
            concerning_trends = await self._identify_concerning_trends(
                confidence_trend, performance_trend, stability_metrics
            )
            
            trend_analysis = {
                'analysis_period': {
                    'start': time_window[0].isoformat() if time_window else filtered_history[0].timestamp.isoformat(),
                    'end': time_window[1].isoformat() if time_window else filtered_history[-1].timestamp.isoformat(),
                    'records_analyzed': len(filtered_history)
                },
                'confidence_trend': confidence_trend,
                'performance_trend': performance_trend,
                'pattern_frequency': pattern_frequency,
                'trigger_patterns': trigger_patterns,
                'stability_metrics': stability_metrics,
                'concerning_trends': concerning_trends,
                'overall_trend_direction': await self._determine_overall_trend_direction(
                    confidence_trend, performance_trend
                ),
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Evolution trends analyzed: {len(filtered_history)} records")
            return trend_analysis
            
        except Exception as e:
            logger.error(f"Evolution trend analysis failed: {str(e)}")
            return {'error': f'Trend analysis failed: {str(e)}'}
    
    async def detect_regression(
        self,
        evolution_history: List[VoiceEvolutionRecord],
        performance_threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """
        Detect voice quality regression.
        
        Args:
            evolution_history: Historical evolution records
            performance_threshold: Minimum performance threshold
            
        Returns:
            List of detected regressions
        """
        regressions = []
        
        try:
            # Use recent history for regression detection
            recent_window = datetime.now() - timedelta(days=self.tracking_config['trend_window_days'])
            recent_history = [
                record for record in evolution_history
                if record.timestamp >= recent_window
            ]
            
            if len(recent_history) < 2:
                return regressions
            
            # Analyze performance trajectory
            performance_trajectory = await self._calculate_performance_trajectory(recent_history)
            
            # Detect significant drops
            for i, record in enumerate(recent_history[1:], 1):
                current_performance = await self._calculate_record_performance(record)
                previous_performance = await self._calculate_record_performance(recent_history[i-1])
                
                performance_drop = previous_performance - current_performance
                
                # Check if drop exceeds threshold
                if (performance_drop > self.tracking_config['regression_threshold'] or
                    current_performance < performance_threshold):
                    
                    regression = {
                        'regression_id': f"reg_{record.timestamp.strftime('%Y%m%d_%H%M%S')}",
                        'detected_at': record.timestamp.isoformat(),
                        'trigger_event': record.trigger_event,
                        'performance_drop': performance_drop,
                        'current_performance': current_performance,
                        'previous_performance': previous_performance,
                        'severity': await self._calculate_regression_severity(
                            performance_drop, current_performance
                        ),
                        'affected_patterns': await self._identify_affected_patterns(record),
                        'recommended_actions': await self._generate_regression_actions(record),
                        'rollback_available': record.rollback_data is not None
                    }
                    
                    regressions.append(regression)
            
            # Update metrics
            if regressions:
                self.performance_metrics['regressions_detected'] += len(regressions)
            
            logger.info(f"Regression detection completed: {len(regressions)} regressions found")
            return regressions
            
        except Exception as e:
            logger.error(f"Regression detection failed: {str(e)}")
            return []
    
    async def recommend_rollback(
        self,
        current_fingerprint: VoiceFingerprint,
        evolution_history: List[VoiceEvolutionRecord]
    ) -> Optional[VoiceFingerprint]:
        """
        Recommend rollback to previous voice state if needed.
        
        Args:
            current_fingerprint: Current voice fingerprint
            evolution_history: Historical evolution records
            
        Returns:
            Recommended rollback fingerprint or None
        """
        try:
            # Detect recent regressions
            regressions = await self.detect_regression(evolution_history)
            
            if not regressions:
                return None
            
            # Find the most recent severe regression
            severe_regressions = [
                reg for reg in regressions
                if reg.get('severity', 'low') in ['high', 'critical']
            ]
            
            if not severe_regressions:
                return None
            
            # Get the most recent severe regression
            latest_regression = max(severe_regressions, key=lambda x: x['detected_at'])
            
            # Find corresponding evolution record
            regression_record = None
            for record in evolution_history:
                if record.timestamp.isoformat() == latest_regression['detected_at']:
                    regression_record = record
                    break
            
            if not regression_record or not regression_record.rollback_data:
                return None
            
            # Create rollback fingerprint
            rollback_fingerprint = await self._create_rollback_fingerprint(
                current_fingerprint, regression_record.rollback_data
            )
            
            # Update metrics
            self.performance_metrics['rollbacks_recommended'] += 1
            
            logger.warning(f"Rollback recommended due to regression: {latest_regression['regression_id']}")
            return rollback_fingerprint
            
        except Exception as e:
            logger.error(f"Rollback recommendation failed: {str(e)}")
            return None
    
    # Private helper methods
    
    async def _analyze_pattern_changes(
        self,
        old_fingerprint: VoiceFingerprint,
        new_fingerprint: VoiceFingerprint
    ) -> Dict[str, Any]:
        """Analyze changes between voice fingerprints."""
        changes = {}
        
        # Analyze each pattern type
        for analyzer_name, analyzer_func in self.pattern_analyzers.items():
            pattern_changes = await analyzer_func(old_fingerprint, new_fingerprint)
            if pattern_changes:
                changes[analyzer_name] = pattern_changes
        
        # Overall change magnitude
        changes['overall_magnitude'] = await self._calculate_overall_change_magnitude(
            old_fingerprint, new_fingerprint
        )
        
        return changes
    
    async def _analyze_vocabulary_changes(
        self,
        old_fingerprint: VoiceFingerprint,
        new_fingerprint: VoiceFingerprint
    ) -> Dict[str, Any]:
        """Analyze vocabulary pattern changes."""
        changes = {}
        
        # Compare vocabulary patterns
        old_vocab = old_fingerprint.personal_patterns.get('vocabulary_patterns', {})
        new_vocab = new_fingerprint.personal_patterns.get('vocabulary_patterns', {})
        
        # Calculate vocabulary overlap
        if old_vocab and new_vocab:
            old_words = set(old_vocab.get('common_words', []))
            new_words = set(new_vocab.get('common_words', []))
            
            if old_words and new_words:
                overlap = len(old_words.intersection(new_words))
                total = len(old_words.union(new_words))
                changes['vocabulary_overlap'] = overlap / total if total > 0 else 0
                changes['new_words_added'] = len(new_words - old_words)
                changes['words_removed'] = len(old_words - new_words)
        
        return changes
    
    async def _analyze_tone_changes(
        self,
        old_fingerprint: VoiceFingerprint,
        new_fingerprint: VoiceFingerprint
    ) -> Dict[str, Any]:
        """Analyze tone pattern changes."""
        changes = {}
        
        # Compare tone patterns
        old_tone = old_fingerprint.personal_patterns.get('tone_patterns', {})
        new_tone = new_fingerprint.personal_patterns.get('tone_patterns', {})
        
        # Calculate tone shifts
        tone_aspects = ['formality', 'warmth', 'directness', 'enthusiasm']
        
        for aspect in tone_aspects:
            old_value = old_tone.get(aspect, 0.5)
            new_value = new_tone.get(aspect, 0.5)
            
            if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
                change = new_value - old_value
                if abs(change) > self.tracking_config['min_change_threshold']:
                    changes[f'{aspect}_change'] = change
        
        return changes
    
    async def _analyze_structure_changes(
        self,
        old_fingerprint: VoiceFingerprint,
        new_fingerprint: VoiceFingerprint
    ) -> Dict[str, Any]:
        """Analyze structure pattern changes."""
        changes = {}
        
        # Compare structural patterns
        old_structure = old_fingerprint.personal_patterns.get('structural_patterns', {})
        new_structure = new_fingerprint.personal_patterns.get('structural_patterns', {})
        
        # Analyze sentence length changes
        old_length = old_structure.get('avg_sentence_length', 0)
        new_length = new_structure.get('avg_sentence_length', 0)
        
        if old_length and new_length:
            length_change = (new_length - old_length) / old_length
            if abs(length_change) > self.tracking_config['min_change_threshold']:
                changes['sentence_length_change'] = length_change
        
        return changes
    
    async def _analyze_style_changes(
        self,
        old_fingerprint: VoiceFingerprint,
        new_fingerprint: VoiceFingerprint
    ) -> Dict[str, Any]:
        """Analyze style pattern changes."""
        changes = {}
        
        # Compare style patterns
        old_style = old_fingerprint.personal_patterns.get('style_patterns', {})
        new_style = new_fingerprint.personal_patterns.get('style_patterns', {})
        
        # Analyze punctuation changes
        old_punct = old_style.get('punctuation_patterns', {})
        new_punct = new_style.get('punctuation_patterns', {})
        
        if old_punct and new_punct:
            punct_changes = {}
            for punct_type in ['exclamation', 'question', 'ellipsis']:
                old_freq = old_punct.get(punct_type, 0)
                new_freq = new_punct.get(punct_type, 0)
                
                if old_freq > 0:
                    change = (new_freq - old_freq) / old_freq
                    if abs(change) > self.tracking_config['min_change_threshold']:
                        punct_changes[f'{punct_type}_frequency_change'] = change
            
            if punct_changes:
                changes['punctuation_changes'] = punct_changes
        
        return changes
    
    async def _calculate_confidence_change(
        self,
        old_fingerprint: VoiceFingerprint,
        new_fingerprint: VoiceFingerprint
    ) -> float:
        """Calculate overall confidence change."""
        old_avg = sum(old_fingerprint.confidence_scores.values()) / len(old_fingerprint.confidence_scores)
        new_avg = sum(new_fingerprint.confidence_scores.values()) / len(new_fingerprint.confidence_scores)
        
        return new_avg - old_avg
    
    async def _analyze_performance_impact(
        self,
        old_fingerprint: VoiceFingerprint,
        new_fingerprint: VoiceFingerprint,
        pattern_changes: Dict[str, Any]
    ) -> Dict[str, float]:
        """Analyze performance impact of changes."""
        impact = {}
        
        # Calculate impact based on confidence change
        confidence_change = await self._calculate_confidence_change(old_fingerprint, new_fingerprint)
        impact['confidence_impact'] = confidence_change
        
        # Calculate impact based on pattern stability
        overall_magnitude = pattern_changes.get('overall_magnitude', 0)
        impact['stability_impact'] = -overall_magnitude  # Negative because more change = less stability
        
        # Calculate overall performance impact
        impact['overall_impact'] = (
            impact['confidence_impact'] * self.tracking_config['confidence_weight'] +
            impact['stability_impact'] * self.tracking_config['performance_weight']
        )
        
        return impact
    
    async def _calculate_overall_change_magnitude(
        self,
        old_fingerprint: VoiceFingerprint,
        new_fingerprint: VoiceFingerprint
    ) -> float:
        """Calculate overall magnitude of changes."""
        total_changes = 0
        total_patterns = 0
        
        # Compare personal patterns
        for key, new_value in new_fingerprint.personal_patterns.items():
            old_value = old_fingerprint.personal_patterns.get(key)
            if old_value is not None:
                if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
                    change = abs(new_value - old_value)
                    total_changes += change
                    total_patterns += 1
                elif isinstance(old_value, list) and isinstance(new_value, list):
                    # Calculate list similarity
                    old_set = set(old_value)
                    new_set = set(new_value)
                    if old_set or new_set:
                        similarity = len(old_set.intersection(new_set)) / len(old_set.union(new_set))
                        total_changes += (1 - similarity)
                        total_patterns += 1
        
        return total_changes / total_patterns if total_patterns > 0 else 0
    
    async def _create_rollback_data(self, old_fingerprint: VoiceFingerprint) -> Dict[str, Any]:
        """Create rollback data for evolution record."""
        return {
            'personal_patterns': old_fingerprint.personal_patterns.copy(),
            'social_patterns': old_fingerprint.social_patterns.copy(),
            'published_patterns': old_fingerprint.published_patterns.copy(),
            'confidence_scores': old_fingerprint.confidence_scores.copy(),
            'metadata': old_fingerprint.metadata.copy(),
            'rollback_timestamp': datetime.now().isoformat()
        }
    
    async def _calculate_overall_impact(self, performance_impact: Dict[str, float]) -> float:
        """Calculate overall impact score."""
        return performance_impact.get('overall_impact', 0.0)
    
    async def _analyze_confidence_trend(self, evolution_history: List[VoiceEvolutionRecord]) -> Dict[str, Any]:
        """Analyze confidence trends over time."""
        confidence_changes = [record.confidence_change for record in evolution_history]
        
        return {
            'average_change': statistics.mean(confidence_changes),
            'trend_direction': 'improving' if statistics.mean(confidence_changes) > 0.01 else 
                             'declining' if statistics.mean(confidence_changes) < -0.01 else 'stable',
            'volatility': statistics.stdev(confidence_changes) if len(confidence_changes) > 1 else 0,
            'total_records': len(confidence_changes)
        }
    
    async def _analyze_performance_trend(self, evolution_history: List[VoiceEvolutionRecord]) -> Dict[str, Any]:
        """Analyze performance trends over time."""
        performance_impacts = [
            record.performance_impact.get('overall_impact', 0) 
            for record in evolution_history
        ]
        
        return {
            'average_impact': statistics.mean(performance_impacts),
            'trend_direction': 'improving' if statistics.mean(performance_impacts) > 0.01 else
                             'declining' if statistics.mean(performance_impacts) < -0.01 else 'stable',
            'volatility': statistics.stdev(performance_impacts) if len(performance_impacts) > 1 else 0,
            'positive_changes': len([x for x in performance_impacts if x > 0]),
            'negative_changes': len([x for x in performance_impacts if x < 0])
        }
    
    async def _analyze_pattern_change_frequency(self, evolution_history: List[VoiceEvolutionRecord]) -> Dict[str, Any]:
        """Analyze frequency of different pattern changes."""
        pattern_counts = defaultdict(int)
        
        for record in evolution_history:
            for pattern_type in record.pattern_changes.keys():
                pattern_counts[pattern_type] += 1
        
        total_records = len(evolution_history)
        
        return {
            'most_frequent_changes': dict(sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:5]),
            'change_frequencies': {k: v/total_records for k, v in pattern_counts.items()},
            'total_pattern_types': len(pattern_counts)
        }
    
    async def _analyze_trigger_patterns(self, evolution_history: List[VoiceEvolutionRecord]) -> Dict[str, Any]:
        """Analyze patterns in trigger events."""
        trigger_counts = defaultdict(int)
        
        for record in evolution_history:
            trigger_counts[record.trigger_event] += 1
        
        return {
            'most_common_triggers': dict(sorted(trigger_counts.items(), key=lambda x: x[1], reverse=True)),
            'trigger_diversity': len(trigger_counts),
            'total_triggers': len(evolution_history)
        }
    
    async def _calculate_stability_metrics(self, evolution_history: List[VoiceEvolutionRecord]) -> Dict[str, Any]:
        """Calculate stability metrics."""
        if len(evolution_history) < 2:
            return {'insufficient_data': True}
        
        # Calculate time between evolutions
        time_deltas = []
        for i in range(1, len(evolution_history)):
            delta = (evolution_history[i].timestamp - evolution_history[i-1].timestamp).total_seconds() / 3600
            time_deltas.append(delta)
        
        return {
            'average_time_between_evolutions_hours': statistics.mean(time_deltas),
            'evolution_frequency_stability': statistics.stdev(time_deltas) if len(time_deltas) > 1 else 0,
            'total_evolution_span_days': (evolution_history[-1].timestamp - evolution_history[0].timestamp).days
        }
    
    async def _identify_concerning_trends(
        self,
        confidence_trend: Dict[str, Any],
        performance_trend: Dict[str, Any],
        stability_metrics: Dict[str, Any]
    ) -> List[str]:
        """Identify concerning trends."""
        concerns = []
        
        if confidence_trend.get('trend_direction') == 'declining':
            concerns.append('Declining confidence trend detected')
        
        if performance_trend.get('trend_direction') == 'declining':
            concerns.append('Declining performance trend detected')
        
        if confidence_trend.get('volatility', 0) > 0.2:
            concerns.append('High confidence volatility detected')
        
        if performance_trend.get('volatility', 0) > 0.3:
            concerns.append('High performance volatility detected')
        
        negative_ratio = performance_trend.get('negative_changes', 0) / max(performance_trend.get('positive_changes', 1), 1)
        if negative_ratio > 2:
            concerns.append('More negative than positive changes detected')
        
        return concerns
    
    async def _determine_overall_trend_direction(
        self,
        confidence_trend: Dict[str, Any],
        performance_trend: Dict[str, Any]
    ) -> str:
        """Determine overall trend direction."""
        conf_direction = confidence_trend.get('trend_direction', 'stable')
        perf_direction = performance_trend.get('trend_direction', 'stable')
        
        if conf_direction == 'improving' and perf_direction == 'improving':
            return 'strongly_improving'
        elif conf_direction == 'improving' or perf_direction == 'improving':
            return 'improving'
        elif conf_direction == 'declining' and perf_direction == 'declining':
            return 'strongly_declining'
        elif conf_direction == 'declining' or perf_direction == 'declining':
            return 'declining'
        else:
            return 'stable'
    
    async def _calculate_performance_trajectory(self, evolution_history: List[VoiceEvolutionRecord]) -> List[float]:
        """Calculate performance trajectory over time."""
        return [
            record.performance_impact.get('overall_impact', 0)
            for record in evolution_history
        ]
    
    async def _calculate_record_performance(self, record: VoiceEvolutionRecord) -> float:
        """Calculate performance score for a single record."""
        return record.performance_impact.get('overall_impact', 0) + 0.5  # Normalize to 0-1 range
    
    async def _calculate_regression_severity(self, performance_drop: float, current_performance: float) -> str:
        """Calculate regression severity."""
        if performance_drop > 0.3 or current_performance < 0.3:
            return 'critical'
        elif performance_drop > 0.2 or current_performance < 0.5:
            return 'high'
        elif performance_drop > 0.1 or current_performance < 0.7:
            return 'medium'
        else:
            return 'low'
    
    async def _identify_affected_patterns(self, record: VoiceEvolutionRecord) -> List[str]:
        """Identify patterns affected by regression."""
        return list(record.pattern_changes.keys())
    
    async def _generate_regression_actions(self, record: VoiceEvolutionRecord) -> List[str]:
        """Generate recommended actions for regression."""
        actions = []
        
        if record.rollback_data:
            actions.append('Consider rollback to previous state')
        
        actions.append('Review recent changes and feedback')
        actions.append('Increase monitoring frequency')
        
        if 'vocabulary_changes' in record.pattern_changes:
            actions.append('Review vocabulary pattern changes')
        
        if 'tone_changes' in record.pattern_changes:
            actions.append('Review tone adaptation settings')
        
        return actions
    
    async def _create_rollback_fingerprint(
        self,
        current_fingerprint: VoiceFingerprint,
        rollback_data: Dict[str, Any]
    ) -> VoiceFingerprint:
        """Create rollback fingerprint from rollback data."""
        return VoiceFingerprint(
            user_id=current_fingerprint.user_id,
            personal_patterns=rollback_data.get('personal_patterns', {}),
            social_patterns=rollback_data.get('social_patterns', {}),
            published_patterns=rollback_data.get('published_patterns', {}),
            created_at=current_fingerprint.created_at,
            updated_at=datetime.now(),
            confidence_scores=rollback_data.get('confidence_scores', {}),
            metadata={
                **rollback_data.get('metadata', {}),
                'rollback_applied': True,
                'rollback_timestamp': datetime.now().isoformat(),
                'original_rollback_timestamp': rollback_data.get('rollback_timestamp')
            }
        )
    
    def get_tracking_statistics(self) -> Dict[str, Any]:
        """Get evolution tracking statistics."""
        return {
            'performance_metrics': self.performance_metrics.copy(),
            'total_records': len(self.evolution_history),
            'tracking_config': self.tracking_config.copy(),
            'recent_activity': len([
                record for record in self.evolution_history
                if (datetime.now() - record.timestamp).days <= 7
            ])
        }
