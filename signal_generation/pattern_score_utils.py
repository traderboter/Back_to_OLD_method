"""
Pattern Score Utilities
تابع‌های کمکی برای دریافت امتیاز الگوها با پشتیبانی از امتیازدهی خاص هر تایم‌فریم
"""

from typing import Dict, Any, Union
import logging

logger = logging.getLogger(__name__)


def get_pattern_score(
    pattern_scores: Dict[str, Any],
    pattern_name: str,
    timeframe: str,
    default_score: float = 1.0
) -> float:
    """
    دریافت امتیاز الگو با پشتیبانی از ساختار قدیم و جدید

    ساختار جدید:
        pattern_scores = {
            'hammer': {
                '5m': 0.8,
                '15m': 1.0,
                '1h': 1.2,
                '4h': 1.5
            }
        }

    ساختار قدیم (برای سازگاری با گذشته):
        pattern_scores = {
            'hammer': 1.0
        }

    Args:
        pattern_scores: دیکشنری امتیازهای الگو از config
        pattern_name: نام الگو (مثل 'hammer', 'bullish_engulfing')
        timeframe: تایم‌فریم فعلی ('5m', '15m', '1h', '4h')
        default_score: امتیاز پیش‌فرض در صورت عدم وجود در config

    Returns:
        امتیاز الگو برای تایم‌فریم مشخص
    """
    if not pattern_scores:
        return default_score

    score_config = pattern_scores.get(pattern_name, default_score)

    # ساختار جدید: دیکشنری با کلیدهای تایم‌فریم
    if isinstance(score_config, dict):
        # اگر تایم‌فریم مشخص موجود است
        if timeframe in score_config:
            return score_config[timeframe]

        # اگر تایم‌فریم موجود نیست، از نزدیک‌ترین تایم‌فریم استفاده کن
        logger.debug(
            f"Timeframe {timeframe} not found for pattern {pattern_name}, "
            f"using fallback"
        )

        # ترتیب تایم‌فریم‌ها از کوچک به بزرگ - Aligned with OLD SYSTEM
        timeframe_order = ['5m', '15m', '1h', '4h']

        try:
            current_idx = timeframe_order.index(timeframe)
        except ValueError:
            # اگر تایم‌فریم در لیست نبود، از پیش‌فرض استفاده کن
            logger.warning(f"Unknown timeframe: {timeframe}")
            return default_score

        # جستجوی نزدیک‌ترین تایم‌فریم موجود
        for i in range(len(timeframe_order)):
            # ابتدا تایم‌فریم‌های بالاتر را چک کن
            if current_idx + i < len(timeframe_order):
                check_tf = timeframe_order[current_idx + i]
                if check_tf in score_config:
                    return score_config[check_tf]

            # سپس تایم‌فریم‌های پایین‌تر
            if current_idx - i >= 0:
                check_tf = timeframe_order[current_idx - i]
                if check_tf in score_config:
                    return score_config[check_tf]

        # اگر هیچ تایم‌فریمی پیدا نشد، از پیش‌فرض استفاده کن
        return default_score

    # ساختار قدیم: عدد ساده
    elif isinstance(score_config, (int, float)):
        return float(score_config)

    # مورد پیش‌فرض
    else:
        logger.warning(
            f"Invalid score config type for pattern {pattern_name}: "
            f"{type(score_config)}"
        )
        return default_score


def update_pattern_scores_in_place(
    pattern_scores: Dict[str, Any],
    pattern_name: str,
    multiplier: float
) -> None:
    """
    به‌روزرسانی امتیاز الگو در همان دیکشنری (in-place)
    با پشتیبانی از ساختار قدیم و جدید

    Args:
        pattern_scores: دیکشنری امتیازهای الگو
        pattern_name: نام الگو
        multiplier: ضریب ضرب
    """
    if pattern_name not in pattern_scores:
        return

    score_config = pattern_scores[pattern_name]

    # ساختار جدید: دیکشنری با تایم‌فریم‌ها
    if isinstance(score_config, dict):
        # همه تایم‌فریم‌ها را ضرب کن
        for tf in score_config:
            pattern_scores[pattern_name][tf] *= multiplier

    # ساختار قدیم: عدد ساده
    elif isinstance(score_config, (int, float)):
        pattern_scores[pattern_name] *= multiplier

    else:
        logger.warning(
            f"Cannot update pattern score for {pattern_name}: "
            f"invalid type {type(score_config)}"
        )


def get_all_pattern_names(pattern_scores: Dict[str, Any]) -> list:
    """
    دریافت لیست نام همه الگوها

    Args:
        pattern_scores: دیکشنری امتیازهای الگو

    Returns:
        لیست نام الگوها
    """
    return list(pattern_scores.keys())


def validate_pattern_scores_config(pattern_scores: Dict[str, Any]) -> bool:
    """
    اعتبارسنجی ساختار pattern_scores

    Args:
        pattern_scores: دیکشنری امتیازهای الگو

    Returns:
        True اگر معتبر باشد
    """
    if not isinstance(pattern_scores, dict):
        logger.error("pattern_scores must be a dictionary")
        return False

    for pattern_name, score_config in pattern_scores.items():
        # باید یا عدد باشد یا دیکشنری
        if not isinstance(score_config, (int, float, dict)):
            logger.error(
                f"Invalid score config for pattern {pattern_name}: "
                f"must be number or dict, got {type(score_config)}"
            )
            return False

        # اگر دیکشنری است، مقادیر باید عدد باشند
        if isinstance(score_config, dict):
            for tf, score in score_config.items():
                if not isinstance(score, (int, float)):
                    logger.error(
                        f"Invalid score for pattern {pattern_name}, "
                        f"timeframe {tf}: must be number, got {type(score)}"
                    )
                    return False

    return True
