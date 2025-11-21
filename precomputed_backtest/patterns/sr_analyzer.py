"""
SRAnalyzer - Support and Resistance Level Detection

Detects support and resistance levels using multiple methods.

Uses indicators (pre-calculated by IndicatorCalculator):
- OHLC data (open, high, low, close)
- atr (Average True Range) for level strength calculation
- volume for validation

Can read from context (context-aware):
- trend: To prioritize levels based on trend direction
- volume: To confirm level strength

Outputs to context:
- support_resistance: {
    'support_levels': [list of support levels],
    'resistance_levels': [list of resistance levels],
    'nearest_support': float,
    'nearest_resistance': float,
    'key_level_distance': float,
    'breakout_zone': bool,
    'level_strength': float (0-3)
  }
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
import pandas as pd
import numpy as np

from signal_generation.analyzers.base_analyzer import BaseAnalyzer
from signal_generation.context import AnalysisContext
from signal_generation.constants import (
    SR_MIN_TOUCHES,
    SR_LEVEL_TOLERANCE_PERCENT,
    SR_ZONE_DISTANCE_PERCENT
)

logger = logging.getLogger(__name__)


class SRAnalyzer(BaseAnalyzer):
    """
    Analyzes support and resistance levels.
    
    Key features:
    1. Pivot point detection
    2. Local highs/lows identification
    3. Level strength calculation
    4. Key zone identification
    5. Breakout detection
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize SRAnalyzer.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        
        # Get SR-specific configuration
        sr_config = config.get('support_resistance', {})

        # Default parameters (can be overridden per-TF)
        self.default_lookback = 100
        self.default_min_touches = SR_MIN_TOUCHES
        self.default_atr_tolerance_multiplier = 0.3
        self.default_prominence_factor = 0.1
        self.default_broken_level_lookback = 20

        # Fallback values
        self.lookback = self.default_lookback
        self.min_touches = self.default_min_touches
        self.atr_tolerance_multiplier = self.default_atr_tolerance_multiplier
        self.prominence_factor = self.default_prominence_factor
        self.broken_level_lookback = self.default_broken_level_lookback

        # Non-TF specific settings
        self.use_atr_tolerance = sr_config.get('use_atr_tolerance', True)
        self.level_tolerance_percent = sr_config.get('level_tolerance', SR_LEVEL_TOLERANCE_PERCENT)
        self.zone_tolerance = sr_config.get('zone_tolerance', SR_ZONE_DISTANCE_PERCENT)

        # Enable/disable
        self.enabled = config.get('analyzers', {}).get('support_resistance', {}).get('enabled', True)
        
        logger.info("SRAnalyzer initialized successfully")
    
    def analyze(self, context: AnalysisContext) -> None:
        """
        Main analysis method - detects support/resistance levels.
        
        Args:
            context: AnalysisContext with pre-calculated indicators
        """
        # 1. Check if enabled
        if not self._check_enabled():
            logger.debug(f"SRAnalyzer disabled for {context.symbol}")
            return
        
        # 2. Validate context
        if not self._validate_context(context):
            logger.warning(f"SRAnalyzer: Invalid context for {context.symbol}")
            return
        
        try:
            # 3. Get per-TF parameters
            self.lookback = self.get_threshold('lookback', self.default_lookback, context.timeframe)
            self.min_touches = self.get_threshold('min_touches', self.default_min_touches, context.timeframe)
            self.atr_tolerance_multiplier = self.get_threshold('atr_tolerance_multiplier', self.default_atr_tolerance_multiplier, context.timeframe)
            self.prominence_factor = self.get_threshold('prominence_factor', self.default_prominence_factor, context.timeframe)
            self.broken_level_lookback = self.get_threshold('broken_level_lookback', self.default_broken_level_lookback, context.timeframe)

            # 4. Read data
            df = context.df

            # Ensure we have enough data
            if len(df) < 50:
                logger.warning(f"Insufficient data for SRAnalyzer on {context.symbol}")
                context.add_result('support_resistance', {
                    'status': 'insufficient_data',
                    'support_levels': [],
                    'resistance_levels': []
                })
                return
            
            current_price = df['close'].iloc[-1]
            atr = df['atr'].iloc[-1] if 'atr' in df.columns else None

            # 5. Detect support levels
            support_levels = self._detect_support_levels(df, current_price)

            # 6. Detect resistance levels
            resistance_levels = self._detect_resistance_levels(df, current_price)

            # 7. Find nearest levels
            nearest_support = self._find_nearest_level(support_levels, current_price, 'below')
            nearest_resistance = self._find_nearest_level(resistance_levels, current_price, 'above')

            # 8. Calculate distance to key levels
            key_level_distance = self._calculate_key_level_distance(
                current_price,
                nearest_support,
                nearest_resistance
            )

            # 9. Detect breakout zones
            is_breakout = self._detect_breakout_zone(
                df,
                current_price,
                support_levels,
                resistance_levels,
                atr
            )

            # 10. Context-aware prioritization
            trend_context = context.get_result('trend')
            volume_context = context.get_result('volume')

            # Prioritize levels based on trend
            if trend_context:
                support_levels = self._prioritize_levels(
                    support_levels,
                    trend_context,
                    'support'
                )
                resistance_levels = self._prioritize_levels(
                    resistance_levels,
                    trend_context,
                    'resistance'
                )

            # 11. Calculate overall level strength
            level_strength = self._calculate_level_strength(
                support_levels,
                resistance_levels,
                volume_context
            )

            # 12. NEW: Detect zones (clusters of levels)
            support_zones = self._detect_zones(support_levels)
            resistance_zones = self._detect_zones(resistance_levels)

            # 13. NEW: Detect broken levels (confirmed breakouts)
            all_levels = support_levels + resistance_levels
            broken_levels = self._detect_broken_levels(df, all_levels)

            # 14. Build result
            result = {
                'status': 'ok',
                'support_levels': support_levels[:5],  # Top 5
                'resistance_levels': resistance_levels[:5],  # Top 5
                'nearest_support': nearest_support,
                'nearest_resistance': nearest_resistance,
                'key_level_distance': key_level_distance,
                'breakout_zone': is_breakout,
                'level_strength': level_strength,
                'current_price': round(current_price, 2),
                'context_aware': trend_context is not None,
                # NEW: Add zone and broken level info
                'support_zones': support_zones,
                'resistance_zones': resistance_zones,
                'broken_levels': broken_levels
            }

            # 15. Store in context
            context.add_result('support_resistance', result)
            
            logger.info(
                f"SRAnalyzer completed for {context.symbol} {context.timeframe}: "
                f"{len(support_levels)} supports, {len(resistance_levels)} resistances, "
                f"{len(support_zones)} support zones, {len(resistance_zones)} resistance zones, "
                f"{len(broken_levels)} broken levels"
            )
            
        except Exception as e:
            logger.error(f"Error in SRAnalyzer for {context.symbol}: {e}", exc_info=True)
            context.add_result('support_resistance', {
                'status': 'error',
                'support_levels': [],
                'resistance_levels': [],
                'error': str(e)
            })
    
    def _detect_support_levels(
        self,
        df: pd.DataFrame,
        current_price: float
    ) -> List[Dict[str, Any]]:
        """
        Detect support levels (potential buying zones).
        
        Args:
            df: DataFrame with OHLC data
            current_price: Current price
            
        Returns:
            List of support levels
        """
        lookback = min(self.lookback, len(df))
        recent_df = df.tail(lookback)
        
        lows = recent_df['low'].values
        
        # Find local lows using scipy
        try:
            from scipy.signal import find_peaks
            peaks, properties = find_peaks(-lows, distance=5, prominence=np.std(lows) * self.prominence_factor)
        except:
            # Fallback: simple method
            peaks = self._find_local_extrema(lows, 'min')
        
        # Group similar levels
        support_prices = lows[peaks]
        levels = self._group_levels(support_prices, current_price, recent_df)
        
        # Calculate strength for each level
        support_levels = []
        for level_price, touches in levels:
            if level_price < current_price:  # Only below current price
                strength = self._calculate_single_level_strength(
                    level_price,
                    touches,
                    recent_df,
                    'support'
                )
                
                support_levels.append({
                    'price': round(level_price, 2),
                    'strength': strength,
                    'touches': touches,
                    'type': 'support',
                    'distance_percent': ((current_price - level_price) / current_price) * 100
                })
        
        # Sort by strength
        support_levels.sort(key=lambda x: x['strength'], reverse=True)
        
        return support_levels
    
    def _detect_resistance_levels(
        self,
        df: pd.DataFrame,
        current_price: float
    ) -> List[Dict[str, Any]]:
        """
        Detect resistance levels (potential selling zones).
        
        Args:
            df: DataFrame with OHLC data
            current_price: Current price
            
        Returns:
            List of resistance levels
        """
        lookback = min(self.lookback, len(df))
        recent_df = df.tail(lookback)
        
        highs = recent_df['high'].values
        
        # Find local highs
        try:
            from scipy.signal import find_peaks
            peaks, properties = find_peaks(highs, distance=5, prominence=np.std(highs) * self.prominence_factor)
        except:
            peaks = self._find_local_extrema(highs, 'max')
        
        # Group similar levels
        resistance_prices = highs[peaks]
        levels = self._group_levels(resistance_prices, current_price, recent_df)
        
        # Calculate strength
        resistance_levels = []
        for level_price, touches in levels:
            if level_price > current_price:  # Only above current price
                strength = self._calculate_single_level_strength(
                    level_price,
                    touches,
                    recent_df,
                    'resistance'
                )
                
                resistance_levels.append({
                    'price': round(level_price, 2),
                    'strength': strength,
                    'touches': touches,
                    'type': 'resistance',
                    'distance_percent': ((level_price - current_price) / current_price) * 100
                })
        
        # Sort by strength
        resistance_levels.sort(key=lambda x: x['strength'], reverse=True)
        
        return resistance_levels
    
    def _find_local_extrema(
        self,
        data: np.ndarray,
        extrema_type: str = 'max'
    ) -> List[int]:
        """
        Simple method to find local extrema (fallback).
        
        Args:
            data: Price data
            extrema_type: 'max' or 'min'
            
        Returns:
            List of indices
        """
        extrema = []
        window = 5
        
        for i in range(window, len(data) - window):
            window_data = data[i-window:i+window+1]
            
            if extrema_type == 'max':
                if data[i] == max(window_data):
                    extrema.append(i)
            else:  # min
                if data[i] == min(window_data):
                    extrema.append(i)
        
        return extrema
    
    def _group_levels(
        self,
        prices: np.ndarray,
        current_price: float,
        df: pd.DataFrame
    ) -> List[Tuple[float, int]]:
        """
        Group similar price levels together.

        Uses ATR-based tolerance (OLD SYSTEM) if available and enabled,
        otherwise falls back to percentage-based tolerance.

        Args:
            prices: Array of prices
            current_price: Current price for tolerance calculation
            df: DataFrame with ATR data

        Returns:
            List of (level_price, touch_count) tuples
        """
        if len(prices) == 0:
            return []

        # Calculate tolerance
        if self.use_atr_tolerance and 'atr' in df.columns:
            # ATR-based tolerance (OLD SYSTEM: ATR × 0.3)
            atr = df['atr'].iloc[-1]
            if pd.notna(atr) and atr > 0:
                tolerance = atr * self.atr_tolerance_multiplier
                logger.debug(f"Using ATR-based tolerance: {tolerance:.2f} (ATR={atr:.2f} × {self.atr_tolerance_multiplier})")
            else:
                # Fallback to percentage
                tolerance = current_price * self.level_tolerance_percent
                logger.debug(f"ATR unavailable, using percentage tolerance: {tolerance:.2f}")
        else:
            # Percentage-based tolerance
            tolerance = current_price * self.level_tolerance_percent
            logger.debug(f"Using percentage tolerance: {tolerance:.2f}")

        # Sort prices
        sorted_prices = np.sort(prices)

        levels = []
        current_level = [sorted_prices[0]]

        for price in sorted_prices[1:]:
            # Compare against the first price in current_level (anchor)
            # This provides more consistent grouping than comparing against mean
            if abs(price - current_level[0]) <= tolerance:
                current_level.append(price)
            else:
                # Save current level
                if len(current_level) >= self.min_touches:
                    levels.append((np.mean(current_level), len(current_level)))
                # Start new level
                current_level = [price]

        # Don't forget last level
        if len(current_level) >= self.min_touches:
            levels.append((np.mean(current_level), len(current_level)))

        return levels
    
    def _calculate_single_level_strength(
        self,
        level_price: float,
        touches: int,
        df: pd.DataFrame,
        level_type: str
    ) -> int:
        """
        Calculate strength of a single level.
        
        Args:
            level_price: Price of the level
            touches: Number of touches
            df: DataFrame for volume analysis
            level_type: 'support' or 'resistance'
            
        Returns:
            Strength (1-3)
        """
        strength = 0
        
        # Base strength from touches
        if touches >= 5:
            strength = 3
        elif touches >= 3:
            strength = 2
        else:
            strength = 1
        
        # Bonus for recent touches
        # Use ATR-based tolerance if available
        if self.use_atr_tolerance and 'atr' in df.columns:
            atr = df['atr'].iloc[-1]
            if pd.notna(atr) and atr > 0:
                tolerance = atr * self.atr_tolerance_multiplier
            else:
                tolerance = level_price * self.level_tolerance_percent
        else:
            tolerance = level_price * self.level_tolerance_percent

        recent_df = df.tail(20)
        
        if level_type == 'support':
            recent_touches = (recent_df['low'] <= level_price + tolerance).sum()
        else:
            recent_touches = (recent_df['high'] >= level_price - tolerance).sum()
        
        if recent_touches >= 2:
            strength = min(strength + 1, 3)
        
        return strength
    
    def _find_nearest_level(
        self,
        levels: List[Dict[str, Any]],
        current_price: float,
        direction: str
    ) -> Optional[float]:
        """
        Find nearest level in given direction.
        
        Args:
            levels: List of levels
            current_price: Current price
            direction: 'above' or 'below'
            
        Returns:
            Price of nearest level, or None
        """
        if not levels:
            return None
        
        if direction == 'below':
            # Find closest support below
            below_levels = [l for l in levels if l['price'] < current_price]
            if below_levels:
                return max(below_levels, key=lambda x: x['price'])['price']
        else:  # above
            # Find closest resistance above
            above_levels = [l for l in levels if l['price'] > current_price]
            if above_levels:
                return min(above_levels, key=lambda x: x['price'])['price']
        
        return None
    
    def _calculate_key_level_distance(
        self,
        current_price: float,
        nearest_support: Optional[float],
        nearest_resistance: Optional[float]
    ) -> float:
        """
        Calculate distance to nearest key level.
        
        Args:
            current_price: Current price
            nearest_support: Nearest support level
            nearest_resistance: Nearest resistance level
            
        Returns:
            Minimum distance to key level
        """
        distances = []
        
        if nearest_support:
            distances.append(abs(current_price - nearest_support))
        
        if nearest_resistance:
            distances.append(abs(current_price - nearest_resistance))
        
        return min(distances) if distances else 0
    
    def _detect_breakout_zone(
        self,
        df: pd.DataFrame,
        current_price: float,
        support_levels: List[Dict],
        resistance_levels: List[Dict],
        atr: Optional[float]
    ) -> bool:
        """
        Detect if price is in breakout zone.
        
        Args:
            df: DataFrame
            current_price: Current price
            support_levels: List of support levels
            resistance_levels: List of resistance levels
            atr: Average True Range
            
        Returns:
            True if in breakout zone
        """
        if not atr:
            atr = df['close'].std() * 0.1  # Fallback
        
        # Check if price is very close to a key level
        threshold = atr * 0.5
        
        for level in support_levels[:3]:  # Check top 3
            if abs(current_price - level['price']) < threshold:
                return True
        
        for level in resistance_levels[:3]:
            if abs(current_price - level['price']) < threshold:
                return True
        
        return False
    
    def _prioritize_levels(
        self,
        levels: List[Dict[str, Any]],
        trend_context: Dict,
        level_type: str
    ) -> List[Dict[str, Any]]:
        """
        Prioritize levels based on trend (context-aware).
        
        Args:
            levels: List of levels
            trend_context: Trend analyzer results
            level_type: 'support' or 'resistance'
            
        Returns:
            Prioritized levels
        """
        trend_direction = trend_context.get('direction', 'neutral')
        
        for level in levels:
            multiplier = 1.0
            
            # In bullish trend, support levels are more important
            if trend_direction == 'bullish' and level_type == 'support':
                multiplier = 1.5
                level['trend_priority'] = True
            # In bearish trend, resistance levels are more important
            elif trend_direction == 'bearish' and level_type == 'resistance':
                multiplier = 1.5
                level['trend_priority'] = True
            else:
                level['trend_priority'] = False
            
            level['strength'] = min(level['strength'] * multiplier, 3.0)
        
        # Re-sort by adjusted strength
        levels.sort(key=lambda x: x['strength'], reverse=True)
        
        return levels
    
    def _calculate_level_strength(
        self,
        support_levels: List[Dict],
        resistance_levels: List[Dict],
        volume_context: Optional[Dict]
    ) -> float:
        """
        Calculate overall level strength.
        
        Args:
            support_levels: Support levels
            resistance_levels: Resistance levels
            volume_context: Volume analyzer results
            
        Returns:
            Overall strength (0-3)
        """
        if not support_levels and not resistance_levels:
            return 0.0
        
        # Average strength of all levels
        all_strengths = (
            [l['strength'] for l in support_levels] +
            [l['strength'] for l in resistance_levels]
        )
        
        avg_strength = sum(all_strengths) / len(all_strengths)
        
        # Bonus if volume confirms
        if volume_context and volume_context.get('is_confirmed'):
            avg_strength *= 1.2
        
        return min(avg_strength, 3.0)
    
    def _validate_context(self, context: AnalysisContext) -> bool:
        """Validate required columns"""
        required = ['high', 'low', 'close']

        df = context.df
        for col in required:
            if col not in df.columns:
                logger.error(f"Missing required column: {col}")
                return False

        return True

    def _detect_zones(self, levels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect zones (clusters of levels).

        A zone is formed when multiple S/R levels are close to each other,
        indicating a strong support/resistance area.

        Args:
            levels: List of support or resistance levels

        Returns:
            List of zones with center, levels, strength, and touches
        """
        if not levels:
            return []

        zones = []

        # Sort levels by price
        sorted_levels = sorted(levels, key=lambda x: x['price'])

        current_zone = [sorted_levels[0]]

        for level in sorted_levels[1:]:
            # Check if close enough to current zone
            zone_center = np.mean([l['price'] for l in current_zone])

            # Calculate distance as percentage
            distance_pct = abs(level['price'] - zone_center) / zone_center

            if distance_pct <= self.zone_tolerance:
                # Add to current zone
                current_zone.append(level)
            else:
                # Save current zone if strong enough (at least 2 levels)
                if len(current_zone) >= 2:
                    zone_center = np.mean([l['price'] for l in current_zone])
                    zones.append({
                        'center': round(zone_center, 2),
                        'levels': current_zone,
                        'level_count': len(current_zone),
                        'strength': sum(l['strength'] for l in current_zone),
                        'touches': sum(l['touches'] for l in current_zone),
                        'type': current_zone[0]['type']  # 'support' or 'resistance'
                    })

                # Start new zone
                current_zone = [level]

        # Don't forget last zone
        if len(current_zone) >= 2:
            zone_center = np.mean([l['price'] for l in current_zone])
            zones.append({
                'center': round(zone_center, 2),
                'levels': current_zone,
                'level_count': len(current_zone),
                'strength': sum(l['strength'] for l in current_zone),
                'touches': sum(l['touches'] for l in current_zone),
                'type': current_zone[0]['type']
            })

        # Sort zones by strength
        zones.sort(key=lambda x: x['strength'], reverse=True)

        return zones

    def _detect_broken_levels(
        self,
        df: pd.DataFrame,
        levels: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect broken levels (confirmed breakouts).

        A level is considered broken when price has closed beyond it
        for at least 3 consecutive candles without returning.

        Args:
            df: DataFrame with price data
            levels: List of all S/R levels (support + resistance)

        Returns:
            List of broken levels with direction and confirmation count
        """
        broken = []
        lookback = min(self.broken_level_lookback, len(df))

        for level in levels:
            level_price = level['price']
            recent_df = df.tail(lookback)

            # Check for break with confirmation
            closes_above = (recent_df['close'] > level_price).sum()
            closes_below = (recent_df['close'] < level_price).sum()

            # Confirmed break: at least 3 closes on one side with NO closes on other side
            if closes_above >= 3 and closes_below == 0:
                broken.append({
                    'price': level_price,
                    'type': level['type'],
                    'original_strength': level['strength'],
                    'broken_direction': 'upward',
                    'confirmation_candles': int(closes_above),
                    'role_reversal': level['type'] == 'resistance'  # Resistance becomes support
                })
            elif closes_below >= 3 and closes_above == 0:
                broken.append({
                    'price': level_price,
                    'type': level['type'],
                    'original_strength': level['strength'],
                    'broken_direction': 'downward',
                    'confirmation_candles': int(closes_below),
                    'role_reversal': level['type'] == 'support'  # Support becomes resistance
                })

        return broken
