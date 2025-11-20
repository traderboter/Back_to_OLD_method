"""
Base Indicator - Base class for all indicator calculators

This is the abstract base class that all indicator calculators must inherit from.
It provides a consistent interface for indicator calculation and validation.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, List
import pandas as pd
import numpy as np
import logging
import hashlib

logger = logging.getLogger(__name__)


class BaseIndicator(ABC):
    """
    Abstract base class for all indicator calculators.

    All indicator classes must inherit from this class and implement
    the abstract methods.

    Key features:
    1. Standardized interface for indicator calculation
    2. Automatic validation of input data
    3. Consistent output format
    4. Error handling
    5. Caching support
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the indicator calculator.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.name = self._get_indicator_name()
        self.indicator_type = self._get_indicator_type()
        self.required_columns = self._get_required_columns()
        self.output_columns = self._get_output_columns()

        # Caching
        self._cache_enabled = self.config.get('cache_enabled', True)
        self._last_result = None
        self._last_hash = None

        # Current timeframe (set by orchestrator)
        self.timeframe = None

        logger.debug(f"Indicator initialized: {self.name}")

    @abstractmethod
    def _get_indicator_name(self) -> str:
        """
        Get the indicator name.

        Returns:
            Indicator name (e.g., 'EMA', 'RSI', 'MACD')
        """
        pass

    @abstractmethod
    def _get_indicator_type(self) -> str:
        """
        Get the indicator type.

        Returns:
            'trend', 'momentum', 'volatility', 'volume', or 'other'
        """
        pass

    @abstractmethod
    def _get_required_columns(self) -> List[str]:
        """
        Get list of required DataFrame columns.

        Returns:
            List of column names (e.g., ['close'], ['high', 'low', 'close'])
        """
        pass

    @abstractmethod
    def _get_output_columns(self) -> List[str]:
        """
        Get list of output column names.

        Returns:
            List of column names that will be added to DataFrame
            (e.g., ['ema_20'], ['macd', 'macd_signal', 'macd_hist'])
        """
        pass

    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the indicator and add columns to DataFrame.

        This is the main method that performs the calculation.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with indicator columns added
        """
        pass

    def calculate_safe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Safely calculate indicator with validation and error handling.

        This is the main public method that should be called.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with indicator columns added (original if error)
        """
        try:
            # Validate input
            if not self._validate_input(df):
                logger.warning(f"{self.name}: Input validation failed")
                return df

            # Check cache
            if self._cache_enabled:
                df_hash = self._get_dataframe_hash(df)
                if df_hash is not None and df_hash == self._last_hash and self._last_result is not None:
                    logger.debug(f"{self.name}: Returning cached result")
                    return self._last_result.copy()

            # Calculate
            result_df = self.calculate(df)

            # Validate output
            if not self._validate_output(result_df):
                logger.warning(f"{self.name}: Output validation failed")
                return df

            # Cache result
            if self._cache_enabled:
                self._last_result = result_df.copy()
                self._last_hash = df_hash

            logger.debug(f"{self.name}: Calculation completed successfully")
            return result_df

        except Exception as e:
            logger.error(f"Error calculating {self.name}: {e}", exc_info=True)
            return df

    def get_values(
        self,
        df: pd.DataFrame,
        column: Optional[str] = None
    ) -> Union[pd.Series, Dict[str, pd.Series]]:
        """
        Get calculated indicator values.

        Args:
            df: DataFrame with calculated indicators
            column: Optional specific column to get (if None, returns all)

        Returns:
            Series if column specified, dict of Series otherwise
        """
        if column:
            if column in df.columns:
                return df[column]
            else:
                logger.warning(f"{self.name}: Column {column} not found")
                return pd.Series()
        else:
            # Return all output columns
            result = {}
            for col in self.output_columns:
                if col in df.columns:
                    result[col] = df[col]
            return result

    def get_latest_value(
        self,
        df: pd.DataFrame,
        column: Optional[str] = None
    ) -> Union[float, Dict[str, float]]:
        """
        Get latest indicator value(s).

        Args:
            df: DataFrame with calculated indicators
            column: Optional specific column to get

        Returns:
            Float if column specified, dict of floats otherwise
        """
        values = self.get_values(df, column)

        if isinstance(values, pd.Series):
            return float(values.iloc[-1]) if len(values) > 0 else np.nan
        else:
            return {k: float(v.iloc[-1]) if len(v) > 0 else np.nan
                    for k, v in values.items()}

    def _validate_input(self, df: pd.DataFrame) -> bool:
        """
        Validate input DataFrame.

        Args:
            df: DataFrame to validate

        Returns:
            True if valid, False otherwise
        """
        # Check DataFrame is not empty
        if df is None or len(df) == 0:
            logger.warning(f"{self.name}: DataFrame is empty")
            return False

        # Check required columns exist
        for col in self.required_columns:
            if col not in df.columns:
                logger.warning(f"{self.name}: Missing required column: {col}")
                return False

        # Check for sufficient data
        min_periods = self._get_min_periods()
        if len(df) < min_periods:
            logger.warning(
                f"{self.name}: Insufficient data. "
                f"Need at least {min_periods} rows, got {len(df)}"
            )
            return False

        return True

    def _validate_output(self, df: pd.DataFrame) -> bool:
        """
        Validate output DataFrame.

        Args:
            df: DataFrame to validate

        Returns:
            True if valid, False otherwise
        """
        # Check output columns were added
        for col in self.output_columns:
            if col not in df.columns:
                logger.warning(f"{self.name}: Output column {col} not found")
                return False

        return True

    def _get_min_periods(self) -> int:
        """
        Get minimum number of periods required for calculation.

        Subclasses should override this.

        Returns:
            Minimum periods (default: 1)
        """
        return 1

    def _safe_divide(self, numerator, denominator, default=0):
        """
        Safe division with protection from division by zero.

        Args:
            numerator: Numerator (can be scalar or array/Series)
            denominator: Denominator (can be scalar or array/Series)
            default: Default value when denominator is zero (default: 0)

        Returns:
            Result of division or default value where denominator is zero
            Returns same type as input (Series if input is Series, array if array)
        """
        # Handle pandas Series
        is_series = isinstance(numerator, pd.Series) or isinstance(denominator, pd.Series)

        # Convert to numpy arrays for computation
        num_arr = np.asarray(numerator)
        den_arr = np.asarray(denominator)

        # Perform safe division
        # Use np.divide with where parameter to avoid division by zero
        result = np.divide(num_arr, den_arr,
                          out=np.full_like(num_arr, default, dtype=float),
                          where=den_arr != 0)

        # Return same type as input
        if is_series:
            if isinstance(numerator, pd.Series):
                return pd.Series(result, index=numerator.index)
            elif isinstance(denominator, pd.Series):
                return pd.Series(result, index=denominator.index)

        return result

    def _get_dataframe_hash(self, df: pd.DataFrame) -> Optional[str]:
        """
        Get hash of DataFrame for caching.

        Args:
            df: DataFrame to hash

        Returns:
            Hash value (SHA256 hex digest) or None if error
        """
        try:
            # Hash based on required columns only
            data_to_hash = df[self.required_columns].values.tobytes()
            # Use SHA256 for reliable hashing, truncate to 16 chars for efficiency
            return hashlib.sha256(data_to_hash).hexdigest()[:16]
        except Exception as e:
            logger.debug(f"{self.name}: Error hashing DataFrame: {e}")
            return None

    def get_parameter(
        self,
        param_name: str,
        default_value: Any,
        timeframe: str = None
    ) -> Any:
        """
        Get indicator parameter with per-timeframe support.

        This method checks for per-timeframe configuration first,
        then falls back to global configuration.

        Args:
            param_name: Parameter name (e.g., 'rsi_period', 'macd_fast')
            default_value: Fallback default value
            timeframe: Current timeframe (e.g., '5m', '15m', '1h', '4h')

        Returns:
            Parameter value (per-TF if available, otherwise global or default)

        Example:
            # In RSIIndicator:
            rsi_period = self.get_parameter('rsi_period', 14, '5m')
            # Returns 10 for 5m, 14 for 1h, 18 for 4h (if configured)
        """
        # Use provided timeframe or instance timeframe
        tf = timeframe or self.timeframe

        # Get indicator calculator config
        # Support both nested (signal_generation_v2.indicator_calculator) and flat config
        if 'signal_generation_v2' in self.config:
            indicator_config = self.config.get('signal_generation_v2', {}).get('indicator_calculator', {})
        else:
            indicator_config = self.config.get('indicator_calculator', {})

        # Check for per-timeframe config
        per_tf_config = indicator_config.get('per_timeframe', {})

        if per_tf_config.get('enabled', False) and tf:
            # Per-TF is enabled, try to get TF-specific value
            tf_config = per_tf_config.get(tf, {})
            if tf_config and param_name in tf_config:
                logger.debug(
                    f"{self.name}: Using per-TF parameter "
                    f"{param_name}={tf_config[param_name]} for {tf}"
                )
                return tf_config[param_name]

        # Fallback to oscillators/moving_averages/volatility config
        # Try to categorize the parameter
        if self.indicator_type == 'momentum':
            type_config = indicator_config.get('oscillators', {})
        elif self.indicator_type == 'trend':
            type_config = indicator_config.get('moving_averages', {})
        elif self.indicator_type == 'volatility':
            type_config = indicator_config.get('volatility', {})
        elif self.indicator_type == 'volume':
            type_config = indicator_config.get('volume', {})
        else:
            type_config = {}

        # Check type-specific config
        if param_name in type_config:
            return type_config[param_name]

        # Fallback to root config (for backward compatibility)
        if param_name in self.config:
            return self.config[param_name]

        # Return default
        logger.debug(
            f"{self.name}: Using default parameter "
            f"{param_name}={default_value}"
        )
        return default_value

    def clear_cache(self):
        """Clear cached results."""
        self._last_result = None
        self._last_hash = None
        logger.debug(f"{self.name}: Cache cleared")

    def __str__(self) -> str:
        """String representation."""
        return f"{self.name} ({self.indicator_type})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"{self.__class__.__name__}(name='{self.name}', "
            f"type='{self.indicator_type}', "
            f"required={self.required_columns}, "
            f"output={self.output_columns})"
        )
