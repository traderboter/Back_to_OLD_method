"""
SignalInfo - Trading Signal Data Structure

Complete trading signal with all necessary information for execution.

Contains:
- Symbol and direction
- Entry, stop loss, take profit levels
- Position sizing
- Risk/reward metrics
- Analysis metadata
- Status tracking
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import uuid4
import logging

from signal_generation.signal_score import SignalScore

logger = logging.getLogger(__name__)


@dataclass
class SignalInfo:
    """
    Complete trading signal information.
    
    This is the final output of signal generation process.
    Contains everything needed to execute a trade.
    """
    
    # === Identification ===
    signal_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now())
    
    # === Symbol and Timeframe ===
    symbol: str = ''
    timeframe: str = ''
    
    # === Direction ===
    direction: str = ''  # 'LONG' or 'SHORT'
    
    # === Price Levels ===
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    take_profit_2: Optional[float] = None  # Optional second target
    take_profit_3: Optional[float] = None  # Optional third target
    
    # === Risk Management ===
    risk_reward_ratio: float = 0.0
    risk_amount: float = 0.0          # Distance to stop loss
    reward_amount: float = 0.0        # Distance to take profit
    position_size_percent: float = 0.0  # Suggested position size (% of capital)
    
    # === Scoring ===
    score: Optional[SignalScore] = None
    confidence: float = 0.0           # 0-1
    
    # === Analysis Metadata ===
    analysis_summary: Dict[str, Any] = field(default_factory=dict)
    contributing_analyzers: List[str] = field(default_factory=list)
    key_factors: List[str] = field(default_factory=list)  # Top reasons for signal
    
    # === Validation Info ===
    validation_passed: bool = False
    validation_checks: Dict[str, bool] = field(default_factory=dict)
    rejection_reasons: List[str] = field(default_factory=list)
    
    # === Status ===
    status: str = 'pending'  # 'pending', 'active', 'filled', 'cancelled', 'expired'
    
    # === Additional Info ===
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # === Context ===
    market_context: Dict[str, Any] = field(default_factory=dict)  # Market conditions at signal time

    # 🆕 === Detailed Analysis Metadata (for backtest analysis) ===
    metadata: Dict[str, Any] = field(default_factory=dict)  # Complete analysis details
    
    def calculate_risk_reward(self) -> float:
        """
        Calculate risk/reward ratio.
        
        Returns:
            Risk/reward ratio
        """
        if self.entry_price == 0 or self.stop_loss == 0 or self.take_profit == 0:
            return 0.0
        
        # Calculate risk (entry to stop loss)
        self.risk_amount = abs(self.entry_price - self.stop_loss)
        
        # Calculate reward (entry to take profit)
        self.reward_amount = abs(self.take_profit - self.entry_price)
        
        # Calculate ratio
        if self.risk_amount > 0:
            self.risk_reward_ratio = self.reward_amount / self.risk_amount
        else:
            self.risk_reward_ratio = 0.0
        
        return self.risk_reward_ratio
    
    def validate_prices(self) -> bool:
        """
        Validate price levels are logical.
        
        Returns:
            True if prices are valid
        """
        if self.entry_price <= 0:
            return False
        
        if self.stop_loss <= 0:
            return False
        
        if self.take_profit <= 0:
            return False
        
        # For LONG: SL < Entry < TP
        if self.direction == 'LONG':
            if not (self.stop_loss < self.entry_price < self.take_profit):
                return False
        
        # For SHORT: TP < Entry < SL
        elif self.direction == 'SHORT':
            if not (self.take_profit < self.entry_price < self.stop_loss):
                return False
        else:
            return False
        
        return True
    
    def add_validation_check(self, check_name: str, passed: bool, reason: str = '') -> None:
        """
        Add validation check result.
        
        Args:
            check_name: Name of the check
            passed: Whether check passed
            reason: Reason if failed
        """
        self.validation_checks[check_name] = passed
        
        if not passed and reason:
            self.rejection_reasons.append(f"{check_name}: {reason}")
    
    def mark_as_valid(self) -> None:
        """Mark signal as validated and ready."""
        self.validation_passed = True
        self.status = 'pending'
    
    def mark_as_invalid(self, reason: str = '') -> None:
        """Mark signal as invalid."""
        self.validation_passed = False
        self.status = 'rejected'
        if reason:
            self.rejection_reasons.append(reason)
    
    def add_key_factor(self, factor: str) -> None:
        """
        Add key factor that contributed to signal.
        
        Args:
            factor: Description of key factor
        """
        if factor not in self.key_factors:
            self.key_factors.append(factor)
    
    def get_summary(self) -> str:
        """
        Get human-readable signal summary.
        
        Returns:
            Signal summary string
        """
        summary = (
            f"Signal {self.signal_id[:8]}\n"
            f"Symbol: {self.symbol} ({self.timeframe})\n"
            f"Direction: {self.direction}\n"
            f"Entry: {self.entry_price:.2f}\n"
            f"Stop Loss: {self.stop_loss:.2f}\n"
            f"Take Profit: {self.take_profit:.2f}\n"
            f"Risk/Reward: {self.risk_reward_ratio:.2f}\n"
            f"Position Size: {self.position_size_percent:.1f}%\n"
        )
        
        if self.score:
            summary += (
                f"Score: {self.score.final_score:.2f}\n"
                f"Confidence: {self.confidence:.2f}\n"
            )
        
        summary += f"Status: {self.status}\n"
        
        if self.key_factors:
            summary += "Key Factors:\n"
            for factor in self.key_factors[:3]:  # Top 3
                summary += f"  - {factor}\n"
        
        return summary
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        data = asdict(self)
        
        # Convert datetime to ISO string
        if isinstance(data.get('timestamp'), datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        
        # Convert score to dict if exists
        if self.score:
            data['score'] = self.score.to_dict()
        
        return data
    
    def __str__(self) -> str:
        """String representation for logging."""
        return (
            f"Signal({self.symbol} {self.direction} @ {self.entry_price:.2f}, "
            f"Score={self.score.final_score if self.score else 0:.1f}, "
            f"RR={self.risk_reward_ratio:.2f})"
        )
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return self.__str__()


@dataclass
class SignalRejection:
    """
    Information about rejected signal.
    
    Used for tracking why signals are rejected.
    """
    
    symbol: str
    timeframe: str
    direction: str
    timestamp: datetime = field(default_factory=lambda: datetime.now())
    
    # Rejection info
    rejection_reason: str = ''
    failed_checks: List[str] = field(default_factory=list)
    
    # Partial scores (if calculated)
    base_score: Optional[float] = None
    final_score: Optional[float] = None
    
    # Context
    market_context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        if isinstance(data.get('timestamp'), datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        return data
    
    def __str__(self) -> str:
        """String representation."""
        return (
            f"SignalRejection({self.symbol} {self.direction}, "
            f"reason={self.rejection_reason})"
        )
