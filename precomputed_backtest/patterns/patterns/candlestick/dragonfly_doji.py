"""
Dragonfly Doji Pattern Detector

Detects Dragonfly Doji candlestick pattern using TALib.
Dragonfly Doji is a bullish reversal pattern.

Version: 1.0.0 (2025-10-26) - Initial Implementation
- Bullish reversal pattern
- Doji with long lower shadow and little/no upper shadow
- Shows rejection of lower prices
"""

DRAGONFLY_DOJI_PATTERN_VERSION = "1.0.0"

import talib
import pandas as pd
import numpy as np
from typing import Dict, Any

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class DragonflyDojiPattern(BasePattern):
    """
    Dragonfly Doji candlestick pattern detector.

    Characteristics:
    - Doji with long lower shadow
    - Little to no upper shadow
    - Open and close at/near the high
    - Shows sellers pushed price down but buyers rejected
    - Strong bullish reversal signal at bottoms

    Strength: 3/3 (Strong)
    Direction: Bullish
    """

    def _get_pattern_name(self) -> str:
        return "Dragonfly Doji"

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
        Detect Dragonfly Doji pattern in last N candles using TALib.

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
            result = talib.CDLDRAGONFLYDOJI(
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
        Get additional details about Dragonfly Doji detection with recency information.
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

        # Lower shadow should be long
        lower_shadow = min(candle_data['open'], candle_data['close']) - candle_data['low']
        upper_shadow = candle_data['high'] - max(candle_data['open'], candle_data['close'])

        # Calculate shadow ratio (lower should be much larger than upper)
        shadow_ratio = lower_shadow / upper_shadow if upper_shadow > 0 else 10.0
        shadow_ratio = min(shadow_ratio, 10.0)  # Cap at 10

        # Base confidence
        # Higher when lower shadow is much larger than upper shadow
        base_confidence = min(0.70 + (shadow_ratio / 20.0), 0.95)

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
                'lower_shadow': float(lower_shadow),
                'upper_shadow': float(upper_shadow),
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
