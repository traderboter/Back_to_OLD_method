"""
اسکریپت ساده برای اجرای Backtest V2

🆕 نسخه 2.2 با SignalOrchestrator + انتخاب Scoring Method
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
    # پارس کردن آرگومان‌های command line
    parser = argparse.ArgumentParser(
        description='Run Backtest V2 with configurable scoring method'
    )
    parser.add_argument(
        '--method',
        type=str,
        choices=['old', 'new'],
        default='old',
        help='Scoring method to use: old (unlimited scoring) or new (bounded scoring)'
    )
    args = parser.parse_args()

    try:
        # نمایش method انتخاب شده
        method_name = "OLD SYSTEM" if args.method == 'old' else "NEW SYSTEM"
        method_desc = "Unlimited Scoring" if args.method == 'old' else "Bounded Scoring (max=100)"

        print("=" * 70)
        print(" " * 20 + "🚀 BACKTEST V2.2")
        print(" " * 15 + "with SignalOrchestrator")
        print(f" " * 10 + f"Scoring Method: {method_name}")
        print(f" " * 10 + f"Description: {method_desc}")
        print(" " * 10 + "Config Merge: main + scoring + backtest")
        print("=" * 70)

        # استفاده از config_backtest_minimal.yaml + config_scoring_{method}.yaml
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
        print(f"📊 Scoring Method: {method_name}")
        print(f"📁 Results saved to: {results_dir}")

    except KeyboardInterrupt:
        print("\n⚠️ Backtest interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
