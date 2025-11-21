"""
MACD (Moving Average Convergence Divergence) Indicator

Calculates MACD, Signal line, and Histogram.
MACD is a trend-following momentum indicator.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List

from signal_generation.analyzers.indicators.base_indicator import BaseIndicator


class MACDIndicator(BaseIndicator):
    """
    MACD (Moving Average Convergence Divergence) indicator calculator.

    MACD shows the relationship between two moving averages.
    Components:
    - MACD Line: (12-period EMA - 26-period EMA)
    - Signal Line: 9-period EMA of MACD Line
    - Histogram: MACD Line - Signal Line
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)

        # Default periods (will be overridden per-TF if configured)
        self.default_fast_period = 12
        self.default_slow_period = 26
        self.default_signal_period = 9

        # Fallback periods
        self.fast_period = self.default_fast_period
        self.slow_period = self.default_slow_period
        self.signal_period = self.default_signal_period

    def _get_indicator_name(self) -> str:
        return "MACD"

    def _get_indicator_type(self) -> str:
        return "momentum"

    def _get_required_columns(self) -> List[str]:
        return ['close']

    def _get_output_columns(self) -> List[str]:
        return ['macd', 'macd_signal', 'macd_hist']

    def _get_min_periods(self) -> int:
        return self.slow_period + self.signal_period

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate MACD, Signal, and Histogram.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with MACD columns added
        """
        result_df = df.copy()

        # Get periods with per-TF support
        fast_period = self.get_parameter('macd_fast', self.default_fast_period, self.timeframe)
        slow_period = self.get_parameter('macd_slow', self.default_slow_period, self.timeframe)
        signal_period = self.get_parameter('macd_signal', self.default_signal_period, self.timeframe)

        # Update instance periods
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

        # Calculate fast and slow EMAs
        ema_fast = result_df['close'].ewm(span=fast_period, adjust=False).mean()
        ema_slow = result_df['close'].ewm(span=slow_period, adjust=False).mean()

        # Calculate MACD line
        result_df['macd'] = ema_fast - ema_slow

        # Calculate Signal line
        result_df['macd_signal'] = result_df['macd'].ewm(span=signal_period, adjust=False).mean()

        # Calculate Histogram
        result_df['macd_hist'] = result_df['macd'] - result_df['macd_signal']

        return result_df
