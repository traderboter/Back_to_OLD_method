"""
Constants for Signal Generation System

این فایل شامل تمام Constants (اعداد ثابت) مورد استفاده در سیستم است.
استفاده از Constants به جای Magic Numbers:
- کد خواناتر
- تغییر آسان‌تر
- مستندسازی بهتر
- جلوگیری از اشتباه در تایپ اعداد
"""

from typing import Final, Dict


# ============================================================================
# ATR (Average True Range) Thresholds
# ============================================================================

# ATR Percent Thresholds (برای تشخیص نوسان):
ATR_PERCENT_LOW_THRESHOLD: Final[float] = 0.5
"""Threshold for low volatility: ATR% < 0.5"""

ATR_PERCENT_HIGH_THRESHOLD: Final[float] = 1.5
"""Threshold for high volatility: ATR% > 1.5"""

ATR_PERCENT_EXTREME_THRESHOLD: Final[float] = 3.0
"""Threshold for extreme volatility: ATR% > 3.0"""

# ATR Multipliers (برای Stop Loss / Take Profit):
ATR_MULTIPLIER_SL: Final[float] = 2.0
"""ATR multiplier for Stop Loss calculation"""

ATR_MULTIPLIER_TP: Final[float] = 3.0
"""ATR multiplier for Take Profit calculation"""

# ATR Tolerance (برای SR clustering):
ATR_TOLERANCE_MULTIPLIER: Final[float] = 0.3
"""ATR multiplier for S/R level clustering: ATR × 0.3"""


# ============================================================================
# ADX (Average Directional Index) Thresholds
# ============================================================================

ADX_STRONG_TREND_THRESHOLD: Final[float] = 25.0
"""Threshold for strong trend: ADX >= 25"""

ADX_WEAK_TREND_THRESHOLD: Final[float] = 20.0
"""Threshold for weak trend: 20 <= ADX < 25"""

ADX_RANGING_THRESHOLD: Final[float] = 20.0
"""Threshold for ranging market: ADX < 20"""


# ============================================================================
# RSI (Relative Strength Index) Thresholds
# ============================================================================

RSI_OVERSOLD_THRESHOLD: Final[int] = 30
"""RSI oversold level"""

RSI_OVERBOUGHT_THRESHOLD: Final[int] = 70
"""RSI overbought level"""

RSI_EXTREME_OVERSOLD_THRESHOLD: Final[int] = 20
"""RSI extreme oversold level"""

RSI_EXTREME_OVERBOUGHT_THRESHOLD: Final[int] = 80
"""RSI extreme overbought level"""

RSI_NEUTRAL_LOW: Final[int] = 40
"""RSI neutral zone - lower bound"""

RSI_NEUTRAL_HIGH: Final[int] = 60
"""RSI neutral zone - upper bound"""


# ============================================================================
# MACD Thresholds
# ============================================================================

MACD_ZERO_CROSS_THRESHOLD: Final[float] = 0.0
"""MACD zero line"""

MACD_SIGNAL_CROSS_MIN_DISTANCE: Final[float] = 0.001
"""Minimum distance for meaningful MACD-Signal cross"""


# ============================================================================
# Stochastic Oscillator Thresholds
# ============================================================================

STOCH_OVERSOLD_THRESHOLD: Final[int] = 20
"""Stochastic oversold level"""

STOCH_OVERBOUGHT_THRESHOLD: Final[int] = 80
"""Stochastic overbought level"""


# ============================================================================
# Volume Thresholds
# ============================================================================

VOLUME_SPIKE_THRESHOLD: Final[float] = 1.5
"""Volume spike: volume > avg × 1.5"""

VOLUME_BREAKOUT_THRESHOLD: Final[float] = 2.0
"""Volume breakout: volume > avg × 2.0"""

VOLUME_CLIMAX_THRESHOLD: Final[float] = 3.0
"""Volume climax: volume > avg × 3.0"""

VOLUME_ACCUMULATION_THRESHOLD: Final[float] = 1.3
"""Volume accumulation threshold"""

VOLUME_ACCUMULATION_RANGE: Final[float] = 0.02
"""Price range threshold for accumulation: 2%"""

VOLUME_CLIMAX_RANGE: Final[float] = 0.03
"""Price move threshold for climax: 3%"""


# ============================================================================
# Support/Resistance (SR) Constants
# ============================================================================

SR_MIN_TOUCHES: Final[int] = 2
"""Minimum touches required to form a S/R level"""

SR_LEVEL_TOLERANCE_PERCENT: Final[float] = 0.005
"""S/R level tolerance as percentage: 0.5%"""

SR_ZONE_DISTANCE_PERCENT: Final[float] = 0.02
"""Distance threshold for S/R zones: 2%"""

SR_ZONE_MIN_LEVELS: Final[int] = 2
"""Minimum levels to form a zone"""

SR_BROKEN_LEVEL_CONFIRMATION_CANDLES: Final[int] = 3
"""Candles required to confirm level breakout"""


# ============================================================================
# Pattern Recognition Constants
# ============================================================================

PATTERN_RECENCY_MULTIPLIER_MAX: Final[float] = 1.5
"""Maximum recency multiplier for recent patterns"""

PATTERN_RECENCY_MULTIPLIER_MIN: Final[float] = 0.5
"""Minimum recency multiplier for old patterns"""

PATTERN_RECENCY_LOOKBACK: Final[int] = 20
"""Lookback period for pattern recency scoring"""

PATTERN_CONTRIBUTION_MULTIPLIER: Final[float] = 0.5
"""Pattern contribution multiplier in multi-TF aggregation"""

SR_BREAKOUT_MULTIPLIER: Final[float] = 1.5
"""S/R breakout contribution multiplier"""


# ============================================================================
# Trend Phase Multipliers (برای Multi-TF Aggregation)
# ============================================================================

class TrendPhaseMultipliers:
    """
    Multipliers برای فازهای مختلف ترند در Multi-TF Aggregation.
    """
    EARLY: Final[float] = 1.2        # +20% - بهترین فرصت
    DEVELOPING: Final[float] = 1.1   # +10%
    MATURE: Final[float] = 0.9       # -10% - احتیاط
    LATE: Final[float] = 0.7         # -30% - پرریسک
    PULLBACK: Final[float] = 1.1     # +10%
    TRANSITION: Final[float] = 0.8   # -20%
    UNDEFINED: Final[float] = 1.0    # بدون تغییر

    @classmethod
    def get(cls, phase: str, default: float = 1.0) -> float:
        """دریافت multiplier برای یک phase."""
        return getattr(cls, phase.upper(), default)


# ============================================================================
# MACD Type Strength Multipliers (برای Multi-TF Aggregation)
# ============================================================================

class MACDTypeStrength:
    """
    Multipliers برای انواع MACD در Multi-TF Aggregation.
    """
    A_TYPE: Final[float] = 1.2  # A_ types (قوی صعودی) +20%
    B_TYPE: Final[float] = 1.0  # B_ types (متوسط صعودی)
    C_TYPE: Final[float] = 1.2  # C_ types (قوی نزولی) +20%
    D_TYPE: Final[float] = 1.0  # D_ types (متوسط نزولی)
    X_TYPE: Final[float] = 0.8  # X_ types (انتقالی) -20%

    @classmethod
    def get(cls, type_prefix: str, default: float = 1.0) -> float:
        """دریافت multiplier برای یک MACD type."""
        mapping = {
            'A': cls.A_TYPE,
            'B': cls.B_TYPE,
            'C': cls.C_TYPE,
            'D': cls.D_TYPE,
            'X': cls.X_TYPE
        }
        return mapping.get(type_prefix.upper(), default)


# ============================================================================
# Scoring Weights (وزن‌های امتیازدهی)
# ============================================================================

class AnalyzerWeights:
    """
    وزن‌های درصدی analyzers در محاسبه base score.

    مجموع: 1.0 (100%)
    """
    TREND: Final[float] = 0.30           # 30% - مهم‌ترین
    MOMENTUM: Final[float] = 0.25        # 25%
    VOLUME: Final[float] = 0.20          # 20%
    PATTERNS: Final[float] = 0.10        # 10%
    SUPPORT_RESISTANCE: Final[float] = 0.08  # 8%
    VOLATILITY: Final[float] = 0.05      # 5%
    HARMONIC: Final[float] = 0.01        # 1%
    CHANNEL: Final[float] = 0.005        # 0.5%
    CYCLICAL: Final[float] = 0.003       # 0.3%
    HTF: Final[float] = 0.002            # 0.2%


# ============================================================================
# Timeframe Weights (وزن‌های تایم‌فریم)
# ============================================================================

class TimeframeWeights:
    """
    وزن‌های تایم‌فریم‌ها برای Multi-TF Aggregation.
    """
    TF_5M: Final[float] = 0.7    # -30% اهمیت
    TF_15M: Final[float] = 0.85  # -15% اهمیت
    TF_1H: Final[float] = 1.0    # مرجع
    TF_4H: Final[float] = 1.2    # +20% اهمیت

    @classmethod
    def get(cls, timeframe: str, default: float = 1.0) -> float:
        """دریافت وزن یک تایم‌فریم."""
        mapping = {
            '5m': cls.TF_5M,
            '15m': cls.TF_15M,
            '1h': cls.TF_1H,
            '4h': cls.TF_4H
        }
        return mapping.get(timeframe.lower(), default)


# ============================================================================
# Score Thresholds (آستانه‌های امتیاز)
# ============================================================================

SCORE_WEAK_THRESHOLD: Final[float] = 80.0
"""Threshold برای سیگنال ضعیف: score < 80"""

SCORE_MEDIUM_THRESHOLD: Final[float] = 80.0
"""Threshold برای سیگنال متوسط: 80 <= score < 150"""

SCORE_STRONG_THRESHOLD: Final[float] = 150.0
"""Threshold برای سیگنال قوی: score >= 150"""

SCORE_MIN_THRESHOLD: Final[float] = 20.0
"""حداقل امتیاز قابل قبول (adaptive می‌تواند تغییر دهد)"""


# ============================================================================
# Confidence Thresholds
# ============================================================================

CONFIDENCE_VERY_HIGH_THRESHOLD: Final[float] = 0.8
"""Confidence very high: > 0.8"""

CONFIDENCE_HIGH_THRESHOLD: Final[float] = 0.6
"""Confidence high: 0.6 - 0.8"""

CONFIDENCE_MEDIUM_THRESHOLD: Final[float] = 0.4
"""Confidence medium: 0.4 - 0.6"""

CONFIDENCE_LOW_THRESHOLD: Final[float] = 0.2
"""Confidence low: 0.2 - 0.4"""


# ============================================================================
# Risk/Reward Constants
# ============================================================================

MIN_RR_RATIO: Final[float] = 1.8
"""حداقل نسبت Risk/Reward قابل قبول"""

PREFERRED_RR_RATIO: Final[float] = 2.5
"""نسبت Risk/Reward مطلوب"""

MAX_RISK_PERCENT: Final[float] = 2.0
"""حداکثر ریسک به ازای هر معامله: 2%"""

MIN_SL_DISTANCE_PERCENT: Final[float] = 0.5
"""حداقل فاصله Stop Loss: 0.5%"""

MAX_SL_DISTANCE_PERCENT: Final[float] = 3.0
"""حداکثر فاصله Stop Loss: 3%"""


# ============================================================================
# Circuit Breaker Constants
# ============================================================================

MAX_SIGNALS_PER_HOUR: Final[int] = 3
"""حداکثر سیگنال در ساعت"""

MAX_SIGNALS_PER_DAY: Final[int] = 10
"""حداکثر سیگنال در روز"""

COOLDOWN_AFTER_LOSS_MINUTES: Final[int] = 30
"""مدت cooldown بعد از ضرر: 30 دقیقه"""


# ============================================================================
# Portfolio Limits
# ============================================================================

MAX_TOTAL_EXPOSURE: Final[float] = 0.5
"""حداکثر exposure کل: 50%"""

MAX_PER_SYMBOL_EXPOSURE: Final[float] = 0.1
"""حداکثر exposure هر سمبل: 10%"""

MAX_SAME_DIRECTION_EXPOSURE: Final[float] = 0.3
"""حداکثر exposure در یک جهت: 30%"""

MAX_OPEN_POSITIONS: Final[int] = 5
"""حداکثر تعداد پوزیشن‌های باز"""


# ============================================================================
# Correlation Constants
# ============================================================================

MAX_CORRELATION: Final[float] = 0.8
"""حداکثر همبستگی مجاز"""

CORRELATION_LOOKBACK_PERIODS: Final[int] = 50
"""تعداد periods برای محاسبه همبستگی"""


# ============================================================================
# Multi-TF Alignment Constants
# ============================================================================

# وزن‌های alignment factor:
ALIGNMENT_WEIGHT_TREND: Final[float] = 0.5      # 50%
ALIGNMENT_WEIGHT_MOMENTUM: Final[float] = 0.3   # 30%
ALIGNMENT_WEIGHT_MACD: Final[float] = 0.2       # 20%

# محدوده alignment factor:
ALIGNMENT_FACTOR_MIN: Final[float] = 0.7
"""حداقل alignment factor"""

ALIGNMENT_FACTOR_MAX: Final[float] = 1.3
"""حداکثر alignment factor"""

ALIGNMENT_FACTOR_RANGE: Final[float] = 0.6
"""Range alignment factor: max - min"""

# Direction margin:
DIRECTION_MARGIN: Final[float] = 1.1
"""Margin برای تعیین جهت: 10%"""


# ============================================================================
# Volatility Risk Multipliers
# ============================================================================

class VolatilityRiskMultipliers:
    """
    Risk multipliers برای رژیم‌های مختلف نوسان.
    """
    LOW: Final[float] = 1.5      # نوسان کم: ریسک بیشتر مجاز
    NORMAL: Final[float] = 1.0   # نوسان عادی
    HIGH: Final[float] = 0.6     # نوسان زیاد: ریسک کمتر


# ============================================================================
# Confluence Bonus Constants
# ============================================================================

MAX_CONFLUENCE_BONUS: Final[float] = 0.5
"""حداکثر confluence bonus: 50%"""

MAX_ALIGNMENT_BONUS: Final[float] = 0.25
"""حداکثر alignment bonus: 25%"""

MAX_RR_BONUS: Final[float] = 0.25
"""حداکثر RR bonus: 25%"""

MIN_RR_FOR_BONUS: Final[float] = 2.0
"""حداقل RR برای دریافت bonus"""

RR_BONUS_MULTIPLIER: Final[float] = 0.125
"""RR bonus multiplier: (RR - 2.0) × 0.125"""


# ============================================================================
# HTF (Higher Timeframe) Multipliers
# ============================================================================

HTF_ALIGNMENT_BONUS: Final[float] = 0.3
"""HTF alignment bonus: +30%"""

HTF_MISALIGNMENT_PENALTY: Final[float] = 0.3
"""HTF misalignment penalty: -30%"""


# ============================================================================
# Trend Alignment Multipliers (برای SignalScorer)
# ============================================================================

TREND_ALIGNMENT_PERFECT: Final[float] = 1.2
"""Perfect trend alignment (strength >= 2.5): 1.2"""

TREND_ALIGNMENT_GOOD: Final[float] = 1.1
"""Good trend alignment (strength >= 1.5): 1.1"""

TREND_ALIGNMENT_WEAK: Final[float] = 1.05
"""Weak trend alignment: 1.05"""

TREND_ALIGNMENT_NEUTRAL: Final[float] = 1.0
"""Neutral: 1.0"""

TREND_ALIGNMENT_AGAINST: Final[float] = 0.8
"""Against trend: 0.8"""


# ============================================================================
# Pattern Quality Multipliers
# ============================================================================

PATTERN_QUALITY_BASE: Final[float] = 1.0
"""Base pattern quality"""

PATTERN_QUALITY_INCREMENT: Final[float] = 0.1
"""Increment per pattern: +0.1"""

PATTERN_QUALITY_MAX: Final[float] = 1.5
"""Maximum pattern quality: 1.5 (capped at 5 patterns)"""


# ============================================================================
# MACD Analysis Score Multipliers (برای SignalScorer)
# ============================================================================

MACD_ANALYSIS_PERFECT: Final[float] = 1.2
"""Perfect MACD alignment"""

MACD_ANALYSIS_NEUTRAL: Final[float] = 1.0
"""Neutral MACD"""

MACD_ANALYSIS_POOR: Final[float] = 0.85
"""Poor MACD alignment"""


# ============================================================================
# Volume Confirmation Multipliers
# ============================================================================

VOLUME_CONFIRMED_MULTIPLIER: Final[float] = 1.1
"""Volume confirmed: +10%"""

VOLUME_NOT_CONFIRMED_MULTIPLIER: Final[float] = 1.0
"""Volume not confirmed"""


# ============================================================================
# Adaptive Threshold Constants
# ============================================================================

ADAPTIVE_PERFORMANCE_WINDOW_DAYS: Final[int] = 7
"""Window برای محاسبه performance: 7 روز"""

ADAPTIVE_GOOD_PERFORMANCE_THRESHOLD: Final[float] = 0.6
"""Win rate برای performance خوب: 60%"""

ADAPTIVE_POOR_PERFORMANCE_THRESHOLD: Final[float] = 0.4
"""Win rate برای performance ضعیف: 40%"""

ADAPTIVE_MIN_TRADES_REQUIRED: Final[int] = 10
"""حداقل معاملات برای adaptive threshold"""

ADAPTIVE_SCORE_REDUCTION: Final[float] = 15.0
"""Threshold برای performance خوب: -25%"""

ADAPTIVE_SCORE_INCREASE: Final[float] = 30.0
"""Threshold برای performance ضعیف: +50%"""


# ============================================================================
# Channel Constants
# ============================================================================

CHANNEL_SLOPE_THRESHOLD: Final[float] = 0.0001
"""Threshold برای تشخیص نوع کانال (horizontal vs ascending/descending)"""

CHANNEL_FIT_QUALITY_EXCELLENT: Final[float] = 0.1
"""Fit error < 10% channel width = excellent (strength 3)"""

CHANNEL_FIT_QUALITY_GOOD: Final[float] = 0.2
"""Fit error < 20% channel width = good (strength 2)"""


# ============================================================================
# Cyclical Analysis Constants
# ============================================================================

CYCLICAL_MIN_CYCLE_PERIOD: Final[int] = 2
"""حداقل دوره چرخه"""

CYCLICAL_MAX_CYCLE_PERIOD_RATIO: Final[float] = 0.5
"""حداکثر دوره چرخه: lookback / 2"""

CYCLICAL_TOP_CYCLES_COUNT: Final[int] = 5
"""تعداد چرخه‌های برتر برای نگه‌داری"""

CYCLICAL_FORECAST_LENGTH: Final[int] = 20
"""تعداد periods برای پیش‌بینی"""


# ============================================================================
# Harmonic Pattern Constants
# ============================================================================

HARMONIC_FIBONACCI_TOLERANCE: Final[float] = 0.05
"""Tolerance برای نسبت‌های Fibonacci: 5%"""

HARMONIC_MIN_COMPLETION: Final[float] = 0.618
"""حداقل completion برای الگوی هارمونیک: 61.8%"""


# ============================================================================
# Cache Constants
# ============================================================================

INDICATOR_CACHE_MAX_SIZE: Final[int] = 1000
"""Maximum size of indicator cache"""

INDICATOR_CACHE_TTL_SECONDS: Final[int] = 300
"""TTL برای indicator cache: 5 دقیقه"""

TIMEFRAME_SCORE_CACHE_TTL_SECONDS: Final[int] = 60
"""TTL برای timeframe score cache: 1 دقیقه"""


# ============================================================================
# Data Validation Constants
# ============================================================================

MIN_CANDLES_FOR_ANALYSIS: Final[int] = 100
"""حداقل تعداد کندل برای تحلیل معتبر"""

MIN_CANDLES_FOR_HTF: Final[int] = 50
"""حداقل تعداد کندل برای HTF analysis"""

MIN_CANDLES_FOR_CYCLICAL: Final[int] = 100
"""حداقل تعداد کندل برای Cyclical analysis"""


# ============================================================================
# Utility Functions
# ============================================================================

def get_all_constants() -> Dict[str, any]:
    """دریافت dictionary از تمام constants."""
    import sys
    import inspect

    current_module = sys.modules[__name__]
    constants = {}

    for name, value in inspect.getmembers(current_module):
        # Skip private, functions, classes, modules:
        if name.startswith('_') or inspect.isfunction(value) or \
           inspect.isclass(value) or inspect.ismodule(value):
            continue

        # Only include Final or uppercase constants:
        if name.isupper() or hasattr(value, '__annotations__'):
            constants[name] = value

    return constants


if __name__ == '__main__':
    # نمایش تمام constants:
    print("="*60)
    print("ALL CONSTANTS IN SIGNAL GENERATION SYSTEM")
    print("="*60)

    all_constants = get_all_constants()

    for const_name, const_value in sorted(all_constants.items()):
        print(f"{const_name}: {const_value}")
