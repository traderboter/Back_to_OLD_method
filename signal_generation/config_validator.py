"""
Config Validator - Validates configuration files to prevent invalid values

This validator checks configuration values to ensure they are within acceptable
ranges and have correct types, preventing silent bugs from typos or mistakes.
"""

from typing import Dict, Any, List, Optional, Tuple, Union
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Configuration validation error."""
    pass


class ConfigValidator:
    """
    Validates configuration dictionaries.

    Checks:
    - Required sections exist
    - Values are within valid ranges
    - Types are correct
    - Logical constraints (e.g., high > low)
    """

    def __init__(self):
        """Initialize validator with validation rules."""
        self.validation_rules = self._build_validation_rules()
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate(self, config: Dict[str, Any], strict: bool = False) -> Tuple[bool, List[str], List[str]]:
        """
        Validate configuration.

        Args:
            config: Configuration dictionary
            strict: If True, warnings are treated as errors

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []

        try:
            # Validate each section
            self._validate_volatility(config)
            self._validate_signal_processing(config)
            self._validate_risk_management(config)
            self._validate_circuit_breaker(config)
            self._validate_correlation(config)

            # Check if valid
            is_valid = len(self.errors) == 0
            if strict and len(self.warnings) > 0:
                is_valid = False

            return is_valid, self.errors, self.warnings

        except Exception as e:
            self.errors.append(f"Validation failed: {str(e)}")
            return False, self.errors, self.warnings

    def _validate_volatility(self, config: Dict[str, Any]) -> None:
        """Validate volatility analyzer configuration."""
        vol_config = config.get('signal_processing', {}).get('analyzers', {}).get('volatility', {})

        if not vol_config:
            self.warnings.append("Volatility config not found, using defaults")
            return

        # Validate thresholds
        low = vol_config.get('low_vol_threshold')
        high = vol_config.get('high_vol_threshold')
        extreme = vol_config.get('extreme_vol_threshold')

        if low is not None:
            if not isinstance(low, (int, float)):
                self.errors.append(f"low_vol_threshold must be numeric, got {type(low).__name__}")
            elif low <= 0 or low >= 5.0:
                self.errors.append(f"low_vol_threshold must be between 0 and 5.0, got {low}")

        if high is not None:
            if not isinstance(high, (int, float)):
                self.errors.append(f"high_vol_threshold must be numeric, got {type(high).__name__}")
            elif high <= 0 or high >= 10.0:
                self.errors.append(f"high_vol_threshold must be between 0 and 10.0, got {high}")

        if extreme is not None:
            if not isinstance(extreme, (int, float)):
                self.errors.append(f"extreme_vol_threshold must be numeric, got {type(extreme).__name__}")
            elif extreme <= 0 or extreme >= 15.0:
                self.errors.append(f"extreme_vol_threshold must be between 0 and 15.0, got {extreme}")

        # Logical constraints
        if low is not None and high is not None:
            if high <= low:
                self.errors.append(
                    f"high_vol_threshold ({high}) must be > low_vol_threshold ({low})"
                )

        if high is not None and extreme is not None:
            if extreme <= high:
                self.errors.append(
                    f"extreme_vol_threshold ({extreme}) must be > high_vol_threshold ({high})"
                )

        # Validate risk multipliers
        risk_mults = vol_config.get('risk_multipliers', {})
        if risk_mults:
            for regime, multiplier in risk_mults.items():
                if regime not in ['low', 'normal', 'high']:
                    self.warnings.append(f"Unknown volatility regime: {regime}")

                if not isinstance(multiplier, (int, float)):
                    self.errors.append(
                        f"risk_multipliers.{regime} must be numeric, got {type(multiplier).__name__}"
                    )
                elif multiplier < 0.1 or multiplier > 3.0:
                    self.errors.append(
                        f"risk_multipliers.{regime} must be between 0.1 and 3.0, got {multiplier}"
                    )

    def _validate_signal_processing(self, config: Dict[str, Any]) -> None:
        """Validate signal processing configuration."""
        sp_config = config.get('signal_processing', {})

        if not sp_config:
            self.errors.append("signal_processing section is required")
            return

        # Validate validation section
        val_config = sp_config.get('validation', {})

        min_score = val_config.get('min_signal_score')
        if min_score is not None:
            if not isinstance(min_score, (int, float)):
                self.errors.append(f"min_signal_score must be numeric, got {type(min_score).__name__}")
            elif min_score < 0 or min_score > 200:
                self.errors.append(f"min_signal_score must be between 0 and 200, got {min_score}")

        strong_threshold = val_config.get('strong_signal_threshold')
        if strong_threshold is not None and min_score is not None:
            if strong_threshold < min_score:
                self.warnings.append(
                    f"strong_signal_threshold ({strong_threshold}) is less than "
                    f"min_signal_score ({min_score})"
                )

    def _validate_risk_management(self, config: Dict[str, Any]) -> None:
        """Validate risk management configuration."""
        risk_config = config.get('risk_management', {})

        if not risk_config:
            self.warnings.append("risk_management config not found")
            return

        # Validate risk percentages
        max_risk = risk_config.get('max_risk_per_trade_percent')
        if max_risk is not None:
            if not isinstance(max_risk, (int, float)):
                self.errors.append(f"max_risk_per_trade_percent must be numeric")
            elif max_risk <= 0 or max_risk > 10:
                self.errors.append(
                    f"max_risk_per_trade_percent must be between 0 and 10, got {max_risk}"
                )

        # Validate RR ratios
        min_rr = risk_config.get('min_risk_reward_ratio')
        if min_rr is not None:
            if not isinstance(min_rr, (int, float)):
                self.errors.append(f"min_risk_reward_ratio must be numeric")
            elif min_rr < 0.5 or min_rr > 10:
                self.errors.append(
                    f"min_risk_reward_ratio must be between 0.5 and 10, got {min_rr}"
                )

    def _validate_circuit_breaker(self, config: Dict[str, Any]) -> None:
        """Validate circuit breaker configuration."""
        cb_config = config.get('circuit_breaker', {})

        if not cb_config:
            self.warnings.append("circuit_breaker config not found")
            return

        max_consecutive = cb_config.get('max_consecutive_losses')
        if max_consecutive is not None:
            if not isinstance(max_consecutive, int):
                self.errors.append(f"max_consecutive_losses must be integer")
            elif max_consecutive < 1 or max_consecutive > 20:
                self.errors.append(
                    f"max_consecutive_losses must be between 1 and 20, got {max_consecutive}"
                )

        max_daily_loss = cb_config.get('max_daily_losses_r')
        if max_daily_loss is not None:
            if not isinstance(max_daily_loss, (int, float)):
                self.errors.append(f"max_daily_losses_r must be numeric")
            elif max_daily_loss < 1 or max_daily_loss > 50:
                self.errors.append(
                    f"max_daily_losses_r must be between 1 and 50, got {max_daily_loss}"
                )

    def _validate_correlation(self, config: Dict[str, Any]) -> None:
        """Validate correlation manager configuration."""
        corr_config = config.get('correlation_management', {})

        if not corr_config:
            self.warnings.append("correlation_management config not found")
            return

        threshold = corr_config.get('correlation_threshold')
        if threshold is not None:
            if not isinstance(threshold, (int, float)):
                self.errors.append(f"correlation_threshold must be numeric")
            elif threshold < 0 or threshold > 1.0:
                self.errors.append(
                    f"correlation_threshold must be between 0 and 1.0, got {threshold}"
                )

        max_exposure = corr_config.get('max_exposure_per_group')
        if max_exposure is not None:
            if not isinstance(max_exposure, int):
                self.errors.append(f"max_exposure_per_group must be integer")
            elif max_exposure < 1 or max_exposure > 20:
                self.errors.append(
                    f"max_exposure_per_group must be between 1 and 20, got {max_exposure}"
                )

    def _build_validation_rules(self) -> Dict[str, Any]:
        """Build validation rules (for future extension)."""
        return {
            'volatility': {
                'low_vol_threshold': {'type': float, 'range': (0.0, 5.0)},
                'high_vol_threshold': {'type': float, 'range': (0.0, 10.0)},
                'extreme_vol_threshold': {'type': float, 'range': (0.0, 15.0)},
            },
            'signal_processing': {
                'min_signal_score': {'type': float, 'range': (0, 200)},
            },
        }

    def print_report(self) -> None:
        """Print validation report."""
        if self.errors:
            logger.error("❌ Configuration Validation Errors:")
            for i, error in enumerate(self.errors, 1):
                logger.error(f"  {i}. {error}")

        if self.warnings:
            logger.warning("⚠️  Configuration Validation Warnings:")
            for i, warning in enumerate(self.warnings, 1):
                logger.warning(f"  {i}. {warning}")

        if not self.errors and not self.warnings:
            logger.info("✅ Configuration validation passed")


def validate_config(config: Dict[str, Any], strict: bool = False) -> bool:
    """
    Validate configuration and log results.

    Args:
        config: Configuration dictionary
        strict: If True, warnings are treated as errors

    Returns:
        True if valid, False otherwise
    """
    validator = ConfigValidator()
    is_valid, errors, warnings = validator.validate(config, strict=strict)

    validator.print_report()

    if not is_valid:
        raise ValidationError(
            f"Configuration validation failed with {len(errors)} error(s) "
            f"and {len(warnings)} warning(s)"
        )

    return is_valid
