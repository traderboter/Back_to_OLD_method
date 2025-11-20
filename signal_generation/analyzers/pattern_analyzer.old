"""
PatternAnalyzer - Candlestick and Chart Pattern Detection

Detects and analyzes candlestick patterns and chart patterns with context-aware scoring.

Uses indicators (pre-calculated by IndicatorCalculator):
- OHLC data (open, high, low, close)
- volume
- Moving averages for pattern confirmation

Can read from context (context-aware):
- trend: To boost pattern scores when aligned with trend
- momentum: To validate pattern signals
- volume: To confirm pattern strength

Outputs to context:
- patterns: {
    'candlestick_patterns': [list of detected patterns],
    'chart_patterns': [list of detected patterns],
    'total_patterns': int,
    'strongest_pattern': dict,
    'pattern_strength': float (0-3),
    'alignment_with_trend': bool,
    'confidence': float (0-1)
  }
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
import pandas as pd
import numpy as np
import talib

from signal_generation.analyzers.base_analyzer import BaseAnalyzer
from signal_generation.context import AnalysisContext
from signal_generation.pattern_score_utils import get_pattern_score

logger = logging.getLogger(__name__)


class PatternAnalyzer(BaseAnalyzer):
    """
    Analyzes candlestick and chart patterns.
    
    Key features:
    1. Candlestick pattern detection (using TALib)
    2. Chart pattern detection (custom algorithms)
    3. Context-aware scoring (considers trend/momentum)
    4. Pattern prioritization
    5. Confidence calculation
    """
    
    # Candlestick patterns to detect (TALib functions)
    CANDLESTICK_PATTERNS = {
        # Bullish patterns
        'CDLHAMMER': {'name': 'Hammer', 'type': 'bullish', 'strength': 2},
        'CDLINVERTEDHAMMER': {'name': 'Inverted Hammer', 'type': 'bullish', 'strength': 2},
        'CDLENGULFING': {'name': 'Engulfing', 'type': 'both', 'strength': 3},
        'CDLMORNINGSTAR': {'name': 'Morning Star', 'type': 'bullish', 'strength': 3},
        'CDLPIERCING': {'name': 'Piercing Line', 'type': 'bullish', 'strength': 2},
        'CDL3WHITESOLDIERS': {'name': 'Three White Soldiers', 'type': 'bullish', 'strength': 3},
        'CDLMORNINGDOJISTAR': {'name': 'Morning Doji Star', 'type': 'bullish', 'strength': 2},
        
        # Bearish patterns
        'CDLSHOOTINGSTAR': {'name': 'Shooting Star', 'type': 'bearish', 'strength': 2},
        'CDLHANGINGMAN': {'name': 'Hanging Man', 'type': 'bearish', 'strength': 2},
        'CDLEVENINGSTAR': {'name': 'Evening Star', 'type': 'bearish', 'strength': 3},
        'CDLDARKCLOUDCOVER': {'name': 'Dark Cloud Cover', 'type': 'bearish', 'strength': 2},
        'CDL3BLACKCROWS': {'name': 'Three Black Crows', 'type': 'bearish', 'strength': 3},
        'CDLEVENINGDOJISTAR': {'name': 'Evening Doji Star', 'type': 'bearish', 'strength': 2},
        
        # Reversal patterns
        'CDLDOJI': {'name': 'Doji', 'type': 'reversal', 'strength': 1},
        'CDLHARAMI': {'name': 'Harami', 'type': 'reversal', 'strength': 2},
        'CDLHARAMICROSS': {'name': 'Harami Cross', 'type': 'reversal', 'strength': 2},
    }
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize PatternAnalyzer.

        Args:
            config: Configuration dictionary
        """
        super().__init__(config)

        # Get pattern-specific configuration
        pattern_config = config.get('pattern', {})

        # Minimum pattern strength to consider
        self.min_pattern_strength = pattern_config.get('min_strength', 2)

        # Chart pattern detection lookback
        self.chart_lookback = pattern_config.get('chart_lookback', 50)

        # Enable/disable
        self.enabled = config.get('analyzers', {}).get('pattern', {}).get('enabled', True)

        # امتیازدهی خاص هر تایم‌فریم (اختیاری)
        # اگر در config موجود باشد، از آن استفاده می‌شود
        # در غیر این صورت از امتیازهای base_strength استفاده خواهد شد
        self.pattern_scores_by_timeframe = config.get('signal_generation_v2', {}) \
            .get('analyzers', {}) \
            .get('pattern_analyzer', {}) \
            .get('pattern_scores_by_timeframe', {})

        logger.info("PatternAnalyzer initialized successfully")
    
    def analyze(self, context: AnalysisContext) -> None:
        """
        Main analysis method - detects patterns.
        
        Args:
            context: AnalysisContext with pre-calculated indicators
        """
        # 1. Check if enabled
        if not self._check_enabled():
            logger.debug(f"PatternAnalyzer disabled for {context.symbol}")
            return
        
        # 2. Validate context
        if not self._validate_context(context):
            logger.warning(f"PatternAnalyzer: Invalid context for {context.symbol}")
            return
        
        try:
            # 3. Read data
            df = context.df
            
            # Ensure we have enough data
            if len(df) < 20:
                logger.warning(f"Insufficient data for PatternAnalyzer on {context.symbol}")
                context.add_result('patterns', {
                    'status': 'insufficient_data',
                    'candlestick_patterns': [],
                    'chart_patterns': []
                })
                return
            
            # 4. Detect candlestick patterns
            candlestick_patterns = self._detect_candlestick_patterns(context)

            # 5. Detect chart patterns
            chart_patterns = self._detect_chart_patterns(context)
            
            # 6. Context-aware scoring (read trend/momentum/volume)
            trend_context = context.get_result('trend')
            momentum_context = context.get_result('momentum')
            volume_context = context.get_result('volume')
            
            # Adjust pattern scores based on context
            candlestick_patterns = self._adjust_pattern_scores(
                candlestick_patterns,
                trend_context,
                momentum_context,
                volume_context
            )
            
            chart_patterns = self._adjust_pattern_scores(
                chart_patterns,
                trend_context,
                momentum_context,
                volume_context
            )
            
            # 7. Find strongest pattern
            all_patterns = candlestick_patterns + chart_patterns
            strongest = max(all_patterns, key=lambda p: p['adjusted_strength']) if all_patterns else None
            
            # 8. Calculate overall pattern strength
            pattern_strength = self._calculate_pattern_strength(all_patterns)
            
            # 9. Check alignment with trend
            alignment = self._check_trend_alignment(all_patterns, trend_context)
            
            # 10. Calculate confidence
            confidence = self._calculate_confidence(
                all_patterns,
                alignment,
                volume_context
            )
            
            # 11. Build result
            result = {
                'status': 'ok',
                'candlestick_patterns': candlestick_patterns,
                'chart_patterns': chart_patterns,
                'total_patterns': len(all_patterns),
                'strongest_pattern': strongest,
                'pattern_strength': pattern_strength,
                'alignment_with_trend': alignment,
                'confidence': confidence,
                'context_aware': trend_context is not None
            }
            
            # 12. Store in context
            context.add_result('patterns', result)
            
            logger.info(
                f"PatternAnalyzer completed for {context.symbol} {context.timeframe}: "
                f"{len(all_patterns)} patterns, strength={pattern_strength:.2f}, "
                f"confidence={confidence:.2f}"
            )
            
        except Exception as e:
            logger.error(f"Error in PatternAnalyzer for {context.symbol}: {e}", exc_info=True)
            context.add_result('patterns', {
                'status': 'error',
                'candlestick_patterns': [],
                'chart_patterns': [],
                'error': str(e)
            })
    
    def _detect_candlestick_patterns(self, context: AnalysisContext) -> List[Dict[str, Any]]:
        """
        Detect candlestick patterns using TALib.

        Args:
            context: AnalysisContext with OHLC data and timeframe

        Returns:
            List of detected patterns with timeframe information
        """
        patterns = []

        df = context.df
        open_prices = df['open'].values
        high_prices = df['high'].values
        low_prices = df['low'].values
        close_prices = df['close'].values
        
        # Check each pattern
        for pattern_func, pattern_info in self.CANDLESTICK_PATTERNS.items():
            try:
                # Call TALib function
                result = getattr(talib, pattern_func)(
                    open_prices, high_prices, low_prices, close_prices
                )
                
                # Check last candle
                if result[-1] != 0:
                    # Determine direction
                    if pattern_info['type'] == 'both':
                        direction = 'bullish' if result[-1] > 0 else 'bearish'
                    else:
                        direction = pattern_info['type']

                    # محاسبه base_strength با توجه به تایم‌فریم
                    # اگر pattern_scores_by_timeframe تنظیم شده باشد، از آن استفاده می‌شود
                    # در غیر این صورت از pattern_info['strength'] استفاده می‌شود
                    base_strength = get_pattern_score(
                        self.pattern_scores_by_timeframe,
                        pattern_info['name'].lower().replace(' ', '_'),  # تبدیل "Morning Star" به "morning_star"
                        context.timeframe,
                        pattern_info['strength']  # مقدار پیش‌فرض
                    )

                    patterns.append({
                        'name': pattern_info['name'],
                        'type': 'candlestick',
                        'direction': direction,
                        'base_strength': base_strength,
                        'adjusted_strength': base_strength,  # Will be adjusted later
                        'location': 'current',
                        'candles_ago': 0,
                        'timeframe': context.timeframe  # ✨ اضافه کردن تایم‌فریم
                    })
                    
            except Exception as e:
                logger.debug(f"Error detecting pattern {pattern_func}: {e}")
                continue
        
        return patterns
    
    def _detect_chart_patterns(self, context: AnalysisContext) -> List[Dict[str, Any]]:
        """
        Detect chart patterns (custom algorithms).

        Args:
            context: AnalysisContext with OHLC data and timeframe

        Returns:
            List of detected chart patterns with timeframe information
        """
        patterns = []

        df = context.df
        lookback = min(self.chart_lookback, len(df))
        if lookback < 20:
            return patterns

        recent_df = df.tail(lookback)
        
        # 1. Double Top/Bottom
        double_pattern = self._detect_double_top_bottom(recent_df)
        if double_pattern:
            double_pattern['timeframe'] = context.timeframe  # ✨ اضافه کردن تایم‌فریم
            patterns.append(double_pattern)

        # 2. Head and Shoulders
        hs_pattern = self._detect_head_shoulders(recent_df)
        if hs_pattern:
            hs_pattern['timeframe'] = context.timeframe  # ✨ اضافه کردن تایم‌فریم
            patterns.append(hs_pattern)

        # 3. Triangle patterns
        triangle = self._detect_triangle(recent_df)
        if triangle:
            triangle['timeframe'] = context.timeframe  # ✨ اضافه کردن تایم‌فریم
            patterns.append(triangle)

        # 4. Wedge patterns
        wedge = self._detect_wedge(recent_df)
        if wedge:
            wedge['timeframe'] = context.timeframe  # ✨ اضافه کردن تایم‌فریم
            patterns.append(wedge)

        return patterns
    
    def _detect_double_top_bottom(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Detect double top/bottom patterns."""
        try:
            highs = df['high'].values
            lows = df['low'].values
            
            # Find local peaks and troughs
            from scipy.signal import find_peaks
            
            peaks, _ = find_peaks(highs, distance=5, prominence=np.std(highs) * 0.5)
            troughs, _ = find_peaks(-lows, distance=5, prominence=np.std(lows) * 0.5)
            
            # Check for double top (two similar peaks)
            if len(peaks) >= 2:
                last_two_peaks = peaks[-2:]
                peak_heights = highs[last_two_peaks]
                
                # Check if peaks are similar (within 2%)
                if abs(peak_heights[0] - peak_heights[1]) / peak_heights[0] < 0.02:
                    return {
                        'name': 'Double Top',
                        'type': 'chart',
                        'direction': 'bearish',
                        'base_strength': 3,
                        'adjusted_strength': 3,
                        'location': 'recent',
                        'completion': 0.8
                    }
            
            # Check for double bottom (two similar troughs)
            if len(troughs) >= 2:
                last_two_troughs = troughs[-2:]
                trough_depths = lows[last_two_troughs]
                
                if abs(trough_depths[0] - trough_depths[1]) / trough_depths[0] < 0.02:
                    return {
                        'name': 'Double Bottom',
                        'type': 'chart',
                        'direction': 'bullish',
                        'base_strength': 3,
                        'adjusted_strength': 3,
                        'location': 'recent',
                        'completion': 0.8
                    }
            
            return None
            
        except Exception as e:
            logger.debug(f"Error detecting double top/bottom: {e}")
            return None
    
    def _detect_head_shoulders(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Detect head and shoulders pattern."""
        try:
            highs = df['high'].values
            lows = df['low'].values
            
            from scipy.signal import find_peaks
            
            # For head and shoulders, need 3 peaks: left shoulder, head, right shoulder
            peaks, properties = find_peaks(highs, distance=5, prominence=np.std(highs) * 0.5)
            
            if len(peaks) >= 3:
                last_three = peaks[-3:]
                peak_heights = highs[last_three]
                
                # Check if middle peak (head) is highest
                if peak_heights[1] > peak_heights[0] and peak_heights[1] > peak_heights[2]:
                    # Check if shoulders are similar height
                    shoulder_diff = abs(peak_heights[0] - peak_heights[2]) / peak_heights[0]
                    
                    if shoulder_diff < 0.05:  # Within 5%
                        return {
                            'name': 'Head and Shoulders',
                            'type': 'chart',
                            'direction': 'bearish',
                            'base_strength': 3,
                            'adjusted_strength': 3,
                            'location': 'forming',
                            'completion': 0.7
                        }
            
            # Inverse head and shoulders
            troughs, _ = find_peaks(-lows, distance=5, prominence=np.std(lows) * 0.5)
            
            if len(troughs) >= 3:
                last_three = troughs[-3:]
                trough_depths = lows[last_three]
                
                if trough_depths[1] < trough_depths[0] and trough_depths[1] < trough_depths[2]:
                    shoulder_diff = abs(trough_depths[0] - trough_depths[2]) / trough_depths[0]
                    
                    if shoulder_diff < 0.05:
                        return {
                            'name': 'Inverse Head and Shoulders',
                            'type': 'chart',
                            'direction': 'bullish',
                            'base_strength': 3,
                            'adjusted_strength': 3,
                            'location': 'forming',
                            'completion': 0.7
                        }
            
            return None
            
        except Exception as e:
            logger.debug(f"Error detecting head and shoulders: {e}")
            return None
    
    def _detect_triangle(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Detect triangle patterns (ascending, descending, symmetrical)."""
        try:
            highs = df['high'].values
            lows = df['low'].values
            
            # Calculate trendlines for highs and lows
            x = np.arange(len(highs))
            
            # Upper trendline (resistance)
            upper_slope = np.polyfit(x, highs, 1)[0]
            
            # Lower trendline (support)
            lower_slope = np.polyfit(x, lows, 1)[0]
            
            # Ascending triangle: flat top, rising bottom
            if abs(upper_slope) < 0.0001 and lower_slope > 0.0001:
                return {
                    'name': 'Ascending Triangle',
                    'type': 'chart',
                    'direction': 'bullish',
                    'base_strength': 2,
                    'adjusted_strength': 2,
                    'location': 'forming',
                    'completion': 0.6
                }
            
            # Descending triangle: declining top, flat bottom
            elif upper_slope < -0.0001 and abs(lower_slope) < 0.0001:
                return {
                    'name': 'Descending Triangle',
                    'type': 'chart',
                    'direction': 'bearish',
                    'base_strength': 2,
                    'adjusted_strength': 2,
                    'location': 'forming',
                    'completion': 0.6
                }
            
            # Symmetrical triangle: converging lines
            elif upper_slope < -0.0001 and lower_slope > 0.0001:
                # Direction depends on breakout (neutral for now)
                return {
                    'name': 'Symmetrical Triangle',
                    'type': 'chart',
                    'direction': 'neutral',
                    'base_strength': 2,
                    'adjusted_strength': 2,
                    'location': 'forming',
                    'completion': 0.6
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Error detecting triangle: {e}")
            return None
    
    def _detect_wedge(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Detect rising/falling wedge patterns."""
        try:
            highs = df['high'].values
            lows = df['low'].values
            
            x = np.arange(len(highs))
            
            upper_slope = np.polyfit(x, highs, 1)[0]
            lower_slope = np.polyfit(x, lows, 1)[0]
            
            # Rising wedge: both lines rising, upper faster (bearish)
            if upper_slope > 0 and lower_slope > 0 and upper_slope > lower_slope:
                return {
                    'name': 'Rising Wedge',
                    'type': 'chart',
                    'direction': 'bearish',
                    'base_strength': 2,
                    'adjusted_strength': 2,
                    'location': 'forming',
                    'completion': 0.5
                }
            
            # Falling wedge: both lines falling, lower faster (bullish)
            elif upper_slope < 0 and lower_slope < 0 and lower_slope < upper_slope:
                return {
                    'name': 'Falling Wedge',
                    'type': 'chart',
                    'direction': 'bullish',
                    'base_strength': 2,
                    'adjusted_strength': 2,
                    'location': 'forming',
                    'completion': 0.5
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Error detecting wedge: {e}")
            return None
    
    def _adjust_pattern_scores(
        self,
        patterns: List[Dict[str, Any]],
        trend_context: Optional[Dict],
        momentum_context: Optional[Dict],
        volume_context: Optional[Dict]
    ) -> List[Dict[str, Any]]:
        """
        Adjust pattern scores based on context (context-aware scoring).
        
        Args:
            patterns: List of detected patterns
            trend_context: Trend analyzer results
            momentum_context: Momentum analyzer results
            volume_context: Volume analyzer results
            
        Returns:
            Patterns with adjusted scores
        """
        for pattern in patterns:
            multiplier = 1.0
            
            # Trend alignment bonus
            if trend_context:
                trend_direction = trend_context.get('direction', 'neutral')
                pattern_direction = pattern['direction']
                
                if trend_direction == pattern_direction:
                    multiplier *= 1.5  # 50% bonus for trend alignment
                    pattern['trend_aligned'] = True
                elif trend_direction == 'neutral':
                    multiplier *= 1.0
                else:
                    multiplier *= 0.7  # Penalty for going against trend
                    pattern['trend_aligned'] = False
            
            # Momentum confirmation
            if momentum_context:
                momentum_direction = momentum_context.get('direction', 'neutral')
                if momentum_direction == pattern['direction']:
                    multiplier *= 1.2
                    pattern['momentum_confirmed'] = True
                else:
                    pattern['momentum_confirmed'] = False
            
            # Volume confirmation
            if volume_context:
                if volume_context.get('is_confirmed', False):
                    multiplier *= 1.3
                    pattern['volume_confirmed'] = True
                else:
                    pattern['volume_confirmed'] = False
            
            # Apply multiplier
            pattern['adjusted_strength'] = pattern['base_strength'] * multiplier
            pattern['score_multiplier'] = multiplier
        
        return patterns
    
    def _calculate_pattern_strength(self, patterns: List[Dict[str, Any]]) -> float:
        """
        Calculate overall pattern strength.
        
        Args:
            patterns: List of all patterns
            
        Returns:
            Overall strength (0-3)
        """
        if not patterns:
            return 0.0
        
        # Average of adjusted strengths
        total_strength = sum(p['adjusted_strength'] for p in patterns)
        avg_strength = total_strength / len(patterns)
        
        return min(avg_strength, 3.0)
    
    def _check_trend_alignment(
        self,
        patterns: List[Dict[str, Any]],
        trend_context: Optional[Dict]
    ) -> bool:
        """
        Check if patterns are aligned with trend.
        
        Args:
            patterns: List of patterns
            trend_context: Trend analyzer results
            
        Returns:
            True if aligned
        """
        if not patterns or not trend_context:
            return False
        
        trend_direction = trend_context.get('direction', 'neutral')
        if trend_direction == 'neutral':
            return False
        
        # Check if majority of patterns align with trend
        aligned_count = sum(
            1 for p in patterns 
            if p['direction'] == trend_direction
        )
        
        return aligned_count > len(patterns) / 2
    
    def _calculate_confidence(
        self,
        patterns: List[Dict[str, Any]],
        alignment: bool,
        volume_context: Optional[Dict]
    ) -> float:
        """
        Calculate confidence score.
        
        Args:
            patterns: List of patterns
            alignment: Trend alignment
            volume_context: Volume analyzer results
            
        Returns:
            Confidence (0-1)
        """
        if not patterns:
            return 0.0
        
        confidence = 0.5
        
        # More patterns increase confidence
        if len(patterns) >= 3:
            confidence += 0.2
        elif len(patterns) >= 2:
            confidence += 0.1
        
        # Strong patterns increase confidence
        avg_strength = sum(p['adjusted_strength'] for p in patterns) / len(patterns)
        if avg_strength >= 2.5:
            confidence += 0.2
        elif avg_strength >= 2.0:
            confidence += 0.1
        
        # Trend alignment increases confidence
        if alignment:
            confidence += 0.15
        
        # Volume confirmation
        if volume_context and volume_context.get('is_confirmed'):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _validate_context(self, context: AnalysisContext) -> bool:
        """Validate required columns"""
        required = ['open', 'high', 'low', 'close']
        
        df = context.df
        for col in required:
            if col not in df.columns:
                logger.error(f"Missing required column: {col}")
                return False
        
        return True
