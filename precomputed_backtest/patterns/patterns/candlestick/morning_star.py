"""
Morning Star Pattern Detector

Detects Morning Star candlestick pattern using TALib.
Morning Star is a strong bullish reversal pattern.

Version: 3.0.0 (2025-10-25) - Recency Scoring Implementation
- ✨ NEW: Multi-candle lookback detection (checks last N candles)
- ✨ NEW: Recency-based scoring (recent patterns score higher)
- ✨ NEW: Configurable lookback_window and recency_multipliers
- 🔄 Detection now checks last 12 candles by default (not just current)
- 📊 Score adjusts based on pattern age (0-12 candles ago)
- 🔬 Based on research: min 13 candles required (12 lookback + 1 current)
"""

MORNING_STAR_PATTERN_VERSION = "3.0.0"

import talib
import pandas as pd
import numpy as np
from typing import Dict, Any

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class MorningStarPattern(BasePattern):
    """
    Morning Star candlestick pattern detector.

    Characteristics:
    - Strong bullish reversal pattern (3 candles)
    - First candle: Large bearish candle
    - Second candle: Small body (star) - gaps down
    - Third candle: Large bullish candle - closes above midpoint of first

    Strength: 3/3 (Strong)
    """

    def _get_pattern_name(self) -> str:
        return "Morning Star"

    def _get_pattern_type(self) -> str:
        return "candlestick"

    def _get_direction(self) -> str:
        return "bullish"

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
        Detect Morning Star pattern in last N candles using TALib.

        NEW in v3.0.0: Multi-candle lookback detection
        - Checks last N candles (lookback_window, default: 12)
        - Stores which candle has the pattern (_last_detection_candles_ago)
        - Enables recency-based scoring

        Based on research:
        - Minimum 13 candles required (12 lookback + 1 current)

        Returns:
            bool: True if Morning Star pattern detected in last N candles
        """
        if not self._validate_dataframe(df):
            return False

        # Reset detection cache
        self._last_detection_candles_ago = None

        # Based on research: need minimum 13 candles
        if len(df) < 13:
            return False

        try:
            # Use TALib to detect
            result = talib.CDLMORNINGSTAR(
                df[open_col].values,
                df[high_col].values,
                df[low_col].values,
                df[close_col].values
            )

            # NEW v3.0.0: Check last N candles (lookback_window)
            lookback = min(self.lookback_window, len(result))

            for i in range(lookback):
                # Check from newest to oldest
                # i=0: last candle (result[-1])
                # i=1: second to last (result[-2])
                # etc.
                idx = -(i + 1)

                if result[idx] != 0:
                    # Pattern found! Store position
                    self._last_detection_candles_ago = i
                    return True

            # Not found in last N candles
            return False

        except Exception as e:
            return False

    def _get_detection_details(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get additional details about Morning Star detection.

        NEW in v3.0.0: Includes recency information
        - candles_ago: Which candle has the pattern (0-12)
        - recency_multiplier: Score multiplier based on age
        - Adjusted confidence based on recency

        Returns:
            Dictionary containing:
            - location: 'current' or 'recent'
            - candles_ago: 0-12
            - recency_multiplier: based on config
            - confidence: Trading confidence (0-1), adjusted by recency
            - metadata: Detailed metrics + recency info
        """
        # Validate minimum candles
        if len(df) < 3:
            return super()._get_detection_details(df)

        try:
            # Get detection position (set by detect())
            candles_ago = getattr(self, '_last_detection_candles_ago', 0)
            if candles_ago is None:
                candles_ago = 0

            # Get recency multiplier
            if candles_ago < len(self.recency_multipliers):
                recency_multiplier = self.recency_multipliers[candles_ago]
            else:
                recency_multiplier = 0.0  # Too old

            # Morning Star is a 3-candle pattern
            # The pattern completes on the last candle (third candle)
            # So if candles_ago=0, we need candles at indices -3, -2, -1
            # If candles_ago=1, we need candles at indices -4, -3, -2
            candle_idx = -(candles_ago + 1)  # Index of third candle (completion)

            # Get the three candles of the pattern
            first_candle = df.iloc[candle_idx - 2]  # First bearish candle
            star_candle = df.iloc[candle_idx - 1]   # Small star in middle
            last_candle = df.iloc[candle_idx]       # Third bullish candle

            # Calculate body sizes and full ranges
            first_body = abs(first_candle['close'] - first_candle['open'])
            star_body = abs(star_candle['close'] - star_candle['open'])
            last_body = abs(last_candle['close'] - last_candle['open'])
            first_full_range = first_candle['high'] - first_candle['low']
            star_full_range = star_candle['high'] - star_candle['low']
            last_full_range = last_candle['high'] - last_candle['low']

            # Star should be small (lower star_ratio = better)
            # Use safe division: minimum threshold is 30% of candle's full range
            safe_first_body = max(first_body, first_full_range * 0.3) if first_full_range > 0 else 0.0001
            star_ratio = star_body / safe_first_body if safe_first_body > 0 else 0

            # Last candle should be strong (higher strength_ratio = better)
            strength_ratio = last_body / safe_first_body if safe_first_body > 0 else 1

            # Calculate base confidence: higher strength + smaller star = higher confidence
            # Subtract star_ratio to reward smaller stars
            base_confidence_score = 0.80 + (strength_ratio / 10) - (star_ratio / 20)
            base_confidence = min(max(base_confidence_score, 0.70), 0.95)  # Keep in valid range

            # NEW v3.0.0: Adjust confidence with recency multiplier
            adjusted_confidence = min(base_confidence * recency_multiplier, 0.95)

            # Determine candle directions
            first_direction = 'bearish' if first_candle['close'] < first_candle['open'] else 'bullish'
            last_direction = 'bullish' if last_candle['close'] > last_candle['open'] else 'bearish'

            return {
                'location': 'current' if candles_ago == 0 else 'recent',
                'candles_ago': candles_ago,
                'recency_multiplier': recency_multiplier,
                'confidence': adjusted_confidence,
                'metadata': {
                    'first_body': float(first_body),
                    'star_body': float(star_body),
                    'last_body': float(last_body),
                    'first_full_range': float(first_full_range),
                    'star_full_range': float(star_full_range),
                    'last_full_range': float(last_full_range),
                    'star_ratio': float(star_ratio),
                    'strength_ratio': float(strength_ratio),
                    'first_candle_direction': first_direction,
                    'last_candle_direction': last_direction,
                    'recency_info': {
                        'candles_ago': candles_ago,
                        'multiplier': recency_multiplier,
                        'lookback_window': self.lookback_window,
                        'base_confidence': base_confidence,
                        'adjusted_confidence': adjusted_confidence
                    }
                }
            }
        except Exception:
            return super()._get_detection_details(df)
