"""
AnalysisContext - Shared Memory Between Analyzers

This is the core context object that flows through the entire analysis pipeline.
It contains:
1. Symbol and timeframe information
2. DataFrame with OHLCV and calculated indicators
3. Results from each analyzer
4. Metadata about the analysis process

All analyzers read from and write to this context, enabling collaboration.
"""

import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AnalysisContext:
    """
    Context object for signal analysis.
    
    Holds all data and results for a single symbol/timeframe analysis.
    Enables analyzers to share data and build on each other's results.
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str,
        df: pd.DataFrame
    ):
        """
        Initialize AnalysisContext.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe string (e.g., '1h', '4h', '1d')
            df: DataFrame with OHLCV data
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.df = df.copy()  # Make a copy to avoid modifying original
        
        # Results from analyzers (e.g., {'trend': {...}, 'momentum': {...}})
        self.results: Dict[str, Any] = {}
        
        # Metadata about the analysis
        self.metadata: Dict[str, Any] = {
            'created_at': datetime.now(),
            'symbol': symbol,
            'timeframe': timeframe,
            'rows': len(df),
            'indicators_calculated': False
        }
        
        # Statistics
        self._stats = {
            'analyzers_run': 0,
            'analyzers_failed': 0
        }
        
        logger.debug(
            f"AnalysisContext created for {symbol} {timeframe} "
            f"with {len(df)} rows"
        )
    
    def add_result(self, analyzer_name: str, result: Dict[str, Any]) -> None:
        """
        Store result from an analyzer.
        
        Args:
            analyzer_name: Name of the analyzer (e.g., 'trend', 'momentum')
            result: Dictionary with analyzer results
        """
        self.results[analyzer_name] = result
        self._stats['analyzers_run'] += 1
        
        if result.get('status') == 'error':
            self._stats['analyzers_failed'] += 1
        
        logger.debug(
            f"Result added from {analyzer_name} for {self.symbol}: "
            f"status={result.get('status', 'unknown')}"
        )
    
    def get_result(self, analyzer_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve result from an analyzer.
        
        Args:
            analyzer_name: Name of the analyzer
            
        Returns:
            Result dictionary, or None if not found
        """
        return self.results.get(analyzer_name)
    
    def has_result(self, analyzer_name: str) -> bool:
        """
        Check if result exists for an analyzer.
        
        Args:
            analyzer_name: Name of the analyzer
            
        Returns:
            True if result exists, False otherwise
        """
        return analyzer_name in self.results
    
    def get_all_results(self) -> Dict[str, Any]:
        """
        Get all analyzer results.
        
        Returns:
            Dictionary of all results
        """
        return self.results.copy()
    
    def update_metadata(self, key: str, value: Any) -> None:
        """
        Update metadata.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
    
    def get_metadata(self, key: str) -> Optional[Any]:
        """
        Get metadata value.
        
        Args:
            key: Metadata key
            
        Returns:
            Metadata value, or None if not found
        """
        return self.metadata.get(key)
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get analysis statistics.
        
        Returns:
            Dictionary with statistics
        """
        return self._stats.copy()
    
    def __repr__(self) -> str:
        """String representation"""
        return (
            f"AnalysisContext(symbol='{self.symbol}', "
            f"timeframe='{self.timeframe}', "
            f"rows={len(self.df)}, "
            f"results={len(self.results)})"
        )
