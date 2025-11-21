"""
RSI (Relative Strength Index) Indicator

Calculates RSI momentum oscillator.
RSI measures the magnitude of recent price changes to evaluate overbought/oversold conditions.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List

from signal_generation.analyzers.indicators.base_indicator import BaseIndicator


class RSIIndicator(BaseIndicator):
    """
    RSI (Relative Strength Index) indicator calculator.

    RSI is a momentum oscillator that measures the speed and magnitude of price changes.
    Values range from 0 to 100.
    - Above 70: Overbought
    - Below 30: Oversold
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)

        # Default period (will be overridden per-TF if configured)
        self.default_period = 14
        self.period = self.default_period  # Fallback

    def _get_indicator_name(self) -> str:
        return "RSI"

    def _get_indicator_type(self) -> str:
        return "momentum"

    def _get_required_columns(self) -> List[str]:
        return ['close']

    def _get_output_columns(self) -> List[str]:
        return ['rsi']

    def _get_min_periods(self) -> int:
        return self.period + 1

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate RSI using Wilder's smoothing method.

        RSI calculation (matching TA-Lib):
        1. Calculate price changes (delta)
        2. Separate gains and losses
        3. First average = SMA of first N gains/losses
        4. Subsequent averages using Wilder's smoothing:
           Avg = (Previous Avg * (N-1) + Current Value) / N
           This is equivalent to EMA with alpha = 1/N

        Optimized version using numpy arrays for fast computation.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with RSI column added
        """
        result_df = df.copy()

        # Get period with per-TF support
        period = self.get_parameter('rsi_period', self.default_period, self.timeframe)
        self.period = period  # Update instance period

        # Calculate price changes
        delta = result_df['close'].diff()

        # Separate gains and losses
        gain = delta.where(delta > 0, 0).values
        loss = (-delta.where(delta < 0, 0)).values

        # Convert to numpy arrays for fast computation
        n = len(gain)

        # Initialize arrays
        avg_gain = np.empty(n)
        avg_loss = np.empty(n)
        avg_gain[:period] = np.nan
        avg_loss[:period] = np.nan

        # First average = SMA of first N periods
        avg_gain[period] = np.mean(gain[1:period+1])
        avg_loss[period] = np.mean(loss[1:period+1])

        # Apply Wilder's smoothing for subsequent values
        # Wilder's formula: Avg[i] = (Avg[i-1] * (N-1) + Value[i]) / N
        # This is much faster with numpy arrays than pandas iloc
        for i in range(period + 1, n):
            avg_gain[i] = (avg_gain[i-1] * (period - 1) + gain[i]) / period
            avg_loss[i] = (avg_loss[i-1] * (period - 1) + loss[i]) / period

        # Calculate RSI using the alternative formula: RSI = 100 * avg_gain / (avg_gain + avg_loss)
        # This is mathematically equivalent to: RSI = 100 - (100 / (1 + RS))
        # But handles edge cases better (when avg_loss = 0)
        total = avg_gain + avg_loss

        # Use safe division: when total = 0 (no movement), RSI = 50 (neutral)
        rsi = 100 * self._safe_divide(avg_gain, total, 0.5)

        # Ensure RSI is within valid range [0, 100]
        rsi = np.clip(rsi, 0, 100)

        result_df['rsi'] = rsi

        return result_df
