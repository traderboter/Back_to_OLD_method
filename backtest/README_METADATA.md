# راهنمای استفاده از Metadata در Backtest

## مقدمه

از این به بعد، هر معامله در backtest شامل یک ستون `metadata_json` است که اطلاعات کامل سیگنال تولید شده را در خود دارد.

## ساختار Metadata

### 1. اطلاعات کلی

```json
{
  "aggregation_method": "multi_timeframe_old_system",
  "direction": "LONG",
  "final_score": 75.5,
  "alignment_factor": 0.85,
  "volume_factor": 0.90,
  "htf_factor": 1.2,
  "volatility_factor": 0.95
}
```

### 2. Confidence Metrics

```json
{
  "confidence": {
    "level": "high",
    "overall": 0.82,
    "timeframe_consensus": 0.85,
    "score_quality": 0.78,
    "direction_clarity": 0.88,
    "htf_alignment": 0.90,
    "volume_confirmation": 0.90,
    "is_uncertain": false,
    "requires_review": false
  }
}
```

### 3. اطلاعات هر تایم‌فریم

برای هر تایم‌فریم (5m, 15m, 1h, 4h):

```json
{
  "timeframes": {
    "1h": {
      "indicators": {
        "close": 45123.50,
        "rsi": 58.3,
        "macd": 88.2,
        "macd_signal": 75.1,
        "ema_20": 44900.0,
        "ema_50": 44700.0,
        "volume": 8500000
      },
      "analyzers": {
        "trend": {
          "direction": "bullish",
          "strength": 8.2,
          "phase": "early"
        },
        "momentum": {
          "direction": "bullish",
          "strength": 7.8,
          "macd_market_type": "A_bullish_strong"
        },
        "patterns": {
          "strongest_pattern": {
            "name": "hammer",
            "confidence": 0.78,
            "candles_ago": 1
          }
        },
        "volume": {
          "is_confirmed": true,
          "strength": 1.35,
          "trend": "increasing"
        }
      },
      "signal_direction": "LONG",
      "signal_score": 78.1,
      "volume_confirmed": true,
      "htf_aligned": true
    }
  }
}
```

## نحوه استفاده

### 1. خواندن فایل CSV

```python
import pandas as pd
import json

# خواندن نتایج backtest
df = pd.read_csv('backtest_results/v2_20251118_044031/trades.csv')

# Parse کردن metadata
df['metadata'] = df['metadata_json'].apply(lambda x: json.loads(x) if x != '{}' else {})

# نمایش اولین معامله
print(df.iloc[0]['metadata'])
```

### 2. تحلیل الگوها

```python
# الگوهایی که در معاملات موفق شناسایی شده
winning_trades = df[df['realized_pnl'] > 0]

patterns = []
for _, trade in winning_trades.iterrows():
    metadata = trade['metadata']
    if metadata and 'timeframes' in metadata:
        for tf, tf_data in metadata['timeframes'].items():
            if 'analyzers' in tf_data and 'patterns' in tf_data['analyzers']:
                pattern = tf_data['analyzers']['patterns'].get('strongest_pattern')
                if pattern:
                    patterns.append({
                        'trade_id': trade['trade_id'],
                        'timeframe': tf,
                        'pattern': pattern['name'],
                        'confidence': pattern['confidence'],
                        'pnl': trade['realized_pnl']
                    })

patterns_df = pd.DataFrame(patterns)
print(patterns_df.groupby('pattern')['pnl'].agg(['count', 'mean', 'sum']))
```

### 3. تحلیل اندیکاتورها

```python
# بررسی RSI در زمان ورود به معاملات
for _, trade in df.iterrows():
    metadata = trade['metadata']
    if metadata and 'timeframes' in metadata:
        for tf, tf_data in metadata['timeframes'].items():
            if 'indicators' in tf_data:
                rsi = tf_data['indicators'].get('rsi')
                print(f"Trade {trade['trade_id']} - {tf} RSI: {rsi:.1f}")
```

### 4. تحلیل Confidence

```python
# معاملاتی که confidence پایین داشتند
low_confidence = []
for _, trade in df.iterrows():
    metadata = trade['metadata']
    if metadata and 'confidence' in metadata:
        conf = metadata['confidence']
        if conf.get('overall', 1.0) < 0.7:
            low_confidence.append({
                'trade_id': trade['trade_id'],
                'confidence': conf['overall'],
                'level': conf['level'],
                'pnl': trade['realized_pnl']
            })

low_conf_df = pd.DataFrame(low_confidence)
print(f"معاملات با confidence پایین: {len(low_conf_df)}")
print(f"PnL میانگین: {low_conf_df['pnl'].mean():.2f}")
```

### 5. تحلیل Multi-Timeframe Consensus

```python
# بررسی هماهنگی بین تایم‌فریم‌ها
high_consensus = df[
    df['metadata'].apply(
        lambda m: m.get('confidence', {}).get('timeframe_consensus', 0) > 0.85
    )
]

print(f"معاملات با consensus بالا: {len(high_consensus)}")
print(f"Win rate: {(high_consensus['realized_pnl'] > 0).mean():.1%}")
```

## موارد قابل تحلیل

با استفاده از metadata می‌توانید:

✅ **الگوها:**
- کدام الگوها موفق‌ترند؟
- در چه تایم‌فریمی الگوها قابل اعتمادترند؟
- confidence الگو چه تاثیری بر نتیجه دارد؟

✅ **اندیکاتورها:**
- بهترین مقادیر RSI برای ورود
- تاثیر MACD market type بر موفقیت
- نقش EMA alignment در سیگنال‌ها

✅ **Confidence:**
- آیا معاملات با confidence بالا موفق‌ترند؟
- چه عواملی confidence را افزایش می‌دهند؟
- آیا معاملات uncertain باید رد شوند؟

✅ **Multi-Timeframe:**
- چه میزان consensus بین TF ها نیاز است؟
- کدام تایم‌فریم‌ها مهم‌ترند؟
- تاثیر HTF alignment چقدر است؟

✅ **Trend Phase:**
- کدام فاز trend موفق‌تر است؟ (early, developing, mature, late)
- آیا معاملات در فاز late ریسک بالاتری دارند؟

✅ **Volume Confirmation:**
- تاثیر تایید حجم بر موفقیت
- چه میزان از معاملات موفق volume confirmed بودند؟

## مثال جامع: اسکریپت تحلیل

```python
import pandas as pd
import json
import matplotlib.pyplot as plt

def analyze_backtest_metadata(csv_path):
    """تحلیل کامل metadata از backtest"""

    # خواندن داده
    df = pd.read_csv(csv_path)
    df['metadata'] = df['metadata_json'].apply(
        lambda x: json.loads(x) if x != '{}' else {}
    )

    # فیلتر معاملات با metadata
    df_with_meta = df[df['metadata'].apply(lambda x: bool(x))]

    print(f"تعداد کل معاملات: {len(df)}")
    print(f"معاملات با metadata: {len(df_with_meta)}")

    # تحلیل confidence
    df_with_meta['confidence_overall'] = df_with_meta['metadata'].apply(
        lambda m: m.get('confidence', {}).get('overall', 0)
    )
    df_with_meta['confidence_level'] = df_with_meta['metadata'].apply(
        lambda m: m.get('confidence', {}).get('level', 'unknown')
    )

    print("\n=== تحلیل Confidence ===")
    print(df_with_meta.groupby('confidence_level').agg({
        'realized_pnl': ['count', 'mean', 'sum'],
        'confidence_overall': 'mean'
    }))

    # تحلیل الگوها
    print("\n=== الگوهای شناسایی شده ===")
    patterns = []
    for _, trade in df_with_meta.iterrows():
        metadata = trade['metadata']
        if 'timeframes' in metadata:
            for tf, tf_data in metadata['timeframes'].items():
                analyzers = tf_data.get('analyzers', {})
                pattern_data = analyzers.get('patterns', {})
                strongest = pattern_data.get('strongest_pattern')
                if strongest:
                    patterns.append({
                        'pattern': strongest['name'],
                        'confidence': strongest['confidence'],
                        'timeframe': tf,
                        'pnl': trade['realized_pnl']
                    })

    if patterns:
        patterns_df = pd.DataFrame(patterns)
        print(patterns_df.groupby('pattern').agg({
            'pnl': ['count', 'mean', 'sum'],
            'confidence': 'mean'
        }).round(2))

    # رسم نمودار
    plt.figure(figsize=(12, 6))

    # نمودار 1: PnL بر اساس confidence
    plt.subplot(1, 2, 1)
    df_with_meta.plot.scatter(
        x='confidence_overall',
        y='realized_pnl',
        c='realized_pnl',
        cmap='RdYlGn',
        ax=plt.gca()
    )
    plt.axhline(y=0, color='black', linestyle='--', alpha=0.3)
    plt.title('PnL vs Confidence')
    plt.xlabel('Overall Confidence')
    plt.ylabel('Realized PnL (USDT)')

    # نمودار 2: توزیع confidence
    plt.subplot(1, 2, 2)
    df_with_meta['confidence_overall'].hist(bins=20)
    plt.title('Distribution of Confidence')
    plt.xlabel('Confidence')
    plt.ylabel('Count')

    plt.tight_layout()
    plt.savefig('backtest_metadata_analysis.png')
    print("\n📊 نمودار ذخیره شد: backtest_metadata_analysis.png")

# استفاده:
# analyze_backtest_metadata('backtest_results/v2_20251118_044031/trades.csv')
```

## نتیجه‌گیری

با استفاده از metadata کامل، می‌توانید:
- دقیقا بدانید چرا هر معامله باز شد
- بهترین الگوها و شرایط را شناسایی کنید
- پارامترهای سیستم را بهینه کنید
- معاملات پرریسک را از قبل تشخیص دهید
- کیفیت سیگنال‌ها را بهبود بخشید

**توجه:** برای دیدن نمونه کامل metadata، فایل `test_metadata_example.py` را اجرا کنید:
```bash
python test_metadata_example.py
```
