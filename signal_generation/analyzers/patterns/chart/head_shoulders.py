"""
Head and Shoulders Pattern Detector

Detects Head and Shoulders and Inverse Head and Shoulders chart patterns.
These are strong reversal patterns.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from scipy.signal import find_peaks

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class HeadShouldersPattern(BasePattern):
    """
    Head and Shoulders chart pattern detector.

    Characteristics:
    - Head and Shoulders: Bearish reversal (3 peaks: left shoulder, head, right shoulder)
    - Inverse H&S: Bullish reversal (3 troughs: left shoulder, head, right shoulder)
    - Head is highest/lowest
    - Shoulders are similar height/depth

    Strength: 3/3 (Strong)
    """

    def __init__(self, config: Dict[str, Any] = None):
        # Initialize instance variables BEFORE calling super().__init__
        # because _get_pattern_name() will be called during parent init
        self._detected_type = None  # 'regular' or 'inverse'
        self.shoulder_tolerance = config.get('hs_shoulder_tolerance', 0.05) if config else 0.05
        self.min_distance = config.get('hs_min_distance', 5) if config else 5

        super().__init__(config)

    def _get_pattern_name(self) -> str:
        if self._detected_type == 'regular':
            return "Head and Shoulders"
        elif self._detected_type == 'inverse':
            return "Inverse Head and Shoulders"
        return "Head and Shoulders"

    def _get_pattern_type(self) -> str:
        return "chart"

    def _get_direction(self) -> str:
        return "both"  # Can be bullish (inverse) or bearish (regular)

    def _get_base_strength(self) -> int:
        return 3  # Strong reversal pattern

    def detect(
        self,
        df: pd.DataFrame,
        open_col: str = 'open',
        high_col: str = 'high',
        low_col: str = 'low',
        close_col: str = 'close',
        volume_col: str = 'volume'
    ) -> bool:
        """Detect Head and Shoulders or Inverse H&S pattern."""
        if not self._validate_dataframe(df):
            return False

        if len(df) < 30:
            return False

        try:
            highs = df[high_col].values
            lows = df[low_col].values

            # Try to detect regular Head and Shoulders
            if self._detect_regular_hs(highs):
                self._detected_type = 'regular'
                return True

            # Try to detect Inverse Head and Shoulders
            if self._detect_inverse_hs(lows):
                self._detected_type = 'inverse'
                return True

            return False

        except Exception as e:
            return False

    def _detect_regular_hs(self, highs: np.ndarray) -> bool:
        """Detect regular Head and Shoulders pattern."""
        try:
            # Find peaks
            peaks, _ = find_peaks(
                highs,
                distance=self.min_distance,
                prominence=np.std(highs) * 0.5
            )

            if len(peaks) < 3:
                return False

            # Get last three peaks
            last_three = peaks[-3:]
            peak_heights = highs[last_three]

            # Check if middle peak (head) is highest
            if peak_heights[1] <= peak_heights[0] or peak_heights[1] <= peak_heights[2]:
                return False

            # Check if shoulders are similar height
            # Use safe division to avoid division by zero
            safe_shoulder = max(peak_heights[0], 0.0001)
            shoulder_diff = abs(peak_heights[0] - peak_heights[2]) / safe_shoulder

            return shoulder_diff < self.shoulder_tolerance

        except Exception:
            return False

    def _detect_inverse_hs(self, lows: np.ndarray) -> bool:
        """Detect Inverse Head and Shoulders pattern."""
        try:
            # Find troughs
            troughs, _ = find_peaks(
                -lows,
                distance=self.min_distance,
                prominence=np.std(lows) * 0.5
            )

            if len(troughs) < 3:
                return False

            # Get last three troughs
            last_three = troughs[-3:]
            trough_depths = lows[last_three]

            # Check if middle trough (head) is lowest
            if trough_depths[1] >= trough_depths[0] or trough_depths[1] >= trough_depths[2]:
                return False

            # Check if shoulders are similar depth
            # Use safe division to avoid division by zero
            safe_shoulder = max(trough_depths[0], 0.0001)
            shoulder_diff = abs(trough_depths[0] - trough_depths[2]) / safe_shoulder

            return shoulder_diff < self.shoulder_tolerance

        except Exception:
            return False

    def _get_actual_direction(
        self,
        df: pd.DataFrame,
        detection_details: Dict[str, Any]
    ) -> str:
        """Determine actual direction (bullish or bearish)."""
        if self._detected_type == 'inverse':
            return 'bullish'
        elif self._detected_type == 'regular':
            return 'bearish'
        return 'bearish'

    def _get_detection_details(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get additional details about pattern detection."""
        if self._detected_type == 'regular':
            return self._get_regular_hs_details(df)
        elif self._detected_type == 'inverse':
            return self._get_inverse_hs_details(df)
        return super()._get_detection_details(df)

    def _get_regular_hs_details(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get details for regular H&S pattern."""
        try:
            highs = df['high'].values
            peaks, _ = find_peaks(
                highs,
                distance=self.min_distance,
                prominence=np.std(highs) * 0.5
            )

            if len(peaks) >= 3:
                last_three = peaks[-3:]
                peak_heights = highs[last_three]

                # Calculate shoulder symmetry
                # Use safe division to avoid division by zero
                safe_shoulder = max(peak_heights[0], 0.0001)
                shoulder_symmetry = 1.0 - (abs(peak_heights[0] - peak_heights[2]) / safe_shoulder)

                # Calculate head prominence
                safe_head = max(peak_heights[1], 0.0001)
                head_prominence = (peak_heights[1] - max(peak_heights[0], peak_heights[2])) / safe_head

                return {
                    'location': 'forming',
                    'candles_ago': len(df) - last_three[-1] - 1,
                    'confidence': min(0.70 + (shoulder_symmetry * 0.15) + (head_prominence * 0.10), 0.95),
                    'metadata': {
                        'left_shoulder': float(peak_heights[0]),
                        'head': float(peak_heights[1]),
                        'right_shoulder': float(peak_heights[2]),
                        'shoulder_symmetry': float(shoulder_symmetry),
                        'head_prominence': float(head_prominence)
                    }
                }
        except Exception:
            pass

        return super()._get_detection_details(df)

    def _get_inverse_hs_details(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get details for inverse H&S pattern."""
        try:
            lows = df['low'].values
            troughs, _ = find_peaks(
                -lows,
                distance=self.min_distance,
                prominence=np.std(lows) * 0.5
            )

            if len(troughs) >= 3:
                last_three = troughs[-3:]
                trough_depths = lows[last_three]

                # Calculate shoulder symmetry
                # Use safe division to avoid division by zero
                safe_shoulder = max(trough_depths[0], 0.0001)
                shoulder_symmetry = 1.0 - (abs(trough_depths[0] - trough_depths[2]) / safe_shoulder)

                # Calculate head prominence
                safe_head = max(trough_depths[1], 0.0001)
                head_prominence = (min(trough_depths[0], trough_depths[2]) - trough_depths[1]) / safe_head

                return {
                    'location': 'forming',
                    'candles_ago': len(df) - last_three[-1] - 1,
                    'confidence': min(0.70 + (shoulder_symmetry * 0.15) + (head_prominence * 0.10), 0.95),
                    'metadata': {
                        'left_shoulder': float(trough_depths[0]),
                        'head': float(trough_depths[1]),
                        'right_shoulder': float(trough_depths[2]),
                        'shoulder_symmetry': float(shoulder_symmetry),
                        'head_prominence': float(head_prominence)
                    }
                }
        except Exception:
            pass

        return super()._get_detection_details(df)
