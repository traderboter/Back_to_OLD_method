"""
Marubozu Pattern Detector

Detects Marubozu candlestick pattern using TALib.
Marubozu is a strong continuation/reversal pattern.

Version: 1.0.0 (2025-10-26) - Initial Implementation
- Strong single candle pattern
- Shows complete dominance of buyers (bullish) or sellers (bearish)
- No or minimal shadows/wicks
"""

MARUBOZU_PATTERN_VERSION = "1.0.0"

import talib
import pandas as pd
import numpy as np
from typing import Dict, Any

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class MarubozuPattern(BasePattern):
    """
    Marubozu candlestick pattern detector.

    Characteristics:
    - Single long candle with little to no shadows
    - Full-bodied candle showing strong momentum
    - Bullish: Opens at low, closes at high (white/green)
    - Bearish: Opens at high, closes at low (black/red)
    - Shows complete dominance of one side

    Strength: 3/3 (Strong)
    Direction: Can be bullish or bearish
    """

    def _get_pattern_name(self) -> str:
        return "Marubozu"

    def _get_pattern_type(self) -> str:
        return "candlestick"

    def _get_direction(self) -> str:
        return "both"  # Can be bullish or bearish

    def _get_base_strength(self) -> int:
        return 3  # Strong pattern

    def detect(
        self,
        df: pd.DataFrame,
        open_col: str = 'open',
        high_col: str = 'high',
        low_col: str = 'low',
        close_col: str = 'close',
        volume_col: str = 'volume'
    ) -> bool:
        """
        Detect Marubozu pattern in last N candles using TALib.

        Multi-candle lookback detection:
        - Checks last N candles (lookback_window, default: 15)
        - Stores which candle has the pattern
        - Enables recency-based scoring

        Based on research:
        - Minimum 12 candles required (11 lookback + 1 current)
        """
        if not self._validate_dataframe(df):
            return False

        # Reset detection cache
        self._last_detection_candles_ago = None
        self._last_detection_direction = None

        # Need minimum 12 candles
        if len(df) < 12:
            return False

        try:
            result = talib.CDLMARUBOZU(
                df[open_col].values,
                df[high_col].values,
                df[low_col].values,
                df[close_col].values
            )

            # Check last N candles (lookback_window)
            lookback = min(self.lookback_window, len(result))

            for i in range(lookback):
                idx = -(i + 1)
                if result[idx] != 0:
                    self._last_detection_candles_ago = i
                    # TALib returns +100 for bullish, -100 for bearish
                    self._last_detection_direction = 'bullish' if result[idx] > 0 else 'bearish'
                    return True

            return False

        except Exception as e:
            return False

    def _get_detection_details(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get additional details about Marubozu detection with recency information.

        Includes:
        - candles_ago: Which candle has the pattern (0-15)
        - recency_multiplier: Score multiplier based on age
        - direction: 'bullish' or 'bearish'
        - Adjusted confidence based on recency
        """
        if len(df) < 1:
            return super()._get_detection_details(df)

        # Get detection position
        candles_ago = getattr(self, '_last_detection_candles_ago', 0)
        if candles_ago is None:
            candles_ago = 0

        # Get direction
        direction = getattr(self, '_last_detection_direction', 'bullish')

        # Get recency multiplier
        if candles_ago < len(self.recency_multipliers):
            recency_multiplier = self.recency_multipliers[candles_ago]
        else:
            recency_multiplier = 0.0

        # Get the candle where pattern was detected
        pattern_end_idx = len(df) - candles_ago
        pattern_start_idx = pattern_end_idx - 1

        # Ensure we have valid indices
        if pattern_start_idx < 0 or pattern_end_idx > len(df):
            return super()._get_detection_details(df)

        candle = df.iloc[pattern_start_idx:pattern_end_idx].copy()

        # Double check we have exactly 1 candle
        if len(candle) != 1:
            return super()._get_detection_details(df)

        # Get candle data
        candle_data = candle.iloc[0]
        body_size = abs(candle_data['close'] - candle_data['open'])
        full_range = candle_data['high'] - candle_data['low']

        # Calculate shadow sizes
        if candle_data['close'] > candle_data['open']:
            # Bullish
            upper_shadow = candle_data['high'] - candle_data['close']
            lower_shadow = candle_data['open'] - candle_data['low']
        else:
            # Bearish
            upper_shadow = candle_data['high'] - candle_data['open']
            lower_shadow = candle_data['close'] - candle_data['low']

        # Calculate body to range ratio (should be close to 1 for Marubozu)
        body_ratio = body_size / full_range if full_range > 0 else 0

        # Base confidence depends on how "pure" the Marubozu is
        # Perfect Marubozu has body_ratio = 1.0
        base_confidence = min(0.75 + (body_ratio * 0.20), 0.95)

        # Adjust confidence with recency multiplier
        adjusted_confidence = min(base_confidence * recency_multiplier, 0.95)

        return {
            'location': 'current' if candles_ago == 0 else 'recent',
            'candles_ago': candles_ago,
            'recency_multiplier': recency_multiplier,
            'direction': direction,
            'confidence': adjusted_confidence,
            'metadata': {
                'body_size': float(body_size),
                'full_range': float(full_range),
                'body_ratio': float(body_ratio),
                'upper_shadow': float(upper_shadow),
                'lower_shadow': float(lower_shadow),
                'recency_info': {
                    'candles_ago': candles_ago,
                    'multiplier': recency_multiplier,
                    'lookback_window': self.lookback_window,
                    'base_confidence': base_confidence,
                    'adjusted_confidence': adjusted_confidence
                }
            }
        }
