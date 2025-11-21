"""
ATR (Average True Range) Indicator

Calculates ATR volatility indicator.
ATR measures market volatility by decomposing the entire range of a price.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List

from signal_generation.analyzers.indicators.base_indicator import BaseIndicator


class ATRIndicator(BaseIndicator):
    """
    ATR (Average True Range) indicator calculator.

    ATR is a volatility indicator that shows how much an asset moves, on average, during a given time period.
    Higher ATR values indicate higher volatility.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)

        # Default period (will be overridden per-TF if configured)
        self.default_period = 14
        self.period = self.default_period  # Fallback

    def _get_indicator_name(self) -> str:
        return "ATR"

    def _get_indicator_type(self) -> str:
        return "volatility"

    def _get_required_columns(self) -> List[str]:
        return ['high', 'low', 'close']

    def _get_output_columns(self) -> List[str]:
        return ['atr']

    def _get_min_periods(self) -> int:
        return self.period + 1

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate ATR using Exponential Moving Average (Wilder's smoothing).

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with ATR column added
        """
        result_df = df.copy()

        # Get period with per-TF support
        period = self.get_parameter('atr_period', self.default_period, self.timeframe)
        self.period = period  # Update instance period

        # Calculate True Range components
        high_low = result_df['high'] - result_df['low']
        high_close = abs(result_df['high'] - result_df['close'].shift(1))
        low_close = abs(result_df['low'] - result_df['close'].shift(1))

        # True Range is the maximum of the three
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

        # ATR uses Wilder's smoothing method (alpha = 1/period)
        # This is different from standard EMA which uses alpha = 2/(period+1)
        # Wilder's formula: ATR[i] = ((ATR[i-1] * (n-1)) + TR[i]) / n
        result_df['atr'] = true_range.ewm(alpha=1/period, adjust=False).mean()

        return result_df
