"""
نسخه جدید PatternAnalyzer که از PatternOrchestrator استفاده می‌کند.

این فایل به عنوان یک wrapper برای PatternOrchestrator عمل می‌کند
تا سازگاری با کد موجود را حفظ کند.
"""

from typing import Dict, Any, List, Optional
import logging
import pandas as pd

from signal_generation.analyzers.base_analyzer import BaseAnalyzer
from signal_generation.context import AnalysisContext
from signal_generation.analyzers.patterns.pattern_orchestrator import PatternOrchestrator

# Import all pattern classes
from signal_generation.analyzers.patterns.candlestick import (
    HammerPattern,
    InvertedHammerPattern,
    EngulfingPattern,
    MorningStarPattern,
    PiercingLinePattern,
    ThreeWhiteSoldiersPattern,
    MorningDojiStarPattern,
    ShootingStarPattern,
    HangingManPattern,
    EveningStarPattern,
    DarkCloudCoverPattern,
    ThreeBlackCrowsPattern,
    EveningDojiStarPattern,
    DojiPattern,
    HaramiPattern,
    HaramiCrossPattern,
    # Phase 1 - New powerful patterns
    MarubozuPattern,
    DragonflyDojiPattern,
    GravestoneDojiPattern,
    SpinningTopPattern,
    LongLeggedDojiPattern,
    # Phase 2 - Continuation and confirmation patterns
    ThreeInsidePattern,
    ThreeOutsidePattern,
    BeltHoldPattern,
    ThreeMethodsPattern,
    MatHoldPattern,
    # Phase 3 - High priority missing patterns (2025-11-18)
    TweezerPattern,
    AbandonedBabyPattern,
    KickingPattern,
)

from signal_generation.analyzers.patterns.chart import (
    DoubleTopBottomPattern,
    HeadShouldersPattern,
    TrianglePattern,
    WedgePattern,
    FlagPennantPattern,
)

logger = logging.getLogger(__name__)


class PatternAnalyzer(BaseAnalyzer):
    """
    Analyzes candlestick and chart patterns using PatternOrchestrator.

    This is a wrapper around PatternOrchestrator that maintains
    compatibility with the existing codebase.

    Key features:
    1. Uses PatternOrchestrator for pattern detection
    2. Registers all available patterns
    3. Context-aware scoring
    4. Pattern prioritization
    5. Confidence calculation
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize PatternAnalyzer.

        Args:
            config: Configuration dictionary
        """
        super().__init__(config)

        # Get pattern-specific configuration
        pattern_config = config.get('pattern', {})

        # Default parameters (can be overridden per-TF)
        self.default_min_pattern_strength = 1

        # Fallback values
        self.min_pattern_strength = self.default_min_pattern_strength

        # Enable/disable
        self.enabled = config.get('analyzers', {}).get('pattern', {}).get('enabled', True)

        # Initialize PatternOrchestrator
        self.orchestrator = PatternOrchestrator(config)

        # Register all candlestick patterns
        self._register_candlestick_patterns()

        # Register all chart patterns
        self._register_chart_patterns()

        logger.info(
            f"PatternAnalyzer initialized with {len(self.orchestrator.candlestick_patterns)} "
            f"candlestick patterns and {len(self.orchestrator.chart_patterns)} chart patterns"
        )

    def _register_candlestick_patterns(self):
        """Register all candlestick pattern detectors."""
        candlestick_classes = [
            HammerPattern,
            InvertedHammerPattern,
            EngulfingPattern,
            MorningStarPattern,
            PiercingLinePattern,
            ThreeWhiteSoldiersPattern,
            MorningDojiStarPattern,
            ShootingStarPattern,
            HangingManPattern,
            EveningStarPattern,
            DarkCloudCoverPattern,
            ThreeBlackCrowsPattern,
            EveningDojiStarPattern,
            DojiPattern,
            HaramiPattern,
            HaramiCrossPattern,
            # Phase 1 - New powerful patterns
            MarubozuPattern,
            DragonflyDojiPattern,
            GravestoneDojiPattern,
            SpinningTopPattern,
            LongLeggedDojiPattern,
            # Phase 2 - Continuation and confirmation patterns
            ThreeInsidePattern,
            ThreeOutsidePattern,
            BeltHoldPattern,
            ThreeMethodsPattern,
            MatHoldPattern,
            # Phase 3 - High priority missing patterns (2025-11-18)
            TweezerPattern,
            AbandonedBabyPattern,
            KickingPattern,
        ]

        for pattern_class in candlestick_classes:
            try:
                self.orchestrator.register_pattern(pattern_class)
            except Exception as e:
                logger.error(f"Error registering candlestick pattern {pattern_class.__name__}: {e}")

    def _register_chart_patterns(self):
        """Register all chart pattern detectors."""
        chart_classes = [
            DoubleTopBottomPattern,
            HeadShouldersPattern,
            TrianglePattern,
            WedgePattern,
            FlagPennantPattern,
        ]

        for pattern_class in chart_classes:
            try:
                self.orchestrator.register_pattern(pattern_class)
            except Exception as e:
                logger.error(f"Error registering chart pattern {pattern_class.__name__}: {e}")

    def analyze(self, context: AnalysisContext) -> None:
        """
        Main analysis method - detects patterns using orchestrator.

        Args:
            context: AnalysisContext with pre-calculated indicators
        """
        # 1. Check if enabled
        if not self._check_enabled():
            logger.debug(f"PatternAnalyzer disabled for {context.symbol}")
            return

        # 2. Validate context
        if not self._validate_context(context):
            logger.warning(f"PatternAnalyzer: Invalid context for {context.symbol}")
            return

        try:
            # 3. Get per-TF parameters
            self.min_pattern_strength = self.get_threshold('min_pattern_strength', self.default_min_pattern_strength, context.timeframe)

            # 4. Read data
            df = context.df

            # Ensure we have enough data
            if len(df) < 20:
                logger.warning(f"Insufficient data for PatternAnalyzer on {context.symbol}")
                context.add_result('patterns', {
                    'status': 'insufficient_data',
                    'candlestick_patterns': [],
                    'chart_patterns': []
                })
                return

            # 5. Get context for context-aware scoring
            trend_context = context.get_result('trend')
            momentum_context = context.get_result('momentum')
            volume_context = context.get_result('volume')

            # Build context dict for orchestrator
            analysis_context = {
                'trend': trend_context,
                'momentum': momentum_context,
                'volume': volume_context
            }

            # 6. Detect all patterns using orchestrator
            all_patterns = self.orchestrator.detect_all_patterns(
                df=df,
                timeframe=context.timeframe,
                context=analysis_context
            )

            # 7. Separate candlestick and chart patterns
            candlestick_patterns = [p for p in all_patterns if p['type'] == 'candlestick']
            chart_patterns = [p for p in all_patterns if p['type'] == 'chart']

            # 8. Apply context-aware scoring adjustments
            candlestick_patterns = self._adjust_pattern_scores(
                candlestick_patterns,
                trend_context,
                momentum_context,
                volume_context
            )

            chart_patterns = self._adjust_pattern_scores(
                chart_patterns,
                trend_context,
                momentum_context,
                volume_context
            )

            # 9. Combine all patterns
            all_patterns = candlestick_patterns + chart_patterns

            # 10. Find strongest pattern
            strongest = max(all_patterns, key=lambda p: p['adjusted_strength']) if all_patterns else None

            # 11. Calculate overall pattern strength
            pattern_strength = self._calculate_pattern_strength(all_patterns)

            # 12. Check alignment with trend
            alignment = self._check_trend_alignment(all_patterns, trend_context)

            # 13. Calculate confidence
            confidence = self._calculate_confidence(
                all_patterns,
                alignment,
                volume_context
            )

            # 14. Build result
            result = {
                'status': 'ok',
                'candlestick_patterns': candlestick_patterns,
                'chart_patterns': chart_patterns,
                'total_patterns': len(all_patterns),
                'strongest_pattern': strongest,
                'pattern_strength': pattern_strength,
                'alignment_with_trend': alignment,
                'confidence': confidence,
                'context_aware': trend_context is not None,
                'orchestrator_stats': self.orchestrator.get_stats()
            }

            # 15. Store in context
            context.add_result('patterns', result)

            logger.info(
                f"PatternAnalyzer completed for {context.symbol} {context.timeframe}: "
                f"{len(all_patterns)} patterns (candlestick={len(candlestick_patterns)}, "
                f"chart={len(chart_patterns)}), strength={pattern_strength:.2f}, "
                f"confidence={confidence:.2f}"
            )

        except Exception as e:
            logger.error(f"Error in PatternAnalyzer for {context.symbol}: {e}", exc_info=True)
            context.add_result('patterns', {
                'status': 'error',
                'candlestick_patterns': [],
                'chart_patterns': [],
                'error': str(e)
            })

    def _adjust_pattern_scores(
        self,
        patterns: List[Dict[str, Any]],
        trend_context: Optional[Dict],
        momentum_context: Optional[Dict],
        volume_context: Optional[Dict]
    ) -> List[Dict[str, Any]]:
        """
        Adjust pattern scores based on context (context-aware scoring).

        Args:
            patterns: List of detected patterns
            trend_context: Trend analyzer results
            momentum_context: Momentum analyzer results
            volume_context: Volume analyzer results

        Returns:
            Patterns with adjusted scores
        """
        for pattern in patterns:
            multiplier = 1.0

            # Trend alignment bonus
            if trend_context:
                trend_direction = trend_context.get('direction', 'neutral')
                pattern_direction = pattern['direction']

                if trend_direction == pattern_direction:
                    multiplier *= 1.5  # 50% bonus for trend alignment
                    pattern['trend_aligned'] = True
                elif trend_direction == 'neutral':
                    multiplier *= 1.0
                else:
                    multiplier *= 0.7  # Penalty for going against trend
                    pattern['trend_aligned'] = False

            # Momentum confirmation
            if momentum_context:
                momentum_direction = momentum_context.get('direction', 'neutral')
                if momentum_direction == pattern['direction']:
                    multiplier *= 1.2
                    pattern['momentum_confirmed'] = True
                else:
                    pattern['momentum_confirmed'] = False

            # Volume confirmation
            if volume_context:
                if volume_context.get('is_confirmed', False):
                    multiplier *= 1.3
                    pattern['volume_confirmed'] = True
                else:
                    pattern['volume_confirmed'] = False

            # NEW v3.0.0: Apply recency multiplier
            # If pattern was detected in recent candles (not current), apply decay
            recency_multiplier = pattern.get('recency_multiplier', 1.0)
            multiplier *= recency_multiplier

            # Apply multiplier
            pattern['adjusted_strength'] = pattern['base_strength'] * multiplier
            pattern['score_multiplier'] = multiplier

        return patterns

    def _calculate_pattern_strength(self, patterns: List[Dict[str, Any]]) -> float:
        """
        Calculate overall pattern strength.

        Args:
            patterns: List of all patterns

        Returns:
            Overall strength (0-3)
        """
        if not patterns:
            return 0.0

        # Average of adjusted strengths
        total_strength = sum(p['adjusted_strength'] for p in patterns)
        avg_strength = total_strength / len(patterns)

        return min(avg_strength, 3.0)

    def _check_trend_alignment(
        self,
        patterns: List[Dict[str, Any]],
        trend_context: Optional[Dict]
    ) -> bool:
        """
        Check if patterns are aligned with trend.

        Args:
            patterns: List of patterns
            trend_context: Trend analyzer results

        Returns:
            True if aligned
        """
        if not patterns or not trend_context:
            return False

        trend_direction = trend_context.get('direction', 'neutral')
        if trend_direction == 'neutral':
            return False

        # Check if majority of patterns align with trend
        aligned_count = sum(
            1 for p in patterns
            if p['direction'] == trend_direction
        )

        return aligned_count > len(patterns) / 2

    def _calculate_confidence(
        self,
        patterns: List[Dict[str, Any]],
        alignment: bool,
        volume_context: Optional[Dict]
    ) -> float:
        """
        Calculate confidence score.

        Args:
            patterns: List of patterns
            alignment: Trend alignment
            volume_context: Volume analyzer results

        Returns:
            Confidence (0-1)
        """
        if not patterns:
            return 0.0

        confidence = 0.5

        # More patterns increase confidence
        if len(patterns) >= 3:
            confidence += 0.2
        elif len(patterns) >= 2:
            confidence += 0.1

        # Strong patterns increase confidence
        avg_strength = sum(p['adjusted_strength'] for p in patterns) / len(patterns)
        if avg_strength >= 2.5:
            confidence += 0.2
        elif avg_strength >= 2.0:
            confidence += 0.1

        # Trend alignment increases confidence
        if alignment:
            confidence += 0.15

        # Volume confirmation
        if volume_context and volume_context.get('is_confirmed'):
            confidence += 0.1

        return min(confidence, 1.0)

    def _validate_context(self, context: AnalysisContext) -> bool:
        """Validate required columns"""
        required = ['open', 'high', 'low', 'close']

        df = context.df
        for col in required:
            if col not in df.columns:
                logger.error(f"Missing required column: {col}")
                return False

        return True
