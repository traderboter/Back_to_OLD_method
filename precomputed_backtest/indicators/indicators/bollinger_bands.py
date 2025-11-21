"""
Bollinger Bands Indicator

Calculates Bollinger Bands (upper, middle, lower).
Bollinger Bands consist of a middle band (SMA) and two outer bands (standard deviations).
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List

from signal_generation.analyzers.indicators.base_indicator import BaseIndicator


class BollingerBandsIndicator(BaseIndicator):
    """
    Bollinger Bands indicator calculator.

    Bollinger Bands consist of:
    - Middle Band: SMA (typically 20-period)
    - Upper Band: Middle Band + (std_dev * multiplier)
    - Lower Band: Middle Band - (std_dev * multiplier)

    Useful for identifying overbought/oversold conditions and volatility.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)

        # Default parameters (will be overridden per-TF if configured)
        self.default_period = 20
        self.default_std_multiplier = 2.0

        # Fallback parameters
        self.period = self.default_period
        self.std_multiplier = self.default_std_multiplier

    def _get_indicator_name(self) -> str:
        return "Bollinger Bands"

    def _get_indicator_type(self) -> str:
        return "volatility"

    def _get_required_columns(self) -> List[str]:
        return ['close']

    def _get_output_columns(self) -> List[str]:
        return ['bb_upper', 'bb_middle', 'bb_lower']

    def _get_min_periods(self) -> int:
        return self.period

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Bollinger Bands using population standard deviation.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with Bollinger Bands columns added
        """
        result_df = df.copy()

        # Get parameters with per-TF support
        period = self.get_parameter('bb_period', self.default_period, self.timeframe)
        std_multiplier = self.get_parameter('bb_std', self.default_std_multiplier, self.timeframe)

        # Update instance parameters
        self.period = period
        self.std_multiplier = std_multiplier

        # Calculate middle band (SMA)
        result_df['bb_middle'] = result_df['close'].rolling(window=period).mean()

        # Calculate standard deviation
        # Use ddof=0 for population standard deviation (standard for Bollinger Bands)
        std = result_df['close'].rolling(window=period).std(ddof=0)

        # Calculate upper and lower bands
        result_df['bb_upper'] = result_df['bb_middle'] + (std * std_multiplier)
        result_df['bb_lower'] = result_df['bb_middle'] - (std * std_multiplier)

        return result_df
