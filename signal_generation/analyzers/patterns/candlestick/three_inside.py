"""
Three Inside Pattern Detector

Detects Three Inside Up/Down candlestick pattern using TALib.
Three Inside is a confirmed reversal pattern (Harami + confirmation).

Version: 1.0.0 (2025-10-26) - Initial Implementation
- 3-candle reversal pattern
- Stronger version of Harami with confirmation
- Up version is bullish, Down version is bearish
"""

THREE_INSIDE_PATTERN_VERSION = "1.0.0"

import talib
import pandas as pd
import numpy as np
from typing import Dict, Any

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class ThreeInsidePattern(BasePattern):
    """
    Three Inside Up/Down candlestick pattern detector.

    Characteristics:
    - 3-candle pattern combining Harami + confirmation
    - Three Inside Up (bullish):
      1. Large bearish candle
      2. Small bullish candle inside (Harami)
      3. Bullish confirmation candle closing above candle 1
    - Three Inside Down (bearish):
      1. Large bullish candle
      2. Small bearish candle inside (Harami)
      3. Bearish confirmation candle closing below candle 1

    Strength: 3/3 (Strong) - confirmed reversal
    Direction: Can be bullish or bearish
    """

    def _get_pattern_name(self) -> str:
        return "Three Inside"

    def _get_pattern_type(self) -> str:
        return "candlestick"

    def _get_direction(self) -> str:
        return "both"  # Can be bullish or bearish

    def _get_base_strength(self) -> int:
        return 3  # Strong pattern - has confirmation

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
        Detect Three Inside pattern in last N candles using TALib.

        Multi-candle lookback detection:
        - Checks last N candles (lookback_window, default: 15)
        - Stores which candle has the pattern
        - Enables recency-based scoring

        Based on research:
        - Minimum 15 candles required (12 lookback + 3 pattern)
        """
        if not self._validate_dataframe(df):
            return False

        # Reset detection cache
        self._last_detection_candles_ago = None
        self._last_detection_direction = None

        # Need minimum 15 candles
        if len(df) < 15:
            return False

        try:
            result = talib.CDL3INSIDE(
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
        Get additional details about Three Inside detection with recency information.
        """
        if len(df) < 3:
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

        # Get the three candles where pattern was detected
        pattern_end_idx = len(df) - candles_ago
        pattern_start_idx = pattern_end_idx - 3

        # Ensure we have valid indices
        if pattern_start_idx < 0 or pattern_end_idx > len(df):
            return super()._get_detection_details(df)

        candles = df.iloc[pattern_start_idx:pattern_end_idx].copy()

        # Double check we have exactly 3 candles
        if len(candles) != 3:
            return super()._get_detection_details(df)

        # Calculate body sizes
        bodies = [abs(candles.iloc[i]['close'] - candles.iloc[i]['open']) for i in range(3)]
        full_ranges = [candles.iloc[i]['high'] - candles.iloc[i]['low'] for i in range(3)]
        avg_body = sum(bodies) / 3
        avg_full_range = sum(full_ranges) / 3

        # Confirmation strength - how much candle 3 confirms the reversal
        confirmation_strength = bodies[2] / avg_body if avg_body > 0 else 0

        # Base confidence
        # Higher when confirmation candle is strong
        base_confidence = min(0.75 + (confirmation_strength * 0.10), 0.95)

        # Adjust confidence with recency multiplier
        adjusted_confidence = min(base_confidence * recency_multiplier, 0.95)

        return {
            'location': 'current' if candles_ago == 0 else 'recent',
            'candles_ago': candles_ago,
            'recency_multiplier': recency_multiplier,
            'direction': direction,
            'confidence': adjusted_confidence,
            'metadata': {
                'body_sizes': [float(b) for b in bodies],
                'full_ranges': [float(r) for r in full_ranges],
                'avg_body': float(avg_body),
                'avg_full_range': float(avg_full_range),
                'confirmation_strength': float(confirmation_strength),
                'recency_info': {
                    'candles_ago': candles_ago,
                    'multiplier': recency_multiplier,
                    'lookback_window': self.lookback_window,
                    'base_confidence': base_confidence,
                    'adjusted_confidence': adjusted_confidence
                }
            }
        }
