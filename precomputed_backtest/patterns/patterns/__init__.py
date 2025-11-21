"""
Patterns Module - Pattern Detection System

This module provides pattern detection functionality for both
candlestick and chart patterns.

Components:
- BasePattern: Abstract base class for all patterns
- PatternOrchestrator: Main coordinator for pattern detection
- Candlestick patterns: Individual candlestick pattern detectors
- Chart patterns: Individual chart pattern detectors
"""

from signal_generation.analyzers.patterns.base_pattern import BasePattern
from signal_generation.analyzers.patterns.pattern_orchestrator import PatternOrchestrator

__all__ = [
    'BasePattern',
    'PatternOrchestrator',
]
