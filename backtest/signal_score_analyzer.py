#!/usr/bin/env python3
"""
Signal Score Threshold Analyzer
تحلیل بهترین threshold برای ورود به معامله بر اساس signal score
"""

import pandas as pd
import sys
from pathlib import Path

class SignalScoreAnalyzer:
    def __init__(self, csv_file: str):
        self.csv_file = csv_file
        self.df = None

    def load_trades(self):
        """بارگذاری trades از CSV"""
        print(f"📂 Loading trades from {self.csv_file}...")
        self.df = pd.read_csv(self.csv_file)
        print(f"✅ Loaded {len(self.df)} trades\n")

    def analyze_score_distribution(self):
        """تحلیل توزیع signal scores"""
        print("="*80)
        print("📊 SIGNAL SCORE DISTRIBUTION")
        print("="*80)

        scores = self.df['signal_score']

        print(f"\n📈 Statistics:")
        print(f"   Min Score: {scores.min():.2f}")
        print(f"   Max Score: {scores.max():.2f}")
        print(f"   Mean Score: {scores.mean():.2f}")
        print(f"   Median Score: {scores.median():.2f}")
        print(f"   Std Dev: {scores.std():.2f}")

        # توزیع بر اساس محدوده‌ها
        print(f"\n📊 Score Ranges:")
        ranges = [
            (0, 50, "< 50 (Very Low)"),
            (50, 60, "50-60 (Low)"),
            (60, 70, "60-70 (Medium)"),
            (70, 80, "70-80 (Good)"),
            (80, 90, "80-90 (Very Good)"),
            (90, 100, "90-100 (Excellent)"),
            (100, 999, "> 100 (Outstanding)")
        ]

        for min_score, max_score, label in ranges:
            count = len(self.df[(self.df['signal_score'] >= min_score) & (self.df['signal_score'] < max_score)])
            pct = (count / len(self.df)) * 100 if len(self.df) > 0 else 0
            print(f"   {label:25s}: {count:3d} trades ({pct:5.1f}%)")

    def analyze_performance_by_threshold(self):
        """تحلیل عملکرد بر اساس threshold های مختلف"""
        print("\n" + "="*80)
        print("🎯 PERFORMANCE BY SCORE THRESHOLD")
        print("="*80)

        # تعیین threshold ها بر اساس محدوده داده‌ها
        min_score = self.df['signal_score'].min()
        max_score = self.df['signal_score'].max()

        if max_score <= 50:
            # برای backtest های قدیمی با score پایین
            thresholds = [-10, -5, 0, 5, 10, 15, 20, 25, 30, 35, 40]
        else:
            # برای backtest های جدید
            thresholds = [40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90]

        results = []

        for threshold in thresholds:
            filtered_df = self.df[self.df['signal_score'] >= threshold]

            if len(filtered_df) == 0:
                continue

            wins = filtered_df[filtered_df['pnl'] > 0]
            losses = filtered_df[filtered_df['pnl'] <= 0]

            total_trades = len(filtered_df)
            win_count = len(wins)
            loss_count = len(losses)
            win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

            total_pnl = filtered_df['pnl'].sum()
            avg_pnl = filtered_df['pnl'].mean()
            avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
            avg_loss = losses['pnl'].mean() if len(losses) > 0 else 0

            wl_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

            results.append({
                'threshold': threshold,
                'trades': total_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_pnl': avg_pnl,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'wl_ratio': wl_ratio,
                'wins': win_count,
                'losses': loss_count
            })

        # چاپ نتایج
        print(f"\n{'Threshold':>10s} | {'Trades':>7s} | {'Win%':>6s} | {'Total PnL':>10s} | {'Avg PnL':>9s} | {'Avg Win':>9s} | {'Avg Loss':>9s} | {'W/L Ratio':>9s}")
        print("-" * 100)

        best_threshold = None
        best_metric = -999999

        for r in results:
            # محاسبه یک متریک ترکیبی برای انتخاب بهترین threshold
            # metric = (win_rate * total_pnl) / 100 if total_trades >= 10 else -999
            metric = r['total_pnl'] if r['trades'] >= 5 else -999999

            symbol = ""
            if r['trades'] >= 10:
                if metric > best_metric:
                    best_metric = metric
                    best_threshold = r['threshold']
                    symbol = " ✅"
            elif r['trades'] >= 5:
                symbol = " ⚠️"
            else:
                symbol = " ❌"

            print(f"{r['threshold']:>10.0f} | {r['trades']:>7d} | {r['win_rate']:>6.1f} | {r['total_pnl']:>10.2f} | "
                  f"{r['avg_pnl']:>9.2f} | {r['avg_win']:>9.2f} | {r['avg_loss']:>9.2f} | {r['wl_ratio']:>9.2f}{symbol}")

        return best_threshold, results

    def analyze_score_ranges(self):
        """تحلیل دقیق‌تر محدوده‌های score"""
        print("\n" + "="*80)
        print("📈 DETAILED PERFORMANCE BY SCORE RANGE")
        print("="*80)

        ranges = [
            (0, 50),
            (50, 60),
            (60, 70),
            (70, 80),
            (80, 90),
            (90, 100),
            (100, 999)
        ]

        print(f"\n{'Score Range':>15s} | {'Trades':>7s} | {'Win%':>6s} | {'Total PnL':>10s} | {'Avg PnL':>9s} | {'Quality':>10s}")
        print("-" * 80)

        for min_score, max_score in ranges:
            filtered_df = self.df[(self.df['signal_score'] >= min_score) & (self.df['signal_score'] < max_score)]

            if len(filtered_df) == 0:
                continue

            wins = filtered_df[filtered_df['pnl'] > 0]
            total_trades = len(filtered_df)
            win_count = len(wins)
            win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

            total_pnl = filtered_df['pnl'].sum()
            avg_pnl = filtered_df['pnl'].mean()

            # تعیین کیفیت
            if total_trades < 5:
                quality = "Low Data"
            elif win_rate >= 65 and avg_pnl > 2:
                quality = "Excellent ⭐"
            elif win_rate >= 60 and avg_pnl > 1:
                quality = "Good ✅"
            elif win_rate >= 50:
                quality = "Neutral ⚠️"
            else:
                quality = "Poor ❌"

            range_label = f"{min_score}-{max_score if max_score < 999 else '100+'}"
            print(f"{range_label:>15s} | {total_trades:>7d} | {win_rate:>6.1f} | {total_pnl:>10.2f} | {avg_pnl:>9.2f} | {quality:>10s}")

    def recommend_threshold(self, best_threshold, results):
        """توصیه threshold بهینه"""
        print("\n" + "="*80)
        print("💡 THRESHOLD RECOMMENDATION")
        print("="*80)

        if best_threshold is None:
            print("\n⚠️  Not enough data to recommend a specific threshold")
            return

        best_result = next((r for r in results if r['threshold'] == best_threshold), None)

        if best_result:
            print(f"\n🎯 Recommended Threshold: {best_threshold}")
            print(f"\n   Based on this threshold:")
            print(f"   • Total Trades: {best_result['trades']}")
            print(f"   • Win Rate: {best_result['win_rate']:.1f}%")
            print(f"   • Total PnL: {best_result['total_pnl']:.2f} USDT")
            print(f"   • Avg PnL per Trade: {best_result['avg_pnl']:.2f} USDT")
            print(f"   • Win/Loss Ratio: {best_result['wl_ratio']:.2f}")

            # مقایسه با threshold فعلی
            current_threshold = 46  # فعلی
            current_result = next((r for r in results if r['threshold'] == current_threshold), None)

            if current_result and current_result['threshold'] != best_threshold:
                print(f"\n📊 Comparison with Current Threshold ({current_threshold}):")
                print(f"   • Trades: {current_result['trades']} → {best_result['trades']} ({best_result['trades'] - current_result['trades']:+d})")
                print(f"   • Win Rate: {current_result['win_rate']:.1f}% → {best_result['win_rate']:.1f}% ({best_result['win_rate'] - current_result['win_rate']:+.1f}%)")
                print(f"   • Total PnL: {current_result['total_pnl']:.2f} → {best_result['total_pnl']:.2f} ({best_result['total_pnl'] - current_result['total_pnl']:+.2f} USDT)")
                print(f"   • Avg PnL: {current_result['avg_pnl']:.2f} → {best_result['avg_pnl']:.2f} ({best_result['avg_pnl'] - current_result['avg_pnl']:+.2f} USDT)")

            print(f"\n🔧 Update config.yaml:")
            print(f"   signal_generation:")
            print(f"     minimum_signal_score: {best_threshold}")

    def run(self):
        """اجرای تحلیل کامل"""
        self.load_trades()

        if 'signal_score' not in self.df.columns:
            print("❌ Error: 'signal_score' column not found in CSV file")
            return 1

        # Check for PnL column (could be 'pnl' or 'realized_pnl')
        if 'pnl' in self.df.columns:
            pnl_col = 'pnl'
        elif 'realized_pnl' in self.df.columns:
            pnl_col = 'realized_pnl'
            self.df['pnl'] = self.df['realized_pnl']  # Create alias
        else:
            print("❌ Error: 'pnl' or 'realized_pnl' column not found in CSV file")
            return 1

        self.analyze_score_distribution()
        best_threshold, results = self.analyze_performance_by_threshold()
        self.analyze_score_ranges()
        self.recommend_threshold(best_threshold, results)

        print("\n" + "="*80)
        print("✅ Analysis Complete!")
        print("="*80)

        return 0

def main():
    if len(sys.argv) < 2:
        print("Usage: python signal_score_analyzer.py <trades.csv>")
        print("\nExample:")
        print("  python signal_score_analyzer.py backtest_results/v2_20251119_062846/trades.csv")
        sys.exit(1)

    csv_file = sys.argv[1]

    if not Path(csv_file).exists():
        print(f"❌ Error: File not found: {csv_file}")
        sys.exit(1)

    analyzer = SignalScoreAnalyzer(csv_file)
    exit_code = analyzer.run()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
