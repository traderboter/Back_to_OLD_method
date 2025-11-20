#!/usr/bin/env python3
"""
تحلیل نتایج بک‌تست برای تأیید اینکه Stop Loss و Target پویا هستند و بر اساس ATR محاسبه می‌شوند
"""

import pandas as pd
import json
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

# تنظیمات نمایش
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
sns.set_style('whitegrid')


def load_trades(csv_path):
    """بارگذاری فایل CSV معاملات"""
    print(f"📂 Loading trades from: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"✅ Loaded {len(df)} trades")
    return df


def extract_atr_from_metadata(metadata_str):
    """استخراج ATR از رشته JSON متادیتا"""
    try:
        metadata = json.loads(metadata_str)
        return metadata.get('indicators', {}).get('atr', None)
    except:
        return None


def calculate_sl_metrics(df):
    """محاسبه معیارهای مربوط به Stop Loss"""

    # استخراج ATR از metadata
    print("\n🔍 Extracting ATR from metadata...")
    df['atr'] = df['metadata_json'].apply(extract_atr_from_metadata)

    # محاسبه فاصله SL از قیمت ورود
    print("📏 Calculating SL distances...")
    df['sl_distance'] = abs(df['entry_price'] - df['stop_loss'])

    # محاسبه فاصله Target از قیمت ورود
    df['target_distance'] = abs(df['take_profit'] - df['entry_price'])

    # محاسبه ATR Percent (نسبت به قیمت ورود)
    df['atr_percent'] = (df['atr'] / df['entry_price']) * 100

    # تعیین Volatility Regime بر اساس ATR%
    def get_volatility_regime(atr_pct):
        if pd.isna(atr_pct):
            return 'unknown'
        elif atr_pct < 0.5:
            return 'low'
        elif atr_pct <= 1.5:
            return 'normal'
        else:
            return 'high'

    df['volatility_regime'] = df['atr_percent'].apply(get_volatility_regime)

    # محاسبه Multiplier (SL_distance / ATR)
    df['sl_atr_multiplier'] = df['sl_distance'] / df['atr']

    # محاسبه Risk-Reward Ratio
    df['rr_ratio'] = df['target_distance'] / df['sl_distance']

    return df


def analyze_sl_variability(df):
    """بررسی اینکه آیا SL ثابت است یا متغیر"""

    print("\n" + "="*80)
    print("📊 ANALYSIS 1: Stop Loss Variability")
    print("="*80)

    # آمار توصیفی SL Distance
    sl_stats = df['sl_distance'].describe()
    print("\n📈 Stop Loss Distance Statistics:")
    print(sl_stats)

    # محاسبه ضریب تغییرات (CV)
    cv = (df['sl_distance'].std() / df['sl_distance'].mean()) * 100
    print(f"\n📉 Coefficient of Variation (CV): {cv:.2f}%")

    if cv < 5:
        print("❌ RESULT: Stop Loss appears to be FIXED (low variability)")
    elif cv < 20:
        print("⚠️  RESULT: Stop Loss has LIMITED variability")
    else:
        print("✅ RESULT: Stop Loss is DYNAMIC (high variability)")

    # بررسی تعداد مقادیر یکتا
    unique_sl = df['sl_distance'].nunique()
    total_trades = len(df)
    uniqueness_ratio = (unique_sl / total_trades) * 100

    print(f"\n🔢 Unique SL values: {unique_sl} out of {total_trades} trades ({uniqueness_ratio:.1f}%)")

    if uniqueness_ratio > 80:
        print("✅ RESULT: High uniqueness suggests DYNAMIC calculation")
    elif uniqueness_ratio > 50:
        print("⚠️  RESULT: Moderate uniqueness")
    else:
        print("❌ RESULT: Low uniqueness suggests possible FIXED values")


def analyze_atr_correlation(df):
    """بررسی همبستگی بین ATR و SL Distance"""

    print("\n" + "="*80)
    print("📊 ANALYSIS 2: ATR Correlation with SL Distance")
    print("="*80)

    # حذف ردیف‌هایی که ATR ندارند
    df_clean = df.dropna(subset=['atr', 'sl_distance'])

    if len(df_clean) == 0:
        print("❌ No ATR data available for analysis")
        return

    # محاسبه همبستگی
    correlation = df_clean['atr'].corr(df_clean['sl_distance'])
    print(f"\n📈 Correlation between ATR and SL Distance: {correlation:.4f}")

    if correlation > 0.8:
        print("✅ RESULT: STRONG positive correlation - SL is ATR-based")
    elif correlation > 0.5:
        print("⚠️  RESULT: MODERATE positive correlation")
    else:
        print("❌ RESULT: WEAK correlation - SL may not be ATR-based")


def analyze_sl_multipliers(df):
    """تحلیل Multiplier (SL_distance / ATR) و مقایسه با volatility regime"""

    print("\n" + "="*80)
    print("📊 ANALYSIS 3: SL-ATR Multipliers by Volatility Regime")
    print("="*80)

    df_clean = df.dropna(subset=['sl_atr_multiplier', 'volatility_regime'])

    if len(df_clean) == 0:
        print("❌ No data available for analysis")
        return

    # آمار Multiplier برای هر Volatility Regime
    print("\n📊 SL-ATR Multiplier Statistics by Volatility Regime:")
    print("-" * 80)

    regime_stats = df_clean.groupby('volatility_regime')['sl_atr_multiplier'].agg([
        ('count', 'count'),
        ('mean', 'mean'),
        ('median', 'median'),
        ('std', 'std'),
        ('min', 'min'),
        ('max', 'max')
    ]).round(2)

    print(regime_stats)

    # مقایسه با مقادیر توصیه شده
    print("\n📋 Expected Multipliers (from documentation):")
    print("   • Low volatility:    1.5× ATR")
    print("   • Normal volatility: 2.0× ATR")
    print("   • High volatility:   3.0× ATR")

    print("\n🔍 Checking if actual multipliers match expected values:")

    expected_multipliers = {
        'low': 1.5,
        'normal': 2.0,
        'high': 3.0
    }

    for regime in ['low', 'normal', 'high']:
        if regime in regime_stats.index:
            actual = regime_stats.loc[regime, 'mean']
            expected = expected_multipliers[regime]
            diff = abs(actual - expected)
            diff_pct = (diff / expected) * 100

            if diff_pct < 10:
                status = "✅ MATCH"
            elif diff_pct < 25:
                status = "⚠️  CLOSE"
            else:
                status = "❌ MISMATCH"

            print(f"   {regime.upper():8} - Expected: {expected:.1f}x, Actual: {actual:.2f}x, Diff: {diff_pct:.1f}% {status}")


def analyze_rr_ratios(df):
    """تحلیل Risk-Reward Ratios"""

    print("\n" + "="*80)
    print("📊 ANALYSIS 4: Risk-Reward Ratio Analysis")
    print("="*80)

    df_clean = df.dropna(subset=['rr_ratio'])

    if len(df_clean) == 0:
        print("❌ No RR ratio data available")
        return

    # آمار توصیفی
    rr_stats = df_clean['rr_ratio'].describe()
    print("\n📈 Risk-Reward Ratio Statistics:")
    print(rr_stats)

    print("\n📋 Expected Range: 1.8 - 3.0")

    # بررسی اینکه چند درصد در محدوده مورد انتظار هستند
    in_range = df_clean['rr_ratio'].between(1.8, 3.0).sum()
    total = len(df_clean)
    pct_in_range = (in_range / total) * 100

    print(f"\n✅ {in_range} out of {total} trades ({pct_in_range:.1f}%) have RR ratio in expected range")

    if pct_in_range > 80:
        print("✅ RESULT: Most trades follow expected RR ratio guidelines")
    elif pct_in_range > 50:
        print("⚠️  RESULT: Moderate adherence to RR ratio guidelines")
    else:
        print("❌ RESULT: Many trades deviate from expected RR ratio")


def analyze_by_direction(df):
    """تحلیل جداگانه برای معاملات LONG و SHORT"""

    print("\n" + "="*80)
    print("📊 ANALYSIS 5: Comparison of LONG vs SHORT Trades")
    print("="*80)

    df_clean = df.dropna(subset=['sl_atr_multiplier', 'rr_ratio'])

    if len(df_clean) == 0:
        print("❌ No data available")
        return

    print("\n📊 Statistics by Trade Direction:")
    print("-" * 80)

    direction_stats = df_clean.groupby('direction').agg({
        'sl_atr_multiplier': ['mean', 'std', 'min', 'max'],
        'rr_ratio': ['mean', 'std', 'min', 'max'],
        'trade_id': 'count'
    }).round(2)

    print(direction_stats)

    # بررسی اینکه آیا LONG و SHORT تقریباً یکسان هستند
    if 'long' in df_clean['direction'].str.lower().values and 'short' in df_clean['direction'].str.lower().values:
        long_avg = df_clean[df_clean['direction'].str.lower() == 'long']['sl_atr_multiplier'].mean()
        short_avg = df_clean[df_clean['direction'].str.lower() == 'short']['sl_atr_multiplier'].mean()

        diff_pct = abs(long_avg - short_avg) / ((long_avg + short_avg) / 2) * 100

        print(f"\n🔍 SL Multiplier difference between LONG and SHORT: {diff_pct:.1f}%")

        if diff_pct < 10:
            print("✅ RESULT: LONG and SHORT use similar SL logic (DYNAMIC)")
        else:
            print("⚠️  RESULT: LONG and SHORT have different SL logic")


def create_visualizations(df):
    """ایجاد نمودارهای تحلیلی"""

    print("\n" + "="*80)
    print("📊 Creating Visualizations...")
    print("="*80)

    df_clean = df.dropna(subset=['atr', 'sl_distance', 'sl_atr_multiplier', 'rr_ratio'])

    if len(df_clean) < 10:
        print("❌ Insufficient data for visualizations")
        return

    # ایجاد figure با 6 subplot
    fig, axes = plt.subplots(3, 2, figsize=(16, 18))
    fig.suptitle('Dynamic Stop Loss & Target Analysis', fontsize=16, fontweight='bold')

    # 1. Scatter: ATR vs SL Distance
    ax1 = axes[0, 0]
    ax1.scatter(df_clean['atr'], df_clean['sl_distance'], alpha=0.5, s=30)
    ax1.set_xlabel('ATR')
    ax1.set_ylabel('SL Distance')
    ax1.set_title('ATR vs Stop Loss Distance')
    ax1.grid(True, alpha=0.3)

    # خط رگرسیون
    z = np.polyfit(df_clean['atr'], df_clean['sl_distance'], 1)
    p = np.poly1d(z)
    ax1.plot(df_clean['atr'], p(df_clean['atr']), "r--", alpha=0.8, linewidth=2,
             label=f'Linear fit: y={z[0]:.2f}x+{z[1]:.2f}')
    ax1.legend()

    # 2. Histogram: SL Distance Distribution
    ax2 = axes[0, 1]
    ax2.hist(df_clean['sl_distance'], bins=50, alpha=0.7, color='steelblue', edgecolor='black')
    ax2.set_xlabel('SL Distance')
    ax2.set_ylabel('Frequency')
    ax2.set_title('Stop Loss Distance Distribution')
    ax2.axvline(df_clean['sl_distance'].mean(), color='red', linestyle='--',
                linewidth=2, label=f'Mean: {df_clean["sl_distance"].mean():.2f}')
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')

    # 3. Boxplot: SL Multiplier by Volatility Regime
    ax3 = axes[1, 0]
    df_clean.boxplot(column='sl_atr_multiplier', by='volatility_regime', ax=ax3)
    ax3.set_xlabel('Volatility Regime')
    ax3.set_ylabel('SL-ATR Multiplier')
    ax3.set_title('SL-ATR Multiplier by Volatility Regime')
    ax3.get_figure().suptitle('')  # حذف عنوان اضافی

    # خطوط راهنما برای مقادیر توصیه شده
    ax3.axhline(1.5, color='green', linestyle=':', linewidth=1.5, alpha=0.7, label='Low (1.5x)')
    ax3.axhline(2.0, color='orange', linestyle=':', linewidth=1.5, alpha=0.7, label='Normal (2.0x)')
    ax3.axhline(3.0, color='red', linestyle=':', linewidth=1.5, alpha=0.7, label='High (3.0x)')
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')

    # 4. Histogram: Risk-Reward Ratio
    ax4 = axes[1, 1]
    ax4.hist(df_clean['rr_ratio'], bins=50, alpha=0.7, color='green', edgecolor='black')
    ax4.set_xlabel('Risk-Reward Ratio')
    ax4.set_ylabel('Frequency')
    ax4.set_title('Risk-Reward Ratio Distribution')
    ax4.axvline(1.8, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Min Expected: 1.8')
    ax4.axvline(3.0, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Max Expected: 3.0')
    ax4.axvline(df_clean['rr_ratio'].mean(), color='blue', linestyle='-',
                linewidth=2, label=f'Mean: {df_clean["rr_ratio"].mean():.2f}')
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')

    # 5. Scatter: Entry Price vs SL Multiplier
    ax5 = axes[2, 0]
    scatter = ax5.scatter(df_clean['entry_price'], df_clean['sl_atr_multiplier'],
                          c=df_clean['atr_percent'], cmap='viridis', alpha=0.6, s=30)
    ax5.set_xlabel('Entry Price')
    ax5.set_ylabel('SL-ATR Multiplier')
    ax5.set_title('Entry Price vs SL Multiplier (colored by ATR%)')
    plt.colorbar(scatter, ax=ax5, label='ATR %')
    ax5.grid(True, alpha=0.3)

    # 6. Comparison: LONG vs SHORT
    ax6 = axes[2, 1]
    direction_data = []
    direction_labels = []
    for direction in df_clean['direction'].unique():
        direction_data.append(df_clean[df_clean['direction'] == direction]['sl_atr_multiplier'])
        direction_labels.append(direction.upper())

    bp = ax6.boxplot(direction_data, labels=direction_labels, patch_artist=True)
    for patch, color in zip(bp['boxes'], ['lightblue', 'lightgreen']):
        patch.set_facecolor(color)

    ax6.set_ylabel('SL-ATR Multiplier')
    ax6.set_title('SL Multiplier Comparison: LONG vs SHORT')
    ax6.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    # ذخیره نمودار
    output_path = Path(__file__).parent / 'sl_target_analysis.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ Visualization saved to: {output_path}")

    # نمایش نمودار (در صورت امکان)
    try:
        plt.show()
    except:
        print("ℹ️  Display not available, chart saved to file only")


def generate_summary_report(df):
    """تولید گزارش خلاصه نهایی"""

    print("\n" + "="*80)
    print("📋 FINAL SUMMARY REPORT")
    print("="*80)

    df_clean = df.dropna(subset=['sl_atr_multiplier', 'rr_ratio'])

    # محاسبه معیارهای کلیدی
    sl_cv = (df['sl_distance'].std() / df['sl_distance'].mean()) * 100
    atr_correlation = df.dropna(subset=['atr', 'sl_distance'])['atr'].corr(
        df.dropna(subset=['atr', 'sl_distance'])['sl_distance']
    )

    avg_multiplier = df_clean['sl_atr_multiplier'].mean()
    avg_rr = df_clean['rr_ratio'].mean()

    rr_in_range = df_clean['rr_ratio'].between(1.8, 3.0).sum()
    rr_pct = (rr_in_range / len(df_clean)) * 100

    print("\n✅ KEY FINDINGS:")
    print("-" * 80)
    print(f"1. SL Variability (CV): {sl_cv:.2f}% - {'HIGH ✅' if sl_cv > 20 else 'LOW ❌'}")
    print(f"2. ATR Correlation: {atr_correlation:.4f} - {'STRONG ✅' if atr_correlation > 0.8 else 'WEAK ❌'}")
    print(f"3. Average SL Multiplier: {avg_multiplier:.2f}x ATR")
    print(f"4. Average RR Ratio: {avg_rr:.2f}")
    print(f"5. RR Ratios in Range (1.8-3.0): {rr_pct:.1f}% - {'GOOD ✅' if rr_pct > 80 else 'NEEDS IMPROVEMENT ⚠️'}")

    print("\n🎯 CONCLUSION:")
    print("-" * 80)

    # تصمیم‌گیری نهایی
    is_dynamic_sl = sl_cv > 20 and atr_correlation > 0.5
    is_dynamic_target = rr_pct > 50

    if is_dynamic_sl and is_dynamic_target:
        print("✅ CONFIRMED: Stop Loss and Target are DYNAMIC and ATR-based")
        print("   • SL varies based on ATR and volatility regime")
        print("   • Target follows RR ratio guidelines")
        print("   • System behaves as documented")
    elif is_dynamic_sl:
        print("⚠️  PARTIAL: Stop Loss is DYNAMIC but Target needs review")
        print("   • SL varies based on ATR")
        print("   • Target RR ratios have high deviation")
    elif is_dynamic_target:
        print("⚠️  PARTIAL: Target is DYNAMIC but Stop Loss needs review")
        print("   • Target follows RR guidelines")
        print("   • SL shows fixed or semi-fixed behavior")
    else:
        print("❌ WARNING: Both SL and Target show signs of being FIXED or having issues")
        print("   • Low variability in SL distances")
        print("   • Weak correlation with ATR")
        print("   • RR ratios outside expected range")

    print("\n" + "="*80)


def main():
    """تابع اصلی"""

    print("\n" + "="*80)
    print("🔍 DYNAMIC STOP LOSS & TARGET VERIFICATION")
    print("="*80)
    print("\nThis script verifies whether Stop Loss and Target values are:")
    print("  • DYNAMIC (varying based on ATR and market conditions)")
    print("  • FIXED (constant values)")
    print("\n" + "="*80)

    # مسیر فایل CSV
    csv_path = Path(__file__).parent.parent / 'backtest_results' / 'v2_20251119_191447' / 'trades.csv'

    if not csv_path.exists():
        print(f"❌ ERROR: File not found: {csv_path}")
        return

    try:
        # بارگذاری داده‌ها
        df = load_trades(csv_path)

        # محاسبه معیارها
        df = calculate_sl_metrics(df)

        # تحلیل‌های مختلف
        analyze_sl_variability(df)
        analyze_atr_correlation(df)
        analyze_sl_multipliers(df)
        analyze_rr_ratios(df)
        analyze_by_direction(df)

        # ایجاد نمودارها
        create_visualizations(df)

        # گزارش نهایی
        generate_summary_report(df)

        # ذخیره نتایج تحلیل در CSV
        output_csv = Path(__file__).parent / 'sl_analysis_results.csv'
        analysis_df = df[['trade_id', 'direction', 'entry_price', 'stop_loss',
                          'take_profit', 'atr', 'atr_percent', 'volatility_regime',
                          'sl_distance', 'target_distance', 'sl_atr_multiplier', 'rr_ratio']]
        analysis_df.to_csv(output_csv, index=False)
        print(f"\n💾 Detailed analysis saved to: {output_csv}")

        print("\n✅ Analysis completed successfully!")

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
