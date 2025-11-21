"""
Double Top/Bottom Pattern Detector

Detects Double Top and Double Bottom chart patterns.
These are reversal patterns formed by two peaks or troughs at similar levels.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from scipy.signal import find_peaks

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class DoubleTopBottomPattern(BasePattern):
    """
    Double Top/Bottom chart pattern detector.

    Characteristics:
    - Double Top: Bearish reversal (two peaks at similar height)
    - Double Bottom: Bullish reversal (two troughs at similar depth)
    - Peaks/troughs should be within 2% of each other
    - Middle valley/peak between the two

    Strength: 3/3 (Strong)
    """

    def __init__(self, config: Dict[str, Any] = None):
        # Initialize instance variables BEFORE calling super().__init__
        # because _get_pattern_name() will be called during parent init
        self._detected_type = None  # 'top' or 'bottom'
        self.tolerance = config.get('double_pattern_tolerance', 0.02) if config else 0.02
        self.min_distance = config.get('double_pattern_min_distance', 5) if config else 5

        super().__init__(config)

    def _get_pattern_name(self) -> str:
        if self._detected_type == 'top':
            return "Double Top"
        elif self._detected_type == 'bottom':
            return "Double Bottom"
        return "Double Top/Bottom"

    def _get_pattern_type(self) -> str:
        return "chart"

    def _get_direction(self) -> str:
        return "both"  # Can be bullish (bottom) or bearish (top)

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
        """Detect Double Top or Double Bottom pattern."""
        if not self._validate_dataframe(df):
            return False

        if len(df) < 20:
            return False

        try:
            highs = df[high_col].values
            lows = df[low_col].values

            # Try to detect Double Top
            if self._detect_double_top(highs):
                self._detected_type = 'top'
                return True

            # Try to detect Double Bottom
            if self._detect_double_bottom(lows):
                self._detected_type = 'bottom'
                return True

            return False

        except Exception as e:
            return False

    def _detect_double_top(self, highs: np.ndarray) -> bool:
        """Detect double top pattern."""
        try:
            # Find peaks
            peaks, properties = find_peaks(
                highs,
                distance=self.min_distance,
                prominence=np.std(highs) * 0.5
            )

            if len(peaks) < 2:
                return False

            # Check last two peaks
            last_two_peaks = peaks[-2:]
            peak_heights = highs[last_two_peaks]

            # Check if peaks are similar (within tolerance)
            # Use safe division to avoid division by zero
            safe_peak_height = max(peak_heights[0], 0.0001)
            height_diff = abs(peak_heights[0] - peak_heights[1]) / safe_peak_height

            return height_diff < self.tolerance

        except Exception:
            return False

    def _detect_double_bottom(self, lows: np.ndarray) -> bool:
        """Detect double bottom pattern."""
        try:
            # Find troughs (peaks of inverted signal)
            troughs, properties = find_peaks(
                -lows,
                distance=self.min_distance,
                prominence=np.std(lows) * 0.5
            )

            if len(troughs) < 2:
                return False

            # Check last two troughs
            last_two_troughs = troughs[-2:]
            trough_depths = lows[last_two_troughs]

            # Check if troughs are similar (within tolerance)
            # Use safe division to avoid division by zero
            safe_trough_depth = max(trough_depths[0], 0.0001)
            depth_diff = abs(trough_depths[0] - trough_depths[1]) / safe_trough_depth

            return depth_diff < self.tolerance

        except Exception:
            return False

    def _get_actual_direction(
        self,
        df: pd.DataFrame,
        detection_details: Dict[str, Any]
    ) -> str:
        """Determine actual direction (bullish or bearish)."""
        if self._detected_type == 'bottom':
            return 'bullish'
        elif self._detected_type == 'top':
            return 'bearish'
        return 'bullish'

    def _get_detection_details(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get additional details about pattern detection."""
        if self._detected_type == 'top':
            return self._get_double_top_details(df)
        elif self._detected_type == 'bottom':
            return self._get_double_bottom_details(df)
        return super()._get_detection_details(df)

    def _get_double_top_details(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get details for double top pattern."""
        try:
            highs = df['high'].values
            peaks, _ = find_peaks(
                highs,
                distance=self.min_distance,
                prominence=np.std(highs) * 0.5
            )

            if len(peaks) >= 2:
                last_two = peaks[-2:]
                peak_heights = highs[last_two]

                # Calculate similarity
                # Use safe division to avoid division by zero
                safe_peak_height = max(peak_heights[0], 0.0001)
                similarity = 1.0 - (abs(peak_heights[0] - peak_heights[1]) / safe_peak_height)

                # Find valley between peaks
                valley_idx = last_two[0] + np.argmin(highs[last_two[0]:last_two[1]])
                safe_min_peak = max(min(peak_heights), 0.0001)
                valley_depth = (min(peak_heights) - highs[valley_idx]) / safe_min_peak

                return {
                    'location': 'recent',
                    'candles_ago': len(df) - last_two[-1] - 1,
                    'confidence': min(0.75 + (similarity * 0.15), 0.95),
                    'metadata': {
                        'peak_1_height': float(peak_heights[0]),
                        'peak_2_height': float(peak_heights[1]),
                        'similarity': float(similarity),
                        'valley_depth_ratio': float(valley_depth),
                        'peak_distance': int(last_two[1] - last_two[0])
                    }
                }
        except Exception:
            pass

        return super()._get_detection_details(df)

    def _get_double_bottom_details(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get details for double bottom pattern."""
        try:
            lows = df['low'].values
            troughs, _ = find_peaks(
                -lows,
                distance=self.min_distance,
                prominence=np.std(lows) * 0.5
            )

            if len(troughs) >= 2:
                last_two = troughs[-2:]
                trough_depths = lows[last_two]

                # Calculate similarity
                # Use safe division to avoid division by zero
                safe_trough_depth = max(trough_depths[0], 0.0001)
                similarity = 1.0 - (abs(trough_depths[0] - trough_depths[1]) / safe_trough_depth)

                # Find peak between troughs
                peak_idx = last_two[0] + np.argmax(lows[last_two[0]:last_two[1]])
                safe_max_trough = max(max(trough_depths), 0.0001)
                peak_height = (lows[peak_idx] - max(trough_depths)) / safe_max_trough

                return {
                    'location': 'recent',
                    'candles_ago': len(df) - last_two[-1] - 1,
                    'confidence': min(0.75 + (similarity * 0.15), 0.95),
                    'metadata': {
                        'trough_1_depth': float(trough_depths[0]),
                        'trough_2_depth': float(trough_depths[1]),
                        'similarity': float(similarity),
                        'peak_height_ratio': float(peak_height),
                        'trough_distance': int(last_two[1] - last_two[0])
                    }
                }
        except Exception:
            pass

        return super()._get_detection_details(df)
