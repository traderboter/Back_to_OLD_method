"""
Emergency Circuit Breaker
Emergency stop mechanism to prevent consecutive losses in abnormal market conditions.
"""

import logging
import numpy as np
import pandas as pd
import talib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Import TradeResult from adaptive_learning_system
from signal_generation.systems.adaptive_learning_system import TradeResult


class EmergencyCircuitBreaker:
    """Emergency stop mechanism to prevent consecutive losses in abnormal market conditions."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration."""
        self.config = config.get('circuit_breaker', {})
        self.enabled = self.config.get('enabled', True)
        self.max_consecutive_losses = self.config.get('max_consecutive_losses', 3)
        self.max_daily_losses_r = self.config.get('max_daily_losses_r', 5.0)
        self.cool_down_period_minutes = self.config.get('cool_down_period_minutes', 60)
        self.reset_period_hours = self.config.get('reset_period_hours', 24)

        # Internal variables
        self.consecutive_losses = 0
        self.daily_loss_r = 0.0
        self.triggered = False
        self.trigger_time: Optional[datetime] = None
        self.last_reset_time = datetime.now(timezone.utc)
        self.trade_log: List[Dict[str, Any]] = []

        logger.info(
            f"EmergencyCircuitBreaker initialized. "
            f"Enabled: {self.enabled}, "
            f"Max consecutive losses: {self.max_consecutive_losses}, "
            f"Max daily loss R: {self.max_daily_losses_r}"
        )

    def add_trade_result(self, trade_result: TradeResult) -> None:
        """
        Register a trade result and check for emergency stop conditions.

        Args:
            trade_result: TradeResult object with trade information
        """
        if not self.enabled:
            return

        try:
            # Reset daily stats if needed
            current_time = datetime.now(timezone.utc)
            hours_since_reset = (current_time - self.last_reset_time).total_seconds() / 3600

            if hours_since_reset >= self.reset_period_hours:
                self._reset_daily_stats()

            # Register new trade
            trade_info = {
                'time': current_time,
                'symbol': trade_result.symbol,
                'direction': trade_result.direction,
                'profit_r': trade_result.profit_r,
                'exit_reason': trade_result.exit_reason
            }
            self.trade_log.append(trade_info)

            # Update stats
            if trade_result.profit_r < 0:
                self.consecutive_losses += 1
                self.daily_loss_r -= trade_result.profit_r  # Negative * negative = positive
            else:
                self.consecutive_losses = 0  # Reset consecutive loss counter

            # Check stop conditions
            if self.consecutive_losses >= self.max_consecutive_losses:
                self._trigger_circuit_breaker(
                    f"Hit {self.consecutive_losses} consecutive losses"
                )
            elif self.daily_loss_r >= self.max_daily_losses_r:
                self._trigger_circuit_breaker(
                    f"Daily loss of {self.daily_loss_r:.2f}R exceeded "
                    f"limit of {self.max_daily_losses_r}R"
                )

            # Log status
            logger.debug(
                f"Circuit breaker status: consecutive_losses={self.consecutive_losses}, "
                f"daily_loss_r={self.daily_loss_r:.2f}, triggered={self.triggered}"
            )

        except Exception as e:
            logger.error(f"Error processing trade result in circuit breaker: {e}", exc_info=True)

    def _trigger_circuit_breaker(self, reason: str) -> None:
        """
        Activate emergency stop.

        Args:
            reason: Reason for triggering
        """
        if self.triggered:
            return  # Already triggered

        self.triggered = True
        self.trigger_time = datetime.now(timezone.utc)

        logger.warning(
            f"🚨 CIRCUIT BREAKER TRIGGERED: {reason}. "
            f"Trading paused for {self.cool_down_period_minutes} minutes."
        )

    def _reset_daily_stats(self) -> None:
        """Reset daily statistics."""
        self.daily_loss_r = 0.0
        self.last_reset_time = datetime.now(timezone.utc)

        # Clean up old trades
        current_time = datetime.now(timezone.utc)
        cutoff_seconds = self.reset_period_hours * 3600

        self.trade_log = [
            t for t in self.trade_log
            if (current_time - t['time']).total_seconds() < cutoff_seconds
        ]

    def check_if_active(self) -> Tuple[bool, Optional[str]]:
        """
        Check if circuit breaker is active and return remaining time.

        Returns:
            Tuple of (is_active, reason)
        """
        if not self.enabled:
            return False, None

        if not self.triggered:
            return False, None

        # Check cool down period end
        current_time = datetime.now(timezone.utc)

        if self.trigger_time:
            minutes_since_trigger = (current_time - self.trigger_time).total_seconds() / 60

            if minutes_since_trigger >= self.cool_down_period_minutes:
                # Reset circuit breaker
                self.triggered = False
                self.trigger_time = None
                self.consecutive_losses = 0  # Reset consecutive loss counter

                logger.info("✅ Circuit breaker cool-down period complete. Trading resumed.")
                return False, None
            else:
                # Still in cool down
                remaining_minutes = self.cool_down_period_minutes - minutes_since_trigger
                reason = (
                    f"Circuit breaker active. "
                    f"Remaining cool-down: {remaining_minutes:.1f} minutes"
                )
                return True, reason

        # Shouldn't reach here, but just in case
        return True, "Circuit breaker triggered"

    def get_market_anomaly_score(self, symbols_data: Dict[str, pd.DataFrame]) -> float:
        """
        Calculate market anomaly score based on unusual market conditions.

        Args:
            symbols_data: Dictionary of {symbol: DataFrame}

        Returns:
            Anomaly score (0.0 to 1.0), higher means more abnormal
        """
        if not self.enabled or not symbols_data:
            return 0.0

        try:
            anomaly_factors = []

            for symbol, df in symbols_data.items():
                if df is None or len(df) < 20:
                    continue

                # Volume spike analysis
                if 'volume' in df.columns:
                    recent_volume = df['volume'].iloc[-1]
                    avg_volume = df['volume'].rolling(window=20).mean().iloc[-1]

                    if avg_volume > 0:
                        vol_ratio = recent_volume / avg_volume

                        if vol_ratio > 3:  # Abnormal volume spike
                            anomaly_factors.append(min(1.0, (vol_ratio - 3) / 7))

                # Price change analysis
                if len(df) >= 2:
                    last_close = df['close'].iloc[-1]
                    prev_close = df['close'].iloc[-2]

                    if prev_close > 0:
                        price_change_pct = abs((last_close - prev_close) / prev_close) * 100

                        if price_change_pct > 3:  # Abnormal price change
                            anomaly_factors.append(min(1.0, (price_change_pct - 3) / 7))

                # High-Low range analysis
                if len(df) >= 1:
                    last_high = df['high'].iloc[-1]
                    last_low = df['low'].iloc[-1]

                    if last_low > 0:
                        hl_ratio = (last_high - last_low) / last_low * 100

                        typical_hl = (
                            df['high']
                            .sub(df['low'])
                            .div(df['low'])
                            .mul(100)
                            .rolling(window=20)
                            .mean()
                        )
                        last_typical_hl = typical_hl.iloc[-1] if not typical_hl.isna().all() else 1.0

                        if last_typical_hl > 0 and hl_ratio > last_typical_hl * 2:
                            anomaly_factors.append(
                                min(1.0, (hl_ratio / last_typical_hl - 2) / 3)
                            )

            # Calculate final score
            if anomaly_factors:
                return sum(anomaly_factors) / len(anomaly_factors)

            return 0.0

        except Exception as e:
            logger.error(f"Error calculating market anomaly score: {e}", exc_info=True)
            return 0.0

    def is_market_volatile(self, symbols_data: Dict[str, pd.DataFrame]) -> bool:
        """
        Detect abnormal market volatility based on ATR.

        Compares recent ATR (last 5 candles) to past ATR (previous 20 candles).
        If recent ATR is 50% higher than past, market is considered volatile.

        Args:
            symbols_data: Dictionary of {symbol: DataFrame}

        Returns:
            True if market volatility has increased significantly
        """
        if not self.enabled or not symbols_data:
            return False

        try:
            volatility_scores = []

            for symbol, df in symbols_data.items():
                if df is None or len(df) < 30:
                    continue

                # Calculate ATR
                atr = talib.ATR(
                    df['high'].values.astype(np.float64),
                    df['low'].values.astype(np.float64),
                    df['close'].values.astype(np.float64),
                    timeperiod=14
                )

                # Calculate ATR% relative to price
                close_prices = df['close'].values[-len(atr):]
                atr_percent = np.where(~np.isnan(atr) & (close_prices > 0),
                                       (atr / close_prices) * 100,
                                       np.nan)

                # Get valid ATR% values
                valid_atr_percent = atr_percent[~np.isnan(atr_percent)]
                if len(valid_atr_percent) < 5:
                    continue

                # Compare last 5 values to previous 20 values
                recent_atr_percent = valid_atr_percent[-5:].mean()
                past_atr_percent = valid_atr_percent[-25:-5].mean() if len(
                    valid_atr_percent) >= 25 else valid_atr_percent[:-5].mean()

                # Volatility change ratio
                if past_atr_percent > 0:
                    volatility_change = recent_atr_percent / past_atr_percent
                    volatility_scores.append(volatility_change)

            # Average volatility change ratio across symbols
            if volatility_scores:
                avg_volatility_change = sum(volatility_scores) / len(volatility_scores)
                # Threshold for significant volatility increase (50%)
                if avg_volatility_change > 1.5:
                    logger.warning(
                        f"⚠️ Market volatility spike detected: "
                        f"{avg_volatility_change:.2f}x increase in ATR"
                    )
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking market volatility: {e}", exc_info=True)
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get circuit breaker statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            'enabled': self.enabled,
            'triggered': self.triggered,
            'consecutive_losses': self.consecutive_losses,
            'daily_loss_r': round(self.daily_loss_r, 2),
            'trigger_time': self.trigger_time.isoformat() if self.trigger_time else None,
            'last_reset_time': self.last_reset_time.isoformat(),
            'total_trades_logged': len(self.trade_log),
            'config': {
                'max_consecutive_losses': self.max_consecutive_losses,
                'max_daily_losses_r': self.max_daily_losses_r,
                'cool_down_period_minutes': self.cool_down_period_minutes,
                'reset_period_hours': self.reset_period_hours
            }
        }

    def reset(self) -> None:
        """Manually reset circuit breaker (use with caution)."""
        self.triggered = False
        self.trigger_time = None
        self.consecutive_losses = 0
        self.daily_loss_r = 0.0

        logger.warning("⚠️ Circuit breaker manually reset!")

