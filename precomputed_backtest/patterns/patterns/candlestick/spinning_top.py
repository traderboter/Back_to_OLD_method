"""
Spinning Top Pattern Detector

Detects Spinning Top candlestick pattern using TALib.
Spinning Top is an indecision pattern that can signal trend weakening.

Version: 1.0.0 (2025-10-26) - Initial Implementation
- Indecision/reversal pattern
- Small body with long shadows on both sides
- Shows battle between buyers and sellers with no clear winner
"""

SPINNING_TOP_PATTERN_VERSION = "1.0.0"

import talib
import pandas as pd
import numpy as np
from typing import Dict, Any

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class SpinningTopPattern(BasePattern):
    """
    Spinning Top candlestick pattern detector.

    Characteristics:
    - Small real body (can be bullish or bearish)
    - Long upper and lower shadows
    - Shows indecision in the market
    - Neither buyers nor sellers could gain control
    - Warning signal of potential trend reversal

    Strength: 2/3 (Medium)
    Direction: Neutral (indecision signal)
    """

    def _get_pattern_name(self) -> str:
        return "Spinning Top"

    def _get_pattern_type(self) -> str:
        return "candlestick"

    def _get_direction(self) -> str:
        return "neutral"  # Indecision pattern

    def _get_base_strength(self) -> int:
        return 2  # Medium strength - more of a warning signal

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
        Detect Spinning Top pattern in last N candles using TALib.

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

        # Need minimum 12 candles
        if len(df) < 12:
            return False

        try:
            result = talib.CDLSPINNINGTOP(
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
                    return True

            return False

        except Exception as e:
            return False

    def _get_detection_details(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get additional details about Spinning Top detection with recency information.
        """
        if len(df) < 1:
            return super()._get_detection_details(df)

        # Get detection position
        candles_ago = getattr(self, '_last_detection_candles_ago', 0)
        if candles_ago is None:
            candles_ago = 0

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

        # Calculate shadows
        upper_shadow = candle_data['high'] - max(candle_data['open'], candle_data['close'])
        lower_shadow = min(candle_data['open'], candle_data['close']) - candle_data['low']

        # For spinning top, shadows should be relatively equal and much larger than body
        total_shadows = upper_shadow + lower_shadow
        shadow_balance = 1.0 - abs(upper_shadow - lower_shadow) / (total_shadows if total_shadows > 0 else 1.0)

        # Body should be small relative to total range
        body_ratio = body_size / full_range if full_range > 0 else 0
        shadow_dominance = total_shadows / full_range if full_range > 0 else 0

        # Base confidence
        # Higher when:
        # 1. Shadows are balanced (shadow_balance close to 1.0)
        # 2. Shadows dominate the candle (shadow_dominance high)
        # 3. Body is small (body_ratio low)
        base_confidence = min(0.60 + (shadow_balance * 0.15) + (shadow_dominance * 0.15) + ((1.0 - body_ratio) * 0.05), 0.90)

        # Adjust confidence with recency multiplier
        adjusted_confidence = min(base_confidence * recency_multiplier, 0.90)

        return {
            'location': 'current' if candles_ago == 0 else 'recent',
            'candles_ago': candles_ago,
            'recency_multiplier': recency_multiplier,
            'confidence': adjusted_confidence,
            'metadata': {
                'body_size': float(body_size),
                'full_range': float(full_range),
                'upper_shadow': float(upper_shadow),
                'lower_shadow': float(lower_shadow),
                'body_ratio': float(body_ratio),
                'shadow_balance': float(shadow_balance),
                'shadow_dominance': float(shadow_dominance),
                'recency_info': {
                    'candles_ago': candles_ago,
                    'multiplier': recency_multiplier,
                    'lookback_window': self.lookback_window,
                    'base_confidence': base_confidence,
                    'adjusted_confidence': adjusted_confidence
                }
            }
        }
