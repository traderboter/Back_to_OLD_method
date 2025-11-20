"""
Dark Cloud Cover Pattern Detector

Detects Dark Cloud Cover candlestick pattern using TALib.
Dark Cloud Cover is a bearish reversal pattern.

Version: 3.0.0 (2025-10-25) - Recency Scoring Implementation
- ✨ NEW: Multi-candle lookback detection (checks last N candles)
- ✨ NEW: Recency-based scoring (recent patterns score higher)
- ✨ NEW: Configurable lookback_window and recency_multipliers
- 🔄 Detection now checks last 11 candles by default (not just current)
- 📊 Score adjusts based on pattern age (0-11 candles ago)
- 🔬 Based on research: min 12 candles required (11 lookback + 1 current)
"""

DARK_CLOUD_COVER_PATTERN_VERSION = "3.0.0"

import talib
import pandas as pd
import numpy as np
from typing import Dict, Any

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class DarkCloudCoverPattern(BasePattern):
    """
    Dark Cloud Cover candlestick pattern detector.

    Characteristics:
    - Bearish reversal pattern (2 candles)
    - First candle: Bullish
    - Second candle: Bearish, opens above previous high, closes below midpoint of first

    Strength: 2/3 (Medium)
    """

    def _get_pattern_name(self) -> str:
        return "Dark Cloud Cover"

    def _get_pattern_type(self) -> str:
        return "candlestick"

    def _get_direction(self) -> str:
        return "bearish"

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
        Detect Dark Cloud Cover pattern in last N candles using TALib.

        NEW in v3.0.0: Multi-candle lookback detection
        - Checks last N candles (lookback_window, default: 11)
        - Stores which candle has the pattern (_last_detection_candles_ago)
        - Enables recency-based scoring

        Based on research:
        - Minimum 12 candles required (11 lookback + 1 current)
        """
        if not self._validate_dataframe(df):
            return False

        # Reset detection cache
        self._last_detection_candles_ago = None

        # Based on research: need minimum 12 candles
        if len(df) < 12:
            return False

        try:
            result = talib.CDLDARKCLOUDCOVER(
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
        Get additional details about Dark Cloud Cover detection with recency information.

        NEW in v3.0.0: Includes recency information
        - candles_ago: Which candle has the pattern (0-11)
        - recency_multiplier: Score multiplier based on age
        - Adjusted confidence based on recency
        """
        if len(df) < 2:
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

        # Get the two candles where pattern was detected
        candle_idx = -(candles_ago + 1)
        detected_candle = df.iloc[candle_idx]
        prev_candle = df.iloc[candle_idx - 1]

        prev_body = abs(prev_candle['close'] - prev_candle['open'])
        curr_body = abs(detected_candle['close'] - detected_candle['open'])
        prev_full_range = prev_candle['high'] - prev_candle['low']
        curr_full_range = detected_candle['high'] - detected_candle['low']

        # How far into previous candle's body
        safe_prev_body = max(prev_body, prev_full_range * 0.3) if prev_full_range > 0 else 0.0001
        prev_midpoint = (prev_candle['open'] + prev_candle['close']) / 2
        penetration = (prev_midpoint - detected_candle['close']) / safe_prev_body if safe_prev_body > 0 else 0

        # Calculate base confidence
        base_confidence = min(0.70 + (penetration / 5), 0.95)

        # NEW v3.0.0: Adjust confidence with recency multiplier
        adjusted_confidence = min(base_confidence * recency_multiplier, 0.95)

        return {
            'location': 'current' if candles_ago == 0 else 'recent',
            'candles_ago': candles_ago,
            'recency_multiplier': recency_multiplier,
            'confidence': adjusted_confidence,
            'metadata': {
                'prev_body': float(prev_body),
                'curr_body': float(curr_body),
                'prev_full_range': float(prev_full_range),
                'curr_full_range': float(curr_full_range),
                'penetration_ratio': float(penetration),
                'recency_info': {
                    'candles_ago': candles_ago,
                    'multiplier': recency_multiplier,
                    'lookback_window': self.lookback_window,
                    'base_confidence': base_confidence,
                    'adjusted_confidence': adjusted_confidence
                }
            }
        }
