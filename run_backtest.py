"""
اجرای Backtest با NEW SYSTEM

این فایل یک backtest ساده را با NEW SYSTEM اجرا می‌کند.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_simple_backtest():
    """
    اجرای یک backtest ساده برای تست NEW SYSTEM
    """
    from backtest.backtest_engine_v2 import run_backtest_v2

    print("\n" + "="*70)
    print("🚀 Starting Backtest with NEW SYSTEM")
    print("="*70 + "\n")

    try:
        # اجرای backtest با تنظیمات پیش‌فرض
        # config_path: backtest/config_backtest_v2.yaml
        # main_config_path: config.yaml
        # scoring_method: 'new' (NEW SYSTEM)
        engine = await run_backtest_v2(
            scoring_method='new'  # استفاده از NEW SYSTEM scoring
        )

        print("\n" + "="*70)
        print("✅ Backtest Completed Successfully!")
        print("="*70)
        print(f"\n📊 Total trades: {engine.results['statistics']['total_trades']}")
        print(f"💰 Final equity: {engine.results['statistics']['current_equity']:.2f} USDT")
        print(f"📈 Total return: {engine.results['statistics']['total_return']:.2f}%")
        print(f"✅ Win rate: {engine.results['statistics']['win_rate']:.1f}%")

        print("\n🔍 NEW SYSTEM Metadata in Results:")
        if engine.results['trades']:
            # نمونه‌ای از یک trade
            sample_trade = engine.results['trades'][0]
            print(f"  - SL Method: {sample_trade.get('sl_method', 'N/A')}")
            print(f"  - Confidence Level: {sample_trade.get('confidence_level', 'N/A')}")
            print(f"  - Base Score: {sample_trade.get('base_score', 0):.2f}")
            print(f"  - Aggregation Method: {sample_trade.get('aggregation_method', 'N/A')}")
            print(f"  - Timeframes Count: {sample_trade.get('timeframes_count', 0)}")

        print("\n" + "="*70 + "\n")

        return engine

    except FileNotFoundError as e:
        logger.error(f"❌ Config file not found: {e}")
        logger.error("💡 Make sure you have:")
        logger.error("   - backtest/config_backtest_v2.yaml")
        logger.error("   - config.yaml")
        logger.error("   - backtest/config_scoring_new.yaml")
        raise

    except Exception as e:
        logger.error(f"❌ Backtest failed: {e}", exc_info=True)
        raise


async def run_quick_test():
    """
    تست سریع با داده‌های کم (برای بررسی سریع)
    """
    print("\n" + "="*70)
    print("⚡ Quick Test Mode (Limited Data)")
    print("="*70 + "\n")

    # TODO: پیاده‌سازی تست سریع با داده‌های محدود
    # این تابع می‌تواند یک backtest کوچک با 1-2 روز داده اجرا کند

    logger.info("Quick test mode not yet implemented")
    logger.info("Use run_simple_backtest() for full backtest")


def main():
    """Main entry point"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'quick':
        # حالت تست سریع
        asyncio.run(run_quick_test())
    else:
        # حالت backtest کامل
        asyncio.run(run_simple_backtest())


if __name__ == '__main__':
    main()
