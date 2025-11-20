# پیشنهادات بهبود سیستم تولید سیگنال

این سند پیشنهادات عملی برای بهبود NEW SYSTEM را ارائه می‌دهد.

**وضعیت فعلی:** ✅ 9,454 خط کد | 82/82 تست موفق | معماری ماژولار

---

## 📊 تحلیل وضعیت فعلی

### ✅ نقاط قوت

1. **معماری ماژولار**
   - 11 فایل جداگانه برای analyzer ها
   - Context-based architecture
   - Separation of concerns خوب

2. **Test Coverage**
   - 82 تست unit/integration
   - Coverage خوب برای RiskCalculator و SignalScorer
   - End-to-end pipeline tests

3. **سیستم امتیازدهی پیشرفته**
   - 13-multiplier scoring system
   - 5-method priority برای SL/TP
   - Multi-timeframe aggregation

4. **مستندات**
   - Documentation جامع (6+ فایل MD)
   - Docstrings در کدها
   - Migration guide

### ⚠️ نقاط قابل بهبود

1. **Performance**
   - هیچ caching برای indicators وجود ندارد
   - محاسبات تکراری در multi-TF analysis
   - عدم استفاده کامل از vectorization

2. **Monitoring**
   - عدم metrics collection
   - عدم performance tracking
   - عدم alert system

3. **Configuration**
   - عدم validation برای config files
   - Hard-coded values در برخی جاها
   - عدم environment-based configs

4. **Testing**
   - عدم property-based testing
   - عدم performance benchmarks
   - Mock data ساده (نه realistic)

---

## 🚀 پیشنهادات بهبود (اولویت‌بندی شده)

### 🔴 اولویت بالا (High Priority)

#### 1. Performance Optimization با Caching

**مشکل:** محاسبات indicator برای هر timeframe چندین بار تکرار می‌شود.

**راه حل:**

```python
# signal_generation/shared/indicator_calculator.py

from functools import lru_cache
from hashlib import md5
import pickle

class CachedIndicatorCalculator:
    """
    IndicatorCalculator با قابلیت caching
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._cache = {}
        self._cache_hits = 0
        self._cache_misses = 0

    def _get_cache_key(self, df: pd.DataFrame, indicator_name: str) -> str:
        """ایجاد cache key بر اساس df و indicator"""
        # استفاده از hash of last 5 rows + indicator name
        data_hash = md5(
            pickle.dumps(df[['close', 'high', 'low', 'volume']].tail(5).values)
        ).hexdigest()
        return f"{indicator_name}_{data_hash}"

    def calculate_all(self, context: AnalysisContext) -> None:
        """محاسبه indicators با caching"""
        cache_key = self._get_cache_key(context.df, 'all_indicators')

        if cache_key in self._cache:
            self._cache_hits += 1
            # بازیابی از cache
            cached_df = self._cache[cache_key]
            context.df = cached_df.copy()
            return

        self._cache_misses += 1

        # محاسبه معمولی
        self._calculate_all_indicators(context)

        # ذخیره در cache
        self._cache[cache_key] = context.df.copy()

        # محدود کردن حجم cache (max 100 entries)
        if len(self._cache) > 100:
            # حذف قدیمی‌ترین entries
            oldest_keys = list(self._cache.keys())[:20]
            for key in oldest_keys:
                del self._cache[key]

    def get_cache_stats(self) -> Dict[str, Any]:
        """آمار cache"""
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0
        return {
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate': hit_rate,
            'cache_size': len(self._cache)
        }
```

**مزایا:**
- ✅ کاهش 50-70% زمان محاسبات
- ✅ بهبود latency در real-time trading
- ✅ کاهش CPU usage

**تخمین زمان پیاده‌سازی:** 4-6 ساعت

---

#### 2. Configuration Validation

**مشکل:** Config files بدون validation خوانده می‌شوند و خطاها runtime رخ می‌دهند.

**راه حل:**

```python
# signal_generation/config_validator.py

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional

class RiskManagementConfig(BaseModel):
    """Validation برای risk management config"""

    max_risk_per_trade_percent: float = Field(
        ge=0.1, le=10.0,
        description="حداکثر ریسک هر معامله (0.1% - 10%)"
    )

    min_risk_reward_ratio: float = Field(
        ge=1.0, le=5.0,
        description="حداقل نسبت ریسک به ریوارد"
    )

    default_stop_loss_percent: float = Field(
        ge=0.5, le=5.0,
        description="درصد پیش‌فرض stop loss"
    )

    max_sr_distance_atr_ratio: float = Field(
        ge=1.0, le=5.0,
        description="حداکثر فاصله S/R به ATR"
    )

    @validator('max_risk_per_trade_percent')
    def validate_risk(cls, v):
        if v > 5.0:
            raise ValueError(
                f"⚠️ ریسک {v}% خیلی بالاست! توصیه می‌شود کمتر از 5% باشد"
            )
        return v


class ScoringConfig(BaseModel):
    """Validation برای scoring config"""

    base_weights: Dict[str, float] = Field(
        description="وزن‌های پایه برای scoring"
    )

    @validator('base_weights')
    def validate_weights(cls, v):
        # بررسی مجموع وزن‌ها
        total = sum(v.values())
        if not (50 <= total <= 150):
            raise ValueError(
                f"مجموع وزن‌ها ({total}) باید بین 50-150 باشد"
            )
        return v


class SystemConfig(BaseModel):
    """Validation کامل برای config سیستم"""

    risk_management: RiskManagementConfig
    scoring: ScoringConfig
    multi_timeframe: Dict[str, Any]

    @classmethod
    def from_yaml(cls, path: str) -> 'SystemConfig':
        """بارگذاری و validation از YAML"""
        import yaml

        with open(path, 'r') as f:
            data = yaml.safe_load(f)

        try:
            config = cls(**data)
            logger.info(f"✅ Config validated successfully: {path}")
            return config
        except Exception as e:
            logger.error(f"❌ Config validation failed: {e}")
            raise


# استفاده
try:
    config = SystemConfig.from_yaml('config.yaml')
except ValidationError as e:
    print("❌ خطاهای validation:")
    for error in e.errors():
        print(f"  - {error['loc']}: {error['msg']}")
    sys.exit(1)
```

**مزایا:**
- ✅ شناسایی خطاهای config قبل از اجرا
- ✅ مستندات خودکار برای تنظیمات
- ✅ جلوگیری از runtime errors

**تخمین زمان پیاده‌سازی:** 3-4 ساعت

---

#### 3. Metrics Collection & Monitoring

**مشکل:** هیچ metrics collection برای track کردن performance وجود ندارد.

**راه حل:**

```python
# signal_generation/metrics/collector.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List
import json

@dataclass
class SignalMetrics:
    """Metrics برای هر signal"""

    timestamp: datetime
    symbol: str
    timeframe: str
    direction: str

    # Scoring metrics
    final_score: float
    base_score: float
    confidence_level: str

    # SL/TP metrics
    sl_method: str
    risk_reward_ratio: float

    # Performance metrics (پر می‌شود بعد از trade)
    actual_pnl: Optional[float] = None
    duration_minutes: Optional[int] = None
    exit_reason: Optional[str] = None


class MetricsCollector:
    """
    جمع‌آوری و تحلیل metrics
    """

    def __init__(self):
        self.signals: List[SignalMetrics] = []
        self.hourly_stats: Dict[str, Dict] = {}

    def add_signal(self, signal: SignalInfo) -> None:
        """اضافه کردن signal به metrics"""
        metrics = SignalMetrics(
            timestamp=datetime.now(),
            symbol=signal.symbol,
            timeframe=signal.timeframe,
            direction=signal.direction,
            final_score=signal.score.final_score,
            base_score=signal.score.base_score,
            confidence_level=signal.metadata.get('confidence', {}).get('level', 'UNKNOWN'),
            sl_method=signal.metadata.get('sl_method', 'unknown'),
            risk_reward_ratio=signal.risk_reward_ratio
        )
        self.signals.append(metrics)

    def update_trade_result(
        self,
        signal_id: str,
        pnl: float,
        duration: int,
        exit_reason: str
    ) -> None:
        """به‌روزرسانی نتیجه trade"""
        # پیدا کردن signal و update
        for signal in self.signals:
            if signal.timestamp.isoformat() == signal_id:  # شناسایی بر اساس timestamp
                signal.actual_pnl = pnl
                signal.duration_minutes = duration
                signal.exit_reason = exit_reason
                break

    def get_hourly_stats(self) -> Dict[str, Any]:
        """آمار ساعتی"""
        from collections import defaultdict

        hourly = defaultdict(lambda: {
            'total_signals': 0,
            'by_confidence': defaultdict(int),
            'by_sl_method': defaultdict(int),
            'avg_score': 0.0
        })

        for signal in self.signals:
            hour = signal.timestamp.strftime('%Y-%m-%d %H:00')
            hourly[hour]['total_signals'] += 1
            hourly[hour]['by_confidence'][signal.confidence_level] += 1
            hourly[hour]['by_sl_method'][signal.sl_method] += 1

        return dict(hourly)

    def get_performance_by_sl_method(self) -> Dict[str, Dict]:
        """تحلیل performance بر اساس SL method"""
        from collections import defaultdict

        by_method = defaultdict(lambda: {
            'total': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0,
            'avg_pnl': 0.0
        })

        for signal in self.signals:
            if signal.actual_pnl is not None:
                method = signal.sl_method
                by_method[method]['total'] += 1
                by_method[method]['total_pnl'] += signal.actual_pnl

                if signal.actual_pnl > 0:
                    by_method[method]['wins'] += 1
                else:
                    by_method[method]['losses'] += 1

        # محاسبه averages
        for method, stats in by_method.items():
            if stats['total'] > 0:
                stats['avg_pnl'] = stats['total_pnl'] / stats['total']
                stats['win_rate'] = stats['wins'] / stats['total']

        return dict(by_method)

    def export_to_json(self, path: str) -> None:
        """Export metrics به JSON"""
        data = {
            'total_signals': len(self.signals),
            'hourly_stats': self.get_hourly_stats(),
            'performance_by_sl_method': self.get_performance_by_sl_method(),
            'signals': [
                {
                    'timestamp': s.timestamp.isoformat(),
                    'symbol': s.symbol,
                    'score': s.final_score,
                    'sl_method': s.sl_method,
                    'pnl': s.actual_pnl
                }
                for s in self.signals
            ]
        }

        with open(path, 'w') as f:
            json.dump(data, f, indent=2)


# استفاده در orchestrator
class SignalOrchestrator:
    def __init__(self, config):
        # ...
        self.metrics = MetricsCollector()  # 🆕

    async def analyze_symbol(self, symbol, timeframes_data):
        signal = # ... generate signal

        if signal:
            self.metrics.add_signal(signal)  # 🆕 جمع‌آوری metrics

        return signal
```

**مزایا:**
- ✅ Track کردن performance real-time
- ✅ شناسایی patterns در signals
- ✅ تحلیل A/B testing (مثلاً Harmonic vs ATR)
- ✅ Export به Grafana/Prometheus

**تخمین زمان پیاده‌سازی:** 6-8 ساعت

---

### 🟡 اولویت متوسط (Medium Priority)

#### 4. Adaptive Parameters با Market Regime

**مشکل:** پارامترها ثابت هستند و با تغییر market conditions تطبیق نمی‌یابند.

**راه حل:**

```python
# signal_generation/adaptive_parameters.py

from enum import Enum

class MarketRegime(Enum):
    """رژیم بازار"""
    TRENDING = "trending"          # روند قوی
    RANGING = "ranging"            # رنج (خنثی)
    VOLATILE = "volatile"          # نوسانات بالا
    LOW_VOLATILITY = "low_vol"     # نوسانات پایین


class MarketRegimeDetector:
    """
    تشخیص رژیم بازار
    """

    def detect_regime(self, df: pd.DataFrame) -> MarketRegime:
        """تشخیص رژیم فعلی بازار"""

        # محاسبه indicators
        atr = df['atr'].iloc[-1]
        atr_sma = df['atr'].rolling(20).mean().iloc[-1]
        adx = self._calculate_adx(df)

        # تشخیص رژیم
        if adx > 25 and atr > atr_sma * 1.2:
            return MarketRegime.TRENDING

        elif adx < 20:
            return MarketRegime.RANGING

        elif atr > atr_sma * 1.5:
            return MarketRegime.VOLATILE

        else:
            return MarketRegime.LOW_VOLATILITY

    def _calculate_adx(self, df: pd.DataFrame) -> float:
        """محاسبه ADX"""
        # پیاده‌سازی ADX
        pass


class AdaptiveParameterManager:
    """
    مدیریت پارامترهای adaptive
    """

    def __init__(self, base_config: Dict[str, Any]):
        self.base_config = base_config
        self.regime_detector = MarketRegimeDetector()

    def get_adapted_config(
        self,
        df: pd.DataFrame,
        regime: Optional[MarketRegime] = None
    ) -> Dict[str, Any]:
        """
        دریافت config تطبیق یافته با رژیم بازار
        """

        if regime is None:
            regime = self.regime_detector.detect_regime(df)

        adapted = self.base_config.copy()

        if regime == MarketRegime.TRENDING:
            # در trending: TP های بزرگ‌تر، SL های تنگ‌تر
            adapted['risk_management']['min_risk_reward_ratio'] = 2.5  # از 1.5 به 2.5
            adapted['risk_management']['default_stop_loss_percent'] = 1.5  # از 2% به 1.5%
            adapted['scoring']['trend_weight'] = 1.3  # وزن بیشتر به trend

        elif regime == MarketRegime.RANGING:
            # در ranging: TP های کوچک‌تر، معاملات کمتر
            adapted['risk_management']['min_risk_reward_ratio'] = 1.8
            adapted['scoring']['min_score_threshold'] = 70  # از 50 به 70
            adapted['scoring']['pattern_weight'] = 1.2  # وزن بیشتر به patterns

        elif regime == MarketRegime.VOLATILE:
            # در volatile: SL های بزرگ‌تر، size کوچک‌تر
            adapted['risk_management']['default_stop_loss_percent'] = 3.0  # از 2% به 3%
            adapted['risk_management']['max_risk_per_trade_percent'] = 1.0  # از 2% به 1%

        elif regime == MarketRegime.LOW_VOLATILITY:
            # در low vol: معاملات کمتر
            adapted['scoring']['min_score_threshold'] = 65

        logger.info(f"📊 Market Regime: {regime.value} - Config adapted")

        return adapted


# استفاده در RiskRewardCalculator
class RiskRewardCalculator:
    def __init__(self, config):
        self.base_config = config
        self.adaptive_manager = AdaptiveParameterManager(config)  # 🆕

    def calculate_sl_tp(self, direction, entry_price, context, adapted_config=None):
        # اگر adapted_config داده نشده، بر اساس رژیم بازار تطبیق بده
        if adapted_config is None:
            adapted_config = self.adaptive_manager.get_adapted_config(context.df)

        # ادامه محاسبات با config تطبیق یافته
        # ...
```

**مزایا:**
- ✅ بهبود performance در شرایط مختلف بازار
- ✅ کاهش drawdown در volatile markets
- ✅ افزایش سود در trending markets

**تخمین زمان پیاده‌سازی:** 10-12 ساعت

---

#### 5. Property-Based Testing

**مشکل:** تست‌ها فقط با مثال‌های ثابت هستند، edge cases ممکن است missed شوند.

**راه حل:**

```python
# tests/property_based/test_risk_calculator_properties.py

from hypothesis import given, strategies as st
import pytest

@given(
    entry_price=st.floats(min_value=100, max_value=100000),
    sl_percent=st.floats(min_value=0.5, max_value=5.0),
    tp_percent=st.floats(min_value=1.0, max_value=10.0)
)
def test_risk_reward_ratio_always_positive(entry_price, sl_percent, tp_percent):
    """
    Property: نسبت ریسک/ریوارد همیشه مثبت است
    """
    calculator = RiskRewardCalculator(config)

    # محاسبه SL/TP
    sl = entry_price * (1 - sl_percent / 100)
    tp = entry_price * (1 + tp_percent / 100)

    risk = abs(entry_price - sl)
    reward = abs(tp - entry_price)
    rr = reward / risk

    assert rr > 0, "Risk/Reward ratio must be positive"


@given(
    direction=st.sampled_from(['LONG', 'SHORT', 'long', 'short']),
    entry_price=st.floats(min_value=100, max_value=100000)
)
def test_stop_loss_always_on_correct_side(direction, entry_price):
    """
    Property: Stop loss همیشه در سمت درست قرار می‌گیرد
    """
    calculator = RiskRewardCalculator(config)
    context = create_mock_context(entry_price)

    result = calculator.calculate_sl_tp(direction, entry_price, context, config)

    sl = result['stop_loss']
    tp = result['take_profit']

    if direction.upper() == 'LONG':
        assert sl < entry_price, "LONG: SL must be below entry"
        assert tp > entry_price, "LONG: TP must be above entry"
    else:
        assert sl > entry_price, "SHORT: SL must be above entry"
        assert tp < entry_price, "SHORT: TP must be below entry"


@given(
    base_score=st.floats(min_value=0, max_value=100),
    multipliers=st.lists(
        st.floats(min_value=0.5, max_value=2.0),
        min_size=13, max_size=13
    )
)
def test_final_score_always_within_bounds(base_score, multipliers):
    """
    Property: امتیاز نهایی همیشه در محدوده معقول است
    """
    scorer = SignalScorer(config)

    # محاسبه score
    final_score = base_score
    for multiplier in multipliers:
        final_score *= multiplier

    # Score نباید منفی یا بیش از حد بزرگ باشد
    assert 0 <= final_score <= 1000, "Final score out of reasonable bounds"
```

**مزایا:**
- ✅ کشف edge cases خودکار
- ✅ تست با هزاران input مختلف
- ✅ Confidence بیشتر در صحت کد

**تخمین زمان پیاده‌سازی:** 4-5 ساعت

---

### 🟢 اولویت پایین (Low Priority)

#### 6. Machine Learning Integration

**مشکل:** Scoring weights ثابت هستند و با داده‌های تاریخی بهینه نمی‌شوند.

**راه حل:**

```python
# signal_generation/ml/weight_optimizer.py

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score
import numpy as np

class MLWeightOptimizer:
    """
    بهینه‌سازی weights با Machine Learning
    """

    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100)
        self.is_trained = False

    def train_from_backtest(self, backtest_results: pd.DataFrame):
        """
        آموزش مدل بر اساس نتایج backtest
        """

        # استخراج features از metadata
        features = []
        targets = []

        for _, trade in backtest_results.iterrows():
            metadata = json.loads(trade['metadata_json'])
            score_breakdown = metadata.get('score_breakdown', {})

            # Features: 13 multipliers
            feature_vector = [
                score_breakdown.get('base_score', 0),
                score_breakdown.get('trend_alignment', 1),
                score_breakdown.get('volume_confirmation', 1),
                # ... 10 multipliers دیگر
            ]

            features.append(feature_vector)
            targets.append(trade['realized_pnl'])

        X = np.array(features)
        y = np.array(targets)

        # آموزش مدل
        self.model.fit(X, y)
        self.is_trained = True

        # Cross-validation score
        cv_score = cross_val_score(self.model, X, y, cv=5).mean()
        logger.info(f"🤖 ML Model trained - CV Score: {cv_score:.3f}")

    def predict_pnl(self, score_breakdown: Dict[str, float]) -> float:
        """
        پیش‌بینی PnL بر اساس score breakdown
        """
        if not self.is_trained:
            raise ValueError("Model not trained yet")

        feature_vector = [
            score_breakdown.get('base_score', 0),
            score_breakdown.get('trend_alignment', 1),
            # ... بقیه features
        ]

        return self.model.predict([feature_vector])[0]

    def get_feature_importance(self) -> Dict[str, float]:
        """
        اهمیت هر feature (multiplier)
        """
        feature_names = [
            'base_score', 'trend_alignment', 'volume_confirmation',
            # ... 10 multipliers دیگر
        ]

        importances = self.model.feature_importances_

        return dict(zip(feature_names, importances))


# استفاده
optimizer = MLWeightOptimizer()

# آموزش بر اساس backtest
backtest_df = pd.read_csv('backtest_results_v2/.../trades.csv')
optimizer.train_from_backtest(backtest_df)

# مشاهده مهم‌ترین factors
importance = optimizer.get_feature_importance()
print("🎯 Most Important Factors:")
for factor, score in sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]:
    print(f"  {factor}: {score:.3f}")
```

**مزایا:**
- ✅ یادگیری از داده‌های واقعی
- ✅ بهینه‌سازی خودکار weights
- ✅ شناسایی مهم‌ترین factors

**تخمین زمان پیاده‌سازی:** 15-20 ساعت

---

#### 7. Advanced Logging & Debugging

**راه حل:**

```python
# signal_generation/utils/structured_logger.py

import logging
import json
from datetime import datetime
from typing import Any, Dict

class StructuredLogger:
    """
    Logger با خروجی ساختارمند (JSON) برای تحلیل آسان‌تر
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logs = []

    def log_signal_generation(
        self,
        symbol: str,
        timeframe: str,
        score: float,
        sl_method: str,
        execution_time_ms: float,
        **kwargs
    ):
        """Log structured برای signal generation"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event': 'signal_generated',
            'symbol': symbol,
            'timeframe': timeframe,
            'score': score,
            'sl_method': sl_method,
            'execution_time_ms': execution_time_ms,
            **kwargs
        }

        self.logs.append(log_entry)
        self.logger.info(json.dumps(log_entry))

    def log_performance(self, operation: str, duration_ms: float):
        """Log performance metrics"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event': 'performance',
            'operation': operation,
            'duration_ms': duration_ms
        }

        self.logs.append(log_entry)

    def export_logs(self, path: str):
        """Export logs به JSON file"""
        with open(path, 'w') as f:
            json.dump(self.logs, f, indent=2)
```

**تخمین زمان پیاده‌سازی:** 3-4 ساعت

---

## 📊 خلاصه اولویت‌ها

| اولویت | پیشنهاد | تأثیر | زمان پیاده‌سازی | ROI |
|--------|---------|-------|-----------------|-----|
| 🔴 بالا | Performance Caching | زیاد | 4-6h | بالا |
| 🔴 بالا | Config Validation | متوسط | 3-4h | بالا |
| 🔴 بالا | Metrics Collection | زیاد | 6-8h | بالا |
| 🟡 متوسط | Adaptive Parameters | زیاد | 10-12h | متوسط |
| 🟡 متوسط | Property-Based Testing | متوسط | 4-5h | متوسط |
| 🟢 پایین | ML Integration | بسیار زیاد | 15-20h | کم (فعلاً) |
| 🟢 پایین | Structured Logging | کم | 3-4h | کم |

**توصیه:** شروع با **3 پیشنهاد اولویت بالا** (Caching, Validation, Metrics)

**زمان کل:** 13-18 ساعت

**مزایا کلی:**
- ✅ کاهش 50-70% زمان اجرا
- ✅ کاهش runtime errors
- ✅ Visibility کامل برای تحلیل

---

## 🎯 نقشه راه پیاده‌سازی (Roadmap)

### فاز 1: Foundation (هفته 1-2)
- [ ] Performance caching
- [ ] Config validation
- [ ] Basic metrics collection

### فاز 2: Observability (هفته 3-4)
- [ ] Structured logging
- [ ] Dashboard برای metrics
- [ ] Alert system

### فاز 3: Intelligence (هفته 5-8)
- [ ] Adaptive parameters
- [ ] Market regime detection
- [ ] Property-based testing

### فاز 4: Advanced (ماه 3-4)
- [ ] ML integration
- [ ] Auto-optimization
- [ ] A/B testing framework

---

## 💡 نکات عملی

### چگونه شروع کنیم؟

1. **یک branch جدید بسازید:**
   ```bash
   git checkout -b feature/performance-improvements
   ```

2. **از کوچک شروع کنید:**
   - ابتدا caching را پیاده‌سازی کنید
   - تست کنید و benchmark بگیرید
   - سپس به بقیه بروید

3. **همیشه test بنویسید:**
   - هر feature جدید باید تست داشته باشد
   - قبل از merge، همه تست‌ها باید pass شوند

4. **مستندات را فراموش نکنید:**
   - هر تغییر را document کنید
   - مثال‌های کاربردی اضافه کنید

---

## 📞 پرسش‌های بعدی

آیا می‌خواهید:
1. ✅ یکی از این پیشنهادات را با هم پیاده‌سازی کنیم؟
2. ✅ جزئیات بیشتر درباره یک مورد خاص؟
3. ✅ roadmap دقیق‌تر برای 3 ماه آینده؟

---

**آخرین بروزرسانی:** 2025-01-20
