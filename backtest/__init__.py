"""
Backtest Package - نسخه 2 با SignalOrchestrator

این پکیج شامل تمام کامپوننت‌های لازم برای بک‌تست ربات معاملاتی است.

نسخه 2 تفاوت‌های کلیدی:
- استفاده از SignalOrchestrator به جای SignalGenerator
- معماری ماژولار signal_generation
- پشتیبانی از 10 Analyzer مستقل
- Context-Based Architecture

Components:
- BacktestEngineV2: موتور اصلی بک‌تست
- BacktestTradeManager: مدیریت معاملات
- CSVDataLoader: بارگذاری داده‌های CSV
- HistoricalDataProvider: ارائه داده‌های تاریخی
- TimeSimulator: شبیه‌ساز زمان

Author: Refactored for SignalOrchestrator
Date: 2025-10-23
"""

# Import classes from their respective modules
from backtest.backtest_engine_v2 import BacktestEngineV2, run_backtest_v2
from backtest.backtest_trade_manager import BacktestTradeManager
from backtest.csv_data_loader import CSVDataLoader
from backtest.historical_data_provider_v2 import HistoricalDataProvider, BacktestMarketDataFetcher
from backtest.time_simulator import TimeSimulator

__version__ = '2.0.0'
__all__ = [
    'BacktestEngineV2',
    'run_backtest_v2',
    'BacktestTradeManager',
    'CSVDataLoader',
    'HistoricalDataProvider',
    'BacktestMarketDataFetcher',
    'TimeSimulator',
]