"""
اسکریپت ساده برای اجرای Backtest V2

🆕 نسخه 2.1 با SignalOrchestrator + Scoring Method Selection
"""

import asyncio
import logging
import sys
import argparse
from pathlib import Path

# اضافه کردن root به path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest.backtest_engine_v2 import run_backtest_v2

# تنظیم logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Backtest V2 - با انتخاب روش امتیازدهی',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
مثال‌های استفاده:
  python backtest/run_backtest_v2.py --method new      # سیستم جدید (8 ضریب)
  python backtest/run_backtest_v2.py --method old      # سیستم قدیمی (13 ضریب)
  python backtest/run_backtest_v2.py --method hybrid   # ترکیبی
  python backtest/run_backtest_v2.py                  # پیش‌فرض: new
        """
    )
    parser.add_argument(
        '--method',
        type=str,
        choices=['new', 'old', 'hybrid'],
        default='new',
        help='روش امتیازدهی: new (پیش‌فرض), old, hybrid'
    )

    args = parser.parse_args()

    try:
        print("=" * 70)
        print(" " * 20 + "🚀 BACKTEST V2.1")
        print(" " * 15 + "with SignalOrchestrator")
        print(" " * 10 + f"Scoring Method: {args.method.upper()}")
        print(" " * 10 + "Config Merge: main + scoring + backtest")
        print("=" * 70)

        # 🆕 استفاده از config_backtest_minimal.yaml + config_scoring_{method}.yaml
        # این فایل‌ها کوچک هستند و فقط override/specific تنظیمات را دارند
        # بقیه از config.yaml اصلی لود می‌شود
        engine, results_dir = asyncio.run(
            run_backtest_v2(
                config_path='backtest/config_backtest_minimal.yaml',
                main_config_path='config.yaml',
                scoring_method=args.method
            )
        )

        print(f"\n✅ Backtest V2 completed successfully!")
        print(f"📊 Scoring Method: {args.method.upper()}")
        print(f"📁 Results saved to: {results_dir}")

    except KeyboardInterrupt:
        print("\n⚠️ Backtest interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
