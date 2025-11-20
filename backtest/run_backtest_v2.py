"""
اسکریپت ساده برای اجرای Backtest V2

🆕 نسخه 2.1 با SignalOrchestrator + OLD Scoring Method
"""

import asyncio
import logging
import sys
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
    try:
        print("=" * 70)
        print(" " * 20 + "🚀 BACKTEST V2.1")
        print(" " * 15 + "with SignalOrchestrator")
        print(" " * 10 + "Scoring Method: OLD SYSTEM")
        print(" " * 10 + "Config Merge: main + scoring + backtest")
        print("=" * 70)

        # استفاده از config_backtest_minimal.yaml + config_scoring_old.yaml
        # این فایل‌ها کوچک هستند و فقط override/specific تنظیمات را دارند
        # بقیه از config.yaml اصلی لود می‌شود
        engine, results_dir = asyncio.run(
            run_backtest_v2(
                config_path='backtest/config_backtest_minimal.yaml',
                main_config_path='config.yaml',
                scoring_method='old'
            )
        )

        print(f"\n✅ Backtest V2 completed successfully!")
        print(f"📊 Scoring Method: OLD SYSTEM")
        print(f"📁 Results saved to: {results_dir}")

    except KeyboardInterrupt:
        print("\n⚠️ Backtest interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
