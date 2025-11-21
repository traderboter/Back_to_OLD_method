"""
Three White Soldiers Pattern Detector

Detects Three White Soldiers candlestick pattern using TALib.
Three White Soldiers is a strong bullish reversal pattern.

Version: 3.0.0 (2025-10-25) - Recency Scoring Implementation
- ✨ NEW: Multi-candle lookback detection (checks last N candles)
- ✨ NEW: Recency-based scoring (recent patterns score higher)
- ✨ NEW: Configurable lookback_window and recency_multipliers
- 🔄 Detection now checks last 12 candles by default (not just current)
- 📊 Score adjusts based on pattern age (0-12 candles ago)
- 🔬 Based on research: min 13 candles required (12 lookback + 1 current)
"""

THREE_WHITE_SOLDIERS_PATTERN_VERSION = "3.0.0"

import talib
import pandas as pd
import numpy as np
from typing import Dict, Any

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class ThreeWhiteSoldiersPattern(BasePattern):
    """
    Three White Soldiers candlestick pattern detector.

    Characteristics:
    - Strong bullish reversal pattern (3 candles)
    - Three consecutive long bullish candles
    - Each opens within previous body
    - Each closes progressively higher
    - Little to no upper shadows

    Strength: 3/3 (Strong)
    """

    def _get_pattern_name(self) -> str:
        return "Three White Soldiers"

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
        Detect Three White Soldiers pattern in last N candles using TALib.

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
            result = talib.CDL3WHITESOLDIERS(
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
        Get additional details about Three White Soldiers detection with recency information.

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
        # Calculate absolute position from end
        pattern_end_idx = len(df) - candles_ago
        pattern_start_idx = pattern_end_idx - 3

        # Ensure we have valid indices
        if pattern_start_idx < 0 or pattern_end_idx > len(df):
            return super()._get_detection_details(df)

        candles = df.iloc[pattern_start_idx:pattern_end_idx].copy()

        # Double check we have exactly 3 candles
        if len(candles) != 3:
            return super()._get_detection_details(df)

        # Calculate body sizes and full ranges
        bodies = [abs(candles.iloc[i]['close'] - candles.iloc[i]['open']) for i in range(3)]
        full_ranges = [candles.iloc[i]['high'] - candles.iloc[i]['low'] for i in range(3)]
        avg_body = sum(bodies) / 3
        avg_full_range = sum(full_ranges) / 3

        # Calculate consistency (similar body sizes)
        # Use safe division: ensure max_body is not zero
        max_body = max(bodies) if max(bodies) > 0 else 0.0001
        body_consistency = 1.0 - (max_body - min(bodies)) / max_body if max_body > 0 else 0

        # Calculate base confidence
        base_confidence = min(0.80 + (body_consistency / 5), 0.95)

        # NEW v3.0.0: Adjust confidence with recency multiplier
        adjusted_confidence = min(base_confidence * recency_multiplier, 0.95)

        return {
            'location': 'current' if candles_ago == 0 else 'recent',
            'candles_ago': candles_ago,
            'recency_multiplier': recency_multiplier,
            'confidence': adjusted_confidence,
            'metadata': {
                'body_sizes': [float(b) for b in bodies],
                'full_ranges': [float(r) for r in full_ranges],
                'avg_body': float(avg_body),
                'avg_full_range': float(avg_full_range),
                'body_consistency': float(body_consistency),
                'recency_info': {
                    'candles_ago': candles_ago,
                    'multiplier': recency_multiplier,
                    'lookback_window': self.lookback_window,
                    'base_confidence': base_confidence,
                    'adjusted_confidence': adjusted_confidence
                }
            }
        }
