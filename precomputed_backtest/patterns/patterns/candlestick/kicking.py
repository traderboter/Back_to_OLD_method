"""
Kicking Pattern Detector

Detects Kicking candlestick pattern using TA-Lib CDLKICKING.
Kicking is a very strong reversal pattern with 85-95% reliability.

Version: 1.0.0 (2025-11-18) - Initial TALib Implementation
- ✨ استفاده از TA-Lib CDLKICKING
- 📊 Multi-candle lookback detection
- 🔄 Recency-based scoring
- 💎 85-95% reliability (very strong!)
- ⚠️ Very rare pattern (requires gap + two Marubozu)
"""

KICKING_PATTERN_VERSION = "1.0.0"

import talib
import pandas as pd
import numpy as np
from typing import Dict, Any

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class KickingPattern(BasePattern):
    """
    Kicking candlestick pattern detector using TA-Lib.

    Characteristics:
    - Very strong reversal pattern (2 candles)
    - Two consecutive Marubozu candles in opposite directions
    - Gap between the two candles
    - Shows dramatic sentiment change
    - 85-95% reliability (rare but very powerful)

    Bullish Kicking:
    - First candle: Bearish Marubozu (no shadows)
    - Second candle: Bullish Marubozu with gap up
    - Very strong bullish reversal signal

    Bearish Kicking:
    - First candle: Bullish Marubozu (no shadows)
    - Second candle: Bearish Marubozu with gap down
    - Very strong bearish reversal signal

    Strength: 3/3 (Very Strong)
    Direction: Both (Bullish or Bearish)
    Reliability: 85-95% (Very High!)

    TA-Lib Requirements:
    - Minimum candles: varies (TA-Lib internal)
    - Gap detection handled by TA-Lib
    - Marubozu detection handled by TA-Lib
    - No additional parameters

    Note on Crypto:
    - In 24/7 crypto markets, true gaps are very rare
    - Marubozu candles (no shadows) are also uncommon
    - This pattern is VERY RARE in crypto
    - Most common in futures and during extreme volatility
    - Best results in 4h+ timeframes
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize Kicking detector.

        Args:
            config: Configuration dictionary with optional pattern settings
        """
        super().__init__(config)
        self.version = KICKING_PATTERN_VERSION

    def _get_pattern_name(self) -> str:
        return "Kicking"

    def _get_pattern_type(self) -> str:
        return "candlestick"

    def _get_direction(self) -> str:
        return "both"  # Can be bullish or bearish

    def _get_base_strength(self) -> int:
        return 3  # Very strong pattern

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
        Detect Kicking pattern in last N candles using TA-Lib CDLKICKING.

        Multi-candle lookback detection:
        - Checks last N candles (lookback_window, default: 5)
        - Stores which candle has the pattern (_last_detection_candles_ago)
        - Enables recency-based scoring

        TA-Lib CDLKICKING detects both bullish and bearish variants.

        Args:
            df: DataFrame with OHLCV data
            open_col: Name of open price column
            high_col: Name of high price column
            low_col: Name of low price column
            close_col: Name of close price column
            volume_col: Name of volume column

        Returns:
            True if Kicking pattern detected in last N candles
        """
        if not self._validate_dataframe(df):
            return False

        # Reset detection cache
        self._last_detection_candles_ago = None

        # Kicking is 2-candle pattern, but TA-Lib may need more for context
        if len(df) < 3:
            return False

        try:
            # Use TA-Lib to detect Kicking
            result = talib.CDLKICKING(
                df[open_col].values,
                df[high_col].values,
                df[low_col].values,
                df[close_col].values
            )

            # Check last N candles (lookback_window)
            lookback = min(self.lookback_window, len(result))

            for i in range(lookback):
                # Check from newest to oldest
                # i=0: last candle (result[-1])
                # i=1: second to last (result[-2])
                # etc.
                idx = -(i + 1)

                # result values: +100 (bullish), -100 (bearish), 0 (no pattern)
                if result[idx] != 0:
                    # Pattern found! Store position
                    self._last_detection_candles_ago = i
                    return True

            # Not found in last N candles
            return False

        except Exception as e:
            return False

    def _get_actual_direction(
        self,
        df: pd.DataFrame,
        detection_details: Dict[str, Any]
    ) -> str:
        """
        Determine actual direction (bullish or bearish).

        Args:
            df: DataFrame with OHLCV data
            detection_details: Detection details

        Returns:
            'bullish' for Bullish Kicking, 'bearish' for Bearish Kicking
        """
        try:
            # Get TA-Lib result
            result = talib.CDLKICKING(
                df['open'].values,
                df['high'].values,
                df['low'].values,
                df['close'].values
            )

            if len(result) == 0:
                return 'bullish'

            # Get detection position
            candles_ago = getattr(self, '_last_detection_candles_ago', 0)
            if candles_ago is None:
                candles_ago = 0

            idx = -(candles_ago + 1)

            # Positive = bullish, negative = bearish
            return 'bullish' if result[idx] > 0 else 'bearish'

        except Exception:
            return 'bullish'

    def _get_detection_details(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get additional details about Kicking detection with recency information.

        Returns:
            Dictionary containing:
            - location: 'current' or 'recent'
            - candles_ago: 0-N
            - recency_multiplier: Score multiplier based on age
            - confidence: Trading confidence (0-1), adjusted by recency
            - metadata: Detailed metrics including pattern quality
        """
        if len(df) < 2:
            return super()._get_detection_details(df)

        try:
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
            idx2 = -(candles_ago + 1)  # Second candle
            idx1 = idx2 - 1              # First candle

            # Ensure valid indices
            if abs(idx1) > len(df):
                return super()._get_detection_details(df)

            candle1 = df.iloc[idx1]
            candle2 = df.iloc[idx2]

            # Determine variant (bullish or bearish)
            result = talib.CDLKICKING(
                df['open'].values,
                df['high'].values,
                df['low'].values,
                df['close'].values
            )

            variant = 'bullish' if result[idx2] > 0 else 'bearish'

            # Calculate Marubozu quality for both candles
            # Perfect Marubozu = no upper or lower shadows
            def calc_marubozu_quality(candle):
                body = abs(candle['close'] - candle['open'])
                full_range = candle['high'] - candle['low']

                if full_range == 0:
                    return 0.0

                # Upper shadow
                upper_shadow = candle['high'] - max(candle['open'], candle['close'])
                # Lower shadow
                lower_shadow = min(candle['open'], candle['close']) - candle['low']

                # Total shadows as percentage of range
                total_shadows = (upper_shadow + lower_shadow) / full_range

                # Perfect Marubozu has 0 shadows
                # Quality = 1.0 - shadows percentage
                return max(0.0, 1.0 - total_shadows)

            marubozu1_quality = calc_marubozu_quality(candle1)
            marubozu2_quality = calc_marubozu_quality(candle2)
            avg_marubozu_quality = (marubozu1_quality + marubozu2_quality) / 2

            # Calculate gap size
            if variant == 'bullish':
                # Gap up from bearish to bullish
                gap_size = candle2['open'] - candle1['close']
                gap_ratio = gap_size / candle1['close'] if candle1['close'] > 0 else 0
            else:  # bearish
                # Gap down from bullish to bearish
                gap_size = candle1['close'] - candle2['open']
                gap_ratio = gap_size / candle1['close'] if candle1['close'] > 0 else 0

            # Normalize gap quality (1% gap = 1.0 quality)
            gap_quality = min(abs(gap_ratio) * 100, 1.0)

            # Calculate body sizes (strength of the Marubozu candles)
            body1_size = abs(candle1['close'] - candle1['open'])
            body2_size = abs(candle2['close'] - candle2['open'])
            body1_pct = body1_size / candle1['open'] if candle1['open'] > 0 else 0
            body2_pct = body2_size / candle2['open'] if candle2['open'] > 0 else 0

            # Base confidence for Kicking is very high
            base_confidence = 0.85  # 85%

            # Bonus for perfect Marubozu (no shadows)
            marubozu_bonus = avg_marubozu_quality * 0.05  # Up to +5%

            # Bonus for good gap
            gap_bonus = gap_quality * 0.05  # Up to +5%

            base_confidence += marubozu_bonus + gap_bonus
            base_confidence = min(base_confidence, 0.95)  # Cap at 95%

            # Adjust confidence with recency multiplier
            adjusted_confidence = min(base_confidence * recency_multiplier, 0.95)

            return {
                'location': 'current' if candles_ago == 0 else 'recent',
                'candles_ago': candles_ago,
                'recency_multiplier': recency_multiplier,
                'confidence': adjusted_confidence,
                'metadata': {
                    'variant': variant,
                    'gap_size': float(gap_size),
                    'gap_ratio_pct': float(gap_ratio * 100),
                    'gap_quality': float(gap_quality),
                    'marubozu1_quality': float(marubozu1_quality),
                    'marubozu2_quality': float(marubozu2_quality),
                    'avg_marubozu_quality': float(avg_marubozu_quality),
                    'body1_size': float(body1_size),
                    'body1_pct': float(body1_pct * 100),
                    'body2_size': float(body2_size),
                    'body2_pct': float(body2_pct * 100),
                    'pattern_name': f"Kicking ({'Bullish' if variant == 'bullish' else 'Bearish'})",
                    'recency_info': {
                        'candles_ago': candles_ago,
                        'multiplier': recency_multiplier,
                        'lookback_window': self.lookback_window,
                        'base_confidence': base_confidence,
                        'adjusted_confidence': adjusted_confidence
                    }
                }
            }

        except Exception as e:
            return super()._get_detection_details(df)

    def _calculate_dynamic_strength(
        self,
        df: pd.DataFrame,
        detection_details: Dict[str, Any]
    ) -> float:
        """
        Calculate dynamic strength based on pattern quality.

        Kicking is always very strong (2.5-3.0), but we adjust based on:
        - Marubozu quality (how perfect the candles are)
        - Gap quality (how big the gap is)

        Args:
            df: DataFrame with OHLCV data
            detection_details: Detection details

        Returns:
            Strength value (2.5 to 3.0)
        """
        base_strength = 3.0  # Very strong pattern

        # Get quality metrics
        metadata = detection_details.get('metadata', {})
        marubozu_quality = metadata.get('avg_marubozu_quality', 0.5)
        gap_quality = metadata.get('gap_quality', 0.5)

        # Small adjustments based on quality
        # Perfect pattern: 3.0
        # Good pattern: 2.7-2.9
        # Acceptable pattern: 2.5-2.7
        quality_adjustment = (marubozu_quality + gap_quality) / 2 * 0.5

        final_strength = 2.5 + quality_adjustment

        # Cap between 2.5 and 3.0
        return max(2.5, min(final_strength, 3.0))
