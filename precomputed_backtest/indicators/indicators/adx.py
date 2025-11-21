"""
ADX (Average Directional Index) Indicator

Calculates ADX trend strength indicator.
ADX measures the strength of a trend, not its direction.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
import talib

from signal_generation.analyzers.indicators.base_indicator import BaseIndicator


class ADXIndicator(BaseIndicator):
    """
    ADX (Average Directional Index) indicator calculator.

    ADX is a trend strength indicator that measures how strong a trend is.
    Values above 25 indicate a strong trend, while values below 20 indicate a weak trend.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)

        # Default period (will be overridden per-TF if configured)
        self.default_period = 14
        self.period = self.default_period  # Fallback

    def _get_indicator_name(self) -> str:
        return "ADX"

    def _get_indicator_type(self) -> str:
        return "trend"

    def _get_required_columns(self) -> List[str]:
        return ['high', 'low', 'close']

    def _get_output_columns(self) -> List[str]:
        return ['adx', 'plus_di', 'minus_di']

    def _get_min_periods(self) -> int:
        return self.period * 2  # ADX needs more periods to stabilize

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate ADX using talib.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with ADX, +DI, -DI columns added
        """
        result_df = df.copy()

        # Get period with per-TF support
        period = self.get_parameter('adx_period', self.default_period, self.timeframe)
        self.period = period  # Update instance period

        high = result_df['high'].values
        low = result_df['low'].values
        close = result_df['close'].values

        # Calculate ADX and directional indicators
        result_df['adx'] = talib.ADX(high, low, close, timeperiod=period)
        result_df['plus_di'] = talib.PLUS_DI(high, low, close, timeperiod=period)
        result_df['minus_di'] = talib.MINUS_DI(high, low, close, timeperiod=period)

        return result_df
