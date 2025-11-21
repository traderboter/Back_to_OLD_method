"""
Hanging Man Pattern Detector

Detects Hanging Man candlestick pattern using TALib.
Hanging Man is a bearish reversal pattern.

Version: 3.0.0 (2025-10-25) - Recency Scoring Implementation
- ✨ NEW: Multi-candle lookback detection (checks last N candles)
- ✨ NEW: Recency-based scoring (recent patterns score higher)
- ✨ NEW: Configurable lookback_window and recency_multipliers
- 🔄 Detection now checks last 11 candles by default (not just current)
- 📊 Score adjusts based on pattern age (0-11 candles ago)
- 🔬 Based on research: min 12 candles required (11 lookback + 1 current)
"""

HANGING_MAN_PATTERN_VERSION = "3.0.0"

import talib
import pandas as pd
import numpy as np
from typing import Dict, Any

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class HangingManPattern(BasePattern):
    """
    Hanging Man candlestick pattern detector.

    Characteristics:
    - Bearish reversal pattern
    - Small body at top of candle
    - Long lower shadow (at least 2x body)
    - Little to no upper shadow
    - Best when appears after uptrend

    Strength: 2/3 (Medium)
    """

    def _get_pattern_name(self) -> str:
        return "Hanging Man"

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
        Detect Hanging Man pattern in last N candles using TALib.

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
            result = talib.CDLHANGINGMAN(
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
        Get additional details about Hanging Man detection with recency information.

        NEW in v3.0.0: Includes recency information
        - candles_ago: Which candle has the pattern (0-11)
        - recency_multiplier: Score multiplier based on age
        - Adjusted confidence based on recency
        """
        if len(df) == 0:
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
        candle_idx = -(candles_ago + 1)
        detected_candle = df.iloc[candle_idx]

        body_size = abs(detected_candle['close'] - detected_candle['open'])
        lower_shadow = min(detected_candle['open'], detected_candle['close']) - detected_candle['low']
        upper_shadow = detected_candle['high'] - max(detected_candle['open'], detected_candle['close'])
        full_range = detected_candle['high'] - detected_candle['low']

        # Use full_range instead of body_size to avoid zero/very small body issues
        shadow_ratio = lower_shadow / full_range if full_range > 0 else 0

        # Calculate base confidence
        base_confidence = min(0.70 + (shadow_ratio / 10), 0.95)

        # NEW v3.0.0: Adjust confidence with recency multiplier
        adjusted_confidence = min(base_confidence * recency_multiplier, 0.95)

        return {
            'location': 'current' if candles_ago == 0 else 'recent',
            'candles_ago': candles_ago,
            'recency_multiplier': recency_multiplier,
            'confidence': adjusted_confidence,
            'metadata': {
                'body_size': float(body_size),
                'lower_shadow': float(lower_shadow),
                'upper_shadow': float(upper_shadow),
                'full_range': float(full_range),
                'shadow_ratio': float(shadow_ratio),
                'recency_info': {
                    'candles_ago': candles_ago,
                    'multiplier': recency_multiplier,
                    'lookback_window': self.lookback_window,
                    'base_confidence': base_confidence,
                    'adjusted_confidence': adjusted_confidence
                }
            }
        }
