"""
Long-Legged Doji Pattern Detector

Detects Long-Legged Doji candlestick pattern using TALib.
Long-Legged Doji is a strong indecision pattern.

Version: 1.0.0 (2025-10-26) - Initial Implementation
- Strong indecision pattern
- Doji with very long shadows on both sides
- Shows intense battle with no winner
"""

LONG_LEGGED_DOJI_PATTERN_VERSION = "1.0.0"

import talib
import pandas as pd
import numpy as np
from typing import Dict, Any

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class LongLeggedDojiPattern(BasePattern):
    """
    Long-Legged Doji candlestick pattern detector.

    Characteristics:
    - Doji with very long upper and lower shadows
    - Open and close at/near the middle
    - Shows extreme indecision and volatility
    - Intense battle between buyers and sellers
    - Strong reversal signal when at trend extremes

    Strength: 3/3 (Strong)
    Direction: Neutral (indecision, but strong reversal signal)
    """

    def _get_pattern_name(self) -> str:
        return "Long-Legged Doji"

    def _get_pattern_type(self) -> str:
        return "candlestick"

    def _get_direction(self) -> str:
        return "neutral"  # Indecision pattern

    def _get_base_strength(self) -> int:
        return 3  # Strong pattern - significant indecision

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
        Detect Long-Legged Doji pattern in last N candles using TALib.

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
            result = talib.CDLLONGLEGGEDDOJI(
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
        Get additional details about Long-Legged Doji detection with recency information.
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

        # Calculate shadows - should both be very long
        upper_shadow = candle_data['high'] - max(candle_data['open'], candle_data['close'])
        lower_shadow = min(candle_data['open'], candle_data['close']) - candle_data['low']

        # For long-legged doji, shadows should be relatively equal and very long
        total_shadows = upper_shadow + lower_shadow
        shadow_balance = 1.0 - abs(upper_shadow - lower_shadow) / (total_shadows if total_shadows > 0 else 1.0)

        # Shadows should dominate the candle
        shadow_dominance = total_shadows / full_range if full_range > 0 else 0

        # Average shadow length relative to range
        avg_shadow = (upper_shadow + lower_shadow) / 2
        avg_shadow_ratio = avg_shadow / full_range if full_range > 0 else 0

        # Base confidence
        # Higher when:
        # 1. Shadows are balanced (shadow_balance close to 1.0)
        # 2. Shadows are very long (avg_shadow_ratio high)
        # 3. Shadows dominate the candle (shadow_dominance high)
        base_confidence = min(0.70 + (shadow_balance * 0.10) + (avg_shadow_ratio * 0.10) + (shadow_dominance * 0.05), 0.95)

        # Adjust confidence with recency multiplier
        adjusted_confidence = min(base_confidence * recency_multiplier, 0.95)

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
                'shadow_balance': float(shadow_balance),
                'shadow_dominance': float(shadow_dominance),
                'avg_shadow_ratio': float(avg_shadow_ratio),
                'recency_info': {
                    'candles_ago': candles_ago,
                    'multiplier': recency_multiplier,
                    'lookback_window': self.lookback_window,
                    'base_confidence': base_confidence,
                    'adjusted_confidence': adjusted_confidence
                }
            }
        }
