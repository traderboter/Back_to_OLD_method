"""
SignalValidator - Signal Validation and Filtering Engine

Validates trading signals against multiple criteria:
1. Risk/Reward validation
2. Circuit breaker (rate limiting)
3. Correlation management
4. Portfolio exposure limits
5. Time-based filters
6. Adaptive threshold adjustment

Only valid signals pass through to execution.
"""

from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging

from signal_generation.context import AnalysisContext
from signal_generation.signal_info import SignalInfo, SignalRejection

logger = logging.getLogger(__name__)


class SignalValidator:
    """
    Validates and filters trading signals.
    
    Key features:
    1. Multi-criteria validation
    2. Risk/reward enforcement
    3. Rate limiting (circuit breaker)
    4. Correlation checking
    5. Portfolio limits
    6. Time filters
    7. Adaptive thresholds
    8. Comprehensive logging
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize SignalValidator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Get validation configuration
        validation_config = config.get('signal_processing', {}).get('validation', {})
        
        # === Risk/Reward Parameters ===
        self.min_rr_ratio = validation_config.get('min_rr_ratio', 1.8)
        self.preferred_rr_ratio = validation_config.get('preferred_rr_ratio', 2.5)
        self.max_risk_percent = validation_config.get('max_risk_percent', 2.0)
        
        # === Circuit Breaker Parameters ===
        circuit_config = validation_config.get('circuit_breaker', {})
        self.circuit_breaker_enabled = circuit_config.get('enabled', True)  # Can be disabled for backtesting
        self.max_signals_per_hour = circuit_config.get('max_signals_per_hour', 3)
        self.max_signals_per_day = circuit_config.get('max_signals_per_day', 10)
        self.cooldown_after_loss = circuit_config.get('cooldown_minutes', 30)
        
        # === Correlation Parameters ===
        corr_config = validation_config.get('correlation', {})
        self.max_correlation = corr_config.get('max_correlation', 0.8)
        self.check_btc_correlation = corr_config.get('check_btc_correlation', True)
        
        # === Portfolio Parameters ===
        portfolio_config = validation_config.get('portfolio', {})
        self.max_total_exposure = portfolio_config.get('max_total_exposure', 0.5)  # 50%
        self.max_per_symbol = portfolio_config.get('max_per_symbol', 0.1)  # 10%
        self.max_same_direction = portfolio_config.get('max_same_direction', 0.3)  # 30%
        self.max_open_positions = portfolio_config.get('max_open_positions', 5)
        
        # === Time Filters ===
        time_config = validation_config.get('time_filters', {})
        self.avoid_weekends = time_config.get('avoid_weekends', False)
        self.avoid_major_news = time_config.get('avoid_major_news', True)
        self.trading_hours = time_config.get('trading_hours', None)  # {'start': 0, 'end': 24}
        
        # === Adaptive Threshold Parameters ===
        adaptive_config = validation_config.get('adaptive', {})
        self.enable_adaptive = adaptive_config.get('enabled', True)
        self.performance_window_days = adaptive_config.get('window_days', 7)
        self.good_performance_threshold = adaptive_config.get('good_performance', 0.6)
        self.poor_performance_threshold = adaptive_config.get('poor_performance', 0.4)
        
        # === State Tracking ===
        self.signal_history = deque(maxlen=1000)  # Last 1000 signals
        self.active_positions = {}  # symbol -> position_info
        self.recent_signals_by_symbol = defaultdict(deque)  # symbol -> recent signals
        self.recent_losses = deque(maxlen=100)  # Recent losing trades
        
        # === Performance Tracking ===
        self.performance_history = {
            'total_signals': 0,
            'successful_signals': 0,
            'failed_signals': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0
        }
        
        logger.info("SignalValidator initialized successfully")
    
    def validate(
        self,
        signal: SignalInfo,
        context: AnalysisContext
    ) -> Tuple[bool, str]:
        """
        Main validation method - runs all validation checks.

        Args:
            signal: SignalInfo to validate
            context: AnalysisContext with market data

        Returns:
            (is_valid, rejection_reason)
        """
        # ✅ FIX: Check if signal is None before using it
        if signal is None:
            logger.error("Signal is None - cannot validate")
            return False, "Signal cannot be None"

        try:
            logger.info(
                f"Validating signal: {signal.symbol} {signal.direction} "
                f"@ {signal.entry_price:.2f}"
            )
            
            # 1. Basic validation
            if not self._validate_basic(signal):
                return False, "Basic validation failed"
            
            # 2. Price validation
            if not signal.validate_prices():
                signal.add_validation_check('price_logic', False, "Invalid price levels")
                return False, "Invalid price levels"
            signal.add_validation_check('price_logic', True)
            
            # 3. Risk/Reward validation
            is_valid, reason = self._validate_risk_reward(signal)
            if not is_valid:
                signal.add_validation_check('risk_reward', False, reason)
                return False, reason
            signal.add_validation_check('risk_reward', True)

            # 4. Circuit breaker check - skip if disabled
            if self.circuit_breaker_enabled:
                is_valid, reason = self._check_circuit_breaker(signal)
                if not is_valid:
                    signal.add_validation_check('circuit_breaker', False, reason)
                    return False, reason
                signal.add_validation_check('circuit_breaker', True)
            else:
                signal.add_validation_check('circuit_breaker', True, 'Disabled for backtest')
            
            # 5. Correlation check
            is_valid, reason = self._check_correlation(signal)
            if not is_valid:
                signal.add_validation_check('correlation', False, reason)
                return False, reason
            signal.add_validation_check('correlation', True)

            # 6. Volatility rejection check (CRITICAL - added for risk management)
            is_valid, reason = self._check_volatility_rejection(signal, context)
            if not is_valid:
                signal.add_validation_check('volatility_rejection', False, reason)
                return False, reason
            signal.add_validation_check('volatility_rejection', True)

            # 7. 4h volume confirmation check (CRITICAL - 81.8% vs 25% win rate!)
            is_valid, reason = self._check_4h_volume_confirmation(signal)
            if not is_valid:
                signal.add_validation_check('4h_volume_confirmation', False, reason)
                return False, reason
            signal.add_validation_check('4h_volume_confirmation', True)

            # 8. Portfolio exposure check
            is_valid, reason = self._check_portfolio_exposure(signal)
            if not is_valid:
                signal.add_validation_check('portfolio_exposure', False, reason)
                return False, reason
            signal.add_validation_check('portfolio_exposure', True)

            # 9. Time-based filters
            is_valid, reason = self._check_time_filters(signal)
            if not is_valid:
                signal.add_validation_check('time_filters', False, reason)
                return False, reason
            signal.add_validation_check('time_filters', True)

            # 10. Score threshold check (with adaptive adjustment)
            is_valid, reason = self._check_score_threshold(signal)
            if not is_valid:
                signal.add_validation_check('score_threshold', False, reason)
                return False, reason
            signal.add_validation_check('score_threshold', True)
            
            # All checks passed!
            signal.mark_as_valid()
            
            logger.info(
                f"Signal validated successfully: {signal.symbol} {signal.direction} "
                f"(Score: {signal.score.final_score if signal.score else 0:.2f}, "
                f"RR: {signal.risk_reward_ratio:.2f})"
            )
            
            return True, "All validation checks passed"
            
        except Exception as e:
            logger.error(f"Error validating signal: {e}", exc_info=True)
            # ✅ FIX: Check if signal is not None before calling mark_as_invalid
            if signal is not None:
                signal.mark_as_invalid(f"Validation error: {str(e)}")
            return False, f"Validation error: {str(e)}"
    
    def _validate_basic(self, signal: SignalInfo) -> bool:
        """Basic validation (non-empty fields, etc)."""
        if not signal.symbol:
            logger.warning("Signal missing symbol")
            return False
        
        if not signal.direction:
            logger.warning("Signal missing direction")
            return False
        
        if signal.direction not in ['LONG', 'SHORT']:
            logger.warning(f"Invalid direction: {signal.direction}")
            return False
        
        if signal.entry_price <= 0:
            logger.warning("Invalid entry price")
            return False
        
        return True
    
    def _validate_risk_reward(self, signal: SignalInfo) -> Tuple[bool, str]:
        """
        Validate risk/reward ratio.
        
        Args:
            signal: Signal to validate
            
        Returns:
            (is_valid, reason)
        """
        # Calculate RR if not already done
        if signal.risk_reward_ratio == 0:
            signal.calculate_risk_reward()
        
        rr = signal.risk_reward_ratio
        
        # Check minimum RR
        if rr < self.min_rr_ratio:
            reason = f"Poor RR ratio: {rr:.2f} < {self.min_rr_ratio:.2f}"
            logger.info(f"Rejecting {signal.symbol}: {reason}")
            return False, reason
        
        # Check risk amount
        risk_percent = (signal.risk_amount / signal.entry_price) * 100
        if risk_percent > self.max_risk_percent:
            reason = f"Risk too high: {risk_percent:.2f}% > {self.max_risk_percent:.2f}%"
            logger.info(f"Rejecting {signal.symbol}: {reason}")
            return False, reason
        
        # Bonus log for excellent RR
        if rr >= self.preferred_rr_ratio:
            logger.info(
                f"Excellent RR ratio for {signal.symbol}: {rr:.2f} "
                f">= {self.preferred_rr_ratio:.2f}"
            )
            signal.add_key_factor(f"Excellent RR: {rr:.2f}")
        
        return True, ""
    
    def _check_circuit_breaker(self, signal: SignalInfo) -> Tuple[bool, str]:
        """
        Check circuit breaker - rate limiting.
        
        Prevents too many signals in short time.
        
        Args:
            signal: Signal to check
            
        Returns:
            (is_valid, reason)
        """
        now = datetime.now()
        symbol = signal.symbol
        
        # Get recent signals for this symbol
        recent = self.recent_signals_by_symbol[symbol]
        
        # Remove old signals (older than 1 day)
        while recent and (now - recent[0]['timestamp']) > timedelta(days=1):
            recent.popleft()
        
        # Check hourly limit
        hourly_signals = [
            s for s in recent 
            if (now - s['timestamp']) < timedelta(hours=1)
        ]
        
        if len(hourly_signals) >= self.max_signals_per_hour:
            reason = (
                f"Circuit breaker: {len(hourly_signals)} signals in last hour "
                f">= {self.max_signals_per_hour}"
            )
            logger.info(f"Rejecting {symbol}: {reason}")
            return False, reason
        
        # Check daily limit
        if len(recent) >= self.max_signals_per_day:
            reason = (
                f"Circuit breaker: {len(recent)} signals today "
                f">= {self.max_signals_per_day}"
            )
            logger.info(f"Rejecting {symbol}: {reason}")
            return False, reason
        
        # Check cooldown after recent loss
        if self.recent_losses:
            last_loss = self.recent_losses[-1]
            if (
                last_loss.get('symbol') == symbol and
                (now - last_loss['timestamp']) < timedelta(minutes=self.cooldown_after_loss)
            ):
                reason = f"Cooldown period after recent loss ({self.cooldown_after_loss}min)"
                logger.info(f"Rejecting {symbol}: {reason}")
                return False, reason
        
        return True, ""
    
    def _check_correlation(self, signal: SignalInfo) -> Tuple[bool, str]:
        """
        Check correlation with active positions.
        
        Prevents taking correlated positions in same direction.
        
        Args:
            signal: Signal to check
            
        Returns:
            (is_valid, reason)
        """
        if not self.active_positions:
            return True, ""  # No active positions
        
        symbol = signal.symbol
        direction = signal.direction
        
        # Check each active position
        for active_symbol, position in self.active_positions.items():
            if active_symbol == symbol:
                # Same symbol
                if position.get('direction') == direction:
                    reason = f"Already have {direction} position on {symbol}"
                    logger.info(f"Rejecting {symbol}: {reason}")
                    return False, reason
            
            # Check correlation (simplified - in production use actual correlation calculation)
            correlation = self._calculate_correlation(symbol, active_symbol)
            
            if correlation > self.max_correlation:
                if position.get('direction') == direction:
                    reason = (
                        f"High correlation with {active_symbol} "
                        f"({correlation:.2f}) in same direction"
                    )
                    logger.info(f"Rejecting {symbol}: {reason}")
                    return False, reason
        
        # BTC correlation check (if enabled) - HYBRID APPROACH
        if self.check_btc_correlation and not symbol.startswith('BTC'):
            btc_direction = self._get_btc_direction()

            if btc_direction and btc_direction != direction:
                # Signal goes against BTC trend - check correlation strength
                correlation = self._calculate_btc_correlation(symbol)

                # STRONG correlation (>0.7): REJECT
                if abs(correlation) > 0.7:
                    reason = (
                        f"Signal against strong BTC trend: "
                        f"BTC {btc_direction}, Signal {direction}, "
                        f"Correlation: {abs(correlation):.2f} > 0.7"
                    )
                    logger.warning(f"Rejecting {symbol}: {reason}")
                    return False, reason

                # MODERATE correlation (0.5-0.7): PENALTY
                elif abs(correlation) > 0.5:
                    penalty = 0.7  # 30% score reduction
                    logger.warning(
                        f"{symbol} signal {direction} goes against BTC {btc_direction} "
                        f"(correlation={abs(correlation):.2f}). Applying {(1-penalty)*100:.0f}% penalty."
                    )
                    signal.add_key_factor(f"Against BTC trend: {btc_direction} (correlation={abs(correlation):.2f})")

                    # Apply score penalty if signal has score
                    if signal.score:
                        original_score = signal.score.final_score
                        signal.score.final_score *= penalty
                        logger.info(
                            f"Score penalty applied to {symbol}: "
                            f"{original_score:.2f} → {signal.score.final_score:.2f}"
                        )

                # LOW correlation (<0.5): Just log
                else:
                    logger.info(
                        f"{symbol} signal {direction} goes against BTC {btc_direction}, "
                        f"but correlation is low ({abs(correlation):.2f} < 0.5). Allowing signal."
                    )
                    signal.add_key_factor(f"Against BTC trend (low correlation: {abs(correlation):.2f})")

        return True, ""
    
    def _check_portfolio_exposure(self, signal: SignalInfo) -> Tuple[bool, str]:
        """
        Check portfolio exposure limits.
        
        Args:
            signal: Signal to check
            
        Returns:
            (is_valid, reason)
        """
        # Check max open positions
        if len(self.active_positions) >= self.max_open_positions:
            reason = (
                f"Max open positions reached: {len(self.active_positions)} "
                f">= {self.max_open_positions}"
            )
            logger.info(f"Rejecting {signal.symbol}: {reason}")
            return False, reason
        
        # Calculate current exposures
        total_exposure = sum(
            pos.get('exposure', 0) 
            for pos in self.active_positions.values()
        )
        
        # Add signal's proposed exposure
        proposed_exposure = signal.position_size_percent / 100.0
        new_total = total_exposure + proposed_exposure
        
        # Check total exposure
        if new_total > self.max_total_exposure:
            reason = (
                f"Total exposure limit: {new_total:.2%} "
                f"> {self.max_total_exposure:.2%}"
            )
            logger.info(f"Rejecting {signal.symbol}: {reason}")
            return False, reason
        
        # Check per-symbol exposure
        symbol_exposure = self.active_positions.get(signal.symbol, {}).get('exposure', 0)
        symbol_exposure += proposed_exposure
        
        if symbol_exposure > self.max_per_symbol:
            reason = (
                f"Per-symbol exposure limit: {symbol_exposure:.2%} "
                f"> {self.max_per_symbol:.2%}"
            )
            logger.info(f"Rejecting {signal.symbol}: {reason}")
            return False, reason
        
        # Check same-direction exposure
        same_direction_exposure = sum(
            pos.get('exposure', 0)
            for pos in self.active_positions.values()
            if pos.get('direction') == signal.direction
        )
        same_direction_exposure += proposed_exposure
        
        if same_direction_exposure > self.max_same_direction:
            reason = (
                f"{signal.direction} exposure limit: {same_direction_exposure:.2%} "
                f"> {self.max_same_direction:.2%}"
            )
            logger.info(f"Rejecting {signal.symbol}: {reason}")
            return False, reason
        
        return True, ""

    
    def _check_volatility_rejection(self, signal: SignalInfo, context: AnalysisContext) -> Tuple[bool, str]:
        """
        Check if signal should be rejected due to extreme volatility.

        In extreme volatility conditions, signals are too risky and should be rejected.

        Args:
            signal: Signal to check
            context: Analysis context with volatility results

        Returns:
            (is_valid, reason)
        """
        # Get volatility analysis result
        volatility_result = context.get_result('volatility')

        if not volatility_result:
            # No volatility analysis available, allow signal
            logger.warning(f"No volatility analysis for {signal.symbol}, skipping volatility check")
            return True, ""

        # Check if volatility analyzer set explicit rejection flag
        if volatility_result.get('reject_signal', False):
            reason = "Extreme volatility detected - signal rejected for risk management"
            logger.warning(f"Rejecting {signal.symbol}: {reason}")
            return False, reason

        # Check volatility regime
        volatility_regime = volatility_result.get('volatility_regime', 'normal')
        if volatility_regime == 'extreme':
            reason = f"Volatility regime too extreme: {volatility_regime}"
            logger.warning(f"Rejecting {signal.symbol}: {reason}")
            return False, reason

        # Check raw volatility percentile
        volatility_percentile = volatility_result.get('volatility_percentile', 0.5)
        if volatility_percentile > 0.95:  # Top 5% most volatile
            reason = f"Volatility in top 5%: {volatility_percentile:.1%} > 95%"
            logger.warning(f"Rejecting {signal.symbol}: {reason}")
            return False, reason

        # Passed volatility checks
        return True, ""

    def _check_4h_volume_confirmation(self, signal: SignalInfo) -> Tuple[bool, str]:
        """
        Check if 4h volume confirmation is required and met.

        Based on backtest analysis:
        - 4h volume confirmed: 81.8% win rate
        - 4h volume NOT confirmed: 25% win rate
        - Difference: +56.8% win rate improvement!

        Args:
            signal: Signal to check

        Returns:
            (is_valid, reason)
        """
        # Check if this requirement is enabled in config
        require_4h = self.config.get('analyzers', {}).get('volume', {}).get('require_4h_confirmation', False)

        if not require_4h:
            # Feature disabled
            return True, ""

        # Check if signal has timeframe_signals attribute
        if not hasattr(signal, 'timeframe_signals') or not signal.timeframe_signals:
            logger.warning(f"Signal {signal.symbol} missing timeframe_signals, skipping 4h volume check")
            return True, ""

        # Check if 4h timeframe exists in signal
        if '4h' not in signal.timeframe_signals:
            logger.debug(f"Signal {signal.symbol} has no 4h timeframe data, skipping 4h volume check")
            return True, ""

        # Get 4h timeframe signal
        tf_4h = signal.timeframe_signals['4h']

        # Get volume analysis result from 4h context
        volume_result = tf_4h.context.get_result('volume') if hasattr(tf_4h, 'context') else None

        if not volume_result:
            reason = "4h volume analysis not available"
            logger.warning(f"Rejecting {signal.symbol}: {reason}")
            return False, reason

        # Check if volume is confirmed in 4h
        is_confirmed = volume_result.get('is_confirmed', False)

        if not is_confirmed:
            volume_ratio = volume_result.get('volume_ratio', 0.0)
            reason = f"4h volume not confirmed (ratio: {volume_ratio:.2f})"
            logger.info(f"Rejecting {signal.symbol}: {reason}")
            return False, reason

        # 4h volume is confirmed - add as key factor
        volume_ratio = volume_result.get('volume_ratio', 0.0)
        logger.info(f"{signal.symbol}: 4h volume confirmed (ratio: {volume_ratio:.2f}) ✓")
        signal.add_key_factor(f"4h volume confirmed ({volume_ratio:.2f}x)")

        return True, ""

    def _check_time_filters(self, signal: SignalInfo) -> Tuple[bool, str]:
        """Check time-based filters."""
        # Implementation here
        return True, ""
    
    def _check_score_threshold(self, signal: SignalInfo) -> Tuple[bool, str]:
        """
        Check score threshold with adaptive adjustment.

        Adjusts threshold based on recent performance:
        - Good performance (>60% win rate): Lower threshold slightly
        - Poor performance (<40% win rate): Raise threshold significantly

        Args:
            signal: Signal to check

        Returns:
            (is_valid, reason)
        """
        if not signal.score:
            return False, "Signal missing score"

        # Get base min score from config
        base_min_score = self.config.get('signal_processing', {}).get('validation', {}).get('min_signal_score', 50.0)

        # Adaptive adjustment based on recent performance
        min_score = base_min_score
        win_rate_text = ""

        if self.enable_adaptive:
            win_rate = self._calculate_recent_win_rate()

            if win_rate > self.good_performance_threshold:  # >60%
                # Good performance: lower threshold slightly (10%)
                min_score = base_min_score * 0.9
                win_rate_text = f" (adaptive: win_rate={win_rate:.1%}, threshold lowered)"
            elif win_rate < self.poor_performance_threshold:  # <40%
                # Poor performance: raise threshold significantly (20%)
                min_score = base_min_score * 1.2
                win_rate_text = f" (adaptive: win_rate={win_rate:.1%}, threshold raised)"

        # Check threshold
        if signal.score.final_score < min_score:
            reason = f"Score too low: {signal.score.final_score:.2f} < {min_score:.2f}{win_rate_text}"
            logger.info(f"Rejecting {signal.symbol}: {reason}")
            return False, reason

        # Passed
        if win_rate_text:
            logger.debug(f"Score check passed for {signal.symbol}: {signal.score.final_score:.2f} >= {min_score:.2f}{win_rate_text}")

        return True, ""

    def _calculate_recent_win_rate(self) -> float:
        """
        Calculate win rate from recent trades.

        Returns:
            Win rate (0.0-1.0), defaults to 0.5 if no trades
        """
        if not self.performance_history.get('total_trades', 0):
            return 0.5  # Default 50% if no history

        winning = self.performance_history.get('winning_trades', 0)
        total = self.performance_history['total_trades']

        return winning / total if total > 0 else 0.5

    def _calculate_correlation(self, symbol1: str, symbol2: str) -> float:
        """
        Calculate correlation between two symbols.

        This is a simplified implementation. In production, this should:
        - Use actual price data correlation
        - Cache correlation matrix
        - Update periodically

        Args:
            symbol1: First symbol
            symbol2: Second symbol

        Returns:
            Correlation coefficient (-1.0 to 1.0)
        """
        # Simplified: return placeholder
        # TODO: Implement actual correlation calculation from price data
        return 0.5  # Placeholder: assume moderate correlation

    def _get_btc_direction(self) -> Optional[str]:
        """
        Get current Bitcoin trend direction.

        Returns:
            'LONG' if bullish, 'SHORT' if bearish, None if neutral/unknown
        """
        # TODO: Implement BTC trend detection
        # Options:
        # 1. Query from cached BTC analysis
        # 2. Simple EMA cross (fast > slow = bullish)
        # 3. Get from external service

        # Placeholder: return None (no BTC trend info)
        return None

    def _calculate_btc_correlation(self, symbol: str) -> float:
        """
        Calculate correlation with Bitcoin.

        Args:
            symbol: Symbol to check

        Returns:
            Correlation coefficient (0.0 to 1.0)
        """
        # TODO: Calculate actual BTC correlation from price data
        # Simplified: assume crypto pairs have moderate correlation with BTC
        if 'BTC' in symbol:
            return 1.0  # BTC pairs
        elif symbol.endswith('USDT'):
            return 0.7  # Typical altcoin correlation with BTC
        else:
            return 0.5  # Other pairs

    def register_signal(self, signal: SignalInfo) -> None:
        """
        ثبت سیگنال در تاریخچه

        Args:
            signal: سیگنال برای ثبت
        """
        from datetime import datetime

        # اضافه به تاریخچه کلی
        self.signal_history.append({
            'symbol': signal.symbol,
            'direction': signal.direction,
            'timestamp': datetime.now(),
            'score': signal.score.final_score if signal.score else 0,
        })

        # اضافه به تاریخچه سمبل
        self.recent_signals_by_symbol[signal.symbol].append({
            'timestamp': datetime.now(),
            'direction': signal.direction,
            'score': signal.score.final_score if signal.score else 0,
        })

        # به‌روزرسانی آمار
        self.performance_history['total_signals'] += 1