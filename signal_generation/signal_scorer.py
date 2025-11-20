"""
SignalScorer - Signal Scoring Engine

Combines results from 10 analyzers and calculates final signal score.

Scoring methodology:
1. Base scoring: Extract scores from each analyzer
2. Weighting: Apply configurable weights
3. Confluence: Calculate alignment bonus
4. Timeframe: Apply timeframe weight
5. HTF alignment: Boost/penalize based on HTF
6. Volatility adjustment: Adjust for market conditions
7. Final score: Combine all factors

Output: SignalScore with detailed breakdown
"""

from typing import Dict, Any, Optional, Tuple, List
import logging

from signal_generation.context import AnalysisContext
from signal_generation.signal_score import SignalScore

logger = logging.getLogger(__name__)


class SignalScorer:
    """
    Scores trading signals by combining analyzer results.
    
    Key features:
    1. Weighted scoring from 10 analyzers
    2. Confluence bonus calculation
    3. Timeframe-aware weighting
    4. HTF alignment multiplier
    5. Volatility adjustment
    6. Configurable weights and thresholds
    """
    
    # Default analyzer weights (sum should be ~1.0)
    DEFAULT_WEIGHTS = {
        'trend': 0.30,          # 30% - Most important
        'momentum': 0.25,       # 25%
        'volume': 0.20,         # 20%
        'patterns': 0.10,       # 10%
        'support_resistance': 0.08,  # 8%
        'volatility': 0.05,     # 5%
        'harmonic': 0.01,       # 1%
        'channel': 0.005,       # 0.5%
        'cyclical': 0.003,      # 0.3%
        'htf': 0.002            # 0.2%
    }
    
    # Timeframe weights (relative importance) - Aligned with OLD SYSTEM
    DEFAULT_TIMEFRAME_WEIGHTS = {
        '5m': 0.7,      # -30% importance (OLD SYSTEM value)
        '15m': 0.85,    # -15% importance (OLD SYSTEM value)
        '1h': 1.0,      # Reference timeframe
        '4h': 1.2       # +20% importance (OLD SYSTEM value)
    }
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize SignalScorer.

        Args:
            config: Configuration dictionary
        """
        self.config = config

        # Get scoring configuration
        scoring_config = config.get('signal_processing', {}).get('scoring', {})

        # Load weights (or use defaults)
        self.weights = scoring_config.get('weights', self.DEFAULT_WEIGHTS.copy())

        # Load timeframe weights
        self.timeframe_weights = scoring_config.get(
            'timeframe_weights',
            self.DEFAULT_TIMEFRAME_WEIGHTS.copy()
        )

        # 🆕 Load per-timeframe analyzer weights configuration
        self.weights_per_tf_config = scoring_config.get('weights_per_timeframe', {})
        self.weights_per_tf_enabled = self.weights_per_tf_config.get('enabled', False)

        # Scoring parameters
        self.base_score_scale = scoring_config.get('base_score_scale', 100)
        self.max_confluence_bonus = scoring_config.get('max_confluence_bonus', 0.5)
        self.htf_alignment_bonus = scoring_config.get('htf_alignment_bonus', 0.3)
        self.htf_misalignment_penalty = scoring_config.get('htf_misalignment_penalty', 0.3)

        # ⚙️ NEW: Scoring method selection ('new', 'old', 'hybrid')
        self.scoring_method = scoring_config.get('scoring_method', 'new')

        # Load OLD SYSTEM configuration (for 'old' or 'hybrid' modes)
        self.old_system_config = scoring_config.get('old_system', {})
        self.max_final_score = self.old_system_config.get('max_final_score', 300.0)

        # Override max_final_score based on method
        if self.scoring_method == 'new':
            self.max_final_score = 300.0  # Always limited for NEW
        elif self.scoring_method == 'old':
            # Use config value (0 = unlimited, OLD style)
            self.max_final_score = self.old_system_config.get('max_final_score', 0)

        logger.info(
            f"SignalScorer initialized successfully "
            f"(method={self.scoring_method}, max_score={self.max_final_score})"
        )
    
    def calculate_score(
        self,
        context: AnalysisContext,
        direction: str
    ) -> Optional[SignalScore]:
        """
        Calculate signal score from analysis context.
        
        Args:
            context: AnalysisContext with analyzer results
            direction: 'LONG' or 'SHORT'
            
        Returns:
            SignalScore if valid, None otherwise
        """
        try:
            # 1. Validate inputs
            if not self._validate_context(context):
                logger.warning(f"Invalid context for {context.symbol}")
                return None
            
            if direction not in ['LONG', 'SHORT']:
                logger.error(f"Invalid direction: {direction}")
                return None
            
            # 2. Create score object
            score = SignalScore()
            
            # 3. Calculate base scores from each analyzer
            self._calculate_base_scores(score, context, direction)

            # 4. Apply weights (with per-TF support)
            self._apply_weights(score, context.timeframe)

            # 5. Calculate confluence bonus
            self._calculate_confluence(score, context, direction)
            
            # 6. Apply timeframe weight
            self._apply_timeframe_weight(score, context.timeframe)
            
            # 7. Apply HTF multiplier
            self._apply_htf_multiplier(score, context, direction)
            
            # 8. Apply volatility adjustment
            self._apply_volatility_adjustment(score, context)

            # 9. NEW: Apply trend alignment multiplier
            self._apply_trend_alignment(score, context, direction)

            # 10. NEW: Apply volume confirmation multiplier
            self._apply_volume_confirmation(score, context, direction)

            # 11. NEW: Apply pattern quality multiplier
            self._apply_pattern_quality(score, context)

            # 12. NEW: Apply MACD analysis score multiplier
            self._apply_macd_analysis_score(score, context)

            # 13. Calculate final score (with method selection)
            score.calculate_final_score(
                method=self.scoring_method,
                max_score=self.max_final_score
            )

            # 14. Determine strength and confidence
            score.determine_signal_strength()
            score.calculate_confidence()

            # 15. Build breakdown
            score.build_breakdown()
            
            logger.debug(
                f"Scored signal for {context.symbol}: {score.final_score:.2f} "
                f"({score.signal_strength}, conf={score.confidence:.2f})"
            )
            
            return score
            
        except Exception as e:
            logger.error(f"Error calculating score for {context.symbol}: {e}", exc_info=True)
            return None
    
    def _calculate_base_scores(
        self,
        score: SignalScore,
        context: AnalysisContext,
        direction: str
    ) -> None:
        """
        Calculate base scores from each analyzer.
        
        Args:
            score: SignalScore to populate
            context: AnalysisContext with results
            direction: 'LONG' or 'SHORT'
        """
        # 1. Trend score
        trend_result = context.get_result('trend')
        if trend_result:
            score.trend_score = self._score_trend(trend_result, direction)
            if score.trend_score > 0:
                score.contributing_analyzers.append('trend')
        
        # 2. Momentum score
        momentum_result = context.get_result('momentum')
        if momentum_result:
            score.momentum_score = self._score_momentum(momentum_result, direction)
            if score.momentum_score > 0:
                score.contributing_analyzers.append('momentum')
        
        # 3. Volume score
        volume_result = context.get_result('volume')
        if volume_result:
            score.volume_score = self._score_volume(volume_result, direction)
            if score.volume_score > 0:
                score.contributing_analyzers.append('volume')
        
        # 4. Pattern score
        pattern_result = context.get_result('patterns')
        if pattern_result:
            score.pattern_score = self._score_patterns(pattern_result, direction, score)  # ✨ ارسال score برای ذخیره جزئیات
            if score.pattern_score > 0:
                score.contributing_analyzers.append('patterns')
        
        # 5. SR score
        sr_result = context.get_result('support_resistance')
        if sr_result:
            score.sr_score = self._score_sr(sr_result, direction, context.df['close'].iloc[-1])
            if score.sr_score > 0:
                score.contributing_analyzers.append('support_resistance')
        
        # 6. Volatility score
        volatility_result = context.get_result('volatility')
        if volatility_result:
            score.volatility_score = self._score_volatility(volatility_result)
            if score.volatility_score > 0:
                score.contributing_analyzers.append('volatility')
        
        # 7. Harmonic score
        harmonic_result = context.get_result('harmonic')
        if harmonic_result:
            score.harmonic_score = self._score_harmonic(harmonic_result, direction)
            if score.harmonic_score > 0:
                score.contributing_analyzers.append('harmonic')
        
        # 8. Channel score
        channel_result = context.get_result('channel')
        if channel_result:
            score.channel_score = self._score_channel(channel_result, direction)
            if score.channel_score > 0:
                score.contributing_analyzers.append('channel')
        
        # 9. Cyclical score
        cyclical_result = context.get_result('cyclical')
        if cyclical_result:
            score.cyclical_score = self._score_cyclical(cyclical_result, direction)
            if score.cyclical_score > 0:
                score.contributing_analyzers.append('cyclical')
        
        # 10. HTF score
        htf_result = context.get_result('htf')
        if htf_result:
            score.htf_score = self._score_htf(htf_result, direction)
            if score.htf_score > 0:
                score.contributing_analyzers.append('htf')
    
    def _score_trend(self, trend_result: Dict, direction: str) -> float:
        """Score trend analyzer result."""
        trend_direction = trend_result.get('direction', 'neutral')
        strength = abs(trend_result.get('strength', 0))
        
        # Check alignment
        if direction == 'LONG' and trend_direction in ['bullish', 'bullish_aligned']:
            return strength * 33.33  # Max 100 (strength 3)
        elif direction == 'SHORT' and trend_direction in ['bearish', 'bearish_aligned']:
            return strength * 33.33
        elif trend_direction in ['sideways', 'neutral']:
            return 10  # Small score for neutral
        else:
            return 0  # Against trend
    
    def _score_momentum(self, momentum_result: Dict, direction: str) -> float:
        """Score momentum analyzer result."""
        mom_direction = momentum_result.get('direction', 'neutral')
        strength = abs(momentum_result.get('strength', 0))
        
        # Check RSI conditions
        rsi_signal = momentum_result.get('rsi_signal', 'neutral')
        
        base_score = 0
        
        if direction == 'LONG':
            if mom_direction == 'bullish':
                base_score = strength * 25  # Max 75
            if rsi_signal == 'oversold':
                base_score += 25  # Bonus for oversold in LONG
        elif direction == 'SHORT':
            if mom_direction == 'bearish':
                base_score = strength * 25
            if rsi_signal == 'overbought':
                base_score += 25
        
        return min(base_score, 100)
    
    def _score_volume(self, volume_result: Dict, direction: str) -> float:
        """Score volume analyzer result."""
        is_confirmed = volume_result.get('is_confirmed', False)
        volume_ratio = volume_result.get('volume_ratio', 1.0)
        
        if not is_confirmed:
            return 0
        
        # Higher volume ratio = higher score
        score = min(volume_ratio * 30, 100)
        
        return score
    
    def _score_patterns(self, pattern_result: Dict, direction: str, score: SignalScore) -> float:
        """
        Score pattern analyzer result and populate pattern details.

        Args:
            pattern_result: Pattern analysis results
            direction: Signal direction ('LONG' or 'SHORT')
            score: SignalScore object to populate with pattern details

        Returns:
            Pattern score (0-100)
        """
        patterns = pattern_result.get('candlestick_patterns', []) + pattern_result.get('chart_patterns', [])

        if not patterns:
            return 0

        total_score = 0

        # ✨ ذخیره تمام الگوهای تشخیص داده شده
        score.detected_patterns = patterns.copy()

        for pattern in patterns:
            pattern_direction = pattern.get('direction', 'neutral')
            adjusted_strength = pattern.get('adjusted_strength', 0)
            pattern_name = pattern.get('name', 'Unknown')

            # محاسبه سهم هر الگو
            contribution = 0

            # Check alignment
            if direction == 'LONG' and pattern_direction == 'bullish':
                contribution = adjusted_strength * 20
                total_score += contribution
            elif direction == 'SHORT' and pattern_direction == 'bearish':
                contribution = adjusted_strength * 20
                total_score += contribution

            # ✨ ذخیره سهم هر الگو در امتیاز کل
            if contribution > 0:
                score.pattern_contributions[pattern_name] = contribution

        return min(total_score, 100)
    
    def _score_sr(self, sr_result: Dict, direction: str, current_price: float) -> float:
        """Score support/resistance analyzer result."""
        nearest_support = sr_result.get('nearest_support')
        nearest_resistance = sr_result.get('nearest_resistance')
        
        if not nearest_support and not nearest_resistance:
            return 0
        
        score = 0
        
        # For LONG: check distance to support
        if direction == 'LONG' and nearest_support:
            distance = abs(current_price - nearest_support) / current_price
            # Closer to support = higher score
            if distance < 0.01:  # Within 1%
                score = 80
            elif distance < 0.02:  # Within 2%
                score = 60
            elif distance < 0.03:  # Within 3%
                score = 40
            else:
                score = 20
        
        # For SHORT: check distance to resistance
        elif direction == 'SHORT' and nearest_resistance:
            distance = abs(current_price - nearest_resistance) / current_price
            if distance < 0.01:
                score = 80
            elif distance < 0.02:
                score = 60
            elif distance < 0.03:
                score = 40
            else:
                score = 20
        
        return score
    
    def _score_volatility(self, volatility_result: Dict) -> float:
        """Score volatility analyzer result."""
        regime = volatility_result.get('volatility_regime', 'normal')
        confidence = volatility_result.get('confidence', 0.5)
        
        # Different regimes have different scores
        regime_scores = {
            'low': 80,      # Low volatility is good
            'normal': 60,   # Normal is okay
            'high': 30      # High volatility is risky
        }
        
        base_score = regime_scores.get(regime, 50)
        
        # Adjust by confidence
        score = base_score * confidence
        
        return score
    
    def _score_harmonic(self, harmonic_result: Dict, direction: str) -> float:
        """Score harmonic analyzer result."""
        patterns = harmonic_result.get('patterns', [])
        
        if not patterns:
            return 0
        
        total_score = 0
        
        for pattern in patterns:
            pattern_type = pattern.get('type', 'neutral')
            completion = pattern.get('completion', 0)
            
            if direction == 'LONG' and pattern_type == 'bullish':
                total_score += completion * 50
            elif direction == 'SHORT' and pattern_type == 'bearish':
                total_score += completion * 50
        
        return min(total_score, 100)
    
    def _score_channel(self, channel_result: Dict, direction: str) -> float:
        """Score channel analyzer result."""
        channel_type = channel_result.get('channel_type', 'unknown')
        position = channel_result.get('price_position', 'middle')
        strength = channel_result.get('strength', 0)
        
        score = 0
        
        if direction == 'LONG':
            if channel_type == 'ascending' and position == 'lower':
                score = strength * 30
            elif position == 'lower':
                score = 20
        elif direction == 'SHORT':
            if channel_type == 'descending' and position == 'upper':
                score = strength * 30
            elif position == 'upper':
                score = 20
        
        return min(score, 100)
    
    def _score_cyclical(self, cyclical_result: Dict, direction: str) -> float:
        """Score cyclical analyzer result."""
        cycle_phase = cyclical_result.get('cycle_phase', 'unknown')
        confidence = cyclical_result.get('confidence', 0)
        
        score = 0
        
        if direction == 'LONG' and cycle_phase == 'bottom':
            score = 70 * confidence
        elif direction == 'SHORT' and cycle_phase == 'top':
            score = 70 * confidence
        elif cycle_phase == 'rising' and direction == 'LONG':
            score = 40 * confidence
        elif cycle_phase == 'falling' and direction == 'SHORT':
            score = 40 * confidence
        
        return score
    
    def _score_htf(self, htf_result: Dict, direction: str) -> float:
        """Score HTF analyzer result."""
        htf_trend = htf_result.get('htf_trend', 'unknown')
        alignment = htf_result.get('alignment', False)
        
        if alignment:
            return 100  # Perfect alignment
        elif htf_trend == direction.lower().replace('long', 'bullish').replace('short', 'bearish'):
            return 70  # Trend matches
        else:
            return 0  # Against HTF
    
    def get_weight(
        self,
        analyzer_name: str,
        default_weight: float,
        timeframe: str = None
    ) -> float:
        """
        Get analyzer weight with per-timeframe support.

        Fallback chain:
        1. Per-TF weight (if enabled and TF exists)
        2. Global weight
        3. Default weight

        Args:
            analyzer_name: Analyzer name (e.g., 'trend', 'momentum')
            default_weight: Default weight value
            timeframe: Current timeframe (e.g., '5m', '1h', '4h')

        Returns:
            Weight for the analyzer (per-TF if available, otherwise global or default)
        """
        # Check if per-TF weights are enabled
        if self.weights_per_tf_enabled and timeframe:
            # Try to get timeframe-specific weight
            tf_weights = self.weights_per_tf_config.get(timeframe, {})
            if analyzer_name in tf_weights:
                logger.debug(
                    f"Using per-TF weight {analyzer_name}={tf_weights[analyzer_name]} for {timeframe}"
                )
                return tf_weights[analyzer_name]

        # Fallback to global weight
        if analyzer_name in self.weights:
            return self.weights[analyzer_name]

        # Final fallback to default
        return default_weight

    def _apply_weights(self, score: SignalScore, timeframe: str = None) -> None:
        """
        Apply analyzer weights to base scores.

        Args:
            score: SignalScore to populate
            timeframe: Current timeframe for per-TF weights
        """
        score.weighted_trend = score.trend_score * self.get_weight('trend', 0.30, timeframe)
        score.weighted_momentum = score.momentum_score * self.get_weight('momentum', 0.25, timeframe)
        score.weighted_volume = score.volume_score * self.get_weight('volume', 0.20, timeframe)
        score.weighted_pattern = score.pattern_score * self.get_weight('patterns', 0.10, timeframe)
        score.weighted_sr = score.sr_score * self.get_weight('support_resistance', 0.08, timeframe)
        score.weighted_volatility = score.volatility_score * self.get_weight('volatility', 0.05, timeframe)
        score.weighted_harmonic = score.harmonic_score * self.get_weight('harmonic', 0.01, timeframe)
        score.weighted_channel = score.channel_score * self.get_weight('channel', 0.005, timeframe)
        score.weighted_cyclical = score.cyclical_score * self.get_weight('cyclical', 0.003, timeframe)
        score.weighted_htf = score.htf_score * self.get_weight('htf', 0.002, timeframe)
        
        # Sum weighted scores
        score.base_score = (
            score.weighted_trend +
            score.weighted_momentum +
            score.weighted_volume +
            score.weighted_pattern +
            score.weighted_sr +
            score.weighted_volatility +
            score.weighted_harmonic +
            score.weighted_channel +
            score.weighted_cyclical +
            score.weighted_htf
        )
    
    def _calculate_confluence(
        self,
        score: SignalScore,
        context: AnalysisContext,
        direction: str
    ) -> None:
        """
        Calculate confluence bonus - HYBRID approach (RR + Alignment).

        This combines two methodologies:
        1. Alignment Bonus: Rewards when multiple analyzers agree (NEW SYSTEM)
        2. Risk/Reward Bonus: Rewards good risk/reward ratio (OLD SYSTEM)

        Total confluence bonus range: 0.0 - 0.5 (max 50%)
        """
        # ─── PART 1: Alignment Bonus (همگرایی Analyzers) ───
        aligned_count = 0

        # Check each analyzer for alignment
        analyzers_to_check = [
            ('trend', self._is_trend_aligned),
            ('momentum', self._is_momentum_aligned),
            ('volume', self._is_volume_aligned),
            ('patterns', self._is_patterns_aligned),
            ('htf', self._is_htf_aligned)
        ]

        for analyzer_name, check_func in analyzers_to_check:
            result = context.get_result(analyzer_name)
            if result and check_func(result, direction):
                aligned_count += 1

        score.aligned_analyzers = aligned_count
        total_analyzers = len(analyzers_to_check)

        # Calculate alignment ratio
        if total_analyzers > 0:
            alignment_ratio = aligned_count / total_analyzers
            alignment_bonus = alignment_ratio * 0.25  # Max +0.25 (25%)
        else:
            alignment_ratio = 0
            alignment_bonus = 0

        # ─── PART 2: Risk/Reward Bonus (RR نسبت) ───
        # Get risk/reward ratio from context metadata
        risk_reward_ratio = context.metadata.get('risk_reward_ratio', 0)
        min_rr = 2.0  # Minimum acceptable RR

        if risk_reward_ratio >= min_rr:
            # OLD SYSTEM formula: bonus for good RR
            # RR 2.0 → 0.00
            # RR 3.0 → 0.125 (12.5%)
            # RR 4.0+ → 0.25 (25%, capped)
            rr_bonus = min(0.25, (risk_reward_ratio - min_rr) * 0.125)
        else:
            rr_bonus = 0

        # ─── PART 3: Combine Both ───
        total_confluence = alignment_bonus + rr_bonus

        # Cap at maximum (0.5 = 50%)
        score.confluence_bonus = min(0.5, total_confluence)

        # Store details for debugging/analysis
        score.confluence_details = {
            'alignment_bonus': alignment_bonus,
            'alignment_ratio': alignment_ratio,
            'aligned_count': aligned_count,
            'total_analyzers': total_analyzers,
            'rr_bonus': rr_bonus,
            'risk_reward_ratio': risk_reward_ratio,
            'total_confluence': total_confluence
        }

        logger.debug(
            f"Confluence calculated: alignment={alignment_bonus:.3f} "
            f"({aligned_count}/{total_analyzers}), "
            f"rr={rr_bonus:.3f} (RR={risk_reward_ratio:.2f}), "
            f"total={score.confluence_bonus:.3f}"
        )
    
    def _is_trend_aligned(self, trend_result: Dict, direction: str) -> bool:
        """Check if trend aligns with direction."""
        trend = trend_result.get('direction', 'neutral')
        if direction == 'LONG':
            return trend in ['bullish', 'bullish_aligned']
        else:
            return trend in ['bearish', 'bearish_aligned']
    
    def _is_momentum_aligned(self, momentum_result: Dict, direction: str) -> bool:
        """Check if momentum aligns with direction."""
        mom_dir = momentum_result.get('direction', 'neutral')
        if direction == 'LONG':
            return mom_dir == 'bullish'
        else:
            return mom_dir == 'bearish'
    
    def _is_volume_aligned(self, volume_result: Dict, direction: str) -> bool:
        """Check if volume confirms signal."""
        return volume_result.get('is_confirmed', False)
    
    def _is_patterns_aligned(self, pattern_result: Dict, direction: str) -> bool:
        """Check if patterns align with direction."""
        return pattern_result.get('alignment_with_trend', False)
    
    def _is_htf_aligned(self, htf_result: Dict, direction: str) -> bool:
        """Check if HTF aligns with direction."""
        return htf_result.get('alignment', False)
    
    def _apply_timeframe_weight(self, score: SignalScore, timeframe: str) -> None:
        """Apply timeframe-specific weight."""
        score.timeframe_weight = self.timeframe_weights.get(timeframe, 1.0)
    
    def _apply_htf_multiplier(
        self,
        score: SignalScore,
        context: AnalysisContext,
        direction: str
    ) -> None:
        """Apply HTF alignment multiplier."""
        htf_result = context.get_result('htf')
        
        if not htf_result or htf_result.get('status') != 'ok':
            score.htf_multiplier = 1.0
            return
        
        alignment = htf_result.get('alignment', False)
        
        if alignment:
            # HTF aligns → bonus
            score.htf_multiplier = 1.0 + self.htf_alignment_bonus
        else:
            # HTF misaligned → penalty
            score.htf_multiplier = 1.0 - self.htf_misalignment_penalty
    
    def _apply_volatility_adjustment(
        self,
        score: SignalScore,
        context: AnalysisContext
    ) -> None:
        """Apply volatility-based adjustment."""
        volatility_result = context.get_result('volatility')
        
        if not volatility_result or volatility_result.get('status') != 'ok':
            score.volatility_multiplier = 1.0
            return
        
        # Use risk_multiplier directly from VolatilityAnalyzer
        score.volatility_multiplier = volatility_result.get('risk_multiplier', 1.0)
    
    def _apply_trend_alignment(
        self,
        score: SignalScore,
        context: AnalysisContext,
        direction: str
    ) -> None:
        """
        Apply trend alignment multiplier (OLD SYSTEM logic).

        Range: 0.8 - 1.2
        - Perfect alignment: 1.2
        - Good alignment: 1.1
        - Neutral: 1.0
        - Against trend: 0.8-0.9
        """
        trend_result = context.get_result('trend')

        if not trend_result or trend_result.get('status') != 'ok':
            score.trend_alignment = 1.0
            return

        trend_direction = trend_result.get('direction', 'neutral')
        trend_strength = abs(trend_result.get('strength', 0))

        # Check alignment
        if direction == 'LONG':
            if trend_direction in ['bullish', 'bullish_aligned']:
                # Aligned with bullish trend
                if trend_strength >= 2.5:
                    score.trend_alignment = 1.2  # Perfect alignment
                elif trend_strength >= 1.5:
                    score.trend_alignment = 1.1  # Good alignment
                else:
                    score.trend_alignment = 1.05  # Weak alignment
            elif trend_direction in ['sideways', 'neutral']:
                score.trend_alignment = 1.0  # Neutral
            else:
                # Against trend (bearish trend but LONG signal)
                score.trend_alignment = 0.8  # Penalty
        elif direction == 'SHORT':
            if trend_direction in ['bearish', 'bearish_aligned']:
                # Aligned with bearish trend
                if trend_strength >= 2.5:
                    score.trend_alignment = 1.2
                elif trend_strength >= 1.5:
                    score.trend_alignment = 1.1
                else:
                    score.trend_alignment = 1.05
            elif trend_direction in ['sideways', 'neutral']:
                score.trend_alignment = 1.0
            else:
                # Against trend (bullish trend but SHORT signal)
                score.trend_alignment = 0.8

    def _apply_volume_confirmation(
        self,
        score: SignalScore,
        context: AnalysisContext,
        direction: str
    ) -> None:
        """
        Apply volume confirmation multiplier (OLD SYSTEM logic).

        Range: 1.0 or 1.1
        - Confirmed by volume: 1.1 (+10% bonus)
        - Not confirmed: 1.0
        """
        volume_result = context.get_result('volume')

        if not volume_result or volume_result.get('status') != 'ok':
            score.volume_confirmation = 1.0
            return

        is_confirmed = volume_result.get('is_confirmed', False)

        if is_confirmed:
            score.volume_confirmation = 1.1  # +10% bonus
        else:
            score.volume_confirmation = 1.0

    def _apply_pattern_quality(
        self,
        score: SignalScore,
        context: AnalysisContext
    ) -> None:
        """
        Apply pattern quality multiplier (OLD SYSTEM logic).

        Formula: 1.0 + min(0.5, len(patterns) * 0.1)
        Range: 1.0 - 1.5
        - No patterns: 1.0
        - 1 pattern: 1.1
        - 2 patterns: 1.2
        - 3 patterns: 1.3
        - 4 patterns: 1.4
        - 5+ patterns: 1.5 (capped)
        """
        pattern_result = context.get_result('patterns')

        if not pattern_result or pattern_result.get('status') != 'ok':
            score.pattern_quality = 1.0
            return

        # Get all patterns (candlestick + chart patterns)
        candlestick_patterns = pattern_result.get('candlestick_patterns', [])
        chart_patterns = pattern_result.get('chart_patterns', [])
        all_patterns = candlestick_patterns + chart_patterns

        pattern_count = len(all_patterns)

        # OLD SYSTEM formula
        score.pattern_quality = 1.0 + min(0.5, pattern_count * 0.1)

    def _apply_macd_analysis_score(
        self,
        score: SignalScore,
        context: AnalysisContext
    ) -> None:
        """
        Apply MACD analysis score multiplier (OLD SYSTEM logic).

        Formula: 1.0 + ((alignment_factor - 1.0) * 0.5)
        Where alignment_factor ranges from 0.7 to 1.3

        Result range: 0.85 - 1.15
        - Perfect alignment (1.3): 1.0 + ((1.3 - 1.0) * 0.5) = 1.15
        - Good alignment (1.2): 1.0 + ((1.2 - 1.0) * 0.5) = 1.10
        - Neutral (1.0): 1.0 + ((1.0 - 1.0) * 0.5) = 1.0
        - Poor alignment (0.7): 1.0 + ((0.7 - 1.0) * 0.5) = 0.85
        """
        momentum_result = context.get_result('momentum')

        if not momentum_result or momentum_result.get('status') != 'ok':
            score.macd_analysis_score = 1.0
            return

        # Get MACD signal details
        macd_signal = momentum_result.get('macd_signal', {})
        if not macd_signal:
            score.macd_analysis_score = 1.0
            return

        # Calculate alignment factor based on MACD strength and direction
        macd_direction = macd_signal.get('direction', 'neutral')
        mom_direction = momentum_result.get('direction', 'neutral')

        # Simple alignment: check if MACD agrees with overall momentum
        if macd_direction == mom_direction and macd_direction != 'neutral':
            # Good alignment
            alignment_factor = 1.2  # Good MACD alignment
        elif macd_direction == 'neutral':
            alignment_factor = 1.0  # Neutral
        else:
            # Poor alignment
            alignment_factor = 0.85  # MACD disagrees

        # OLD SYSTEM formula: adjust based on how much MACD aligns
        # Simplified version: directly use alignment strength
        score.macd_analysis_score = alignment_factor

    def _validate_context(self, context: AnalysisContext) -> bool:
        """Validate that context has minimum required results."""
        required = ['trend', 'momentum', 'volume']

        for analyzer in required:
            if not context.get_result(analyzer):
                logger.warning(f"Missing required analyzer: {analyzer}")
                return False

        return True
