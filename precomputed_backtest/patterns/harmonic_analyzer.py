"""
HarmonicAnalyzer - Harmonic Pattern Detection

Detects harmonic patterns using Fibonacci ratios.

Patterns detected:
- Gartley
- Butterfly
- Bat
- Crab
- Cypher (optional)

Uses indicators:
- OHLC data for swing point detection
- Fibonacci ratios for pattern validation

Outputs to context:
- harmonic: {
    'patterns': [list of detected harmonic patterns],
    'active_patterns': int,
    'strongest_pattern': dict | None,
    'confidence': float (0-1)
  }
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
import pandas as pd
import numpy as np

from signal_generation.analyzers.base_analyzer import BaseAnalyzer
from signal_generation.context import AnalysisContext

logger = logging.getLogger(__name__)


class HarmonicAnalyzer(BaseAnalyzer):
    """
    Analyzes harmonic patterns based on Fibonacci ratios.
    
    Key features:
    1. Swing point detection (X, A, B, C, D)
    2. Fibonacci ratio calculation
    3. Pattern validation
    4. Entry zone calculation
    5. Target calculation
    """
    
    # Harmonic pattern definitions (Fibonacci ratios)
    # All ratios are defined as: (min_value, max_value)
    # Pattern structure: X-A-B-C-D (5 points alternating high/low)
    PATTERNS = {
        'gartley': {
            'AB_XA': (0.618, 0.618),   # AB must be 61.8% retracement of XA
            'BC_AB': (0.382, 0.886),   # BC retracement of AB (38.2%-88.6%)
            'CD_BC': (1.13, 1.618),    # CD extension of BC (113%-161.8%)
            'AD_XA': (0.786, 0.786),   # AD must be 78.6% retracement of XA (critical)
            'type': 'both',
            'strength': 3
        },
        'butterfly': {
            'AB_XA': (0.786, 0.786),   # AB must be 78.6% retracement of XA
            'BC_AB': (0.382, 0.886),   # BC retracement of AB (38.2%-88.6%)
            'CD_BC': (1.618, 2.618),   # CD extension of BC (161.8%-261.8%)
            'AD_XA': (1.27, 1.618),    # AD extends beyond X (127%-161.8%)
            'type': 'both',
            'strength': 3
        },
        'bat': {
            'AB_XA': (0.382, 0.50),    # AB retracement of XA (38.2%-50%)
            'BC_AB': (0.382, 0.886),   # BC retracement of AB (38.2%-88.6%)
            'CD_BC': (1.618, 2.618),   # CD extension of BC (161.8%-261.8%)
            'AD_XA': (0.886, 0.886),   # AD must be exactly 88.6% of XA (critical)
            'type': 'both',
            'strength': 3
        },
        'crab': {
            'AB_XA': (0.382, 0.618),   # AB retracement of XA (38.2%-61.8%)
            'BC_AB': (0.382, 0.886),   # BC retracement of AB (38.2%-88.6%)
            'CD_BC': (2.618, 3.618),   # CD very large extension of BC (261.8%-361.8%)
            'AD_XA': (1.618, 1.618),   # AD must be exactly 161.8% of XA (extends beyond X)
            'type': 'both',
            'strength': 3
        }
    }
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize HarmonicAnalyzer."""
        super().__init__(config)

        harmonic_config = config.get('harmonic', {})

        # Default parameters (can be overridden per-TF)
        self.default_lookback = 100
        self.default_tolerance = 0.05  # 5% tolerance
        self.default_swing_window = 5

        # Fallback values
        self.lookback = self.default_lookback
        self.tolerance = self.default_tolerance
        self.swing_window = self.default_swing_window

        self.enabled = config.get('analyzers', {}).get('harmonic', {}).get('enabled', True)

        logger.info(f"HarmonicAnalyzer initialized (swing_window={self.swing_window}, tolerance={self.tolerance*100}%)")
    
    def analyze(self, context: AnalysisContext) -> None:
        """Main analysis method."""
        if not self._check_enabled():
            return
        
        if not self._validate_context(context):
            return
        
        try:
            # Get per-TF parameters
            self.lookback = self.get_threshold('lookback', self.default_lookback, context.timeframe)
            self.tolerance = self.get_threshold('tolerance', self.default_tolerance, context.timeframe)
            self.swing_window = self.get_threshold('swing_window', self.default_swing_window, context.timeframe)

            df = context.df

            if len(df) < 50:
                context.add_result('harmonic', {
                    'status': 'insufficient_data',
                    'patterns': []
                })
                return
            
            # Detect swing points
            swing_points = self._detect_swing_points(df)

            # Search for harmonic patterns
            patterns = self._search_harmonic_patterns(swing_points, df)

            # Add quality scores to patterns
            total_candles = len(df)
            for pattern in patterns:
                pattern['score'] = self._calculate_pattern_score(pattern, total_candles)

            # Find strongest based on comprehensive score
            strongest = max(patterns, key=lambda p: p['score']) if patterns else None

            # Calculate overall confidence (average of pattern scores)
            confidence = sum(p['score'] for p in patterns) / len(patterns) if patterns else 0.0

            result = {
                'status': 'ok',
                'patterns': patterns,
                'active_patterns': len(patterns),
                'strongest_pattern': strongest,
                'confidence': round(confidence, 2)
            }
            
            context.add_result('harmonic', result)
            
            logger.info(f"HarmonicAnalyzer: {len(patterns)} patterns for {context.symbol}")
            
        except Exception as e:
            logger.error(f"Error in HarmonicAnalyzer: {e}", exc_info=True)
            context.add_result('harmonic', {
                'status': 'error',
                'patterns': [],
                'error': str(e)
            })
    
    def _detect_swing_points(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect swing highs and lows.

        Prevents duplicate swing points at the same index by choosing
        the stronger signal (high or low) based on distance from mean.
        """
        lookback = min(self.lookback, len(df))
        recent_df = df.tail(lookback)

        highs = recent_df['high'].values
        lows = recent_df['low'].values

        swing_points = []
        window = self.swing_window

        for i in range(window, len(highs) - window):
            is_swing_high = highs[i] == max(highs[i-window:i+window+1])
            is_swing_low = lows[i] == min(lows[i-window:i+window+1])

            # If both high and low, choose the stronger one
            if is_swing_high and is_swing_low:
                # Calculate strength: distance from local mean
                high_strength = highs[i] - np.mean(highs[i-window:i+window+1])
                low_strength = np.mean(lows[i-window:i+window+1]) - lows[i]

                if high_strength > low_strength:
                    swing_points.append({
                        'type': 'high',
                        'price': highs[i],
                        'index': i
                    })
                else:
                    swing_points.append({
                        'type': 'low',
                        'price': lows[i],
                        'index': i
                    })
            elif is_swing_high:
                swing_points.append({
                    'type': 'high',
                    'price': highs[i],
                    'index': i
                })
            elif is_swing_low:
                swing_points.append({
                    'type': 'low',
                    'price': lows[i],
                    'index': i
                })

        return sorted(swing_points, key=lambda x: x['index'])
    
    def _search_harmonic_patterns(
        self,
        swing_points: List[Dict],
        df: pd.DataFrame
    ) -> List[Dict]:
        """
        Search for harmonic patterns in swing points.

        Prevents overlapping patterns by tracking used D points.
        """
        patterns = []
        used_d_indices = set()  # Track used D points to prevent overlaps

        if len(swing_points) < 5:
            return patterns

        # Look for 5-point patterns (X, A, B, C, D)
        for i in range(len(swing_points) - 4):
            # Skip if this D point was already used
            if i + 4 in used_d_indices:
                continue

            x = swing_points[i]
            a = swing_points[i+1]
            b = swing_points[i+2]
            c = swing_points[i+3]
            d = swing_points[i+4]

            # Check if alternating (high-low-high-low or vice versa)
            if not self._is_valid_sequence(x, a, b, c, d):
                continue

            # Determine pattern direction
            pattern_type = 'bullish' if x['type'] == 'low' else 'bearish'

            # Check each pattern type
            for pattern_name, ratios in self.PATTERNS.items():
                if self._matches_pattern(x, a, b, c, d, ratios):
                    patterns.append({
                        'name': pattern_name.capitalize(),
                        'type': pattern_type,
                        'completion': self._calculate_completion(x, a, b, c, d, ratios),
                        'entry_zone': self._calculate_entry_zone(d, pattern_type),
                        'targets': self._calculate_targets(x, a, d, pattern_type),
                        'stop_loss': self._calculate_stop_loss(x, d, pattern_type),
                        'strength': ratios['strength'],
                        'points': {
                            'X': {'price': x['price'], 'index': x['index']},
                            'A': {'price': a['price'], 'index': a['index']},
                            'B': {'price': b['price'], 'index': b['index']},
                            'C': {'price': c['price'], 'index': c['index']},
                            'D': {'price': d['price'], 'index': d['index']}
                        }
                    })
                    # Mark this D point as used
                    used_d_indices.add(i + 4)
                    break  # Only one pattern per 5-point sequence

        return patterns
    
    def _is_valid_sequence(self, x, a, b, c, d) -> bool:
        """Check if points form valid alternating sequence."""
        types = [x['type'], a['type'], b['type'], c['type'], d['type']]
        
        # Should alternate: low-high-low-high-low or high-low-high-low-high
        for i in range(len(types) - 1):
            if types[i] == types[i+1]:
                return False
        
        return True
    
    def _matches_pattern(self, x, a, b, c, d, ratios: Dict) -> bool:
        """
        Check if points match pattern ratios.

        Validates all 4 critical Fibonacci ratios:
        1. AB/XA - Initial retracement
        2. BC/AB - Secondary retracement
        3. CD/BC - Extension move
        4. AD/XA - Final completion level (most critical)

        Args:
            x, a, b, c, d: Pattern points (X-A-B-C-D)
            ratios: Expected pattern ratios

        Returns:
            True if all ratios match within tolerance
        """
        tolerance = self.tolerance

        # Calculate distances between points
        xa = abs(a['price'] - x['price'])
        ab = abs(b['price'] - a['price'])
        bc = abs(c['price'] - b['price'])
        cd = abs(d['price'] - c['price'])
        ad = abs(d['price'] - a['price'])

        # Validate non-zero distances
        if xa == 0 or ab == 0 or bc == 0:
            return False

        # 1. Check AB/XA ratio (initial retracement)
        ab_xa_ratio = ab / xa
        if not self._in_range(ab_xa_ratio, ratios['AB_XA'], tolerance):
            return False

        # 2. Check BC/AB ratio (secondary retracement)
        bc_ab_ratio = bc / ab
        if not self._in_range(bc_ab_ratio, ratios['BC_AB'], tolerance):
            return False

        # 3. Check CD/BC ratio (extension move)
        cd_bc_ratio = cd / bc
        if not self._in_range(cd_bc_ratio, ratios['CD_BC'], tolerance):
            return False

        # 4. Check AD/XA ratio (final completion - most critical!)
        ad_xa_ratio = ad / xa
        if not self._in_range(ad_xa_ratio, ratios['AD_XA'], tolerance):
            return False

        return True
    
    def _in_range(self, value: float, target: Tuple[float, float], tolerance: float) -> bool:
        """Check if value is within range with tolerance."""
        min_val = target[0] * (1 - tolerance)
        max_val = target[1] * (1 + tolerance)
        return min_val <= value <= max_val
    
    def _calculate_completion(self, x, a, b, c, d, ratios: Dict) -> float:
        """
        Calculate pattern completion percentage based on actual price position.

        Args:
            x, a, b, c, d: Pattern points
            ratios: Expected pattern ratios

        Returns:
            Completion percentage (0-1)
        """
        try:
            # Calculate expected D level based on AD_XA ratio
            xa = abs(a['price'] - x['price'])
            expected_ad_ratio = (ratios['AD_XA'][0] + ratios['AD_XA'][1]) / 2  # Average
            expected_d_price = a['price'] + (xa * expected_ad_ratio * (1 if a['price'] > x['price'] else -1))

            # Calculate actual AD
            actual_ad = abs(d['price'] - a['price'])

            # Completion is how close actual is to expected
            if expected_d_price != 0:
                completion = min(abs(actual_ad / (expected_ad_ratio * xa)), 1.0)
            else:
                completion = 0.85  # Fallback

            return round(completion, 2)

        except Exception:
            # Fallback to reasonable default
            return 0.85
    
    def _calculate_entry_zone(self, d: Dict, pattern_type: str, zone_percent: float = 0.5) -> List[float]:
        """
        Calculate entry zone around point D.

        Args:
            d: Point D dictionary with price
            pattern_type: 'bullish' or 'bearish'
            zone_percent: Zone width as percentage (default 0.5%)

        Returns:
            [lower_bound, upper_bound] for entry zone
        """
        d_price = d['price']
        zone_width = d_price * zone_percent / 100

        if pattern_type == 'bullish':
            # For bullish: enter slightly below D (on pullback)
            return [round(d_price - zone_width, 2), round(d_price + zone_width * 0.5, 2)]
        else:
            # For bearish: enter slightly above D (on bounce)
            return [round(d_price - zone_width * 0.5, 2), round(d_price + zone_width, 2)]

    def _calculate_targets(self, x: Dict, a: Dict, d: Dict, pattern_type: str) -> List[float]:
        """
        Calculate target levels based on pattern direction.

        Args:
            x: Point X
            a: Point A
            d: Point D
            pattern_type: 'bullish' or 'bearish'

        Returns:
            List of 3 target prices (38.2%, 61.8%, 100% retracement of XA)
        """
        xa = abs(a['price'] - x['price'])

        # Determine direction
        # Bullish: targets go UP from D (price increases)
        # Bearish: targets go DOWN from D (price decreases)
        direction = 1 if pattern_type == 'bullish' else -1

        # Standard Fibonacci targets
        target1 = d['price'] + (xa * 0.382 * direction)  # Conservative
        target2 = d['price'] + (xa * 0.618 * direction)  # Moderate
        target3 = d['price'] + (xa * 1.0 * direction)    # Aggressive (full XA retracement)

        return [round(target1, 2), round(target2, 2), round(target3, 2)]

    def _calculate_stop_loss(self, x: Dict, d: Dict, pattern_type: str, buffer_percent: float = 2.0) -> float:
        """
        Calculate stop loss level.

        Args:
            x: Point X (pattern start)
            d: Point D (pattern completion)
            pattern_type: 'bullish' or 'bearish'
            buffer_percent: Buffer percentage beyond X (default 2%)

        Returns:
            Stop loss price level
        """
        x_price = x['price']
        d_price = d['price']

        # Calculate buffer (percentage of XD range)
        xd_range = abs(x_price - d_price)
        buffer = xd_range * buffer_percent / 100

        if pattern_type == 'bullish':
            # For bullish: SL below X (invalidation if price goes below X)
            return round(x_price - buffer, 2)
        else:
            # For bearish: SL above X (invalidation if price goes above X)
            return round(x_price + buffer, 2)

    def _calculate_pattern_score(self, pattern: Dict, total_candles: int) -> float:
        """
        Calculate comprehensive pattern quality score.

        Args:
            pattern: Pattern dictionary
            total_candles: Total candles in the dataset for recency calculation

        Returns:
            Score between 0 and 1 (higher is better)
        """
        # 1. Completion score (50% weight)
        completion = pattern.get('completion', 0.85)

        # 2. Strength score (30% weight) - normalized 0-1
        strength = pattern.get('strength', 3) / 3.0

        # 3. Recency score (20% weight) - how recent is point D
        d_index = pattern.get('points', {}).get('D', {}).get('index', 0)
        if total_candles > 0:
            # More recent = higher score
            recency = 1.0 - (total_candles - d_index) / total_candles
            recency = max(0.0, min(1.0, recency))  # Clamp to 0-1
        else:
            recency = 0.5  # Fallback

        # Weighted sum
        score = (
            completion * 0.5 +
            strength * 0.3 +
            recency * 0.2
        )

        return round(score, 3)

    def _validate_context(self, context: AnalysisContext) -> bool:
        """Validate required columns."""
        required = ['high', 'low', 'close']
        return all(col in context.df.columns for col in required)
