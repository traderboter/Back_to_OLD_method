"""
Multi-Timeframe Aggregator - Legacy System Compatibility

Aggregates signal scores from multiple timeframes exactly like the old system.

This implements the OLD SYSTEM's Multi-TF aggregation approach:
- Collects scores from multiple timeframes (5m, 15m, 1h, 4h, etc.)
- Applies timeframe weights
- Sums bullish/bearish scores across all TFs
- Determines final direction with 10% margin
- Calculates alignment factors

Purpose: Replicate old system scoring for comparison and gradual migration.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import logging

from signal_generation.signal_info import SignalInfo, SignalScore
from signal_generation.context import AnalysisContext
from signal_generation.confidence_calculator import ConfidenceCalculator, ConfidenceMetrics
from signal_generation.risk_calculator import RiskRewardCalculator

logger = logging.getLogger(__name__)


@dataclass
class TimeframeSignal:
    """Represents a signal from a single timeframe."""
    timeframe: str
    direction: str  # 'LONG', 'SHORT', or 'NEUTRAL'
    score: SignalScore
    context: AnalysisContext

    # Individual analyzer contributions
    trend_score: float = 0.0
    momentum_bullish: float = 0.0
    momentum_bearish: float = 0.0
    volume_confirmed: bool = False
    htf_aligned: bool = False
    volatility_factor: float = 1.0


class MultiTimeframeAggregator:
    """
    Aggregates signals from multiple timeframes using OLD SYSTEM approach.

    OLD SYSTEM Logic:
    1. For each timeframe, get analysis results
    2. Calculate bullish_score and bearish_score separately
    3. Apply timeframe weights
    4. Apply phase multipliers and MACD type strength
    5. Sum across all timeframes
    6. Determine direction with 10% margin
    7. Calculate alignment factors
    """

    # Timeframe weights (تنظیم شده برای balance بهتر)
    DEFAULT_TF_WEIGHTS = {
        '5m': 0.7,   # -30% importance
        '15m': 0.85, # -15% importance
        '1h': 1.0,   # Reference
        '4h': 1.1    # +10% importance (کاهش از 1.2 برای جلوگیری از over-dominance)
    }

    # Phase multipliers (OLD SYSTEM)
    PHASE_MULTIPLIERS = {
        'early': 1.2,       # +20% - Best opportunity
        'developing': 1.1,  # +10%
        'mature': 0.9,      # -10% - Caution
        'late': 0.7,        # -30% - Risky
        'pullback': 1.1,    # +10%
        'transition': 0.8,  # -20%
        'undefined': 1.0    # No change
    }

    # MACD type strength (OLD SYSTEM)
    MACD_TYPE_STRENGTH = {
        'A': 1.2,  # A_ types (strong bullish) +20%
        'C': 1.2,  # C_ types (strong bearish) +20%
        'B': 1.0,  # B_ types (neutral)
        'D': 1.0,  # D_ types (neutral)
        'X': 0.8   # X_ types (transition) -20%
    }

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Multi-TF Aggregator.

        Args:
            config: Configuration dictionary
        """
        self.config = config

        # Get multi-TF configuration
        mtf_config = config.get('signal_processing', {}).get('multi_timeframe', {})

        # Timeframe weights
        self.tf_weights = mtf_config.get('weights', self.DEFAULT_TF_WEIGHTS.copy())

        # Direction determination margin (افزایش از 1.1 به 1.3 برای سیگنال‌های قوی‌تر)
        self.direction_margin = mtf_config.get('direction_margin', 1.3)

        # Minimum TFs required for valid signal
        self.min_timeframes = mtf_config.get('min_timeframes', 2)

        # Initialize Confidence Calculator
        self.confidence_calculator = ConfidenceCalculator(config)

        # Initialize Risk Reward Calculator
        self.risk_calculator = RiskRewardCalculator(config)

        logger.info("MultiTimeframeAggregator initialized (OLD SYSTEM MODE with Confidence Scoring)")

    def aggregate_timeframe_scores(
        self,
        symbol: str,
        timeframe_signals: Dict[str, TimeframeSignal]
    ) -> Optional[SignalInfo]:
        """
        Aggregate scores from multiple timeframes (OLD SYSTEM approach).

        This replicates: calculate_multi_timeframe_score() from old system

        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe_signals: Dict of {timeframe: TimeframeSignal}

        Returns:
            Aggregated SignalInfo or None if no clear signal
        """
        if not timeframe_signals or len(timeframe_signals) < self.min_timeframes:
            logger.debug(f"Insufficient timeframes for {symbol}: {len(timeframe_signals)}")
            return None

        logger.info(f"Aggregating {len(timeframe_signals)} timeframes for {symbol}")

        # Step 1: Calculate bullish and bearish scores
        bullish_score, bearish_score = self._calculate_aggregate_scores(timeframe_signals)

        # Step 2: Determine final direction (with 30% margin)
        final_direction = self._determine_direction(bullish_score, bearish_score)

        if final_direction == 'NEUTRAL':
            logger.debug(f"No clear direction for {symbol}: "
                        f"bullish={bullish_score:.2f}, bearish={bearish_score:.2f}")
            return None

        # Step 2.5: Check timeframe consensus (NEW: minimum 75% agreement)
        has_consensus = self._check_timeframe_consensus(
            timeframe_signals,
            final_direction,
            min_consensus=0.75
        )

        if not has_consensus:
            logger.debug(f"Insufficient timeframe consensus for {symbol}: {final_direction}")
            return None

        # Step 3: Calculate alignment factor (timeframe consensus)
        alignment_factor = self._calculate_alignment_factor(
            timeframe_signals,
            final_direction
        )

        # Step 4: Calculate volume confirmation factor
        volume_factor = self._calculate_volume_factor(timeframe_signals)

        # Step 5: Calculate HTF structure factor
        htf_factor = self._calculate_htf_factor(timeframe_signals)

        # Step 6: Calculate volatility factor
        volatility_factor = self._calculate_volatility_factor(timeframe_signals)

        # Step 7: Calculate Confidence Metrics
        # Convert TimeframeSignal objects to dict format for confidence calculator
        tf_signals_dict = {}
        for tf, tf_signal in timeframe_signals.items():
            tf_signals_dict[tf] = {
                'direction': tf_signal.direction,
                'score': tf_signal.score.final_score if hasattr(tf_signal.score, 'final_score') else 0,
                'volume_confirmed': tf_signal.volume_confirmed
            }

        confidence_metrics = self.confidence_calculator.calculate_confidence(
            timeframe_signals=tf_signals_dict,
            final_direction=final_direction,
            bullish_score=bullish_score,
            bearish_score=bearish_score
        )

        logger.info(
            f"Confidence: {confidence_metrics.confidence_level} "
            f"({confidence_metrics.overall_confidence:.1%})"
        )

        if confidence_metrics.is_uncertain:
            logger.warning(f"⚠️  Signal is uncertain for {symbol}")

        # Step 8: Build final signal
        final_score = bullish_score if final_direction == 'LONG' else bearish_score

        signal_info = self._build_signal_info(
            symbol=symbol,
            direction=final_direction,
            final_score=final_score,
            timeframe_signals=timeframe_signals,
            alignment_factor=alignment_factor,
            volume_factor=volume_factor,
            htf_factor=htf_factor,
            volatility_factor=volatility_factor,
            confidence_metrics=confidence_metrics
        )

        logger.info(
            f"Multi-TF signal for {symbol}: {final_direction} "
            f"score={final_score:.2f}, alignment={alignment_factor:.2f}, "
            f"confidence={confidence_metrics.confidence_level}"
        )

        return signal_info

    def _calculate_aggregate_scores(
        self,
        timeframe_signals: Dict[str, TimeframeSignal]
    ) -> Tuple[float, float]:
        """
        Calculate aggregate bullish and bearish scores (OLD SYSTEM).

        OLD SYSTEM Logic:
        for each TF:
            tf_weight = weights[tf]
            bullish += (trend_score + momentum_bullish + ...) * tf_weight
            bearish += (momentum_bearish + ...) * tf_weight

        Returns:
            (bullish_score, bearish_score)
        """
        bullish_score = 0.0
        bearish_score = 0.0

        for tf, tf_signal in timeframe_signals.items():
            # Get timeframe weight
            tf_weight = self.tf_weights.get(tf, 1.0)

            # Get analyzer results from context
            context = tf_signal.context

            # 1. Trend contribution (with phase multiplier)
            trend_result = context.get_result('trend')
            if trend_result:
                trend_strength = trend_result.get('strength', 0)
                trend_direction = trend_result.get('direction', 'neutral')
                trend_phase = trend_result.get('phase', 'undefined')

                # Apply phase multiplier
                phase_multiplier = self.PHASE_MULTIPLIERS.get(trend_phase, 1.0)

                if trend_direction == 'bullish':
                    bullish_score += trend_strength * tf_weight * phase_multiplier
                elif trend_direction == 'bearish':
                    bearish_score += trend_strength * tf_weight * phase_multiplier

                logger.debug(
                    f"{tf} Trend: {trend_direction} strength={trend_strength}, "
                    f"phase={trend_phase}, multiplier={phase_multiplier:.2f}"
                )

            # 2. Momentum contribution (with MACD type strength)
            momentum_result = context.get_result('momentum')
            if momentum_result:
                # Get bullish and bearish scores separately
                mom_direction = momentum_result.get('direction', 'neutral')
                mom_strength = momentum_result.get('strength', 0)

                # Get MACD type strength multiplier (from enhanced MomentumAnalyzer)
                macd_type_multiplier = 1.0
                macd_market_type = momentum_result.get('macd_market_type', '')
                if macd_market_type:
                    # Extract first character (A, B, C, D, or X)
                    # Examples: "A_bullish_strong" → 'A', "C_bearish_strong" → 'C', "X_transition" → 'X'
                    type_prefix = macd_market_type[0] if macd_market_type else ''
                    macd_type_multiplier = self.MACD_TYPE_STRENGTH.get(type_prefix, 1.0)

                if mom_direction == 'bullish':
                    bullish_score += mom_strength * tf_weight * macd_type_multiplier
                elif mom_direction == 'bearish':
                    bearish_score += mom_strength * tf_weight * macd_type_multiplier

                logger.debug(
                    f"{tf} Momentum: {mom_direction} strength={mom_strength}, "
                    f"MACD type multiplier={macd_type_multiplier:.2f}"
                )

            # 3. Pattern contribution (if any patterns detected)
            pattern_result = context.get_result('patterns')
            if pattern_result and pattern_result.get('patterns'):
                for pattern in pattern_result['patterns']:
                    pattern_score = pattern.get('score', 0)
                    pattern_direction = pattern.get('direction', 'neutral')

                    if pattern_direction == 'bullish':
                        bullish_score += pattern_score * tf_weight * 0.5  # Scaled down
                    elif pattern_direction == 'bearish':
                        bearish_score += pattern_score * tf_weight * 0.5

            # 4. S/R breakout contribution
            sr_result = context.get_result('support_resistance')
            if sr_result:
                # Check for broken levels (breakouts)
                broken_levels = sr_result.get('broken_levels', [])
                for broken in broken_levels:
                    if broken['broken_direction'] == 'upward':
                        # Broken resistance = bullish
                        strength = broken.get('original_strength', 1)
                        bullish_score += strength * tf_weight * 1.5
                    else:
                        # Broken support = bearish
                        strength = broken.get('original_strength', 1)
                        bearish_score += strength * tf_weight * 1.5

            # 5. Cyclical forecast contribution
            cyclical_result = context.get_result('cyclical')
            if cyclical_result and 'signal' in cyclical_result:
                signal = cyclical_result['signal']
                if signal.get('direction') == 'bullish':
                    bullish_score += signal.get('score', 0) * tf_weight
                elif signal.get('direction') == 'bearish':
                    bearish_score += signal.get('score', 0) * tf_weight

        # Get symbol from first timeframe signal
        symbol = next(iter(timeframe_signals.values())).context.symbol if timeframe_signals else "UNKNOWN"
        logger.info(f"Aggregate scores for {symbol}: bullish={bullish_score:.2f}, bearish={bearish_score:.2f}")

        return bullish_score, bearish_score

    def _determine_direction(
        self,
        bullish_score: float,
        bearish_score: float
    ) -> str:
        """
        Determine final direction with margin.

        With margin=1.0:
        - if bullish > bearish → LONG
        - if bearish > bullish → SHORT
        - if equal → NEUTRAL (no clear direction)
        """
        direction = 'NEUTRAL'
        if bullish_score > bearish_score * self.direction_margin:
            direction = 'LONG'
        elif bearish_score > bullish_score * self.direction_margin:
            direction = 'SHORT'

        logger.info(
            f"Direction determination: bullish={bullish_score:.2f}, bearish={bearish_score:.2f}, "
            f"margin={self.direction_margin}, direction={direction}"
        )
        return direction

    def _check_timeframe_consensus(
        self,
        timeframe_signals: Dict[str, TimeframeSignal],
        final_direction: str,
        min_consensus: float = 0.75
    ) -> bool:
        """
        بررسی اجماع (consensus) بین تایم‌فریم‌ها.

        برای جلوگیری از معاملات با تایم‌فریم‌های متضاد، حداقل درصدی از
        تایم‌فریم‌ها باید در جهت نهایی باشند.

        Args:
            timeframe_signals: Dict of {timeframe: TimeframeSignal}
            final_direction: جهت نهایی ('LONG' یا 'SHORT')
            min_consensus: حداقل درصد اجماع مورد نیاز (پیش‌فرض: 0.75 = 75%)

        Returns:
            True اگر اجماع کافی وجود داشته باشد، وگرنه False
        """
        if not timeframe_signals:
            return False

        # شمارش تایم‌فریم‌های هم‌جهت و مخالف
        aligned_count = 0
        total_count = len(timeframe_signals)

        for tf, tf_signal in timeframe_signals.items():
            if tf_signal.direction == final_direction:
                aligned_count += 1

        consensus_ratio = aligned_count / total_count if total_count > 0 else 0

        has_consensus = consensus_ratio >= min_consensus

        logger.info(
            f"Consensus check: {aligned_count}/{total_count} timeframes aligned "
            f"with {final_direction} ({consensus_ratio:.1%}) - "
            f"{'✅ PASS' if has_consensus else '❌ FAIL'} (min: {min_consensus:.1%})"
        )

        return has_consensus

    def _calculate_alignment_factor(
        self,
        timeframe_signals: Dict[str, TimeframeSignal],
        final_direction: str
    ) -> float:
        """
        Calculate timeframe alignment factor using OLD SYSTEM logic.

        OLD SYSTEM uses indicator-based alignment:
        - Checks Trend, Momentum, and MACD alignment separately
        - Weights: Trend 50%, Momentum 30%, MACD 20%
        - Range: 0.7 to 1.3

        Returns:
            Alignment factor (0.7 - 1.3)
        """
        if not timeframe_signals:
            return 0.7

        # Count aligned indicators per type
        aligned_trend = 0
        total_trend = 0
        aligned_momentum = 0
        total_momentum = 0
        aligned_macd = 0
        total_macd = 0

        for tf_signal in timeframe_signals.values():
            context = tf_signal.context

            # Check Trend alignment
            trend_result = context.get_result('trend')
            if trend_result and trend_result.get('direction'):
                total_trend += 1
                trend_dir = trend_result['direction']
                if (final_direction == 'LONG' and trend_dir == 'bullish') or \
                   (final_direction == 'SHORT' and trend_dir == 'bearish'):
                    aligned_trend += 1

            # Check Momentum alignment
            momentum_result = context.get_result('momentum')
            if momentum_result and momentum_result.get('direction'):
                total_momentum += 1
                mom_dir = momentum_result['direction']
                if (final_direction == 'LONG' and mom_dir == 'bullish') or \
                   (final_direction == 'SHORT' and mom_dir == 'bearish'):
                    aligned_momentum += 1

            # Check MACD alignment (from momentum analyzer's macd_signal)
            if momentum_result and momentum_result.get('macd_signal'):
                total_macd += 1
                macd_signal_data = momentum_result['macd_signal']
                macd_dir = macd_signal_data.get('direction', 'neutral')
                if (final_direction == 'LONG' and macd_dir == 'bullish') or \
                   (final_direction == 'SHORT' and macd_dir == 'bearish'):
                    aligned_macd += 1

        # Calculate ratios
        trend_ratio = aligned_trend / total_trend if total_trend > 0 else 0.0
        momentum_ratio = aligned_momentum / total_momentum if total_momentum > 0 else 0.0
        macd_ratio = aligned_macd / total_macd if total_macd > 0 else 0.0

        # Weighted combination (Trend 50%, Momentum 30%, MACD 20%)
        weighted_alignment = (
            trend_ratio * 0.5 +
            momentum_ratio * 0.3 +
            macd_ratio * 0.2
        )

        # Convert to range 0.7 - 1.3
        alignment_factor = 0.7 + (weighted_alignment * 0.6)

        logger.debug(
            f"Alignment calculation: Trend={aligned_trend}/{total_trend} ({trend_ratio:.2f}), "
            f"Momentum={aligned_momentum}/{total_momentum} ({momentum_ratio:.2f}), "
            f"MACD={aligned_macd}/{total_macd} ({macd_ratio:.2f}), "
            f"Weighted={weighted_alignment:.2f}, Factor={alignment_factor:.2f}"
        )

        return alignment_factor

    def _calculate_volume_factor(
        self,
        timeframe_signals: Dict[str, TimeframeSignal]
    ) -> float:
        """
        Calculate weighted volume confirmation factor (0.0 - 1.0) - OLD SYSTEM aligned.

        OLD SYSTEM formula:
        weighted_volume_factor = Σ(is_confirmed × tf_weight) / Σ(tf_weight)

        Higher timeframes have more weight in volume confirmation.
        """
        if not timeframe_signals:
            return 0.0

        weighted_volume = 0.0
        total_weight = 0.0

        for tf, tf_signal in timeframe_signals.items():
            # Get timeframe weight (OLD SYSTEM alignment)
            tf_weight = self.tf_weights.get(tf, 1.0)

            # Check if volume is confirmed
            volume_result = tf_signal.context.get_result('volume')
            is_confirmed = volume_result.get('is_confirmed', False) if volume_result else False

            # Add weighted confirmation
            weighted_volume += (1.0 if is_confirmed else 0.0) * tf_weight
            total_weight += tf_weight

        # Calculate weighted average
        volume_factor = weighted_volume / total_weight if total_weight > 0 else 0.0

        logger.debug(f"Volume confirmation factor: {volume_factor:.3f} (weighted)")

        return volume_factor

    def _calculate_htf_factor(
        self,
        timeframe_signals: Dict[str, TimeframeSignal]
    ) -> float:
        """
        Calculate HTF (Higher Timeframe) alignment factor.

        OLD SYSTEM: 0.8 - 1.5 multiplier
        """
        # Get configured timeframes to determine HTF dynamically
        configured_tfs = self.config.get('signal_generation', {}).get('timeframes', ['5m', '15m', '1h', '4h'])

        # Use highest configured timeframe as HTF (last in list)
        # This allows flexibility for Daily, Weekly, etc.
        if configured_tfs:
            highest_tf = configured_tfs[-1]  # Last timeframe is highest
            htf_timeframes = [highest_tf]
        else:
            # Fallback to 4h if no config found
            htf_timeframes = ['4h']

        htf_aligned = 0
        htf_total = 0

        for tf in htf_timeframes:
            if tf in timeframe_signals:
                htf_total += 1
                if timeframe_signals[tf].htf_aligned:
                    htf_aligned += 1

        if htf_total == 0:
            return 1.0  # Neutral

        # Map to 0.8 - 1.5 range (like old system)
        alignment_ratio = htf_aligned / htf_total
        htf_factor = 0.8 + (alignment_ratio * 0.7)  # 0.8 to 1.5

        return htf_factor

    def _calculate_volatility_factor(
        self,
        timeframe_signals: Dict[str, TimeframeSignal]
    ) -> float:
        """
        Calculate volatility adjustment factor.

        OLD SYSTEM: 0.5 - 1.0 multiplier
        """
        if not timeframe_signals:
            return 1.0

        volatility_factors = []

        for tf_signal in timeframe_signals.values():
            vol_result = tf_signal.context.get_result('volatility')
            if vol_result:
                # Get risk multiplier (0.5 - 2.0 in new system)
                # Map to 0.5 - 1.0 range (like old system)
                risk_mult = vol_result.get('risk_multiplier', 1.0)
                # Clamp to old system range
                vol_factor = min(max(risk_mult, 0.5), 1.0)
                volatility_factors.append(vol_factor)

        if not volatility_factors:
            return 1.0

        # Weighted average
        avg_vol_factor = sum(volatility_factors) / len(volatility_factors)

        return avg_vol_factor

    def _build_signal_info(
        self,
        symbol: str,
        direction: str,
        final_score: float,
        timeframe_signals: Dict[str, TimeframeSignal],
        alignment_factor: float,
        volume_factor: float,
        htf_factor: float,
        volatility_factor: float,
        confidence_metrics: ConfidenceMetrics
    ) -> SignalInfo:
        """
        Build final SignalInfo from aggregated results.
        """
        # Get the dominant timeframe (highest weighted TF with signal)
        dominant_tf = max(
            timeframe_signals.keys(),
            key=lambda tf: self.tf_weights.get(tf, 1.0)
        )
        dominant_signal = timeframe_signals[dominant_tf]

        # Use dominant TF's context for entry/SL/TP calculation
        # Use the highest weighted timeframe context for SL/TP calculation (OLD SYSTEM approach)
        context = dominant_signal.context
        current_price = context.df['close'].iloc[-1]
        entry_price = current_price

        # Calculate SL/TP using RiskRewardCalculator (5-method priority system)
        # This matches OLD SYSTEM: Harmonic → Channel → S/R → ATR → Percentage
        risk_config = self.config.get('risk_management', {})

        sl_tp_result = self.risk_calculator.calculate_sl_tp(
            direction=direction,
            entry_price=entry_price,
            context=context,
            adapted_config=risk_config
        )

        stop_loss = sl_tp_result['stop_loss']
        take_profit = sl_tp_result['take_profit']
        risk_reward_ratio = sl_tp_result['risk_reward_ratio']
        sl_method = sl_tp_result['sl_method']

        # Check minimum RR requirement
        min_rr = risk_config.get('min_risk_reward_ratio', 1.5)
        if risk_reward_ratio < min_rr:
            logger.info(
                f"Multi-TF signal rejected for {symbol}: RR {risk_reward_ratio:.2f} < min {min_rr:.2f} "
                f"(method: {sl_method})"
            )
            return None

        # Create SignalInfo
        signal = SignalInfo(
            symbol=symbol,
            timeframe=dominant_tf,  # Use dominant TF
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=risk_reward_ratio
        )

        logger.info(
            f"Multi-TF signal SL/TP calculated: Entry={entry_price:.2f}, "
            f"SL={stop_loss:.2f}, TP={take_profit:.2f}, RR={risk_reward_ratio:.2f}, "
            f"Method={sl_method}"
        )

        # Mark this as multi-TF aggregate via tags
        signal.tags.append('multi_tf_aggregate')

        # Create SignalScore
        score = SignalScore()
        score.final_score = final_score
        score.determine_signal_strength()
        score.calculate_confidence()

        # Add multi-TF metadata
        score.metadata = {
            'aggregation_method': 'multi_timeframe_old_system',
            'timeframes_used': list(timeframe_signals.keys()),
            'alignment_factor': alignment_factor,
            'volume_factor': volume_factor,
            'htf_factor': htf_factor,
            'volatility_factor': volatility_factor,
            'total_timeframes': len(timeframe_signals),
            'sl_method': sl_method,  # Track which method was used for SL/TP
            'risk_reward_ratio': risk_reward_ratio,
            # Confidence metrics
            'confidence_level': confidence_metrics.confidence_level,
            'overall_confidence': confidence_metrics.overall_confidence,
            'timeframe_consensus': confidence_metrics.timeframe_consensus,
            'score_quality': confidence_metrics.score_quality,
            'direction_clarity': confidence_metrics.direction_clarity,
            'htf_alignment': confidence_metrics.htf_alignment,
            'volume_confirmation': confidence_metrics.volume_confirmation,
            'is_uncertain': confidence_metrics.is_uncertain,
            'requires_review': confidence_metrics.requires_review
        }

        signal.score = score

        # 🆕 Build comprehensive metadata for signal (for backtest analysis)
        signal.metadata = self._build_aggregate_metadata(
            timeframe_signals=timeframe_signals,
            direction=direction,
            final_score=final_score,
            alignment_factor=alignment_factor,
            volume_factor=volume_factor,
            htf_factor=htf_factor,
            volatility_factor=volatility_factor,
            confidence_metrics=confidence_metrics,
            sl_method=sl_method,
            risk_reward_ratio=risk_reward_ratio,
            aggregated_score=score
        )

        # Add key factors
        signal.add_key_factor(f"Multi-TF aggregation ({len(timeframe_signals)} TFs)")
        signal.add_key_factor(f"SL/TP method: {sl_method} (RR={risk_reward_ratio:.2f})")
        signal.add_key_factor(f"Confidence: {confidence_metrics.confidence_level} ({confidence_metrics.overall_confidence:.0%})")
        signal.add_key_factor(f"Alignment: {alignment_factor:.0%}")
        signal.add_key_factor(f"Volume confirmation: {volume_factor:.0%}")

        if confidence_metrics.is_uncertain:
            signal.add_key_factor("⚠️ Uncertain signal - requires review")

        return signal

    def _build_aggregate_metadata(
        self,
        timeframe_signals: Dict[str, TimeframeSignal],
        direction: str,
        final_score: float,
        alignment_factor: float,
        volume_factor: float,
        htf_factor: float,
        volatility_factor: float,
        confidence_metrics: ConfidenceMetrics,
        sl_method: str,
        risk_reward_ratio: float,
        aggregated_score: SignalScore
    ) -> Dict[str, Any]:
        """
        Build comprehensive metadata from multi-timeframe aggregation.

        This includes ALL information from all timeframes for complete analysis.

        Args:
            timeframe_signals: Dict of TimeframeSignal objects by timeframe
            direction: Final signal direction
            final_score: Final aggregated score
            alignment_factor: TF alignment factor
            volume_factor: Volume confirmation factor
            htf_factor: HTF alignment factor
            volatility_factor: Volatility adjustment factor
            confidence_metrics: Confidence metrics object
            sl_method: SL/TP calculation method used
            risk_reward_ratio: Calculated risk/reward ratio
            aggregated_score: Complete score object with all multipliers

        Returns:
            Complete metadata dictionary
        """
        # Collect analyzer results from all timeframes
        timeframes_data = {}

        for tf, tf_signal in timeframe_signals.items():
            context = tf_signal.context
            df = context.df

            # Extract indicator values for this TF
            indicators = {}
            indicator_cols = [
                'ema_20', 'ema_50', 'ema_100', 'ema_200',
                'sma_20', 'sma_50', 'sma_200',
                'rsi', 'macd', 'macd_signal', 'macd_hist',
                'stoch_k', 'stoch_d',
                'atr', 'bb_upper', 'bb_middle', 'bb_lower',
                'obv', 'volume', 'volume_sma',
                'close', 'high', 'low', 'open'
            ]

            for col in indicator_cols:
                if col in df.columns:
                    try:
                        indicators[col] = float(df[col].iloc[-1])
                    except (ValueError, TypeError):
                        indicators[col] = None

            # Extract analyzer results for this TF
            analyzers = {}
            analyzer_names = [
                'trend', 'momentum', 'volume', 'patterns', 'sr',
                'volatility', 'harmonic', 'channel', 'cyclical', 'htf'
            ]

            for analyzer_name in analyzer_names:
                result = context.get_result(analyzer_name)
                if result:
                    analyzers[analyzer_name] = self._make_serializable(result)

            # Add this TF's data
            timeframes_data[tf] = {
                'indicators': indicators,
                'analyzers': analyzers,
                'signal_direction': tf_signal.direction,
                'signal_score': tf_signal.score.final_score if hasattr(tf_signal.score, 'final_score') else 0,
                'volume_confirmed': tf_signal.volume_confirmed,
                'htf_aligned': tf_signal.htf_aligned
            }

        # Build complete metadata
        metadata = {
            'aggregation_method': 'multi_timeframe_old_system',
            'direction': direction,
            'final_score': final_score,

            # SL/TP calculation (🆕 NEW SYSTEM)
            'sl_method': sl_method,
            'risk_reward_ratio': risk_reward_ratio,

            # Aggregation factors
            'alignment_factor': alignment_factor,
            'volume_factor': volume_factor,
            'htf_factor': htf_factor,
            'volatility_factor': volatility_factor,

            # 🆕 Score breakdown (13 multipliers from NEW SYSTEM)
            # Use getattr with defaults for safety (multi-TF aggregation may not populate all fields)
            'score_breakdown': {
                'base_score': getattr(aggregated_score, 'base_score', 0.0),
                'timeframe_weight': getattr(aggregated_score, 'timeframe_weight', 1.0),
                'trend_alignment': getattr(aggregated_score, 'trend_alignment', 1.0),
                'volume_confirmation': getattr(aggregated_score, 'volume_confirmation', 1.0),
                'pattern_quality': getattr(aggregated_score, 'pattern_quality', 1.0),
                'confluence_score': getattr(aggregated_score, 'confluence_score', 0.0),
                'symbol_performance_factor': getattr(aggregated_score, 'symbol_performance_factor', 1.0),
                'correlation_safety_factor': getattr(aggregated_score, 'correlation_safety_factor', 1.0),
                'macd_analysis_score': getattr(aggregated_score, 'macd_analysis_score', 1.0),
                'structure_score': getattr(aggregated_score, 'structure_score', 1.0),
                'volatility_score': getattr(aggregated_score, 'volatility_score', 1.0),
                'harmonic_pattern_score': getattr(aggregated_score, 'harmonic_pattern_score', 1.0),
                'price_channel_score': getattr(aggregated_score, 'price_channel_score', 1.0),
                'cyclical_pattern_score': getattr(aggregated_score, 'cyclical_pattern_score', 1.0),
                'final_score': getattr(aggregated_score, 'final_score', 0.0)
            },

            # Confidence metrics
            'confidence': {
                'level': confidence_metrics.confidence_level,
                'overall': confidence_metrics.overall_confidence,
                'timeframe_consensus': confidence_metrics.timeframe_consensus,
                'score_quality': confidence_metrics.score_quality,
                'direction_clarity': confidence_metrics.direction_clarity,
                'htf_alignment': confidence_metrics.htf_alignment,
                'volume_confirmation': confidence_metrics.volume_confirmation,
                'is_uncertain': confidence_metrics.is_uncertain,
                'requires_review': confidence_metrics.requires_review
            },

            # All timeframes data
            'timeframes': timeframes_data,
            'timeframes_used': list(timeframe_signals.keys()),
            'total_timeframes': len(timeframe_signals)
        }

        return metadata

    def _make_serializable(self, obj: Any) -> Any:
        """
        Convert object to JSON-serializable format.

        Args:
            obj: Object to convert

        Returns:
            Serializable version
        """
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            return self._make_serializable(obj.__dict__)
        elif isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        else:
            return str(obj)
