"""
Enums for Signal Generation System

این فایل شامل تمام Enum های مورد استفاده در سیستم تولید سیگنال است.
استفاده از Enum ها به جای رشته‌های ثابت:
- جلوگیری از typo
- Type safety
- IDE autocomplete
- مستندسازی بهتر
"""

from enum import Enum, auto


# ============================================================================
# Direction Enums (جهت)
# ============================================================================

class Direction(str, Enum):
    """
    جهت سیگنال یا تحلیل.

    استفاده در:
    - TrendAnalyzer
    - MomentumAnalyzer
    - PatternAnalyzer
    - SignalOrchestrator
    """
    BULLISH = 'bullish'
    BEARISH = 'bearish'
    NEUTRAL = 'neutral'

    # برای سیگنال‌های نهایی:
    LONG = 'LONG'
    SHORT = 'SHORT'

    def __str__(self) -> str:
        return self.value


class SignalDirection(str, Enum):
    """
    جهت سیگنال نهایی (برای backward compatibility).
    """
    BUY = 'buy'
    SELL = 'sell'
    LONG = 'LONG'
    SHORT = 'SHORT'

    def __str__(self) -> str:
        return self.value


# ============================================================================
# Market Regime Enums (رژیم بازار)
# ============================================================================

class MarketRegime(str, Enum):
    """
    رژیم بازار (9 رژیم اصلی).

    فرمول: ADX + Volatility (ATR%)
    - Strong Trend: ADX >= 25
    - Weak Trend: 20 <= ADX < 25
    - Ranging: ADX < 20

    - Low Volatility: ATR% < 0.5
    - Normal Volatility: 0.5 <= ATR% <= 1.5
    - High Volatility: ATR% > 1.5
    """
    # Strong Trend (ADX >= 25):
    STRONG_TREND_LOW_VOL = 'strong_trend_low_volatility'
    STRONG_TREND_NORMAL = 'strong_trend_normal'
    STRONG_TREND_HIGH_VOL = 'strong_trend_high_volatility'

    # Weak Trend (20 <= ADX < 25):
    WEAK_TREND_LOW_VOL = 'weak_trend_low_volatility'
    WEAK_TREND_NORMAL = 'weak_trend_normal'
    WEAK_TREND_HIGH_VOL = 'weak_trend_high_volatility'

    # Ranging (ADX < 20):
    RANGING_LOW_VOL = 'ranging_low_volatility'
    RANGING_NORMAL = 'ranging_normal'
    RANGING_HIGH_VOL = 'ranging_high_volatility'

    # Special:
    UNKNOWN = 'unknown'

    def __str__(self) -> str:
        return self.value


# ============================================================================
# Trend Enums (ترند)
# ============================================================================

class TrendPhase(str, Enum):
    """
    فاز ترند (از TrendAnalyzer).

    مراحل ترند:
    - early: شروع ترند (بهترین فرصت)
    - developing: در حال توسعه
    - mature: بالغ (احتیاط)
    - late: اواخر (پرریسک)
    - pullback: اصلاح
    - transition: انتقال
    """
    EARLY = 'early'
    DEVELOPING = 'developing'
    MATURE = 'mature'
    LATE = 'late'
    PULLBACK = 'pullback'
    TRANSITION = 'transition'
    UNDEFINED = 'undefined'

    def __str__(self) -> str:
        return self.value


class TrendAlignment(str, Enum):
    """
    الگوی چینش EMA ها (از TrendAnalyzer).
    """
    BULLISH_ALIGNED = 'bullish_aligned'          # EMA20 > EMA50 > EMA100
    BEARISH_ALIGNED = 'bearish_aligned'          # EMA20 < EMA50 < EMA100
    POTENTIAL_BULLISH_REVERSAL = 'potential_bullish_reversal'
    POTENTIAL_BEARISH_REVERSAL = 'potential_bearish_reversal'
    BULLISH_PULLBACK = 'bullish_pullback'
    BEARISH_PULLBACK = 'bearish_pullback'
    MIXED = 'mixed'

    def __str__(self) -> str:
        return self.value


# ============================================================================
# Volatility Enums (نوسان)
# ============================================================================

class VolatilityRegime(str, Enum):
    """
    رژیم نوسان (از VolatilityAnalyzer).

    بر اساس ATR%:
    - Low: ATR% < 0.5
    - Normal: 0.5 <= ATR% <= 1.5
    - High: 1.5 < ATR% <= 3.0
    - Extreme: ATR% > 3.0
    """
    LOW = 'low'
    NORMAL = 'normal'
    HIGH = 'high'
    EXTREME = 'extreme'

    def __str__(self) -> str:
        return self.value


# ============================================================================
# Signal Strength Enums (قدرت سیگنال)
# ============================================================================

class SignalStrength(str, Enum):
    """
    قدرت سیگنال (از SignalScorer).

    محدوده‌ها:
    - Weak: score < 80
    - Medium: 80 <= score < 150
    - Strong: score >= 150
    """
    WEAK = 'weak'
    MEDIUM = 'medium'
    STRONG = 'strong'

    def __str__(self) -> str:
        return self.value


# ============================================================================
# Pattern Enums (الگوها)
# ============================================================================

class PatternType(str, Enum):
    """
    نوع الگو.
    """
    CANDLESTICK = 'candlestick'
    CHART = 'chart'
    HARMONIC = 'harmonic'
    VOLUME = 'volume'

    def __str__(self) -> str:
        return self.value


class PatternDirection(str, Enum):
    """
    جهت الگو.
    """
    BULLISH = 'bullish'
    BEARISH = 'bearish'
    NEUTRAL = 'neutral'

    def __str__(self) -> str:
        return self.value


# ============================================================================
# Channel Enums (کانال)
# ============================================================================

class ChannelType(str, Enum):
    """
    نوع کانال (از ChannelAnalyzer).
    """
    ASCENDING = 'ascending'      # صعودی
    DESCENDING = 'descending'    # نزولی
    HORIZONTAL = 'horizontal'    # افقی
    IRREGULAR = 'irregular'      # نامنظم

    def __str__(self) -> str:
        return self.value


class PricePosition(str, Enum):
    """
    موقعیت قیمت در کانال.
    """
    ABOVE = 'above'      # بالای کانال (breakout)
    UPPER = 'upper'      # قسمت بالای کانال
    MIDDLE = 'middle'    # وسط کانال
    LOWER = 'lower'      # قسمت پایین کانال
    BELOW = 'below'      # زیر کانال (breakdown)

    def __str__(self) -> str:
        return self.value


# ============================================================================
# Cycle Enums (چرخه)
# ============================================================================

class CyclePhase(str, Enum):
    """
    فاز چرخه (از CyclicalAnalyzer).
    """
    TOP = 'top'          # قله
    BOTTOM = 'bottom'    # کف
    RISING = 'rising'    # صعودی
    FALLING = 'falling'  # نزولی
    UNKNOWN = 'unknown'

    def __str__(self) -> str:
        return self.value


class MarketStructure(str, Enum):
    """
    ساختار بازار (از HTFAnalyzer).

    انواع ساختار:
    - HIGHER_HIGHS: Higher Highs + Higher Lows (صعودی قوی)
    - LOWER_LOWS: Lower Highs + Lower Lows (نزولی قوی)
    - RANGING: حرکت رنج (بدون روند مشخص)
    - UNKNOWN: نامشخص
    """
    HIGHER_HIGHS = 'higher_highs'  # ساختار صعودی
    LOWER_LOWS = 'lower_lows'      # ساختار نزولی
    RANGING = 'ranging'            # رنج
    UNKNOWN = 'unknown'            # نامشخص

    def __str__(self) -> str:
        return self.value


# ============================================================================
# Volume Pattern Enums (الگوهای حجمی)
# ============================================================================

class VolumePattern(str, Enum):
    """
    الگوهای حجمی (از VolumePatternAnalyzer).

    6 الگو:
    1. Accumulation: جمع‌آوری
    2. Distribution: توزیع
    3. Climax: اوج حجم
    4. Divergence: واگرایی
    5. Smart Money: پول هوشمند
    6. Volume Profile: پروفایل حجمی
    """
    ACCUMULATION = 'accumulation'
    DISTRIBUTION = 'distribution'
    CLIMAX = 'climax_volume'
    DIVERGENCE = 'volume_divergence'
    SMART_MONEY = 'smart_money_flow'
    VOLUME_PROFILE = 'volume_profile'
    SPIKE = 'spike'
    DRY_UP = 'dry_up'

    def __str__(self) -> str:
        return self.value


class VolumeTrend(str, Enum):
    """
    روند حجم معاملات (از VolumeAnalyzer).
    """
    INCREASING = 'increasing'  # افزایش حجم
    DECREASING = 'decreasing'  # کاهش حجم
    STABLE = 'stable'          # حجم ثابت

    def __str__(self) -> str:
        return self.value


# ============================================================================
# RSI Signal Enums
# ============================================================================

class RSISignal(str, Enum):
    """
    سیگنال RSI (از MomentumAnalyzer).
    """
    OVERSOLD = 'oversold'              # RSI < 30
    OVERBOUGHT = 'overbought'          # RSI > 70
    EXTREME_OVERSOLD = 'extreme_oversold'  # RSI < 20
    EXTREME_OVERBOUGHT = 'extreme_overbought'  # RSI > 80
    NEUTRAL = 'neutral'

    def __str__(self) -> str:
        return self.value


# ============================================================================
# MACD Market Type Enums (5 نوع بازار MACD)
# ============================================================================

class MACDMarketType(str, Enum):
    """
    نوع بازار MACD (از MomentumAnalyzer).

    5 نوع اصلی:
    - A_* : قوی صعودی (multiplier: 1.2)
    - B_* : متوسط صعودی (multiplier: 1.0)
    - C_* : قوی نزولی (multiplier: 1.2)
    - D_* : متوسط نزولی (multiplier: 1.0)
    - X_* : انتقالی (multiplier: 0.8)
    """
    # Type A - Strong Bullish (MACD > 0, Signal > 0, MACD > Signal):
    A_BULLISH_STRONG = 'A_bullish_strong'
    A_BULLISH_PULLBACK = 'A_bullish_pullback'

    # Type B - Moderate Bullish (MACD > 0, Signal > 0, MACD < Signal):
    B_BULLISH_NORMAL = 'B_bullish_normal'

    # Type C - Strong Bearish (MACD < 0, Signal < 0, MACD < Signal):
    C_BEARISH_STRONG = 'C_bearish_strong'
    C_BEARISH_RALLY = 'C_bearish_rally'

    # Type D - Moderate Bearish (MACD < 0, Signal < 0, MACD > Signal):
    D_BEARISH_NORMAL = 'D_bearish_normal'

    # Type X - Transition (mixed signals):
    X_TRANSITION = 'X_transition'

    @property
    def type_prefix(self) -> str:
        """دریافت پیشوند نوع (A, B, C, D, X)."""
        return self.value[0]

    @property
    def strength_multiplier(self) -> float:
        """دریافت multiplier قدرت برای multi-TF aggregation."""
        if self.type_prefix in ('A', 'C'):
            return 1.2  # قوی
        elif self.type_prefix in ('B', 'D'):
            return 1.0  # متوسط
        else:  # X
            return 0.8  # انتقالی

    def __str__(self) -> str:
        return self.value


# ============================================================================
# Validation Enums
# ============================================================================

class ValidationStatus(str, Enum):
    """
    وضعیت اعتبارسنجی.
    """
    VALID = 'valid'
    REJECTED = 'rejected'
    PENDING = 'pending'

    def __str__(self) -> str:
        return self.value


class RejectionReason(str, Enum):
    """
    دلیل رد سیگنال (از SignalValidator).
    """
    SCORE_TOO_LOW = 'score_too_low'
    RR_TOO_LOW = 'rr_too_low'
    RISK_TOO_HIGH = 'risk_too_high'
    CIRCUIT_BREAKER = 'circuit_breaker'
    HIGH_CORRELATION = 'high_correlation'
    EXTREME_VOLATILITY = 'extreme_volatility'
    PORTFOLIO_LIMIT = 'portfolio_limit'
    TIME_FILTER = 'time_filter'
    BASIC_VALIDATION = 'basic_validation'
    PRICE_VALIDATION = 'price_validation'

    def __str__(self) -> str:
        return self.value


# ============================================================================
# Confidence Level Enums
# ============================================================================

class ConfidenceLevel(str, Enum):
    """
    سطح اطمینان (از ConfidenceCalculator).
    """
    VERY_HIGH = 'very_high'    # > 0.8
    HIGH = 'high'              # 0.6 - 0.8
    MEDIUM = 'medium'          # 0.4 - 0.6
    LOW = 'low'                # 0.2 - 0.4
    VERY_LOW = 'very_low'      # < 0.2
    UNCERTAIN = 'uncertain'    # خاص

    def __str__(self) -> str:
        return self.value


# ============================================================================
# Timeframe Enums
# ============================================================================

class Timeframe(str, Enum):
    """
    تایم‌فریم‌های معاملاتی.
    """
    M1 = '1m'
    M5 = '5m'
    M15 = '15m'
    M30 = '30m'
    H1 = '1h'
    H4 = '4h'
    D1 = '1d'
    W1 = '1w'

    @property
    def minutes(self) -> int:
        """تبدیل به دقیقه."""
        mapping = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '4h': 240,
            '1d': 1440,
            '1w': 10080
        }
        return mapping.get(self.value, 0)

    def __str__(self) -> str:
        return self.value


# ============================================================================
# Error Severity Enums
# ============================================================================

class ErrorSeverity(str, Enum):
    """
    شدت خطا (برای error handling یکپارچه).
    """
    WARNING = 'warning'      # می‌توان ادامه داد
    ERROR = 'error'          # نمی‌توان ادامه داد
    CRITICAL = 'critical'    # باید متوقف شود

    def __str__(self) -> str:
        return self.value


# ============================================================================
# Status Enums
# ============================================================================

class AnalysisStatus(str, Enum):
    """
    وضعیت تحلیل.
    """
    OK = 'ok'
    ERROR = 'error'
    INSUFFICIENT_DATA = 'insufficient_data'
    CALCULATION_ERROR = 'calculation_error'

    def __str__(self) -> str:
        return self.value


# ============================================================================
# Utility Functions
# ============================================================================

def get_all_enums():
    """دریافت لیست تمام Enum های تعریف شده."""
    import sys
    import inspect

    current_module = sys.modules[__name__]

    enums = {}
    for name, obj in inspect.getmembers(current_module):
        if inspect.isclass(obj) and issubclass(obj, Enum) and obj != Enum:
            enums[name] = obj

    return enums


if __name__ == '__main__':
    # نمایش تمام Enum ها:
    print("="*60)
    print("ALL ENUMS IN SIGNAL GENERATION SYSTEM")
    print("="*60)

    all_enums = get_all_enums()

    for enum_name, enum_class in sorted(all_enums.items()):
        print(f"\n{enum_name}:")
        for member in enum_class:
            print(f"  - {member.name}: {member.value}")
