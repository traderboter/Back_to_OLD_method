"""
Morning Doji Star Pattern Detector

Detects Morning Doji Star candlestick pattern using TALib.
Morning Doji Star is a bullish reversal pattern.

Version: 3.0.0 (2025-10-25) - Recency Scoring Implementation
- ✨ NEW: Multi-candle lookback detection (checks last N candles)
- ✨ NEW: Recency-based scoring (recent patterns score higher)
- ✨ NEW: Configurable lookback_window and recency_multipliers
- 🔄 Detection now checks last 12 candles by default (not just current)
- 📊 Score adjusts based on pattern age (0-12 candles ago)
- 🔬 Based on research: min 13 candles required (12 lookback + 1 current)
"""

MORNING_DOJI_STAR_PATTERN_VERSION = "3.0.0"

import talib
import pandas as pd
import numpy as np
from typing import Dict, Any

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class MorningDojiStarPattern(BasePattern):
    """
    Morning Doji Star candlestick pattern detector.

    Characteristics:
    - Bullish reversal pattern (3 candles)
    - First candle: Large bearish
    - Second candle: Doji (very small body) - gaps down
    - Third candle: Large bullish - closes above midpoint of first

    Strength: 2/3 (Medium)
    """

    def _get_pattern_name(self) -> str:
        return "Morning Doji Star"

    def _get_pattern_type(self) -> str:
        return "candlestick"

    def _get_direction(self) -> str:
        return "bullish"

    def _get_base_strength(self) -> int:
        return 2

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
        Detect Morning Doji Star pattern in last N candles using TALib.

        NEW in v3.0.0: Multi-candle lookback detection
        - Checks last N candles (lookback_window, default: 12)
        - Stores which candle has the pattern (_last_detection_candles_ago)
        - Enables recency-based scoring

        Based on research:
        - Minimum 13 candles required (12 lookback + 1 current)
        """
        if not self._validate_dataframe(df):
            return False

        # Reset detection cache
        self._last_detection_candles_ago = None

        # Based on research: need minimum 13 candles
        if len(df) < 13:
            return False

        try:
            result = talib.CDLMORNINGDOJISTAR(
                df[open_col].values,
                df[high_col].values,
                df[low_col].values,
                df[close_col].values
            )

            # NEW v3.0.0: Check last N candles (lookback_window)
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
        Get additional details about Morning Doji Star detection with recency information.

        NEW in v3.0.0: Includes recency information
        - candles_ago: Which candle has the pattern (0-12)
        - recency_multiplier: Score multiplier based on age
        - Adjusted confidence based on recency
        """
        if len(df) < 3:
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

        # Get the three candles where pattern was detected
        candle_idx = -(candles_ago + 1)
        first_candle = df.iloc[candle_idx - 2]
        doji_candle = df.iloc[candle_idx - 1]
        last_candle = df.iloc[candle_idx]

        first_body = abs(first_candle['close'] - first_candle['open'])
        doji_body = abs(doji_candle['close'] - doji_candle['open'])
        last_body = abs(last_candle['close'] - last_candle['open'])
        first_full_range = first_candle['high'] - first_candle['low']
        doji_full_range = doji_candle['high'] - doji_candle['low']
        last_full_range = last_candle['high'] - last_candle['low']

        # Doji should be very small
        # Use safe division: minimum threshold is 30% of candle's full range
        safe_first_body = max(first_body, first_full_range * 0.3) if first_full_range > 0 else 0.0001
        doji_ratio = doji_body / safe_first_body if safe_first_body > 0 else 0

        # Calculate base confidence
        base_confidence = min(0.75 - (doji_ratio * 2), 0.95)

        # NEW v3.0.0: Adjust confidence with recency multiplier
        adjusted_confidence = min(base_confidence * recency_multiplier, 0.95)

        return {
            'location': 'current' if candles_ago == 0 else 'recent',
            'candles_ago': candles_ago,
            'recency_multiplier': recency_multiplier,
            'confidence': adjusted_confidence,
            'metadata': {
                'first_body': float(first_body),
                'doji_body': float(doji_body),
                'last_body': float(last_body),
                'first_full_range': float(first_full_range),
                'doji_full_range': float(doji_full_range),
                'last_full_range': float(last_full_range),
                'doji_ratio': float(doji_ratio),
                'recency_info': {
                    'candles_ago': candles_ago,
                    'multiplier': recency_multiplier,
                    'lookback_window': self.lookback_window,
                    'base_confidence': base_confidence,
                    'adjusted_confidence': adjusted_confidence
                }
            }
        }
