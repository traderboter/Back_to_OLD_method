"""
Abandoned Baby Pattern Detector

Detects Abandoned Baby candlestick pattern using TA-Lib CDLABANDONEDBABY.
Abandoned Baby is a very strong reversal pattern with 85-95% reliability.

Version: 2.0.0 (2025-11-18) - TALib Integration
- 🔄 CHANGED: استفاده از TA-Lib CDLABANDONEDBABY
- ✅ KEPT: Multi-candle lookback detection
- ✅ KEPT: Recency-based scoring
- 📊 TALib parameter: penetration (gap tolerance)
- 💎 85-95% reliability when detected

Version: 1.0.0 (2025-11-18) - Initial Manual Implementation
- Manual Doji and gap detection
- Custom gap tolerance for crypto
"""

ABANDONED_BABY_PATTERN_VERSION = "2.0.0"

import talib
import pandas as pd
import numpy as np
from typing import Dict, Any

from signal_generation.analyzers.patterns.base_pattern import BasePattern


class AbandonedBabyPattern(BasePattern):
    """
    Abandoned Baby candlestick pattern detector using TA-Lib.

    Characteristics:
    - Very strong reversal pattern (3 candles)
    - Middle candle is a Doji, isolated by gaps
    - Can be bullish or bearish
    - 85-95% reliability (rare but very powerful)

    Bullish Abandoned Baby:
    - First candle: Bearish (downtrend)
    - Second candle: Doji with gap down
    - Third candle: Bullish with gap up from Doji
    - Very strong bullish reversal signal

    Bearish Abandoned Baby:
    - First candle: Bullish (uptrend)
    - Second candle: Doji with gap up
    - Third candle: Bearish with gap down from Doji
    - Very strong bearish reversal signal

    Strength: 3/3 (Very Strong)
    Direction: Both (Bullish or Bearish)
    Reliability: 85-95% (Highest!)

    TA-Lib Requirements:
    - Minimum candles: varies (TA-Lib internal)
    - Gap detection handled by TA-Lib
    - Doji detection handled by TA-Lib
    - Penetration parameter controls gap strictness

    Note on Crypto:
    - In 24/7 crypto markets, true gaps are rare
    - TA-Lib penetration parameter can be adjusted (default: 0.3)
    - Higher penetration = more lenient gap detection
    - Best results in 4h+ timeframes and futures
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize Abandoned Baby detector.

        Args:
            config: Configuration dictionary with optional pattern settings
        """
        super().__init__(config)
        self.version = ABANDONED_BABY_PATTERN_VERSION

        # Get pattern-specific configuration
        pattern_config = self.config.get('patterns', {}).get('abandoned_baby', {})

        # Penetration parameter for TA-Lib
        # Default 0.3 (30% penetration allowed)
        # Higher value = more lenient (better for crypto 24/7)
        self.penetration = pattern_config.get('penetration', 0.3)

    def _get_pattern_name(self) -> str:
        return "Abandoned Baby"

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
        Detect Abandoned Baby pattern in last N candles using TA-Lib CDLABANDONEDBABY.

        Multi-candle lookback detection:
        - Checks last N candles (lookback_window, default: 5)
        - Stores which candle has the pattern (_last_detection_candles_ago)
        - Enables recency-based scoring

        TA-Lib CDLABANDONEDBABY detects both bullish and bearish variants.

        Args:
            df: DataFrame with OHLCV data
            open_col: Name of open price column
            high_col: Name of high price column
            low_col: Name of low price column
            close_col: Name of close price column
            volume_col: Name of volume column

        Returns:
            True if Abandoned Baby pattern detected in last N candles
        """
        if not self._validate_dataframe(df):
            return False

        # Reset detection cache
        self._last_detection_candles_ago = None

        # TA-Lib needs reasonable number of candles
        # Abandoned Baby is 3-candle pattern, but TA-Lib may need more for context
        if len(df) < 5:
            return False

        try:
            # Use TA-Lib to detect Abandoned Baby
            # penetration: default 0.3 (can be adjusted for crypto)
            result = talib.CDLABANDONEDBABY(
                df[open_col].values,
                df[high_col].values,
                df[low_col].values,
                df[close_col].values,
                penetration=self.penetration
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
            'bullish' for Bullish Abandoned Baby, 'bearish' for Bearish
        """
        try:
            # Get TA-Lib result
            result = talib.CDLABANDONEDBABY(
                df['open'].values,
                df['high'].values,
                df['low'].values,
                df['close'].values,
                penetration=self.penetration
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
        Get additional details about Abandoned Baby detection with recency information.

        Returns:
            Dictionary containing:
            - location: 'current' or 'recent'
            - candles_ago: 0-N
            - recency_multiplier: Score multiplier based on age
            - confidence: Trading confidence (0-1), adjusted by recency
            - metadata: Detailed metrics including pattern quality
        """
        if len(df) < 3:
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

            # Get the three candles where pattern was detected
            idx3 = -(candles_ago + 1)
            idx2 = idx3 - 1
            idx1 = idx2 - 1

            # Ensure valid indices
            if abs(idx1) > len(df):
                return super()._get_detection_details(df)

            candle1 = df.iloc[idx1]
            candle2 = df.iloc[idx2]
            candle3 = df.iloc[idx3]

            # Determine variant (bullish or bearish)
            result = talib.CDLABANDONEDBABY(
                df['open'].values,
                df['high'].values,
                df['low'].values,
                df['close'].values,
                penetration=self.penetration
            )

            variant = 'bullish' if result[idx3] > 0 else 'bearish'

            # Calculate Doji quality (middle candle)
            doji_body = abs(candle2['close'] - candle2['open'])
            doji_range = candle2['high'] - candle2['low']
            doji_body_ratio = doji_body / doji_range if doji_range > 0 else 0
            # Perfect Doji has body_ratio close to 0
            doji_quality = max(0, 1.0 - (doji_body_ratio * 10))  # Normalize

            # Calculate gap sizes
            if variant == 'bullish':
                # Gap down from candle1 to Doji
                gap1_size = candle1['low'] - candle2['high']
                gap1_ratio = gap1_size / candle1['low'] if candle1['low'] > 0 else 0

                # Gap up from Doji to candle3
                gap2_size = candle3['low'] - candle2['high']
                gap2_ratio = gap2_size / candle2['high'] if candle2['high'] > 0 else 0
            else:  # bearish
                # Gap up from candle1 to Doji
                gap1_size = candle2['low'] - candle1['high']
                gap1_ratio = gap1_size / candle1['high'] if candle1['high'] > 0 else 0

                # Gap down from Doji to candle3
                gap2_size = candle2['low'] - candle3['high']
                gap2_ratio = gap2_size / candle2['low'] if candle2['low'] > 0 else 0

            # Isolation quality (how separated is the Doji)
            avg_gap = (abs(gap1_ratio) + abs(gap2_ratio)) / 2
            isolation_quality = min(avg_gap * 100, 1.0)  # Normalize to 1% = 1.0

            # Base confidence for Abandoned Baby is very high
            base_confidence = 0.85  # 85%

            # Bonus for perfect Doji
            doji_bonus = doji_quality * 0.05  # Up to +5%

            # Bonus for good isolation
            isolation_bonus = isolation_quality * 0.05  # Up to +5%

            base_confidence += doji_bonus + isolation_bonus
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
                    'gap1_size': float(gap1_size),
                    'gap1_ratio_pct': float(gap1_ratio * 100),
                    'gap2_size': float(gap2_size),
                    'gap2_ratio_pct': float(gap2_ratio * 100),
                    'doji_body_ratio': float(doji_body_ratio),
                    'doji_quality': float(doji_quality),
                    'isolation_quality': float(isolation_quality),
                    'avg_gap_ratio_pct': float(avg_gap * 100),
                    'penetration_param': self.penetration,
                    'pattern_name': f"Abandoned Baby ({'Bullish' if variant == 'bullish' else 'Bearish'})",
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

        Abandoned Baby is always very strong (2.5-3.0), but we adjust slightly based on:
        - Doji quality (how perfect the Doji is)
        - Isolation quality (how separated the Doji is)

        Args:
            df: DataFrame with OHLCV data
            detection_details: Detection details

        Returns:
            Strength value (2.5 to 3.0)
        """
        base_strength = 3.0  # Very strong pattern

        # Get quality metrics
        metadata = detection_details.get('metadata', {})
        doji_quality = metadata.get('doji_quality', 0.5)
        isolation_quality = metadata.get('isolation_quality', 0.5)

        # Small adjustments based on quality
        # Perfect pattern: 3.0
        # Good pattern: 2.7-2.9
        # Acceptable pattern: 2.5-2.7
        quality_adjustment = (doji_quality + isolation_quality) / 2 * 0.5

        final_strength = 2.5 + quality_adjustment

        # Cap between 2.5 and 3.0
        return max(2.5, min(final_strength, 3.0))
