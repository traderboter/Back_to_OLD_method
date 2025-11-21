"""
SignalScorer - Calculate Signal Scores with 13 Multipliers

این ماژول امتیازدهی سیگنال را با استفاده از 13 ضریب مشابه سیستم قدیم انجام می‌دهد.

Formula (Old System):
    final_score = (
        base_score *
        timeframe_weight *          # Higher TF confirmation
        trend_alignment *           # Trend alignment
        volume_confirmation *       # Volume confirmation
        pattern_quality *           # Pattern quality
        (1.0 + confluence_score) *  # Confluence (includes RR)
        symbol_performance_factor * # Symbol history (from adaptive learning)
        correlation_safety_factor * # Correlation safety
        macd_analysis_score *       # MACD analysis
        structure_score *           # HTF structure
        volatility_score *          # Volatility regime
        harmonic_pattern_score *    # Harmonic patterns
        price_channel_score *       # Price channels
        cyclical_pattern_score      # Cyclical patterns
    )

Usage:
    scorer = SignalScorer(config)
    score = scorer.calculate_score(context, direction='LONG')
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import logging
from signal_generation.context import AnalysisContext

logger = logging.getLogger(__name__)


@dataclass
class SignalScore:
    """
    کلاس داده‌ای برای ذخیره تمام اجزای امتیاز.

    این کلاس تمام 13 ضریب + امتیاز نهایی را نگه می‌دارد.
    """
    # Base components
    base_score: float = 0.0

    # 13 Multipliers (matching old system)
    timeframe_weight: float = 1.0
    trend_alignment: float = 1.0
    volume_confirmation: float = 1.0
    pattern_quality: float = 1.0
    confluence_score: float = 0.0  # Additive (0-0.5)
    symbol_performance_factor: float = 1.0
    correlation_safety_factor: float = 1.0
    macd_analysis_score: float = 1.0
    structure_score: float = 1.0
    volatility_score: float = 1.0
    harmonic_pattern_score: float = 1.0
    price_channel_score: float = 1.0
    cyclical_pattern_score: float = 1.0

    # Final score
    final_score: float = 0.0

    # Metadata
    details: Dict[str, Any] = field(default_factory=dict)


class SignalScorer:
    """
    امتیازدهی سیگنال با 13 ضریب مشابه سیستم قدیم.

    این کلاس تمام منطق امتیازدهی سیستم قدیم را پیاده‌سازی می‌کند.

    Key features:
    - 13 multipliers matching old system exactly
    - Multi-timeframe awareness
    - Adaptive learning integration (optional)
    - Correlation safety (optional)
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize SignalScorer.

        Args:
            config: Global configuration dictionary
        """
        self.config = config

        # Timeframe weights (old system values)
        self.timeframe_weights = {
            '5m': 0.15,   # 15%
            '15m': 0.20,  # 20%
            '1h': 0.30,   # 30%
            '4h': 0.35    # 35%
        }

        # Scoring thresholds
        self.min_base_score = config.get('scoring', {}).get('min_base_score', 50.0)
        self.min_final_score = config.get('scoring', {}).get('min_final_score', 60.0)

        # Optional components (can be None)
        self.adaptive_learning = None  # Will be set if adaptive learning is enabled
        self.correlation_manager = None  # Will be set if correlation checking is enabled

        logger.info("SignalScorer initialized with 13-multiplier system")

    def calculate_score(
        self,
        context: AnalysisContext,
        direction: str,
        timeframe_data: Optional[Dict[str, Any]] = None
    ) -> SignalScore:
        """
        محاسبه امتیاز سیگنال با 13 ضریب.

        این متد امتیاز نهایی را با استفاده از 13 ضریب سیستم قدیم محاسبه می‌کند.

        Args:
            context: AnalysisContext با نتایج تمام analyzers
            direction: 'LONG' or 'SHORT'
            timeframe_data: اطلاعات multi-TF (اختیاری)

        Returns:
            SignalScore با تمام اجزا و امتیاز نهایی
        """
        score = SignalScore()

        try:
            # 1. Base Score (امتیاز پایه از الگوها و تحلیل‌ها)
            score.base_score = self._calculate_base_score(context, direction)

            # 2. Timeframe Weight (وزن بر اساس تأیید TF های بالاتر)
            if timeframe_data:
                score.timeframe_weight = self._calculate_timeframe_weight(
                    timeframe_data, direction
                )
            else:
                score.timeframe_weight = 1.0

            # 3. Trend Alignment (همسویی با ترند)
            score.trend_alignment = self._calculate_trend_alignment(
                context, direction, timeframe_data
            )

            # 4. Volume Confirmation (تأیید حجم)
            score.volume_confirmation = self._calculate_volume_confirmation(
                context, timeframe_data
            )

            # 5. Pattern Quality (کیفیت الگو)
            score.pattern_quality = self._calculate_pattern_quality(context)

            # 6. Confluence Score (همگرایی - شامل RR)
            score.confluence_score = self._calculate_confluence_score(
                context, direction
            )

            # 7. Symbol Performance Factor (عملکرد تاریخی سیمبل)
            score.symbol_performance_factor = self._calculate_symbol_performance(
                context.symbol, direction
            )

            # 8. Correlation Safety Factor (امنیت همبستگی)
            score.correlation_safety_factor = self._calculate_correlation_safety(
                context.symbol, direction
            )

            # 9. MACD Analysis Score (تحلیل MACD)
            score.macd_analysis_score = self._calculate_macd_score(
                context, timeframe_data
            )

            # 10. HTF Structure Score (امتیاز ساختار HTF)
            score.structure_score = self._calculate_structure_score(
                context, direction, timeframe_data
            )

            # 11. Volatility Score (امتیاز نوسان)
            score.volatility_score = self._calculate_volatility_score(context)

            # 12. Harmonic Pattern Score (امتیاز الگوهای هارمونیک)
            score.harmonic_pattern_score = self._calculate_harmonic_score(context)

            # 13. Price Channel Score (امتیاز کانال قیمت)
            score.price_channel_score = self._calculate_channel_score(context)

            # 14. Cyclical Pattern Score (امتیاز الگوهای چرخه‌ای)
            score.cyclical_pattern_score = self._calculate_cyclical_score(context)

            # ✅ محاسبه نهایی (مشابه سیستم قدیم)
            score.final_score = (
                score.base_score *
                score.timeframe_weight *
                score.trend_alignment *
                score.volume_confirmation *
                score.pattern_quality *
                (1.0 + score.confluence_score) *
                score.symbol_performance_factor *
                score.correlation_safety_factor *
                score.macd_analysis_score *
                score.structure_score *
                score.volatility_score *
                score.harmonic_pattern_score *
                score.price_channel_score *
                score.cyclical_pattern_score
            )

            # ذخیره جزئیات برای debugging
            score.details = {
                'direction': direction,
                'symbol': context.symbol,
                'timeframe': context.timeframe,
                'calculation_method': 'old_system_13_multipliers'
            }

            logger.debug(
                f"Score calculated for {context.symbol}: "
                f"base={score.base_score:.1f}, final={score.final_score:.1f}"
            )

            return score

        except Exception as e:
            logger.error(f"Error calculating score: {e}", exc_info=True)
            # Return minimal score on error
            return SignalScore(base_score=0.0, final_score=0.0)

    def _calculate_base_score(
        self,
        context: AnalysisContext,
        direction: str
    ) -> float:
        """
        محاسبه Base Score (امتیاز پایه).

        Base score شامل:
        - امتیاز momentum (20-40 امتیاز)
        - امتیاز pattern (20-40 امتیاز)
        - امتیاز S/R position (10-20 امتیاز)

        Old system: signal_generator.py:4859-4950

        Returns:
            Float بین 50-100 (امتیاز پایه)
        """
        base = 0.0

        # 1. Momentum contribution (20-40)
        momentum_result = context.get_result('momentum')
        if momentum_result and momentum_result.get('status') == 'ok':
            mom_dir = momentum_result.get('direction', 'neutral')
            mom_strength = momentum_result.get('momentum_strength', 0)

            if direction.upper() == 'LONG' and mom_dir == 'bullish':
                base += min(20 + mom_strength * 5, 40)
            elif direction.upper() == 'SHORT' and mom_dir == 'bearish':
                base += min(20 + mom_strength * 5, 40)
            else:
                base += 15  # Weak momentum
        else:
            base += 20  # Neutral

        # 2. Pattern contribution (20-40)
        pattern_result = context.get_result('pattern')
        if pattern_result and pattern_result.get('status') == 'ok':
            patterns = pattern_result.get('patterns', [])
            if patterns:
                # Use highest confidence pattern
                max_confidence = max(p.get('confidence', 0) for p in patterns)
                base += 20 + (max_confidence * 20)
            else:
                base += 25
        else:
            base += 25

        # 3. S/R position (10-20)
        sr_result = context.get_result('support_resistance')
        if sr_result and sr_result.get('status') == 'ok':
            level_strength = sr_result.get('level_strength', 0)
            base += 10 + (level_strength * 3.33)  # 0-3 → 10-20
        else:
            base += 15

        return round(min(100, max(50, base)), 1)

    def _calculate_timeframe_weight(
        self,
        timeframe_data: Dict[str, Any],
        direction: str
    ) -> float:
        """
        محاسبه Timeframe Weight بر اساس تأیید TF های بالاتر.

        Old system: signal_generator.py:5055-5078

        Logic:
        - Higher TF confirmation → multiplier بالاتر
        - Reversal → multiplier پایین‌تر
        - Range: 0.7 - 1.5

        Returns:
            Float بین 0.7-1.5
        """
        if not timeframe_data:
            return 1.0

        # Check for reversal
        is_reversal = timeframe_data.get('is_reversal', False)
        reversal_strength = timeframe_data.get('reversal_strength', 0)

        # Get higher TF confirmations
        primary_tf = timeframe_data.get('primary_timeframe')
        successful_tfs = timeframe_data.get('analysis_results', {})

        if not primary_tf or not successful_tfs:
            return 1.0

        primary_tf_weight = self.timeframe_weights.get(primary_tf, 0.25)

        higher_tf_confirmations = 0
        total_higher_tfs = 0

        for tf, result in successful_tfs.items():
            tf_weight = self.timeframe_weights.get(tf, 0.25)

            if tf_weight > primary_tf_weight:
                total_higher_tfs += 1
                trend_result = result.get('trend', {})
                trend_dir = trend_result.get('direction', 'neutral')

                if (direction.upper() == 'LONG' and trend_dir == 'bullish') or \
                   (direction.upper() == 'SHORT' and trend_dir == 'bearish'):
                    higher_tf_confirmations += 1

        higher_tf_ratio = higher_tf_confirmations / total_higher_tfs if total_higher_tfs > 0 else 0

        if is_reversal:
            # Reversal: کمتر به HTF وابسته
            reversal_modifier = max(0.3, 1.0 - (reversal_strength * 0.7))
            weight = 1.0 + (higher_tf_ratio * 0.3 * reversal_modifier)
        else:
            # Continuation: بیشتر به HTF وابسته
            weight = 1.0 + (higher_tf_ratio * 0.5)

        return round(min(1.5, max(0.7, weight)), 2)

    def _calculate_trend_alignment(
        self,
        context: AnalysisContext,
        direction: str,
        timeframe_data: Optional[Dict[str, Any]]
    ) -> float:
        """
        محاسبه Trend Alignment.

        Old system: signal_generator.py:5071-5078

        Logic:
        - Aligned with trend: 1.3
        - Against trend: 0.7
        - Neutral: 1.0

        Returns:
            0.7, 1.0, or 1.3
        """
        trend_result = context.get_result('trend')
        if not trend_result or trend_result.get('status') != 'ok':
            return 1.0

        trend_direction = trend_result.get('direction', 'neutral')

        if direction.upper() == 'LONG':
            if trend_direction == 'bullish':
                return 1.3  # Aligned
            elif trend_direction == 'bearish':
                return 0.7  # Against
        elif direction.upper() == 'SHORT':
            if trend_direction == 'bearish':
                return 1.3  # Aligned
            elif trend_direction == 'bullish':
                return 0.7  # Against

        return 1.0  # Neutral

    def _calculate_volume_confirmation(
        self,
        context: AnalysisContext,
        timeframe_data: Optional[Dict[str, Any]]
    ) -> float:
        """
        محاسبه Volume Confirmation.

        Old system: signal_generator.py:5079-5089

        Logic:
        - High volume + aligned: 1.2
        - Low volume: 0.8
        - Normal: 1.0

        Returns:
            0.8, 1.0, or 1.2
        """
        volume_result = context.get_result('volume')
        if not volume_result or volume_result.get('status') != 'ok':
            return 1.0

        volume_signal = volume_result.get('signal', 'normal')
        volume_trend = volume_result.get('volume_trend', 'neutral')

        if volume_signal == 'high' and volume_trend == 'increasing':
            return 1.2  # Strong confirmation
        elif volume_signal == 'low':
            return 0.8  # Weak

        return 1.0  # Normal

    def _calculate_pattern_quality(
        self,
        context: AnalysisContext
    ) -> float:
        """
        محاسبه Pattern Quality.

        Old system: signal_generator.py:5090-5100

        Based on pattern confidence/strength.

        Returns:
            Float بین 0.8-1.2
        """
        pattern_result = context.get_result('pattern')
        if not pattern_result or pattern_result.get('status') != 'ok':
            return 1.0

        patterns = pattern_result.get('patterns', [])
        if not patterns:
            return 1.0

        # Get highest confidence
        max_confidence = max(p.get('confidence', 0) for p in patterns)

        # Map 0-1 confidence to 0.8-1.2 multiplier
        quality = 0.8 + (max_confidence * 0.4)

        return round(quality, 2)

    def _calculate_confluence_score(
        self,
        context: AnalysisContext,
        direction: str
    ) -> float:
        """
        محاسبه Confluence Score (additive).

        Old system: signal_generator.py:4937-4994

        Confluence factors:
        - Multiple patterns (+0.1)
        - S/R at key level (+0.1)
        - High RR (>2.5) (+0.15)
        - Multiple indicators aligned (+0.15)

        Returns:
            Float بین 0.0-0.5 (additive)
        """
        confluence = 0.0

        # 1. Multiple patterns
        pattern_result = context.get_result('pattern')
        if pattern_result and pattern_result.get('status') == 'ok':
            patterns = pattern_result.get('patterns', [])
            if len(patterns) >= 2:
                confluence += 0.1

        # 2. S/R at key level
        sr_result = context.get_result('support_resistance')
        if sr_result and sr_result.get('status') == 'ok':
            level_strength = sr_result.get('level_strength', 0)
            if level_strength >= 2:
                confluence += 0.1

        # 3. High RR (would need risk/reward data - placeholder)
        # This will be calculated when we have SL/TP
        # For now, assume normal RR
        confluence += 0.0

        # 4. Multiple indicators aligned
        aligned_count = 0

        momentum_result = context.get_result('momentum')
        if momentum_result and momentum_result.get('status') == 'ok':
            mom_dir = momentum_result.get('direction', 'neutral')
            if (direction.upper() == 'LONG' and mom_dir == 'bullish') or \
               (direction.upper() == 'SHORT' and mom_dir == 'bearish'):
                aligned_count += 1

        trend_result = context.get_result('trend')
        if trend_result and trend_result.get('status') == 'ok':
            trend_dir = trend_result.get('direction', 'neutral')
            if (direction.upper() == 'LONG' and trend_dir == 'bullish') or \
               (direction.upper() == 'SHORT' and trend_dir == 'bearish'):
                aligned_count += 1

        if aligned_count >= 2:
            confluence += 0.15

        return round(min(0.5, confluence), 2)

    def _calculate_symbol_performance(
        self,
        symbol: str,
        direction: str
    ) -> float:
        """
        محاسبه Symbol Performance Factor.

        Old system: Uses adaptive learning

        If adaptive learning is enabled, get historical performance.
        Otherwise, return 1.0 (neutral).

        Returns:
            Float بین 0.9-1.1
        """
        if self.adaptive_learning and hasattr(self.adaptive_learning, 'get_symbol_performance_factor'):
            try:
                return self.adaptive_learning.get_symbol_performance_factor(symbol, direction)
            except Exception as e:
                logger.debug(f"Adaptive learning error: {e}")
                return 1.0

        return 1.0  # Neutral if not available

    def _calculate_correlation_safety(
        self,
        symbol: str,
        direction: str
    ) -> float:
        """
        محاسبه Correlation Safety Factor.

        Old system: Uses correlation manager

        If correlation manager is enabled, check correlation safety.
        Otherwise, return 1.0 (neutral).

        Returns:
            Float بین 0.8-1.0
        """
        if self.correlation_manager and hasattr(self.correlation_manager, 'get_correlation_safety_factor'):
            try:
                return self.correlation_manager.get_correlation_safety_factor(symbol, direction)
            except Exception as e:
                logger.debug(f"Correlation manager error: {e}")
                return 1.0

        return 1.0  # Neutral if not available

    def _calculate_macd_score(
        self,
        context: AnalysisContext,
        timeframe_data: Optional[Dict[str, Any]]
    ) -> float:
        """
        محاسبه MACD Analysis Score.

        Old system: signal_generator.py:3562-3658

        Based on:
        - Market type (A/B/C/D/X)
        - Advanced MACD signals

        Returns:
            Float بین 1.0-1.4
        """
        momentum_result = context.get_result('momentum')
        if not momentum_result or momentum_result.get('status') != 'ok':
            return 1.0

        macd_market_type = momentum_result.get('macd_market_type', 'X')
        advanced_signals = momentum_result.get('advanced_macd_signals', [])

        score = 1.0

        # Market type bonus
        if macd_market_type in ['A_TREND', 'C_TREND']:
            score += 0.2  # Strong trend markets
        elif macd_market_type in ['B_REVERSAL']:
            score += 0.15  # Reversal opportunity

        # Advanced signal bonus
        if advanced_signals:
            signal_count = len(advanced_signals)
            score += min(0.2, signal_count * 0.05)

        return round(min(1.4, score), 2)

    def _calculate_structure_score(
        self,
        context: AnalysisContext,
        direction: str,
        timeframe_data: Optional[Dict[str, Any]]
    ) -> float:
        """
        محاسبه HTF Structure Score.

        Old system: Uses HTF structure analysis

        Uses structure_score from HTFAnalyzer (already calculated).

        Returns:
            Float بین 0.7-1.3
        """
        htf_result = context.get_result('htf')
        if not htf_result or htf_result.get('status') != 'ok':
            return 1.0

        # HTFAnalyzer already calculates structure_score (0.7-1.3)
        structure_score = htf_result.get('structure_score', 1.0)

        return round(structure_score, 2)

    def _calculate_volatility_score(
        self,
        context: AnalysisContext
    ) -> float:
        """
        محاسبه Volatility Score.

        Old system: signal_generator.py:3100-3150

        Based on volatility regime:
        - Low volatility: 0.8 (less favorable)
        - Normal: 1.0
        - High: 1.2 (more opportunity)

        Returns:
            Float بین 0.8-1.2
        """
        volatility_result = context.get_result('volatility')
        if not volatility_result or volatility_result.get('status') != 'ok':
            return 1.0

        regime = volatility_result.get('regime', 'normal')

        if regime == 'low':
            return 0.8
        elif regime == 'high':
            return 1.2

        return 1.0  # Normal

    def _calculate_harmonic_score(
        self,
        context: AnalysisContext
    ) -> float:
        """
        محاسبه Harmonic Pattern Score.

        Old system: signal_generator.py:2800-2900

        If harmonic pattern found: 1.0-1.3
        Otherwise: 1.0

        Returns:
            Float بین 1.0-1.3
        """
        harmonic_result = context.get_result('harmonic')
        if not harmonic_result or harmonic_result.get('status') != 'ok':
            return 1.0

        patterns = harmonic_result.get('patterns', [])
        if not patterns:
            return 1.0

        # Find strongest pattern
        max_strength = max(p.get('strength', 0) for p in patterns)
        max_completion = max(p.get('completion', 0) for p in patterns)

        # Score based on strength and completion
        score = 1.0 + (max_strength * 0.1) + (max_completion * 0.2)

        return round(min(1.3, score), 2)

    def _calculate_channel_score(
        self,
        context: AnalysisContext
    ) -> float:
        """
        محاسبه Price Channel Score.

        Old system: signal_generator.py:2650-2750

        If channel found with good fit: 1.0-1.2
        Otherwise: 1.0

        Returns:
            Float بین 1.0-1.2
        """
        channel_result = context.get_result('channel')
        if not channel_result or channel_result.get('status') != 'ok':
            return 1.0

        channel_type = channel_result.get('channel_type', 'irregular')
        strength = channel_result.get('strength', 0)

        if channel_type in ['ascending', 'descending', 'horizontal'] and strength >= 2:
            score = 1.0 + (strength * 0.067)  # 2→1.13, 3→1.2
            return round(min(1.2, score), 2)

        return 1.0

    def _calculate_cyclical_score(
        self,
        context: AnalysisContext
    ) -> float:
        """
        محاسبه Cyclical Pattern Score.

        Old system: signal_generator.py:3400-3500

        If cyclical pattern confirmed: 1.0-1.15
        Otherwise: 1.0

        Returns:
            Float بین 1.0-1.15
        """
        cyclical_result = context.get_result('cyclical')
        if not cyclical_result or cyclical_result.get('status') != 'ok':
            return 1.0

        phase = cyclical_result.get('phase', 'unknown')
        confidence = cyclical_result.get('confidence', 0)

        if phase in ['accumulation', 'markup', 'distribution', 'markdown'] and confidence > 0.5:
            score = 1.0 + (confidence * 0.15)
            return round(min(1.15, score), 2)

        return 1.0
