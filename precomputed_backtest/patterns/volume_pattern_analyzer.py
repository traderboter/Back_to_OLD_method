"""
VolumePatternAnalyzer - Advanced Volume Pattern Detection

Detects 6 advanced volume patterns from OLD SYSTEM:
1. Accumulation Detection - Smart money buying
2. Distribution Detection - Smart money selling
3. Climax Volume - Exhaustion signals
4. Volume Divergence - Price/volume disagreement
5. Smart Money Flow - Institutional activity
6. Volume Profile Analysis - Support/resistance levels

Uses indicators (pre-calculated by IndicatorCalculator):
- volume
- volume_sma
- close, high, low
- obv (On-Balance Volume)

Outputs to context:
- volume_patterns: {
    'accumulation': {'detected': bool, 'strength': float, 'duration': int},
    'distribution': {'detected': bool, 'strength': float, 'duration': int},
    'climax_volume': {'type': 'buying'|'selling'|None, 'intensity': float},
    'volume_divergence': {'detected': bool, 'type': 'bullish'|'bearish', 'strength': float},
    'smart_money': {'flow': 'buying'|'selling'|'neutral', 'confidence': float},
    'volume_profile': {'support_levels': list, 'resistance_levels': list, 'poc': float}
  }
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
import pandas as pd
import numpy as np
from collections import defaultdict

from signal_generation.analyzers.base_analyzer import BaseAnalyzer
from signal_generation.context import AnalysisContext
from signal_generation.enums import Direction
from signal_generation.constants import (
    VOLUME_ACCUMULATION_THRESHOLD,
    VOLUME_ACCUMULATION_RANGE,
    VOLUME_CLIMAX_THRESHOLD,
    VOLUME_CLIMAX_RANGE
)

logger = logging.getLogger(__name__)


class VolumePatternAnalyzer(BaseAnalyzer):
    """
    Detects advanced volume patterns for institutional activity and
    market structure analysis.

    Features:
    1. Accumulation: Low volatility + high volume + narrow range
    2. Distribution: Low volatility + high volume + topping pattern
    3. Climax Volume: Extreme volume + potential reversal
    4. Volume Divergence: Price moves without volume support
    5. Smart Money Flow: Net buying/selling pressure
    6. Volume Profile: Volume distribution across price levels
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize VolumePatternAnalyzer.

        Args:
            config: Configuration dictionary
        """
        super().__init__(config)

        # Get pattern-specific configuration
        pattern_config = config.get('volume_patterns', {})

        # Accumulation/Distribution settings - Using Constants
        self.accumulation_lookback = pattern_config.get('accumulation_lookback', 20)
        self.accumulation_volume_threshold = pattern_config.get('accumulation_volume_threshold', VOLUME_ACCUMULATION_THRESHOLD)
        self.accumulation_range_threshold = pattern_config.get('accumulation_range_threshold', VOLUME_ACCUMULATION_RANGE)

        # Climax volume settings - Using Constants
        self.climax_volume_threshold = pattern_config.get('climax_volume_threshold', VOLUME_CLIMAX_THRESHOLD)
        self.climax_range_threshold = pattern_config.get('climax_range_threshold', VOLUME_CLIMAX_RANGE)

        # Divergence settings
        self.divergence_lookback = pattern_config.get('divergence_lookback', 14)
        self.divergence_sensitivity = pattern_config.get('divergence_sensitivity', 0.7)

        # Smart money settings
        self.smart_money_lookback = pattern_config.get('smart_money_lookback', 10)

        # Volume profile settings
        self.vp_lookback = pattern_config.get('vp_lookback', 100)
        self.vp_bins = pattern_config.get('vp_bins', 20)

        # Enable/disable
        self.enabled = config.get('analyzers', {}).get('volume_patterns', {}).get('enabled', True)

        logger.info("VolumePatternAnalyzer initialized successfully")

    def analyze(self, context: AnalysisContext) -> None:
        """
        Main analysis method - detects volume patterns.

        Args:
            context: AnalysisContext with pre-calculated indicators
        """
        # 1. Check if enabled
        if not self._check_enabled():
            logger.debug(f"VolumePatternAnalyzer disabled for {context.symbol}")
            return

        # 2. Validate context
        if not self._validate_context(context):
            logger.warning(f"VolumePatternAnalyzer: Invalid context for {context.symbol}")
            return

        try:
            df = context.df

            # Need sufficient data
            if len(df) < 50:
                logger.warning(f"Insufficient data for VolumePatternAnalyzer on {context.symbol}")
                context.add_result('volume_patterns', {'status': 'insufficient_data'})
                return

            # 3. Detect all patterns
            accumulation = self._detect_accumulation(df)
            distribution = self._detect_distribution(df)
            climax = self._detect_climax_volume(df)
            divergence = self._detect_volume_divergence(df)
            smart_money = self._detect_smart_money_flow(df)
            volume_profile = self._analyze_volume_profile(df)

            # 4. Build result
            result = {
                'status': 'ok',
                'accumulation': accumulation,
                'distribution': distribution,
                'climax_volume': climax,
                'volume_divergence': divergence,
                'smart_money': smart_money,
                'volume_profile': volume_profile,
                'patterns_detected': []
            }

            # 5. List detected patterns
            if accumulation['detected']:
                result['patterns_detected'].append('accumulation')
            if distribution['detected']:
                result['patterns_detected'].append('distribution')
            if climax['type'] is not None:
                result['patterns_detected'].append(f"climax_{climax['type']}")
            if divergence['detected']:
                result['patterns_detected'].append(f"divergence_{divergence['type']}")
            if smart_money['flow'] != 'neutral':
                result['patterns_detected'].append(f"smart_money_{smart_money['flow']}")

            # 6. Store in context
            context.add_result('volume_patterns', result)

            logger.info(
                f"VolumePatternAnalyzer completed for {context.symbol} {context.timeframe}: "
                f"patterns={len(result['patterns_detected'])}"
            )

        except Exception as e:
            logger.error(f"Error in VolumePatternAnalyzer for {context.symbol}: {e}", exc_info=True)
            context.add_result('volume_patterns', {
                'status': 'error',
                'error': str(e)
            })

    def _detect_accumulation(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect accumulation pattern: Smart money buying.

        Characteristics:
        - Higher than average volume
        - Narrow price range (low volatility)
        - Price stable or slowly rising
        - Sustained over multiple periods

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Accumulation analysis
        """
        lookback = min(self.accumulation_lookback, len(df))
        recent_data = df.tail(lookback)

        # Calculate metrics
        volume_ratio = recent_data['volume'].mean() / df['volume_sma'].iloc[-1]

        # Price range (as % of close)
        price_range = (recent_data['high'].max() - recent_data['low'].min()) / recent_data['close'].mean()

        # Price trend (should be flat or slightly up)
        price_change = (recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]) / recent_data['close'].iloc[0]

        # OBV trend (should be increasing)
        obv_change = (recent_data['obv'].iloc[-1] - recent_data['obv'].iloc[0]) / abs(recent_data['obv'].iloc[0] + 1)

        # Detect accumulation
        detected = (
            volume_ratio >= self.accumulation_volume_threshold and  # High volume
            price_range <= self.accumulation_range_threshold and     # Narrow range
            price_change >= -0.02 and                                # Not falling
            obv_change > 0                                           # OBV rising
        )

        # Calculate strength
        strength = 0.0
        if detected:
            strength += min(volume_ratio / 2.0, 1.0) * 0.4      # Volume contribution
            strength += (1.0 - price_range / 0.05) * 0.3        # Range contribution
            strength += min(max(obv_change * 10, 0), 1.0) * 0.3 # OBV contribution

        # Duration (how many consecutive periods)
        duration = 0
        for i in range(len(recent_data) - 1, -1, -1):
            candle_range = (recent_data['high'].iloc[i] - recent_data['low'].iloc[i]) / recent_data['close'].iloc[i]
            if candle_range <= self.accumulation_range_threshold:
                duration += 1
            else:
                break

        return {
            'detected': detected,
            'strength': round(strength, 2),
            'duration': duration,
            'volume_ratio': round(volume_ratio, 2),
            'price_range': round(price_range * 100, 2),  # As percentage
            'obv_trend': 'rising' if obv_change > 0 else 'falling'
        }

    def _detect_distribution(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect distribution pattern: Smart money selling.

        Characteristics:
        - Higher than average volume
        - Narrow price range (low volatility)
        - Price stable or slowly falling
        - OBV decreasing

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Distribution analysis
        """
        lookback = min(self.accumulation_lookback, len(df))
        recent_data = df.tail(lookback)

        # Calculate metrics
        volume_ratio = recent_data['volume'].mean() / df['volume_sma'].iloc[-1]

        # Price range
        price_range = (recent_data['high'].max() - recent_data['low'].min()) / recent_data['close'].mean()

        # Price trend (should be flat or slightly down)
        price_change = (recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]) / recent_data['close'].iloc[0]

        # OBV trend (should be decreasing)
        obv_change = (recent_data['obv'].iloc[-1] - recent_data['obv'].iloc[0]) / abs(recent_data['obv'].iloc[0] + 1)

        # Detect distribution
        detected = (
            volume_ratio >= self.accumulation_volume_threshold and  # High volume
            price_range <= self.accumulation_range_threshold and     # Narrow range
            price_change <= 0.02 and                                 # Not rising much
            obv_change < 0                                           # OBV falling
        )

        # Calculate strength
        strength = 0.0
        if detected:
            strength += min(volume_ratio / 2.0, 1.0) * 0.4      # Volume contribution
            strength += (1.0 - price_range / 0.05) * 0.3        # Range contribution
            strength += min(max(-obv_change * 10, 0), 1.0) * 0.3 # OBV contribution

        # Duration
        duration = 0
        for i in range(len(recent_data) - 1, -1, -1):
            candle_range = (recent_data['high'].iloc[i] - recent_data['low'].iloc[i]) / recent_data['close'].iloc[i]
            if candle_range <= self.accumulation_range_threshold:
                duration += 1
            else:
                break

        return {
            'detected': detected,
            'strength': round(strength, 2),
            'duration': duration,
            'volume_ratio': round(volume_ratio, 2),
            'price_range': round(price_range * 100, 2),
            'obv_trend': 'rising' if obv_change > 0 else 'falling'
        }

    def _detect_climax_volume(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect climax volume: Exhaustion signal.

        Buying Climax:
        - Extreme high volume (3x+ average)
        - Large up move
        - Potential top

        Selling Climax:
        - Extreme high volume (3x+ average)
        - Large down move
        - Potential bottom

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Climax volume analysis
        """
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume_sma'].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

        # Price change
        current_close = df['close'].iloc[-1]
        prev_close = df['close'].iloc[-2]
        price_change = (current_close - prev_close) / prev_close

        # Detect climax
        climax_type = None
        intensity = 0.0

        if volume_ratio >= self.climax_volume_threshold:
            if price_change >= self.climax_range_threshold:
                # Buying climax
                climax_type = 'buying'
                intensity = min(volume_ratio / 5.0, 1.0)
            elif price_change <= -self.climax_range_threshold:
                # Selling climax
                climax_type = 'selling'
                intensity = min(volume_ratio / 5.0, 1.0)

        return {
            'type': climax_type,
            'intensity': round(intensity, 2),
            'volume_ratio': round(volume_ratio, 2),
            'price_change': round(price_change * 100, 2),  # As percentage
            'signal': 'exhaustion' if climax_type else None
        }

    def _detect_volume_divergence(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect volume divergence: Price moves without volume support.

        Bullish Divergence:
        - Price making lower lows
        - Volume decreasing or OBV rising
        - Potential reversal up

        Bearish Divergence:
        - Price making higher highs
        - Volume decreasing or OBV falling
        - Potential reversal down

        Args:
            df: DataFrame with OHLCV and OBV data

        Returns:
            Divergence analysis
        """
        lookback = min(self.divergence_lookback, len(df))
        recent_data = df.tail(lookback)

        # Find price peaks and troughs
        prices = recent_data['close'].values
        volumes = recent_data['volume'].values
        obv_values = recent_data['obv'].values

        # Simple peak/trough detection
        price_trend = 1 if prices[-1] > prices[0] else -1
        volume_trend = 1 if volumes[-1] > volumes[0] else -1
        obv_trend = 1 if obv_values[-1] > obv_values[0] else -1

        # Detect divergence
        detected = False
        div_type = None
        strength = 0.0

        # Bearish divergence: price up, volume/OBV down
        if price_trend > 0 and (volume_trend < 0 or obv_trend < 0):
            detected = True
            div_type = 'bearish'
            # Strength based on magnitude
            price_change = (prices[-1] - prices[0]) / prices[0]
            obv_change = (obv_values[-1] - obv_values[0]) / abs(obv_values[0] + 1)
            strength = min(abs(price_change - obv_change), 1.0)

        # Bullish divergence: price down, volume/OBV up
        elif price_trend < 0 and (volume_trend > 0 or obv_trend > 0):
            detected = True
            div_type = 'bullish'
            price_change = (prices[-1] - prices[0]) / prices[0]
            obv_change = (obv_values[-1] - obv_values[0]) / abs(obv_values[0] + 1)
            strength = min(abs(price_change - obv_change), 1.0)

        return {
            'detected': detected,
            'type': div_type,
            'strength': round(strength, 2),
            'price_trend': 'up' if price_trend > 0 else 'down',
            'obv_trend': 'up' if obv_trend > 0 else 'down',
            'signal': 'reversal' if detected else None
        }

    def _detect_smart_money_flow(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect smart money flow: Institutional buying/selling.

        Uses:
        - Large volume candles
        - Price action
        - OBV direction

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Smart money flow analysis
        """
        lookback = min(self.smart_money_lookback, len(df))
        recent_data = df.tail(lookback)

        avg_volume = df['volume_sma'].iloc[-1]

        # Identify large volume candles (smart money)
        large_volume_candles = recent_data[recent_data['volume'] > avg_volume * 1.5]

        if len(large_volume_candles) == 0:
            return {
                'flow': 'neutral',
                'confidence': 0.0,
                'buying_pressure': 0.0,
                'selling_pressure': 0.0
            }

        # Calculate buying vs selling pressure
        buying_pressure = 0.0
        selling_pressure = 0.0

        for idx, row in large_volume_candles.iterrows():
            # Close position in range
            close_position = (row['close'] - row['low']) / (row['high'] - row['low']) if row['high'] != row['low'] else 0.5

            # Volume weighted
            vol_weight = row['volume'] / avg_volume

            if close_position > 0.6:  # Closed high = buying
                buying_pressure += vol_weight
            elif close_position < 0.4:  # Closed low = selling
                selling_pressure += vol_weight

        # Determine flow
        if buying_pressure > selling_pressure * 1.3:
            flow = 'buying'
            confidence = min((buying_pressure - selling_pressure) / (buying_pressure + selling_pressure + 0.01), 1.0)
        elif selling_pressure > buying_pressure * 1.3:
            flow = 'selling'
            confidence = min((selling_pressure - buying_pressure) / (buying_pressure + selling_pressure + 0.01), 1.0)
        else:
            flow = 'neutral'
            confidence = 0.0

        return {
            'flow': flow,
            'confidence': round(confidence, 2),
            'buying_pressure': round(buying_pressure, 2),
            'selling_pressure': round(selling_pressure, 2)
        }

    def _analyze_volume_profile(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze volume profile: Volume distribution across price levels.

        Identifies:
        - Point of Control (POC): Price level with highest volume
        - High Volume Nodes: Support/resistance
        - Low Volume Nodes: Potential quick moves

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Volume profile analysis
        """
        lookback = min(self.vp_lookback, len(df))
        recent_data = df.tail(lookback)

        # Price range
        min_price = recent_data['low'].min()
        max_price = recent_data['high'].max()

        if max_price == min_price:
            return {
                'poc': float(df['close'].iloc[-1]),
                'support_levels': [],
                'resistance_levels': [],
                'value_area_high': None,
                'value_area_low': None
            }

        # Create price bins
        bins = np.linspace(min_price, max_price, self.vp_bins)
        volume_at_price = np.zeros(len(bins) - 1)

        # Distribute volume across price bins
        for idx, row in recent_data.iterrows():
            # Assume volume is distributed evenly across the candle range
            low_bin = np.digitize(row['low'], bins) - 1
            high_bin = np.digitize(row['high'], bins) - 1

            low_bin = max(0, min(low_bin, len(volume_at_price) - 1))
            high_bin = max(0, min(high_bin, len(volume_at_price) - 1))

            # Distribute volume
            if low_bin == high_bin:
                volume_at_price[low_bin] += row['volume']
            else:
                for b in range(low_bin, high_bin + 1):
                    volume_at_price[b] += row['volume'] / (high_bin - low_bin + 1)

        # Find Point of Control (highest volume)
        poc_idx = np.argmax(volume_at_price)
        poc_price = (bins[poc_idx] + bins[poc_idx + 1]) / 2

        # Find high volume nodes (support/resistance)
        threshold = np.percentile(volume_at_price, 75)
        high_volume_indices = np.where(volume_at_price > threshold)[0]

        current_price = df['close'].iloc[-1]

        # Separate into support and resistance
        support_levels = []
        resistance_levels = []

        for idx in high_volume_indices:
            price_level = (bins[idx] + bins[idx + 1]) / 2
            if price_level < current_price:
                support_levels.append(round(price_level, 2))
            elif price_level > current_price:
                resistance_levels.append(round(price_level, 2))

        # Sort
        support_levels = sorted(support_levels, reverse=True)[:3]  # Top 3 nearest
        resistance_levels = sorted(resistance_levels)[:3]           # Top 3 nearest

        # Value Area (70% of volume)
        cumsum = np.cumsum(sorted(volume_at_price, reverse=True))
        total_volume = cumsum[-1]
        value_area_volume = total_volume * 0.7

        value_area_idx = np.where(cumsum >= value_area_volume)[0][0]
        value_area_high = bins[-value_area_idx] if value_area_idx < len(bins) else max_price
        value_area_low = bins[value_area_idx] if value_area_idx < len(bins) else min_price

        return {
            'poc': round(poc_price, 2),
            'support_levels': support_levels,
            'resistance_levels': resistance_levels,
            'value_area_high': round(float(value_area_high), 2),
            'value_area_low': round(float(value_area_low), 2)
        }

    def _validate_context(self, context: AnalysisContext) -> bool:
        """Validate required indicators."""
        required = ['volume', 'volume_sma', 'obv', 'close', 'high', 'low']

        df = context.df
        for col in required:
            if col not in df.columns:
                logger.error(f"Missing required column: {col}")
                return False

        return True
