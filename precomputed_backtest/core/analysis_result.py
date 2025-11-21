"""
Analysis Result - Unified result type for all analyzers

Provides consistent error handling and result reporting across all analyzers.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, TypeVar, Generic
from enum import Enum

T = TypeVar('T')


class ErrorSeverity(Enum):
    """Error severity levels."""
    WARNING = 'warning'    # Can continue, degraded functionality
    ERROR = 'error'        # Cannot continue with this analyzer
    CRITICAL = 'critical'  # Must stop immediately


@dataclass
class AnalysisError:
    """
    Analysis error details.

    Attributes:
        severity: Error severity level
        analyzer: Name of analyzer that failed
        message: Human-readable error message
        exception: Original exception (if any)
        context: Additional context (symbol, timeframe, etc.)
    """
    severity: ErrorSeverity
    analyzer: str
    message: str
    exception: Optional[Exception] = None
    context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        result = {
            'severity': self.severity.value,
            'analyzer': self.analyzer,
            'message': self.message,
        }

        if self.exception:
            result['exception_type'] = type(self.exception).__name__
            result['exception_message'] = str(self.exception)

        if self.context:
            result['context'] = self.context

        return result


@dataclass
class AnalysisResult(Generic[T]):
    """
    Generic result type for analysis operations.

    Provides unified interface for success/failure with proper typing.

    Attributes:
        success: Whether analysis succeeded
        data: Analysis data (if successful)
        error: Error details (if failed)

    Example:
        >>> result = AnalysisResult.ok({'trend': 'bullish', 'strength': 0.8})
        >>> if result.success:
        ...     print(result.data)
        ...
        >>> result = AnalysisResult.fail(AnalysisError(...))
        >>> if not result.success:
        ...     print(result.error.message)
    """
    success: bool
    data: Optional[T]
    error: Optional[AnalysisError]

    @classmethod
    def ok(cls, data: T) -> 'AnalysisResult[T]':
        """
        Create successful result.

        Args:
            data: Analysis data

        Returns:
            AnalysisResult with success=True
        """
        return cls(success=True, data=data, error=None)

    @classmethod
    def fail(cls, error: AnalysisError) -> 'AnalysisResult[T]':
        """
        Create failed result.

        Args:
            error: Error details

        Returns:
            AnalysisResult with success=False
        """
        return cls(success=False, data=None, error=error)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], analyzer: str) -> 'AnalysisResult[Dict[str, Any]]':
        """
        Create AnalysisResult from analyzer's dictionary output.

        This helps convert old-style dict returns to new AnalysisResult.

        Args:
            data: Dictionary from analyzer
            analyzer: Analyzer name

        Returns:
            AnalysisResult
        """
        if isinstance(data, dict) and data.get('status') == 'error':
            # Old-style error dict
            error = AnalysisError(
                severity=ErrorSeverity.ERROR,
                analyzer=analyzer,
                message=data.get('message', 'Unknown error'),
                context={'error_data': data}
            )
            return cls.fail(error)
        else:
            # Success
            return cls.ok(data)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary (backward compatibility).

        Returns standard format: {'status': 'ok'/'error', ...}
        """
        if self.success:
            return {
                'status': 'ok',
                'data': self.data
            }
        else:
            error_dict = self.error.to_dict() if self.error else {}
            return {
                'status': 'error',
                'severity': error_dict.get('severity', 'error'),
                'message': error_dict.get('message', 'Unknown error'),
                **error_dict
            }

    def unwrap(self) -> T:
        """
        Unwrap the result or raise exception.

        Returns:
            Data if successful

        Raises:
            RuntimeError: If result is not successful
        """
        if self.success:
            return self.data
        else:
            raise RuntimeError(
                f"Cannot unwrap failed result: {self.error.message if self.error else 'Unknown error'}"
            )

    def unwrap_or(self, default: T) -> T:
        """
        Unwrap the result or return default.

        Args:
            default: Default value if failed

        Returns:
            Data if successful, default otherwise
        """
        return self.data if self.success else default

    def map(self, func):
        """
        Map function over successful result.

        Args:
            func: Function to apply to data

        Returns:
            New AnalysisResult with transformed data
        """
        if self.success:
            try:
                new_data = func(self.data)
                return AnalysisResult.ok(new_data)
            except Exception as e:
                error = AnalysisError(
                    severity=ErrorSeverity.ERROR,
                    analyzer='map',
                    message=f"Map function failed: {e}",
                    exception=e
                )
                return AnalysisResult.fail(error)
        else:
            return self
