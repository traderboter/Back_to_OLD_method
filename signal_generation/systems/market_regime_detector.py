"""
Market Regime Detector - OLD SYSTEM Aligned

Detects market regime combining trend strength and volatility (9 main regimes).

Main Regimes (OLD SYSTEM format):
1. strong_trend_normal: Strong trend (ADX > 25) + Normal volatility (0.7-1.3% ATR)
2. strong_trend_high: Strong trend + High volatility (> 1.3% ATR)
3. strong_trend_low: Strong trend + Low volatility (< 0.7% ATR)
4. weak_trend_normal: Weak trend (ADX 20-25) + Normal volatility
5. weak_trend_high: Weak trend + High volatility
6. weak_trend_low: Weak trend + Low volatility
7. range_normal: No trend (ADX < 20) + Normal volatility
8. range_high: No trend + High volatility (dangerous!)
9. range_low: No trend + Low volatility (tight range)

Special Regimes:
- breakout_{direction}_{volatility}: Breakout detected
- choppy: Choppy market (high ADX changes)

Uses:
- ADX: Trend strength measurement
- ATR%: Volatility measurement (ATR / close × 100)
- DI: Trend direction (+DI vs -DI)
- Bollinger Bands: Additional volatility confirmation
- RSI: Overbought/oversold detection
- Volume: Volume-price correlation
"""

import logging
import time
import copy
import hashlib
import numpy as np
import pandas as pd
import talib
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass

# Import centralized Enums instead of defining locally
from signal_generation.enums import Direction, VolatilityRegime, MarketRegime

logger = logging.getLogger(__name__)


# Keep only local-specific enums (not in central enums.py)
class TrendStrength(str, Enum):
    """Trend strength classification."""
    STRONG = 'strong_trend'
    WEAK = 'weak_trend'
    NONE = 'no_trend'


class RegimeStatus(str, Enum):
    """Regime detection status."""
    DISABLED = 'disabled'
    UNKNOWN_DATA = 'unknown_data'
    UNKNOWN_CALC = 'unknown_calc'
    ERROR = 'error'


# Constants
ADX_MAX_REFERENCE = 50.0  # Maximum ADX value for normalization
CACHE_TTL_SECONDS = 300  # Cache time-to-live (5 minutes)
REGIME_HISTORY_MAXLEN = 10  # Maximum regime history to keep
EXTRA_DATA_BUFFER = 10  # Extra samples for indicator calculation


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero or invalid.

    Args:
        numerator: The numerator
        denominator: The denominator
        default: Default value to return if division fails

    Returns:
        Result of division or default value
    """
    if denominator == 0 or np.isnan(denominator) or np.isinf(denominator):
        return default
    result = numerator / denominator
    if np.isnan(result) or np.isinf(result):
        return default
    return result


class MarketRegimeDetector:
    """Detects market regime (trend, volatility) and adapts parameters."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration."""
        self.config = config.get('market_regime', {})
        self.enabled = self.config.get('enabled', True)

        # Indicator parameters with validation
        self.adx_period = self._validate_period(
            self.config.get('adx_period', 14),
            'adx_period',
            min_value=5,
            max_value=100
        )
        self.volatility_period = self._validate_period(
            self.config.get('volatility_period', 20),
            'volatility_period',
            min_value=5,
            max_value=100
        )

        # Detection thresholds with validation
        self.strong_trend_threshold = self._validate_threshold(
            self.config.get('strong_trend_threshold', 25),
            'strong_trend_threshold',
            min_value=0,
            max_value=100
        )
        self.weak_trend_threshold = self._validate_threshold(
            self.config.get('weak_trend_threshold', 20),
            'weak_trend_threshold',
            min_value=0,
            max_value=100
        )
        self.high_volatility_threshold = self._validate_threshold(
            self.config.get('high_volatility_threshold', 1.5),
            'high_volatility_threshold',
            min_value=0,
            max_value=10.0
        )
        self.low_volatility_threshold = self._validate_threshold(
            self.config.get('low_volatility_threshold', 0.5),
            'low_volatility_threshold',
            min_value=0,
            max_value=10.0
        )

        # Additional indicator periods for enhanced detection
        self.bollinger_period = self._validate_period(
            self.config.get('bollinger_period', 20),
            'bollinger_period',
            min_value=5,
            max_value=100
        )
        self.bollinger_std = self._validate_threshold(
            self.config.get('bollinger_std', 2.0),
            'bollinger_std',
            min_value=0.5,
            max_value=5.0
        )
        self.rsi_period = self._validate_period(
            self.config.get('rsi_period', 14),
            'rsi_period',
            min_value=5,
            max_value=100
        )
        self.breakout_lookback = self._validate_period(
            self.config.get('breakout_lookback', 10),
            'breakout_lookback',
            min_value=3,
            max_value=50
        )
        self.breakout_threshold = self._validate_threshold(
            self.config.get('breakout_threshold', 2.0),
            'breakout_threshold',
            min_value=0.5,
            max_value=10.0
        )
        self.choppy_threshold = self._validate_threshold(
            self.config.get('choppy_threshold', 0.3),
            'choppy_threshold',
            min_value=0.1,
            max_value=5.0
        )

        # Volume analysis settings
        self.use_volume_analysis = self.config.get('use_volume_analysis', True)

        # Validate threshold relationships
        if self.weak_trend_threshold > self.strong_trend_threshold:
            logger.warning(
                f"weak_trend_threshold ({self.weak_trend_threshold}) > "
                f"strong_trend_threshold ({self.strong_trend_threshold}). Swapping values."
            )
            self.weak_trend_threshold, self.strong_trend_threshold = (
                self.strong_trend_threshold, self.weak_trend_threshold
            )

        if self.low_volatility_threshold > self.high_volatility_threshold:
            logger.warning(
                f"low_volatility_threshold ({self.low_volatility_threshold}) > "
                f"high_volatility_threshold ({self.high_volatility_threshold}). Swapping values."
            )
            self.low_volatility_threshold, self.high_volatility_threshold = (
                self.high_volatility_threshold, self.low_volatility_threshold
            )

        # Cache results
        self._regime_cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self._cache_ttl_seconds = CACHE_TTL_SECONDS

        # Required samples (consider all indicator periods)
        self._required_samples = max(
            self.adx_period,
            self.volatility_period,
            self.bollinger_period,
            self.rsi_period
        ) + EXTRA_DATA_BUFFER

        # Regime history for transition analysis
        self._regime_history = deque(maxlen=REGIME_HISTORY_MAXLEN)
        self._regime_transition_probabilities = defaultdict(lambda: defaultdict(int))

        logger.info(f"MarketRegimeDetector initialized. Enabled: {self.enabled}")

    def _validate_period(self, value: Any, name: str, min_value: int = 1, max_value: int = 1000) -> int:
        """
        Validate period parameter.

        Args:
            value: Value to validate
            name: Parameter name for logging
            min_value: Minimum allowed value
            max_value: Maximum allowed value

        Returns:
            Validated integer value

        Raises:
            ValueError: If value is invalid
        """
        try:
            int_value = int(value)
            if int_value < min_value or int_value > max_value:
                raise ValueError(
                    f"{name} must be between {min_value} and {max_value}, got {int_value}"
                )
            return int_value
        except (TypeError, ValueError) as e:
            logger.error(f"Invalid {name}: {value}. Error: {e}")
            raise ValueError(f"Invalid {name}: {value}") from e

    def _validate_threshold(self, value: Any, name: str, min_value: float = 0.0, max_value: float = 100.0) -> float:
        """
        Validate threshold parameter.

        Args:
            value: Value to validate
            name: Parameter name for logging
            min_value: Minimum allowed value
            max_value: Maximum allowed value

        Returns:
            Validated float value

        Raises:
            ValueError: If value is invalid
        """
        try:
            float_value = float(value)
            if float_value < min_value or float_value > max_value:
                raise ValueError(
                    f"{name} must be between {min_value} and {max_value}, got {float_value}"
                )
            return float_value
        except (TypeError, ValueError) as e:
            logger.error(f"Invalid {name}: {value}. Error: {e}")
            raise ValueError(f"Invalid {name}: {value}") from e

    def detect_regime(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect market regime based on ADX and ATR.

        Args:
            df: OHLCV DataFrame

        Returns:
            Dictionary with regime info
        """
        if not self.enabled:
            return {
                'regime': RegimeStatus.DISABLED.value,
                'confidence': 1.0,
                'details': {}
            }

        # Check cache
        cache_key = self._generate_cache_key(df)
        if cache_key in self._regime_cache:
            cached_result, timestamp = self._regime_cache[cache_key]
            if time.time() - timestamp < self._cache_ttl_seconds:
                return cached_result

        # Minimum data needed
        if df is None or len(df) < self._required_samples:
            logger.debug(
                f"Not enough data ({len(df) if df is not None else 0} rows) "
                f"to detect market regime (requires {self._required_samples})."
            )
            return {
                'regime': RegimeStatus.UNKNOWN_DATA.value,
                'confidence': 0.0,
                'details': {}
            }

        try:
            # Prepare data
            df_copy = df.copy()
            high_prices = df_copy['high'].values.astype(np.float64)
            low_prices = df_copy['low'].values.astype(np.float64)
            close_prices = df_copy['close'].values.astype(np.float64)

            # Use pre-calculated indicators if available, otherwise calculate
            # ADX, +DI, -DI
            if 'adx' in df_copy.columns and 'plus_di' in df_copy.columns and 'minus_di' in df_copy.columns:
                adx = df_copy['adx'].values
                plus_di = df_copy['plus_di'].values
                minus_di = df_copy['minus_di'].values
            else:
                logger.debug("ADX not pre-calculated, calculating...")
                adx = talib.ADX(high_prices, low_prices, close_prices, timeperiod=self.adx_period)
                plus_di = talib.PLUS_DI(high_prices, low_prices, close_prices, timeperiod=self.adx_period)
                minus_di = talib.MINUS_DI(high_prices, low_prices, close_prices, timeperiod=self.adx_period)

            # ATR
            if 'atr' in df_copy.columns:
                atr = df_copy['atr'].values
            else:
                logger.debug("ATR not pre-calculated, calculating...")
                atr = talib.ATR(high_prices, low_prices, close_prices, timeperiod=self.volatility_period)

            atr_percent = np.where(close_prices > 0, (atr / close_prices) * 100, 0)

            # Bollinger Bands
            if 'bb_upper' in df_copy.columns and 'bb_middle' in df_copy.columns and 'bb_lower' in df_copy.columns:
                bb_upper = df_copy['bb_upper'].values
                bb_middle = df_copy['bb_middle'].values
                bb_lower = df_copy['bb_lower'].values
            else:
                logger.debug("Bollinger Bands not pre-calculated, calculating...")
                bb_upper, bb_middle, bb_lower = talib.BBANDS(
                    close_prices,
                    timeperiod=self.bollinger_period,
                    nbdevup=self.bollinger_std,
                    nbdevdn=self.bollinger_std
                )

            bb_width = np.where(bb_middle > 0, (bb_upper - bb_lower) / bb_middle * 100, 0)

            # RSI
            if 'rsi' in df_copy.columns:
                rsi = df_copy['rsi'].values
            else:
                logger.debug("RSI not pre-calculated, calculating...")
                rsi = talib.RSI(close_prices, timeperiod=self.rsi_period)

            # Calculate Volume Analysis (if available)
            volume_ratio = None
            volume_price_correlation = None
            if self.use_volume_analysis and 'volume' in df_copy.columns:
                try:
                    volume_values = df_copy['volume'].values.astype(np.float64)

                    # Use pre-calculated volume SMA if available
                    if 'volume_sma' in df_copy.columns:
                        volume_sma = df_copy['volume_sma'].values
                    else:
                        logger.debug("Volume SMA not pre-calculated, calculating...")
                        volume_sma = talib.SMA(volume_values, timeperiod=20)

                    volume_ratio = np.where(volume_sma > 0, volume_values / volume_sma, 1.0)

                    # Calculate volume-price correlation
                    if len(df_copy) >= 20:
                        price_changes = pd.Series(close_prices).pct_change().iloc[-20:]
                        volume_changes = pd.Series(volume_values).pct_change().iloc[-20:]
                        volume_price_correlation = abs(price_changes.corr(volume_changes))
                except Exception as e:
                    logger.debug(f"Could not calculate volume analysis: {e}")

            # Add indicators to dataframe for detection methods
            df_copy['adx'] = adx
            df_copy['plus_di'] = plus_di
            df_copy['minus_di'] = minus_di
            df_copy['atr'] = atr
            df_copy['atr_percent'] = atr_percent
            df_copy['bb_upper'] = bb_upper
            df_copy['bb_middle'] = bb_middle
            df_copy['bb_lower'] = bb_lower
            df_copy['bb_width'] = bb_width
            df_copy['rsi'] = rsi

            # Get last valid values
            last_valid_idx = self._find_last_valid_index([adx, atr_percent])
            if last_valid_idx is None:
                logger.warning("Could not find valid ADX/ATR values for regime detection.")
                return {
                    'regime': RegimeStatus.UNKNOWN_CALC.value,
                    'confidence': 0.0,
                    'details': {}
                }

            current_adx = adx[last_valid_idx]
            current_plus_di = plus_di[last_valid_idx]
            current_minus_di = minus_di[last_valid_idx]
            current_atr_percent = atr_percent[last_valid_idx]
            current_bb_width = bb_width[last_valid_idx] if not np.isnan(bb_width[last_valid_idx]) else 0.0
            current_rsi = rsi[last_valid_idx] if not np.isnan(rsi[last_valid_idx]) else 50.0
            current_atr = atr[last_valid_idx] if not np.isnan(atr[last_valid_idx]) else 0.0
            current_volume_ratio = volume_ratio[last_valid_idx] if volume_ratio is not None and not np.isnan(volume_ratio[last_valid_idx]) else 1.0

            # Validate that values are not NaN
            assert not np.isnan(current_adx), "current_adx is NaN"
            assert not np.isnan(current_atr_percent), "current_atr_percent is NaN"

            # Determine trend strength
            if current_adx >= self.strong_trend_threshold:
                trend_strength = TrendStrength.STRONG
            elif current_adx >= self.weak_trend_threshold:
                trend_strength = TrendStrength.WEAK
            else:
                trend_strength = TrendStrength.NONE

            # Determine trend direction
            if current_plus_di > current_minus_di:
                trend_direction = Direction.BULLISH
            elif current_minus_di > current_plus_di:
                trend_direction = Direction.BEARISH
            else:
                trend_direction = Direction.NEUTRAL

            # Determine volatility
            if current_atr_percent >= self.high_volatility_threshold:
                volatility = VolatilityRegime.HIGH
            elif current_atr_percent <= self.low_volatility_threshold:
                volatility = VolatilityRegime.LOW
            else:
                volatility = VolatilityRegime.NORMAL

            # Detect special market conditions
            is_breakout, breakout_direction = self._detect_breakout(df_copy, current_atr)
            is_choppy = self._is_choppy_market(df_copy)

            # Build regime string (OLD SYSTEM: 9 regimes)
            # Format: {trend_strength}_{volatility}
            # e.g., "strong_trend_normal", "weak_trend_high", "range_low"
            if is_breakout:
                # Special case: breakout gets priority but still includes volatility
                regime = f"breakout_{breakout_direction}_{volatility.value}"
            elif is_choppy:
                # Special case: choppy market (range with high ADX changes)
                regime = "choppy"
            elif trend_strength == TrendStrength.STRONG:
                # Strong trend + volatility combination
                if volatility == VolatilityRegime.HIGH:
                    regime = "strong_trend_high"  # OLD SYSTEM format
                elif volatility == VolatilityRegime.LOW:
                    regime = "strong_trend_low"  # OLD SYSTEM format
                else:
                    regime = "strong_trend_normal"  # OLD SYSTEM format
            elif trend_strength == TrendStrength.WEAK:
                # Weak trend + volatility combination
                if volatility == VolatilityRegime.HIGH:
                    regime = "weak_trend_high"  # OLD SYSTEM format
                elif volatility == VolatilityRegime.LOW:
                    regime = "weak_trend_low"  # OLD SYSTEM format
                else:
                    regime = "weak_trend_normal"  # OLD SYSTEM format
            else:  # TrendStrength.NONE (range/sideways)
                # Range + volatility combination
                if volatility == VolatilityRegime.HIGH:
                    regime = "range_high"  # OLD SYSTEM format
                elif volatility == VolatilityRegime.LOW:
                    regime = "range_low"  # OLD SYSTEM format
                else:
                    regime = "range_normal"  # OLD SYSTEM format

            # Calculate improved confidence
            confidence = self._calculate_confidence(
                df_copy, current_adx, is_breakout, breakout_direction,
                trend_direction.value, current_volume_ratio, volume_price_correlation
            )

            # Enhanced details
            details = {
                'adx': round(current_adx, 2),
                'plus_di': round(current_plus_di, 2),
                'minus_di': round(current_minus_di, 2),
                'atr_percent': round(current_atr_percent, 3),
                'bb_width': round(current_bb_width, 3),
                'rsi': round(current_rsi, 2),
                'is_breakout': is_breakout,
                'is_choppy': is_choppy
            }

            # Add volume details if available
            if volume_ratio is not None:
                details['volume_ratio'] = round(current_volume_ratio, 3)
            if volume_price_correlation is not None:
                details['volume_price_correlation'] = round(volume_price_correlation, 3)

            # Regime transition probabilities
            if self._regime_history:
                prev_regime = self._regime_history[-1]
                self._regime_transition_probabilities[prev_regime][regime] += 1
                next_regime_probs = self._calculate_next_regime_probabilities(regime)
                details['next_regime_probabilities'] = next_regime_probs

            # Add to history
            self._regime_history.append(regime)

            logger.debug(
                f"Regime Detected: {regime}, Strength: {trend_strength.value} ({details['adx']}), "
                f"Direction: {trend_direction.value}, Volatility: {volatility.value} ({details['atr_percent']}), "
                f"Confidence: {confidence:.2f}"
            )

            result = {
                'regime': regime,
                'trend_strength': trend_strength.value,
                'trend_direction': trend_direction.value,
                'volatility': volatility.value,
                'confidence': confidence,
                'details': details
            }

            # Save to cache
            self._regime_cache[cache_key] = (result, time.time())

            return result

        except AssertionError as e:
            logger.error(f"Assertion failed in regime detection: {str(e)}", exc_info=True)
            return {
                'regime': RegimeStatus.ERROR.value,
                'confidence': 0.0,
                'details': {'error': str(e)}
            }
        except Exception as e:
            logger.error(f"Error detecting market regime: {str(e)}", exc_info=True)
            return {
                'regime': RegimeStatus.ERROR.value,
                'confidence': 0.0,
                'details': {'error': str(e)}
            }

    def _detect_breakout(self, df: pd.DataFrame, current_atr: float) -> Tuple[bool, str]:
        """
        Detect price breakout from Bollinger Bands range.

        Args:
            df: DataFrame with indicators including bb_upper, bb_lower
            current_atr: Current ATR value for strength calculation

        Returns:
            Tuple of (is_breakout, direction) where direction is 'bullish', 'bearish', or 'neutral'
        """
        try:
            if 'bb_upper' not in df.columns or 'bb_lower' not in df.columns:
                return False, "neutral"

            # Check for breakout above or below Bollinger Bands
            close_values = df['close'].iloc[-self.breakout_lookback:]
            upper_values = df['bb_upper'].iloc[-self.breakout_lookback:]
            lower_values = df['bb_lower'].iloc[-self.breakout_lookback:]

            # Bullish breakout: price above upper band
            if close_values.iloc[-1] > upper_values.iloc[-1] and all(close_values.iloc[-3:-1] <= upper_values.iloc[-3:-1]):
                # Check breakout strength
                breakout_strength = (close_values.iloc[-1] - upper_values.iloc[-1]) / current_atr

                if breakout_strength > self.breakout_threshold:
                    return True, "bullish"
                else:
                    return False, "neutral"

            # Bearish breakout: price below lower band
            if close_values.iloc[-1] < lower_values.iloc[-1] and all(close_values.iloc[-3:-1] >= lower_values.iloc[-3:-1]):
                # Check breakout strength
                breakout_strength = (lower_values.iloc[-1] - close_values.iloc[-1]) / current_atr

                if breakout_strength > self.breakout_threshold:
                    return True, "bearish"
                else:
                    return False, "neutral"

            return False, "neutral"

        except Exception as e:
            logger.error(f"Error detecting breakout: {e}")
            return False, "neutral"

    def _is_choppy_market(self, df: pd.DataFrame) -> bool:
        """
        Detect choppy/chaotic market conditions.

        Args:
            df: DataFrame with indicators including adx, rsi, atr_percent

        Returns:
            True if market is choppy/chaotic
        """
        try:
            if 'adx' not in df.columns or 'rsi' not in df.columns:
                return False

            # Low ADX indicates lack of trend
            low_adx = df['adx'].iloc[-1] < self.weak_trend_threshold

            # Rapid RSI changes indicate choppy market
            rsi_changes = abs(df['rsi'].diff(1).iloc[-5:])
            high_rsi_changes = (rsi_changes > 10).sum() >= 3

            # High price oscillation in small range
            if 'atr_percent' in df.columns:
                price_changes = abs(df['close'].pct_change(1).iloc[-5:]) * 100
                avg_change = price_changes.mean()
                direction_changes = (np.sign(df['close'].diff(1).iloc[-6:]).diff(1) != 0).sum()

                # Many direction changes + high price changes = choppy market
                if low_adx and (high_rsi_changes or (direction_changes >= 3 and avg_change >= self.choppy_threshold)):
                    logger.debug(
                        f"Choppy market detected: ADX={df['adx'].iloc[-1]:.2f}, "
                        f"direction_changes={direction_changes}, avg_price_change={avg_change:.2f}%"
                    )
                    return True

            return low_adx and high_rsi_changes

        except Exception as e:
            logger.error(f"Error detecting choppy market: {e}")
            return False

    def _calculate_confidence(
        self,
        df: pd.DataFrame,
        current_adx: float,
        is_breakout: bool,
        breakout_direction: str,
        trend_direction: str,
        current_volume_ratio: float,
        volume_price_correlation: float
    ) -> float:
        """
        Calculate confidence level for regime detection using multiple factors.

        Args:
            df: DataFrame with indicators
            current_adx: Current ADX value
            is_breakout: Whether breakout is detected
            breakout_direction: Direction of breakout ('bullish', 'bearish', 'neutral')
            trend_direction: Current trend direction
            current_volume_ratio: Current volume ratio vs average
            volume_price_correlation: Correlation between volume and price changes

        Returns:
            Confidence score between 0.0 and 1.0
        """
        try:
            # Calculate ADX stability over recent periods
            adx_stability = 1.0
            try:
                recent_adx = df['adx'].iloc[-5:]
                adx_std = recent_adx.std()
                adx_mean = recent_adx.mean()
                if adx_mean > 0.1:
                    adx_stability = 1.0 - min(1.0, adx_std / adx_mean)
            except:
                pass

            # Combine different factors in confidence calculation
            confidence_factors = [
                adx_stability * 0.5,  # ADX stability (weight: 50%)
                0.3,  # Base confidence (30%)
            ]

            # If breakout detected and aligned with trend, increase confidence
            if is_breakout:
                if ((breakout_direction == "bullish" and trend_direction == "bullish") or
                    (breakout_direction == "bearish" and trend_direction == "bearish")):
                    confidence_factors.append(0.2)  # Breakout bonus (20%)

            # If volume analysis is active, use it in confidence calculation
            if self.use_volume_analysis and current_volume_ratio > 1.5:
                # Increase confidence based on volume-price correlation
                confidence_factors.append(0.1 * volume_price_correlation)

            # Final confidence
            confidence = min(1.0, sum(confidence_factors))

            return confidence

        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.5  # Default moderate confidence

    def _calculate_next_regime_probabilities(self, current_regime: str) -> Dict[str, float]:
        """Calculate transition probabilities to next regimes."""
        transitions = self._regime_transition_probabilities[current_regime]
        total_transitions = sum(transitions.values())

        if total_transitions == 0:
            return {}

        return {
            next_regime: safe_divide(count, total_transitions, 0.0)
            for next_regime, count in transitions.items()
        }

    def _find_last_valid_index(self, arrays: List[np.ndarray]) -> Optional[int]:
        """Find the last valid index across multiple arrays."""
        if not arrays:
            return None

        max_len = min(len(arr) for arr in arrays)
        if max_len == 0:
            return None

        # Search from end to beginning
        for i in range(-1, -max_len - 1, -1):
            if all(not np.isnan(arr[i]) for arr in arrays):
                return i

        return None

    def _generate_cache_key(self, df: pd.DataFrame) -> str:
        """
        Generate cache key from dataframe using hash for uniqueness.

        Args:
            df: Input dataframe

        Returns:
            Unique cache key string
        """
        if df is None or len(df) == 0:
            return "empty_dataframe"

        try:
            last_idx = df.index[-1]
            last_close = df['close'].iloc[-1]
            last_high = df['high'].iloc[-1]
            last_low = df['low'].iloc[-1]

            # Create a unique string representation
            timestamp_str = str(last_idx) if isinstance(last_idx, (int, float)) else (
                str(last_idx.timestamp()) if hasattr(last_idx, 'timestamp') else str(last_idx)
            )

            # Use hash for better uniqueness guarantee
            data_str = f"{timestamp_str}_{last_close:.8f}_{last_high:.8f}_{last_low:.8f}_{len(df)}"
            hash_value = hashlib.md5(data_str.encode()).hexdigest()[:16]

            return f"regime_{hash_value}"
        except (IndexError, KeyError, AttributeError) as e:
            logger.debug(f"Error generating cache key: {e}")
            return f"dataframe_len_{len(df)}"

    def _apply_adjustment(
            self,
            base_value: float,
            modifier: float,
            confidence: float
    ) -> float:
        """
        Apply adjustment with confidence weighting.

        Args:
            base_value: Base parameter value
            modifier: Adjustment modifier (1.0 = no change)
            confidence: Confidence level (0.0 to 1.0)

        Returns:
            Adjusted value
        """
        return base_value * (1.0 + (modifier - 1.0) * confidence)

    def _adapt_risk_parameters(
            self,
            risk_params: Dict[str, Any],
            base_risk: Dict[str, Any],
            trend_strength: str,
            volatility: str,
            confidence: float
    ) -> None:
        """
        Adapt risk management parameters based on market regime.

        Args:
            risk_params: Risk parameters to modify (modified in-place)
            base_risk: Base risk configuration
            trend_strength: Trend strength classification
            volatility: Volatility classification
            confidence: Confidence level
        """
        # 1. Max risk per trade
        base_risk_pct = base_risk.get('max_risk_per_trade_percent', 2.0)
        risk_modifier = 1.0

        if volatility == VolatilityRegime.HIGH.value:
            risk_modifier = 0.7  # Reduce risk
        elif volatility == VolatilityRegime.LOW.value:
            risk_modifier = 1.2  # Can increase slightly

        risk_params['max_risk_per_trade_percent'] = self._apply_adjustment(
            base_risk_pct, risk_modifier, confidence
        )

        # 2. Preferred RR ratio
        base_rr = base_risk.get('preferred_risk_reward_ratio', 2.5)
        rr_modifier = 1.0

        if trend_strength == TrendStrength.STRONG.value:
            rr_modifier = 1.2  # Higher targets in strong trends
        elif trend_strength == TrendStrength.NONE.value:
            rr_modifier = 0.8  # Lower targets in ranging

        risk_params['preferred_risk_reward_ratio'] = self._apply_adjustment(
            base_rr, rr_modifier, confidence
        )

        # 3. Stop loss percentage
        base_sl_percent = base_risk.get('default_stop_loss_percent', 1.5)
        sl_modifier = 1.0

        if volatility == VolatilityRegime.HIGH.value:
            sl_modifier = 1.3  # Wider stop loss
        elif volatility == VolatilityRegime.LOW.value:
            sl_modifier = 0.8  # Tighter stop loss

        risk_params['default_stop_loss_percent'] = self._apply_adjustment(
            base_sl_percent, sl_modifier, confidence
        )

    def _adapt_signal_parameters(
            self,
            signal_params: Dict[str, Any],
            base_signal: Dict[str, Any],
            trend_strength: str,
            volatility: str,
            confidence: float
    ) -> None:
        """
        Adapt signal generation parameters based on market regime.

        Args:
            signal_params: Signal parameters to modify (modified in-place)
            base_signal: Base signal configuration
            trend_strength: Trend strength classification
            volatility: Volatility classification
            confidence: Confidence level
        """
        # Minimum signal score
        base_min_score = base_signal.get('minimum_signal_score', 33)
        score_modifier = 1.0

        if trend_strength == TrendStrength.NONE.value or volatility == VolatilityRegime.HIGH.value:
            score_modifier = 1.1  # More strict

        signal_params['minimum_signal_score'] = self._apply_adjustment(
            base_min_score, score_modifier, confidence
        )

    def _round_parameters(self, *param_dicts: Dict[str, Any]) -> None:
        """
        Round float parameters to 2 decimal places.

        Args:
            *param_dicts: Variable number of parameter dictionaries to round
        """
        for params in param_dicts:
            for key, value in params.items():
                if isinstance(value, float):
                    params[key] = round(value, 2)

    def get_adapted_parameters(
            self,
            regime_info: Dict[str, Any],
            base_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Adjust strategy parameters based on market regime.

        Args:
            regime_info: Regime detection results
            base_config: Base configuration

        Returns:
            Adapted configuration
        """
        # Check if adaptation is needed
        disabled_regimes = [
            RegimeStatus.DISABLED.value,
            RegimeStatus.UNKNOWN_DATA.value,
            RegimeStatus.UNKNOWN_CALC.value,
            RegimeStatus.ERROR.value
        ]
        if not self.enabled or regime_info.get('regime', 'disabled') in disabled_regimes:
            return base_config

        # Deep copy to avoid changing original
        adapted_config = copy.deepcopy(base_config)

        # Extract regime information
        regime = regime_info.get('regime')
        trend_strength = regime_info.get('trend_strength')
        volatility = regime_info.get('volatility')
        confidence = regime_info.get('confidence', 0.5)

        # Get config sections
        risk_params = adapted_config.setdefault('risk_management', {})
        signal_params = adapted_config.setdefault('signal_generation', {})

        # Base values
        base_risk = copy.deepcopy(self.config.get('risk_management', {}))
        base_signal = copy.deepcopy(self.config.get('signal_generation', {}))

        # Apply adaptations
        self._adapt_risk_parameters(risk_params, base_risk, trend_strength, volatility, confidence)
        self._adapt_signal_parameters(signal_params, base_signal, trend_strength, volatility, confidence)

        # Round all parameter values
        self._round_parameters(risk_params, signal_params)

        # Log the adaptation
        logger.debug(
            f"Regime '{regime}' (Conf: {confidence:.2f}) -> Adapted Params: "
            f"Risk%: {risk_params.get('max_risk_per_trade_percent', 'N/A')}, "
            f"RR: {risk_params.get('preferred_risk_reward_ratio', 'N/A')}, "
            f"MinScore: {signal_params.get('minimum_signal_score', 'N/A')}"
        )

        return adapted_config