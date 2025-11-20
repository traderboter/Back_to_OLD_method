"""
SignalScore - Signal Scoring Data Structure

Holds comprehensive scoring information for a trading signal.
Includes base score, weighted components, bonuses, and final score.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class SignalScore:
    """
    Comprehensive signal scoring structure.
    
    Contains all scoring components:
    - Base scores from each analyzer
    - Weighted scores
    - Bonuses (confluence, HTF alignment)
    - Multipliers (timeframe, volatility)
    - Final score
    """
    
    # Base scores (0-100 each)
    trend_score: float = 0.0
    momentum_score: float = 0.0
    volume_score: float = 0.0
    pattern_score: float = 0.0
    sr_score: float = 0.0
    volatility_score: float = 0.0
    harmonic_score: float = 0.0
    channel_score: float = 0.0
    cyclical_score: float = 0.0
    htf_score: float = 0.0
    
    # Weighted scores (after applying weights)
    weighted_trend: float = 0.0
    weighted_momentum: float = 0.0
    weighted_volume: float = 0.0
    weighted_pattern: float = 0.0
    weighted_sr: float = 0.0
    weighted_volatility: float = 0.0
    weighted_harmonic: float = 0.0
    weighted_channel: float = 0.0
    weighted_cyclical: float = 0.0
    weighted_htf: float = 0.0
    
    # Aggregate scores
    base_score: float = 0.0              # Sum of weighted scores
    
    # Bonuses and multipliers (OLD SYSTEM - 13 multipliers)
    confluence_bonus: float = 0.0               # 0-0.5 (RR-based همگرایی)
    timeframe_weight: float = 1.0               # 0.7-1.2 (وزن تایم‌فریم)
    trend_alignment: float = 1.0                # 0.8-1.2 (همراستایی روند)
    volume_confirmation: float = 1.0            # 1.0-1.4 (تأیید حجم)
    pattern_quality: float = 1.0                # 1.0-1.5 (کیفیت الگو)
    symbol_performance_factor: float = 1.0      # 0.8-1.3 (Adaptive Learning)
    correlation_safety_factor: float = 1.0      # 0.5-1.0 (ایمنی همبستگی)
    macd_analysis_score: float = 1.0            # 0.85-1.15 (تحلیل MACD)
    structure_score: float = 1.0                # 0.8-1.2 (HTF structure)
    volatility_multiplier: float = 1.0          # 0.5-1.0 (تنظیم نوسان)
    harmonic_multiplier: float = 1.0            # 1.0-1.2 (ضریب هارمونیک)
    channel_multiplier: float = 1.0             # 1.0-1.1 (ضریب کانال)
    cyclical_multiplier: float = 1.0            # 1.0-1.1 (ضریب چرخه‌ای)

    # Final score
    final_score: float = 0.0             # امتیاز نهایی (unlimited - OLD SYSTEM)
    
    # Metadata
    confidence: float = 0.5              # اطمینان (0-1)
    signal_strength: str = 'weak'        # 'weak', 'medium', 'strong'
    contributing_analyzers: List[str] = field(default_factory=list)
    aligned_analyzers: int = 0

    # ✨ جزئیات الگوهای تشخیص داده شده
    detected_patterns: List[Dict[str, Any]] = field(default_factory=list)
    pattern_contributions: Dict[str, float] = field(default_factory=dict)  # هر الگو چقدر به امتیاز کمک کرد

    # ✨ جزئیات confluence (ترکیب Alignment + RR)
    confluence_details: Dict[str, Any] = field(default_factory=dict)

    # Scoring breakdown for debugging
    breakdown: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_final_score(self, max_score: float = 0.0) -> float:
        """
        Calculate final score from all components using OLD SYSTEM method.

        Args:
            max_score: Maximum final score (0 = unlimited, default for OLD system)

        Formula: 13 multipliers (OLD SYSTEM)
        - base_score
        - confluence_bonus (RR-based)
        - timeframe_weight
        - trend_alignment
        - volume_confirmation
        - pattern_quality
        - symbol_performance_factor (Adaptive Learning)
        - correlation_safety_factor
        - macd_analysis_score
        - structure_score (HTF structure)
        - volatility_multiplier
        - harmonic_multiplier
        - channel_multiplier
        - cyclical_multiplier

        Returns:
            Final score
        """
        # OLD SYSTEM (13 multipliers)
        self.final_score = (
            self.base_score
            * (1.0 + self.confluence_bonus)       # 0-0.5 (RR-based)
            * self.timeframe_weight                # 0.7-1.2
            * self.trend_alignment                 # 0.8-1.2
            * self.volume_confirmation             # 1.0-1.4
            * self.pattern_quality                 # 1.0-1.5
            * self.symbol_performance_factor       # 0.8-1.3 (Adaptive Learning)
            * self.correlation_safety_factor       # 0.5-1.0
            * self.macd_analysis_score             # 0.85-1.15
            * self.structure_score                 # 0.8-1.2 (HTF structure)
            * self.volatility_multiplier           # 0.5-1.0
            * self.harmonic_multiplier             # 1.0-1.2
            * self.channel_multiplier              # 1.0-1.1
            * self.cyclical_multiplier             # 1.0-1.1
        )

        # Apply max_score limit (0 = unlimited, default for OLD system)
        if max_score > 0:
            self.final_score = max(0.0, min(self.final_score, max_score))
        else:
            self.final_score = max(0.0, self.final_score)

        return self.final_score
    
    def determine_signal_strength(self) -> str:
        """
        Determine signal strength category based on final score.
        
        Categories:
        - weak: < 80
        - medium: 80-150
        - strong: > 150
        
        Returns:
            Signal strength category
        """
        if self.final_score < 80:
            self.signal_strength = 'weak'
        elif self.final_score < 150:
            self.signal_strength = 'medium'
        else:
            self.signal_strength = 'strong'
        
        return self.signal_strength
    
    def calculate_confidence(self) -> float:
        """
        Calculate confidence score (0-1).
        
        Based on:
        - Number of aligned analyzers
        - Final score magnitude
        - Confluence bonus
        
        Returns:
            Confidence (0-1)
        """
        confidence = 0.3  # Base confidence
        
        # Aligned analyzers boost confidence
        if self.aligned_analyzers >= 7:
            confidence += 0.3
        elif self.aligned_analyzers >= 5:
            confidence += 0.2
        elif self.aligned_analyzers >= 3:
            confidence += 0.1
        
        # High final score boosts confidence
        if self.final_score > 200:
            confidence += 0.2
        elif self.final_score > 150:
            confidence += 0.15
        elif self.final_score > 100:
            confidence += 0.1
        
        # Confluence bonus
        confidence += self.confluence_bonus * 0.3
        
        # Clamp between 0 and 1
        self.confidence = max(0.0, min(confidence, 1.0))
        
        return self.confidence
    
    def build_breakdown(self) -> Dict[str, Any]:
        """
        Build detailed breakdown of scoring.
        
        Returns:
            Dictionary with scoring details
        """
        self.breakdown = {
            'base_scores': {
                'trend': round(self.trend_score, 2),
                'momentum': round(self.momentum_score, 2),
                'volume': round(self.volume_score, 2),
                'pattern': round(self.pattern_score, 2),
                'sr': round(self.sr_score, 2),
                'volatility': round(self.volatility_score, 2),
                'harmonic': round(self.harmonic_score, 2),
                'channel': round(self.channel_score, 2),
                'cyclical': round(self.cyclical_score, 2),
                'htf': round(self.htf_score, 2)
            },
            'weighted_scores': {
                'trend': round(self.weighted_trend, 2),
                'momentum': round(self.weighted_momentum, 2),
                'volume': round(self.weighted_volume, 2),
                'pattern': round(self.weighted_pattern, 2),
                'sr': round(self.weighted_sr, 2),
                'volatility': round(self.weighted_volatility, 2),
                'harmonic': round(self.weighted_harmonic, 2),
                'channel': round(self.weighted_channel, 2),
                'cyclical': round(self.weighted_cyclical, 2),
                'htf': round(self.weighted_htf, 2)
            },
            'aggregates': {
                'base_score': round(self.base_score, 2),
                'confluence_bonus': round(self.confluence_bonus, 3),
                'confluence_details': self.confluence_details,              # NEW: جزئیات confluence
                'timeframe_weight': round(self.timeframe_weight, 2),
                'trend_alignment': round(self.trend_alignment, 3),          # NEW
                'volume_confirmation': round(self.volume_confirmation, 2),  # NEW
                'pattern_quality': round(self.pattern_quality, 3),          # NEW
                'macd_analysis_score': round(self.macd_analysis_score, 3),  # NEW
                'htf_multiplier': round(self.htf_multiplier, 2),
                'volatility_multiplier': round(self.volatility_multiplier, 2)
            },
            'final': {
                'score': round(self.final_score, 2),
                'confidence': round(self.confidence, 2),
                'strength': self.signal_strength
            },
            'meta': {
                'contributing_analyzers': self.contributing_analyzers,
                'aligned_analyzers': self.aligned_analyzers
            },
            'patterns': {
                'detected': self.detected_patterns,
                'contributions': self.pattern_contributions
            }
        }

        return self.breakdown
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        return asdict(self)
    
    def __str__(self) -> str:
        """String representation for logging."""
        return (
            f"SignalScore(final={self.final_score:.2f}, "
            f"confidence={self.confidence:.2f}, "
            f"strength={self.signal_strength}, "
            f"aligned={self.aligned_analyzers})"
        )
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return self.__str__()

    def get_pattern_summary(self) -> str:
        """
        دریافت خلاصه الگوهای تشخیص داده شده برای نمایش در لاگ.

        Returns:
            رشته‌ای حاوی خلاصه الگوها و تایم‌فریم‌های آن‌ها
        """
        if not self.detected_patterns:
            return "هیچ الگویی تشخیص داده نشد"

        summary_lines = []
        for pattern in self.detected_patterns:
            name = pattern.get('name', 'Unknown')
            timeframe = pattern.get('timeframe', 'N/A')
            adjusted_strength = pattern.get('adjusted_strength', 0)
            direction = pattern.get('direction', 'neutral')
            pattern_type = pattern.get('type', 'unknown')

            # افزودن ایموجی بر اساس نوع الگو
            if pattern_type == 'candlestick':
                icon = '🕯️'
            elif pattern_type == 'chart':
                icon = '📊'
            else:
                icon = '📈'

            # افزودن ایموجی بر اساس جهت
            if direction == 'bullish':
                dir_icon = '🟢'
            elif direction == 'bearish':
                dir_icon = '🔴'
            else:
                dir_icon = '⚪'

            contribution = self.pattern_contributions.get(name, 0)

            summary_lines.append(
                f"{icon} {name} [{timeframe}] {dir_icon} "
                f"(قدرت: {adjusted_strength:.2f}, سهم: {contribution:.2f})"
            )

        return "\n".join(summary_lines)
