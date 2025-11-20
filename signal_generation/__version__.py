"""
Version information for Signal Generation system
"""

__version__ = "1.2.2"
__version_date__ = "2025-10-24"
__version_info__ = {
    "version": __version__,
    "date": __version_date__,
    "changes": [
        "v1.2.2 (2025-10-24): رفع ادامه مشکل Shooting Star - max_lower_shadow 0.5→1.0 🔧",
        "  - با debug test متوجه شدیم threshold 0.5 هنوز خیلی سخت است",
        "  - اضافه کردن debug_shooting_star.py برای تست با کندل‌های مصنوعی",
        "",
        "v1.2.1 (2025-10-24): رفع مشکل threshold های خیلی سخت در Shooting Star 🔧",
        "  - تغییر default thresholds: min_upper_shadow 2.0→1.5, max_lower_shadow 0.1→0.5, max_body_position 0.33→0.4",
        "  - مشابه رفع مشکل اولیه Doji که threshold های TA-Lib خیلی سخت بود",
        "",
        "v1.2.0 (2025-10-24): اضافه کردن سیستم Quality Scoring جامع برای Doji, Hammer, Shooting Star 🎯",
        "  - Doji: Quality scoring (0-100), Doji type detection (Standard/Dragonfly/Gravestone/Long-legged)",
        "  - Hammer: Quality scoring با context analysis (downtrend detection), Hammer types (Perfect/Strong/Standard)",
        "  - Shooting Star: Quality scoring با context analysis (uptrend detection), types (Perfect/Strong/Standard)",
        "  - test_pattern.py: نمایش آمار کیفیت و توزیع انواع الگوها",
        "",
        "v1.1.0 (2025-10-24): رفع مشکل تشخیص کم Doji با معیارهای قابل تنظیم",
        "  - جایگزینی TA-Lib با detector دستی",
        "  - threshold قابل تنظیم برای DojiPattern",
        "  - اسکن همه کندل‌ها در test_pattern.py",
        "  - PatternOrchestrator: پشتیبانی از class و instance"
    ]
}


def get_version_string():
    """نمایش اطلاعات ورژن"""
    return f"Signal Generation v{__version__} ({__version_date__})"


def print_version():
    """چاپ کامل اطلاعات ورژن"""
    print(f"\n{'='*80}")
    print(f"📦 {get_version_string()}")
    print(f"{'='*80}")
    print("تغییرات:")
    for change in __version_info__['changes']:
        print(f"  {change}")
    print(f"{'='*80}\n")
