"""
Pattern Orchestrator - Coordinates all pattern detection

This orchestrator manages the detection of all patterns (candlestick and chart).
It loads pattern detectors dynamically and coordinates their execution.
"""

from typing import Dict, Any, List, Optional, Type
import pandas as pd
import logging
from pathlib import Path
import importlib
import inspect

from signal_generation.analyzers.patterns.base_pattern import BasePattern

logger = logging.getLogger(__name__)


class PatternOrchestrator:
    """
    Orchestrator for pattern detection.

    Responsibilities:
    1. Load all available pattern detectors
    2. Execute pattern detection for each pattern
    3. Collect and aggregate results
    4. Provide unified interface for pattern detection

    Key features:
    - Dynamic pattern loading
    - Parallel detection support (future)
    - Filtering by pattern type
    - Context-aware scoring
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize PatternOrchestrator.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Pattern detectors
        self.candlestick_patterns: Dict[str, BasePattern] = {}
        self.chart_patterns: Dict[str, BasePattern] = {}

        # Settings
        self.enabled_candlestick = self.config.get('patterns', {}).get('candlestick_enabled', True)
        self.enabled_chart = self.config.get('patterns', {}).get('chart_enabled', True)
        self.min_strength = self.config.get('patterns', {}).get('min_strength', 1)

        # Statistics
        self.stats = {
            'total_detections': 0,
            'candlestick_detections': 0,
            'chart_detections': 0
        }

        # Load patterns
        self._load_patterns()

        logger.info(
            f"PatternOrchestrator initialized: "
            f"{len(self.candlestick_patterns)} candlestick patterns, "
            f"{len(self.chart_patterns)} chart patterns"
        )

    def _load_patterns(self):
        """Load all available pattern detectors."""
        # For now, we'll use a manual registry
        # Later, we can add dynamic loading from directories

        # This will be populated as we implement each pattern
        # For now, it's empty
        logger.debug("Pattern loading completed (registry empty - to be populated)")

    def register_pattern(self, pattern_class_or_instance):
        """
        Register a pattern detector.

        Args:
            pattern_class_or_instance: Pattern class or instance to register
                                      If a class is provided, it will be instantiated with self.config
                                      If an instance is provided, it will be used directly
        """
        try:
            # Check if it's already an instance or a class
            if isinstance(pattern_class_or_instance, BasePattern):
                # It's already an instance, use it directly
                pattern = pattern_class_or_instance
            else:
                # It's a class, instantiate it with config
                pattern = pattern_class_or_instance(self.config)

            # Add to appropriate registry
            if pattern.pattern_type == 'candlestick':
                self.candlestick_patterns[pattern.name] = pattern
                logger.debug(f"Registered candlestick pattern: {pattern.name}")
            elif pattern.pattern_type == 'chart':
                self.chart_patterns[pattern.name] = pattern
                logger.debug(f"Registered chart pattern: {pattern.name}")
            else:
                logger.warning(f"Unknown pattern type: {pattern.pattern_type}")

        except Exception as e:
            pattern_name = getattr(pattern_class_or_instance, '__name__', str(pattern_class_or_instance))
            logger.error(f"Error registering pattern {pattern_name}: {e}")

    def detect_all_patterns(
        self,
        df: pd.DataFrame,
        timeframe: str = '1h',
        context: Optional[Dict[str, Any]] = None,
        pattern_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect all patterns in the data.

        Args:
            df: DataFrame with OHLCV data
            timeframe: Timeframe string
            context: Optional context for context-aware scoring
            pattern_types: Optional filter for pattern types
                          (e.g., ['candlestick'], ['chart'], or both)

        Returns:
            List of detected patterns with their information
        """
        detected_patterns = []

        # Determine which pattern types to check
        check_candlestick = (
            self.enabled_candlestick and
            (pattern_types is None or 'candlestick' in pattern_types)
        )
        check_chart = (
            self.enabled_chart and
            (pattern_types is None or 'chart' in pattern_types)
        )

        # Detect candlestick patterns
        if check_candlestick:
            candlestick_results = self._detect_candlestick_patterns(
                df, timeframe, context
            )
            detected_patterns.extend(candlestick_results)
            self.stats['candlestick_detections'] += len(candlestick_results)

        # Detect chart patterns
        if check_chart:
            chart_results = self._detect_chart_patterns(
                df, timeframe, context
            )
            detected_patterns.extend(chart_results)
            self.stats['chart_detections'] += len(chart_results)

        # Update total stats
        self.stats['total_detections'] += len(detected_patterns)

        # Filter by minimum strength
        detected_patterns = [
            p for p in detected_patterns
            if p['base_strength'] >= self.min_strength
        ]

        logger.debug(
            f"Pattern detection completed: {len(detected_patterns)} patterns found "
            f"(candlestick={self.stats['candlestick_detections']}, "
            f"chart={self.stats['chart_detections']})"
        )

        return detected_patterns

    def _detect_candlestick_patterns(
        self,
        df: pd.DataFrame,
        timeframe: str,
        context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect all candlestick patterns.

        Args:
            df: DataFrame with OHLCV data
            timeframe: Timeframe string
            context: Optional context

        Returns:
            List of detected candlestick patterns
        """
        detected = []

        for pattern_name, pattern_detector in self.candlestick_patterns.items():
            try:
                pattern_info = pattern_detector.get_pattern_info(
                    df, timeframe, context
                )

                if pattern_info:
                    detected.append(pattern_info)
                    logger.debug(f"Detected candlestick pattern: {pattern_name}")

            except Exception as e:
                logger.error(
                    f"Error detecting candlestick pattern {pattern_name}: {e}",
                    exc_info=True
                )

        return detected

    def _detect_chart_patterns(
        self,
        df: pd.DataFrame,
        timeframe: str,
        context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect all chart patterns.

        Args:
            df: DataFrame with OHLCV data
            timeframe: Timeframe string
            context: Optional context

        Returns:
            List of detected chart patterns
        """
        detected = []

        for pattern_name, pattern_detector in self.chart_patterns.items():
            try:
                pattern_info = pattern_detector.get_pattern_info(
                    df, timeframe, context
                )

                if pattern_info:
                    detected.append(pattern_info)
                    logger.debug(f"Detected chart pattern: {pattern_name}")

            except Exception as e:
                logger.error(
                    f"Error detecting chart pattern {pattern_name}: {e}",
                    exc_info=True
                )

        return detected

    def get_pattern_by_name(self, name: str) -> Optional[BasePattern]:
        """
        Get a specific pattern detector by name.

        Args:
            name: Pattern name

        Returns:
            Pattern detector if found, None otherwise
        """
        # Check candlestick patterns
        if name in self.candlestick_patterns:
            return self.candlestick_patterns[name]

        # Check chart patterns
        if name in self.chart_patterns:
            return self.chart_patterns[name]

        return None

    def get_available_patterns(self) -> Dict[str, List[str]]:
        """
        Get list of all available patterns.

        Returns:
            Dictionary with 'candlestick' and 'chart' keys
        """
        return {
            'candlestick': list(self.candlestick_patterns.keys()),
            'chart': list(self.chart_patterns.keys())
        }

    def get_stats(self) -> Dict[str, int]:
        """
        Get detection statistics.

        Returns:
            Dictionary with statistics
        """
        return self.stats.copy()

    def reset_stats(self):
        """Reset detection statistics."""
        self.stats = {
            'total_detections': 0,
            'candlestick_detections': 0,
            'chart_detections': 0
        }
        logger.debug("Pattern detection stats reset")

    def __str__(self) -> str:
        """String representation."""
        return (
            f"PatternOrchestrator("
            f"candlestick={len(self.candlestick_patterns)}, "
            f"chart={len(self.chart_patterns)})"
        )
