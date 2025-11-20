"""
Correlation Manager
Manages correlations between symbols for portfolio diversification and risk reduction.
"""

import logging
import json
import os
import time
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class CorrelationManager:
    """Manages correlations between symbols for portfolio diversification and risk reduction."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration."""
        self.config = config.get('correlation_management', {})
        self.enabled = self.config.get('enabled', True)
        self.data_file = self.config.get('data_file', 'data/correlation_data.json')
        self.correlation_threshold = self.config.get('correlation_threshold', 0.7)
        self.max_exposure_per_group = self.config.get('max_exposure_per_group', 3)
        self.update_interval = self.config.get('update_interval', 86400)  # 24 hours
        self.lookback_periods = self.config.get('lookback_periods', 100)

        # Data structures
        self.correlation_groups: Dict[str, List[str]] = {}
        self.correlation_matrix: Dict[str, Dict[str, float]] = {}
        self.last_update_time = 0
        self.active_positions: Dict[str, Dict[str, Any]] = {}

        # Load existing data
        self._load_data()

        logger.info(
            f"CorrelationManager initialized. "
            f"Enabled: {self.enabled}, "
            f"Correlation threshold: {self.correlation_threshold}"
        )

    def _load_data(self) -> None:
        """Load correlation data from file."""
        try:
            if not os.path.exists(self.data_file):
                logger.info(
                    f"Correlation data file not found: {self.data_file}, "
                    f"starting with empty data."
                )
                return

            with open(self.data_file, 'r') as f:
                data = json.load(f)

            self.correlation_matrix = data.get('correlation_matrix', {})
            self.correlation_groups = data.get('correlation_groups', {})
            self.last_update_time = data.get('last_update_time', 0)

            logger.info(
                f"Loaded correlation data: {len(self.correlation_matrix)} symbols, "
                f"{len(self.correlation_groups)} groups."
            )

        except Exception as e:
            logger.error(f"Error loading correlation data: {e}", exc_info=True)

    def save_data(self) -> None:
        """Save correlation data to file."""
        if not self.enabled:
            return

        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(os.path.abspath(self.data_file)), exist_ok=True)

            # Prepare data for saving
            data = {
                'correlation_matrix': self.correlation_matrix,
                'correlation_groups': self.correlation_groups,
                'last_update_time': self.last_update_time,
                'update_timestamp': datetime.now().isoformat()
            }

            # Save to file
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved correlation data to {self.data_file}")

        except Exception as e:
            logger.error(f"Error saving correlation data: {e}", exc_info=True)

    def update_correlations(self, symbols_data: Dict[str, pd.DataFrame]) -> None:
        """
        Update correlation matrix between symbols.

        Args:
            symbols_data: Dictionary of {symbol: DataFrame with OHLCV data}
        """
        if not self.enabled or len(symbols_data) < 2:
            return

        # Check if update is needed based on time
        current_time = time.time()
        if current_time - self.last_update_time < self.update_interval:
            logger.debug("Skipping correlation update, not enough time passed since last update.")
            return

        try:
            logger.info(f"Updating correlations for {len(symbols_data)} symbols...")

            # Extract closing prices
            symbol_prices = {}
            for symbol, df in symbols_data.items():
                if df is not None and len(df) >= self.lookback_periods:
                    symbol_prices[symbol] = df['close'].iloc[-self.lookback_periods:].values

            # Calculate correlation between all symbol pairs
            new_correlation_matrix = {}
            symbols = list(symbol_prices.keys())

            for i, symbol1 in enumerate(symbols):
                if symbol1 not in new_correlation_matrix:
                    new_correlation_matrix[symbol1] = {}

                prices1 = symbol_prices[symbol1]

                for j, symbol2 in enumerate(symbols[i:], i):
                    if symbol1 == symbol2:
                        new_correlation_matrix[symbol1][symbol2] = 1.0
                        continue

                    if symbol2 not in new_correlation_matrix:
                        new_correlation_matrix[symbol2] = {}

                    prices2 = symbol_prices[symbol2]

                    # Calculate correlation coefficient
                    try:
                        corr = np.corrcoef(prices1, prices2)[0, 1]

                        # Check for NaN
                        if np.isnan(corr):
                            corr = 0.0
                    except Exception:
                        corr = 0.0

                    # Store in matrix (symmetric)
                    new_correlation_matrix[symbol1][symbol2] = corr
                    new_correlation_matrix[symbol2][symbol1] = corr

            # Update main matrix
            self.correlation_matrix = new_correlation_matrix

            # Update correlation groups
            self._update_correlation_groups()

            # Update time
            self.last_update_time = current_time

            # Save data
            self.save_data()

            logger.info(
                f"Updated correlations for {len(new_correlation_matrix)} symbols "
                f"with {len(self.correlation_groups)} groups."
            )

        except Exception as e:
            logger.error(f"Error updating correlations: {e}", exc_info=True)

    def _update_correlation_groups(self) -> None:
        """Update correlation groups based on correlation matrix."""
        try:
            # Reset groups
            self.correlation_groups = {}

            # Get all symbols
            symbols = list(self.correlation_matrix.keys())
            if not symbols:
                return

            # Simple clustering algorithm
            group_id = 0
            ungrouped_symbols = set(symbols)

            while ungrouped_symbols:
                # Select a base symbol
                base_symbol = next(iter(ungrouped_symbols))
                current_group = [base_symbol]
                ungrouped_symbols.remove(base_symbol)

                # Find all symbols correlated with base symbol
                for symbol in list(ungrouped_symbols):
                    if (base_symbol in self.correlation_matrix and
                            symbol in self.correlation_matrix[base_symbol]):

                        corr = abs(self.correlation_matrix[base_symbol][symbol])

                        if corr >= self.correlation_threshold:
                            current_group.append(symbol)
                            ungrouped_symbols.remove(symbol)

                # Save group if it has more than one symbol
                if len(current_group) > 1:
                    self.correlation_groups[f"group_{group_id}"] = current_group
                    group_id += 1

        except Exception as e:
            logger.error(f"Error updating correlation groups: {e}", exc_info=True)

    def get_correlated_symbols(
            self,
            symbol: str,
            threshold: Optional[float] = None
    ) -> List[Tuple[str, float]]:
        """
        Get list of symbols correlated with a specific symbol.

        Args:
            symbol: Target symbol
            threshold: Correlation threshold (optional, uses default if None)

        Returns:
            List of (symbol, correlation) tuples, sorted by correlation magnitude
        """
        if not self.enabled or symbol not in self.correlation_matrix:
            return []

        try:
            corr_threshold = threshold if threshold is not None else self.correlation_threshold
            correlated = []

            for other_symbol, corr in self.correlation_matrix[symbol].items():
                if other_symbol != symbol and abs(corr) >= corr_threshold:
                    correlated.append((other_symbol, corr))

            # Sort by correlation magnitude (descending)
            return sorted(correlated, key=lambda x: abs(x[1]), reverse=True)

        except Exception as e:
            logger.error(f"Error getting correlated symbols for {symbol}: {e}", exc_info=True)
            return []

    def update_active_positions(self, positions: Dict[str, Dict[str, Any]]) -> None:
        """
        Update list of active positions.

        Args:
            positions: Dictionary of {symbol: position_info}
        """
        if not self.enabled:
            return

        self.active_positions = positions

    def get_correlation_safety_factor(self, symbol: str, direction: str) -> float:
        """
        Calculate correlation safety factor for a symbol given active positions.

        Args:
            symbol: Symbol to check
            direction: Direction ('long' or 'short')

        Returns:
            Safety factor (0.5 to 1.0), lower means higher risk
        """
        if not self.enabled or not self.active_positions:
            return 1.0

        try:
            # Find correlation group of symbol
            symbol_group = None
            for group_id, group_symbols in self.correlation_groups.items():
                if symbol in group_symbols:
                    symbol_group = group_id
                    break

            if not symbol_group:
                return 1.0  # Symbol is not in any correlation group

            # Check number of active positions in this group
            group_positions = 0

            for pos_symbol, pos_info in self.active_positions.items():
                # Check if position symbol is in correlation group
                if pos_symbol in self.correlation_groups.get(symbol_group, []):
                    # Check position direction
                    pos_direction = pos_info.get('direction', '')

                    # Positions with opposite direction are not dangerous
                    if direction == pos_direction:
                        group_positions += 1

            # Calculate safety factor based on number of active positions in group
            if group_positions >= self.max_exposure_per_group:
                return 0.5  # Substantial score reduction to prevent concentration risk
            elif group_positions > 0:
                # Gradual reduction based on position count
                return 1.0 - (0.5 * group_positions / self.max_exposure_per_group)

            return 1.0  # No other active positions in this group

        except Exception as e:
            logger.error(f"Error calculating correlation safety factor for {symbol}: {e}", exc_info=True)
            return 1.0

    def calculate_correlation_safety_factor(
            self,
            symbol: str,
            direction: str,
            active_positions: Dict[str, Dict[str, Any]]
    ) -> float:
        """
        Calculate correlation safety factor (backward compatibility method).

        Args:
            symbol: Symbol to check
            direction: Direction ('long' or 'short')
            active_positions: Dictionary of active positions

        Returns:
            Safety factor (0.5 to 1.0)
        """
        # Update active positions
        self.update_active_positions(active_positions)

        # Return safety factor
        return self.get_correlation_safety_factor(symbol, direction)