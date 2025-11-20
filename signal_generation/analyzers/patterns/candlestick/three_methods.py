"""
Rising/Falling Three Methods Pattern Detector

Detects Rising Three Methods and Falling Three Methods candlestick patterns using TALib.
These are continuation patterns that confirm trend strength.

Version: 1.0.0 (2025-10-26) - Initial Implementation
- 5-candle continuation pattern
- Shows brief consolidation before trend continues
- Strong confirmation of existing trend
"""

THREE_METHODS_PATTERN_VERSION = "1.0.0"

import talib
import pandas as pd
import numpy as np
from typing import Dict, Any

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class ThreeMethodsPattern(BasePattern):
    """
    Rising/Falling Three Methods candlestick pattern detector.

    Characteristics:
    - 5-candle continuation pattern
    - Rising Three Methods (bullish continuation):
      1. Long bullish candle
      2-4. Three small candles (pullback) staying within candle 1
      5. Long bullish candle closing above candle 1
    - Falling Three Methods (bearish continuation):
      1. Long bearish candle
      2-4. Three small candles (pullback) staying within candle 1
      5. Long bearish candle closing below candle 1
    - Confirms trend continuation

    Strength: 3/3 (Strong) - trend continuation
    Direction: Can be bullish or bearish
    """

    def _get_pattern_name(self) -> str:
        return "Three Methods"

    def _get_pattern_type(self) -> str:
        return "candlestick"

    def _get_direction(self) -> str:
        return "both"  # Can be bullish or bearish

    def _get_base_strength(self) -> int:
        return 3  # Strong pattern - confirms trend

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
        Detect Rising/Falling Three Methods pattern in last N candles using TALib.

        Multi-candle lookback detection:
        - Checks last N candles (lookback_window, default: 15)
        - Stores which candle has the pattern
        - Enables recency-based scoring

        Based on research:
        - Minimum 17 candles required (12 lookback + 5 pattern)
        """
        if not self._validate_dataframe(df):
            return False

        # Reset detection cache
        self._last_detection_candles_ago = None
        self._last_detection_direction = None

        # Need minimum 17 candles
        if len(df) < 17:
            return False

        try:
            result = talib.CDLRISEFALL3METHODS(
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
        Get additional details about Three Methods detection with recency information.
        """
        if len(df) < 5:
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

        # Get the five candles where pattern was detected
        pattern_end_idx = len(df) - candles_ago
        pattern_start_idx = pattern_end_idx - 5

        # Ensure we have valid indices
        if pattern_start_idx < 0 or pattern_end_idx > len(df):
            return super()._get_detection_details(df)

        candles = df.iloc[pattern_start_idx:pattern_end_idx].copy()

        # Double check we have exactly 5 candles
        if len(candles) != 5:
            return super()._get_detection_details(df)

        # Calculate body sizes
        bodies = [abs(candles.iloc[i]['close'] - candles.iloc[i]['open']) for i in range(5)]
        full_ranges = [candles.iloc[i]['high'] - candles.iloc[i]['low'] for i in range(5)]
        avg_body = sum(bodies) / 5
        avg_full_range = sum(full_ranges) / 5

        # Trend candles (1st and 5th) should be larger
        trend_candle_size = (bodies[0] + bodies[4]) / 2
        consolidation_size = (bodies[1] + bodies[2] + bodies[3]) / 3

        # Trend strength - trend candles should be much larger than consolidation
        trend_strength = trend_candle_size / consolidation_size if consolidation_size > 0 else 1.0

        # Base confidence
        # Higher when trend candles are much larger than consolidation
        base_confidence = min(0.75 + (min(trend_strength, 3.0) / 30.0), 0.95)

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
                'trend_candle_size': float(trend_candle_size),
                'consolidation_size': float(consolidation_size),
                'trend_strength': float(trend_strength),
                'recency_info': {
                    'candles_ago': candles_ago,
                    'multiplier': recency_multiplier,
                    'lookback_window': self.lookback_window,
                    'base_confidence': base_confidence,
                    'adjusted_confidence': adjusted_confidence
                }
            }
        }
