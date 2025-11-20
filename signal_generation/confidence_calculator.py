"""
Confidence Calculator for Multi-Timeframe Signals

Calculates confidence level for aggregated signals based on:
1. Timeframe consensus (agreement across timeframes)
2. Score quality (signal strength)
3. Direction clarity (bullish vs bearish margin)
4. HTF alignment (higher timeframe confirmation)

Confidence Levels:
- HIGH (90%+): All TFs agree, strong signals
- MEDIUM (70-89%): Majority agree, decent signals
- LOW (<70%): Weak consensus or signals

Purpose: Quantify uncertainty in multi-TF aggregated signals
"""

from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceMetrics:
    """Metrics used to calculate confidence."""
    timeframe_consensus: float  # 0.0-1.0
    score_quality: float  # 0.0-1.0
    direction_clarity: float  # 0.0-1.0
    htf_alignment: float  # 0.0-1.0
    volume_confirmation: float  # 0.0-1.0

    overall_confidence: float  # 0.0-1.0 (final)
    confidence_level: str  # 'HIGH', 'MEDIUM', 'LOW'

    # Flags
    is_uncertain: bool  # True if balanced/conflicting
    requires_review: bool  # True if borderline


class ConfidenceCalculator:
    """
    Calculates confidence levels for multi-timeframe signals.

    Uses multiple factors to quantify signal quality and certainty:
    - Timeframe consensus: How many TFs agree on direction
    - Score quality: Average signal strength
    - Direction clarity: Margin between bullish/bearish
    - HTF alignment: Higher timeframe confirmation
    - Volume confirmation: Volume support
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize ConfidenceCalculator.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Confidence thresholds
        confidence_config = self.config.get('confidence', {})
        self.high_threshold = confidence_config.get('high_threshold', 0.90)
        self.medium_threshold = confidence_config.get('medium_threshold', 0.70)

        # Weights for each factor
        self.weights = confidence_config.get('weights', {
            'timeframe_consensus': 0.35,
            'score_quality': 0.25,
            'direction_clarity': 0.20,
            'htf_alignment': 0.15,
            'volume_confirmation': 0.05
        })

        # Uncertainty detection
        self.balanced_margin = confidence_config.get('balanced_margin', 0.05)  # 5%

        logger.info(f"ConfidenceCalculator initialized (high>={self.high_threshold}, medium>={self.medium_threshold})")

    def calculate_confidence(
        self,
        timeframe_signals: Dict[str, Any],
        final_direction: str,
        bullish_score: float,
        bearish_score: float
    ) -> ConfidenceMetrics:
        """
        Calculate overall confidence for multi-TF aggregated signal.

        Args:
            timeframe_signals: Dict of {timeframe: signal_data}
            final_direction: Final aggregated direction ('LONG', 'SHORT', 'NEUTRAL')
            bullish_score: Aggregated bullish score
            bearish_score: Aggregated bearish score

        Returns:
            ConfidenceMetrics with all calculated metrics
        """
        # 1. Timeframe Consensus
        tf_consensus = self._calculate_timeframe_consensus(
            timeframe_signals,
            final_direction
        )

        # 2. Score Quality
        score_quality = self._calculate_score_quality(timeframe_signals)

        # 3. Direction Clarity
        direction_clarity = self._calculate_direction_clarity(
            bullish_score,
            bearish_score,
            final_direction
        )

        # 4. HTF Alignment
        htf_alignment = self._calculate_htf_alignment(
            timeframe_signals,
            final_direction
        )

        # 5. Volume Confirmation
        volume_confirmation = self._calculate_volume_confirmation(timeframe_signals)

        # 6. Calculate weighted overall confidence
        overall_confidence = (
            tf_consensus * self.weights['timeframe_consensus'] +
            score_quality * self.weights['score_quality'] +
            direction_clarity * self.weights['direction_clarity'] +
            htf_alignment * self.weights['htf_alignment'] +
            volume_confirmation * self.weights['volume_confirmation']
        )

        # 7. Determine confidence level
        if overall_confidence >= self.high_threshold:
            confidence_level = 'HIGH'
        elif overall_confidence >= self.medium_threshold:
            confidence_level = 'MEDIUM'
        else:
            confidence_level = 'LOW'

        # 8. Check for uncertainty flags
        is_uncertain = self._check_if_uncertain(
            bullish_score,
            bearish_score,
            tf_consensus
        )

        requires_review = (
            is_uncertain or
            overall_confidence < self.medium_threshold or
            final_direction == 'NEUTRAL'
        )

        return ConfidenceMetrics(
            timeframe_consensus=tf_consensus,
            score_quality=score_quality,
            direction_clarity=direction_clarity,
            htf_alignment=htf_alignment,
            volume_confirmation=volume_confirmation,
            overall_confidence=overall_confidence,
            confidence_level=confidence_level,
            is_uncertain=is_uncertain,
            requires_review=requires_review
        )

    def _calculate_timeframe_consensus(
        self,
        timeframe_signals: Dict[str, Any],
        final_direction: str
    ) -> float:
        """
        Calculate timeframe consensus (0.0-1.0).

        Measures how many timeframes agree with final direction.

        Returns:
            Consensus score: 1.0 = all agree, 0.0 = none agree
        """
        if not timeframe_signals or final_direction == 'NEUTRAL':
            return 0.0

        agreeing_count = 0
        total_count = len(timeframe_signals)

        for tf_data in timeframe_signals.values():
            tf_direction = tf_data.get('direction', 'NEUTRAL')
            if tf_direction == final_direction:
                agreeing_count += 1

        consensus = agreeing_count / total_count if total_count > 0 else 0.0

        logger.debug(f"Timeframe consensus: {agreeing_count}/{total_count} = {consensus:.2%}")

        return consensus

    def _calculate_score_quality(
        self,
        timeframe_signals: Dict[str, Any]
    ) -> float:
        """
        Calculate average score quality (0.0-1.0).

        Based on signal strength across timeframes.

        Returns:
            Quality score: 1.0 = excellent, 0.0 = poor
        """
        if not timeframe_signals:
            return 0.0

        # Collect scores
        scores = []
        for tf_data in timeframe_signals.values():
            score = tf_data.get('score', 0)
            # Normalize score (assuming 0-100 scale) to 0-1
            normalized = min(max(score / 100.0, 0.0), 1.0)
            scores.append(normalized)

        # Average quality
        avg_quality = sum(scores) / len(scores) if scores else 0.0

        logger.debug(f"Score quality: {avg_quality:.2%} (avg of {len(scores)} scores)")

        return avg_quality

    def _calculate_direction_clarity(
        self,
        bullish_score: float,
        bearish_score: float,
        final_direction: str
    ) -> float:
        """
        Calculate direction clarity (0.0-1.0).

        Measures how clear the direction is based on score difference.

        Returns:
            Clarity score: 1.0 = very clear, 0.0 = very unclear
        """
        if final_direction == 'NEUTRAL':
            return 0.0

        total_score = bullish_score + bearish_score
        if total_score == 0:
            return 0.0

        # Calculate difference ratio
        diff = abs(bullish_score - bearish_score)
        clarity = diff / total_score if total_score > 0 else 0.0

        # Normalize: 0-0.5 diff → 0.0-1.0 clarity
        # (50%+ difference = max clarity)
        clarity = min(clarity * 2.0, 1.0)

        logger.debug(
            f"Direction clarity: {clarity:.2%} "
            f"(bullish={bullish_score:.2f}, bearish={bearish_score:.2f})"
        )

        return clarity

    def _calculate_htf_alignment(
        self,
        timeframe_signals: Dict[str, Any],
        final_direction: str
    ) -> float:
        """
        Calculate higher timeframe alignment (0.0-1.0).

        Checks if higher timeframes (1h, 4h) agree with direction.

        Returns:
            Alignment score: 1.0 = HTF fully aligned, 0.0 = not aligned
        """
        if not timeframe_signals or final_direction == 'NEUTRAL':
            return 0.0

        # Define HTF priority (higher = more important)
        htf_priority = {
            '4h': 2.0,
            '1h': 1.5,
            '15m': 1.0,
            '5m': 0.5
        }

        aligned_weight = 0.0
        total_weight = 0.0

        for tf, tf_data in timeframe_signals.items():
            weight = htf_priority.get(tf, 1.0)
            total_weight += weight

            if tf_data.get('direction') == final_direction:
                aligned_weight += weight

        alignment = aligned_weight / total_weight if total_weight > 0 else 0.0

        logger.debug(f"HTF alignment: {alignment:.2%}")

        return alignment

    def _calculate_volume_confirmation(
        self,
        timeframe_signals: Dict[str, Any]
    ) -> float:
        """
        Calculate volume confirmation (0.0-1.0).

        Checks how many timeframes have volume confirmation.

        Returns:
            Confirmation score: 1.0 = all confirmed, 0.0 = none confirmed
        """
        if not timeframe_signals:
            return 0.0

        confirmed_count = 0
        total_count = len(timeframe_signals)

        for tf_data in timeframe_signals.values():
            if tf_data.get('volume_confirmed', False):
                confirmed_count += 1

        confirmation = confirmed_count / total_count if total_count > 0 else 0.0

        logger.debug(f"Volume confirmation: {confirmed_count}/{total_count} = {confirmation:.2%}")

        return confirmation

    def _check_if_uncertain(
        self,
        bullish_score: float,
        bearish_score: float,
        tf_consensus: float
    ) -> bool:
        """
        Check if signal is uncertain/balanced.

        Returns:
            True if signal is too balanced or conflicting
        """
        # Check if scores are too balanced
        total = bullish_score + bearish_score
        if total > 0:
            diff_ratio = abs(bullish_score - bearish_score) / total
            if diff_ratio < self.balanced_margin:
                logger.debug(f"Signal is uncertain: balanced scores (diff={diff_ratio:.1%})")
                return True

        # Check if TF consensus is too low
        if tf_consensus < 0.5:  # Less than 50% agreement
            logger.debug(f"Signal is uncertain: low TF consensus ({tf_consensus:.1%})")
            return True

        return False

    def format_confidence_report(
        self,
        metrics: ConfidenceMetrics,
        include_details: bool = True
    ) -> str:
        """
        Format confidence metrics into readable report.

        Args:
            metrics: ConfidenceMetrics to format
            include_details: Include detailed breakdown

        Returns:
            Formatted string report
        """
        report = []

        # Header
        report.append(f"Confidence Level: {metrics.confidence_level} ({metrics.overall_confidence:.1%})")

        if include_details:
            report.append("\nBreakdown:")
            report.append(f"  • Timeframe Consensus: {metrics.timeframe_consensus:.1%}")
            report.append(f"  • Score Quality: {metrics.score_quality:.1%}")
            report.append(f"  • Direction Clarity: {metrics.direction_clarity:.1%}")
            report.append(f"  • HTF Alignment: {metrics.htf_alignment:.1%}")
            report.append(f"  • Volume Confirmation: {metrics.volume_confirmation:.1%}")

        # Flags
        if metrics.is_uncertain:
            report.append("\n⚠️  Warning: Signal is uncertain (balanced/conflicting)")

        if metrics.requires_review:
            report.append("📌 Recommendation: Requires manual review")

        return "\n".join(report)
