"""
BaseAnalyzer - Abstract Base Class for All Analyzers

All analyzers must inherit from this base class and implement the analyze() method.

Standard pattern:
1. Check if enabled
2. Validate context
3. Perform analysis
4. Store results in context
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

from signal_generation.analysis_result import AnalysisResult, AnalysisError, ErrorSeverity

logger = logging.getLogger(__name__)


class BaseAnalyzer(ABC):
    """
    Abstract base class for all analyzers.
    
    All analyzers must:
    1. Inherit from this class
    2. Implement the analyze() method
    3. Store results in context using context.add_result()
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the analyzer.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.enabled = True
        
        logger.debug(f"{self.__class__.__name__} initialized")
    
    @abstractmethod
    def analyze(self, context: 'AnalysisContext') -> None:
        """
        Main analysis method - must be implemented by all analyzers.
        
        Args:
            context: AnalysisContext with dataframe and indicators
            
        This method should:
        1. Check if enabled (using _check_enabled())
        2. Validate context (using _validate_context())
        3. Perform analysis
        4. Store results (using context.add_result())
        """
        pass
    
    def _check_enabled(self) -> bool:
        """
        Check if this analyzer is enabled.
        
        Returns:
            True if enabled, False otherwise
        """
        return getattr(self, 'enabled', True)
    
    def _validate_context(self, context: 'AnalysisContext') -> bool:
        """
        Validate that context has required data.
        
        Override this method in subclasses to add specific validation.
        
        Args:
            context: AnalysisContext to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Basic validation
        if context.df is None or len(context.df) == 0:
            logger.warning(f"{self.__class__.__name__}: Empty DataFrame")
            return False
        
        return True
    
    def safe_analyze(self, context: 'AnalysisContext') -> AnalysisResult[Dict[str, Any]]:
        """
        Safely execute analysis with unified error handling.

        This method wraps analyze() with consistent error handling.
        Analyzers can optionally use this instead of analyze() directly.

        Args:
            context: AnalysisContext

        Returns:
            AnalysisResult with success/error information
        """
        analyzer_name = self.__class__.__name__

        try:
            # Check if enabled
            if not self._check_enabled():
                error = AnalysisError(
                    severity=ErrorSeverity.WARNING,
                    analyzer=analyzer_name,
                    message=f"{analyzer_name} is disabled",
                    context={'symbol': context.symbol, 'timeframe': context.timeframe}
                )
                return AnalysisResult.fail(error)

            # Validate context
            if not self._validate_context(context):
                error = AnalysisError(
                    severity=ErrorSeverity.WARNING,
                    analyzer=analyzer_name,
                    message="Context validation failed (empty DataFrame or insufficient data)",
                    context={'symbol': context.symbol, 'timeframe': context.timeframe}
                )
                return AnalysisResult.fail(error)

            # Perform analysis (old-style, modifies context in-place)
            self.analyze(context)

            # Get result from context
            result_data = context.get_result(self._get_result_key())

            if result_data is None:
                # Analyzer didn't store result
                error = AnalysisError(
                    severity=ErrorSeverity.WARNING,
                    analyzer=analyzer_name,
                    message="Analyzer completed but stored no result",
                    context={'symbol': context.symbol, 'timeframe': context.timeframe}
                )
                return AnalysisResult.fail(error)

            # Check if result indicates error
            if isinstance(result_data, dict) and result_data.get('status') == 'error':
                error = AnalysisError(
                    severity=ErrorSeverity.ERROR,
                    analyzer=analyzer_name,
                    message=result_data.get('message', 'Unknown error'),
                    context={'symbol': context.symbol, 'timeframe': context.timeframe}
                )
                return AnalysisResult.fail(error)

            # Success
            return AnalysisResult.ok(result_data)

        except Exception as e:
            # Unexpected error
            logger.error(f"Unexpected error in {analyzer_name}: {e}", exc_info=True)
            error = AnalysisError(
                severity=ErrorSeverity.CRITICAL,
                analyzer=analyzer_name,
                message=f"Unexpected error: {str(e)}",
                exception=e,
                context={'symbol': context.symbol, 'timeframe': context.timeframe}
            )
            return AnalysisResult.fail(error)

    def _get_result_key(self) -> str:
        """
        Get the key used to store results in context.

        Override this in subclasses if needed.

        Returns:
            Result key (e.g., 'trend', 'momentum', etc.)
        """
        # Default: lowercase class name without 'Analyzer' suffix
        name = self.__class__.__name__
        if name.endswith('Analyzer'):
            name = name[:-8]  # Remove 'Analyzer'
        return name.lower()

    def _handle_error(
        self,
        context: 'AnalysisContext',
        error_message: str,
        exception: Optional[Exception] = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR
    ) -> None:
        """
        Standardized error handling for analyzers.

        Stores error result in context with consistent format.

        Args:
            context: AnalysisContext
            error_message: Error message
            exception: Original exception (if any)
            severity: Error severity
        """
        analyzer_name = self.__class__.__name__
        result_key = self._get_result_key()

        # Log error
        if exception:
            logger.error(f"Error in {analyzer_name}: {error_message}", exc_info=True)
        else:
            logger.error(f"Error in {analyzer_name}: {error_message}")

        # Store error result in context
        error_dict = {
            'status': 'error',
            'severity': severity.value,
            'message': error_message,
            'analyzer': analyzer_name
        }

        if exception:
            error_dict['exception_type'] = type(exception).__name__
            error_dict['exception_message'] = str(exception)

        context.add_result(result_key, error_dict)

    def get_threshold(
        self,
        param_name: str,
        default_value: Any,
        timeframe: str = None
    ) -> Any:
        """
        Get threshold value with per-timeframe support.

        This method checks for per-timeframe configuration first,
        then falls back to global configuration.

        Args:
            param_name: Parameter name (e.g., 'rsi_oversold', 'volume_high_ratio')
            default_value: Fallback default value
            timeframe: Current timeframe (e.g., '5m', '15m', '1h', '4h')

        Returns:
            Threshold value (per-TF if available, otherwise global or default)

        Example:
            # In MomentumAnalyzer:
            rsi_oversold = self.get_threshold('rsi_oversold', 30, '5m')
            # Returns 25 for 5m, 30 for 1h, 35 for 4h (if configured)

        Fallback chain:
            1. per_timeframe config (if enabled and TF exists)
            2. Analyzer-specific global config
            3. Default value
        """
        # Get analyzer type from class name
        # MomentumAnalyzer -> 'momentum', TrendAnalyzer -> 'trend'
        result_key = self._get_result_key()

        # Map short keys to full config keys
        config_key_map = {
            'sr': 'support_resistance',
            'htf': 'htf',
            'pattern': 'pattern',
            'harmonic': 'harmonic',
            'channel': 'channel',
            'cyclical': 'cyclical'
        }

        # Get actual config key
        config_key = config_key_map.get(result_key, result_key)

        # Get analyzer-specific config
        analyzer_config = self.config.get(config_key, {})

        if not analyzer_config:
            # Try alternative key (e.g., 'support_resistance' instead of 'sr')
            # This handles both ways
            for alt_key, full_key in config_key_map.items():
                if full_key == result_key:
                    analyzer_config = self.config.get(alt_key, {})
                    if analyzer_config:
                        break

        # Check per-timeframe config
        per_tf_config = analyzer_config.get('per_timeframe', {})

        if per_tf_config.get('enabled', False) and timeframe:
            # Per-TF is enabled, try to get TF-specific value
            tf_config = per_tf_config.get(timeframe, {})
            if tf_config and param_name in tf_config:
                logger.debug(
                    f"{self.__class__.__name__}: Using per-TF threshold "
                    f"{param_name}={tf_config[param_name]} for {timeframe}"
                )
                return tf_config[param_name]

        # Fallback to global analyzer config
        if param_name in analyzer_config:
            return analyzer_config[param_name]

        # Return default
        logger.debug(
            f"{self.__class__.__name__}: Using default threshold "
            f"{param_name}={default_value}"
        )
        return default_value

    def get_weight(self, timeframe: str = None) -> float:
        """
        Get analyzer weight with per-timeframe support.

        This method checks for per-timeframe analyzer weights first,
        then falls back to the analyzer's default weight.

        Args:
            timeframe: Current timeframe (e.g., '5m', '15m', '1h', '4h')

        Returns:
            Analyzer weight (per-TF if available, otherwise default weight)

        Example:
            # In TrendAnalyzer:
            weight = self.get_weight('5m')  # Returns 0.20 for 5m, 0.35 for 4h
        """
        # Check per-TF weights in scoring config
        scoring_config = self.config.get('scoring', {})
        per_tf_weights = scoring_config.get('analyzer_weights_per_timeframe', {})

        if per_tf_weights.get('enabled', False) and timeframe:
            # Per-TF weights enabled
            analyzer_name = self._get_result_key() + '_analyzer'
            tf_weights = per_tf_weights.get(timeframe, {})

            if analyzer_name in tf_weights:
                weight = tf_weights[analyzer_name]
                logger.debug(
                    f"{self.__class__.__name__}: Using per-TF weight "
                    f"{weight} for {timeframe}"
                )
                return weight

        # Fallback to analyzer's default weight
        analyzer_name = self._get_result_key() + '_analyzer'
        analyzer_config = self.config.get('analyzers', {}).get(analyzer_name, {})
        default_weight = analyzer_config.get('weight', 1.0)

        logger.debug(
            f"{self.__class__.__name__}: Using default weight {default_weight}"
        )
        return default_weight

    def __repr__(self) -> str:
        """String representation"""
        return f"{self.__class__.__name__}(enabled={self.enabled})"
