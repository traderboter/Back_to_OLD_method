"""
نمونه ساده برای نشان دادن ساختار metadata در backtest

این اسکریپت یک نمونه از metadata که در فایل trades.csv ذخیره می‌شود را نمایش می‌دهد.
"""

import json

# نمونه metadata برای یک معامله Multi-TF Aggregation
sample_metadata = {
    "aggregation_method": "multi_timeframe_old_system",
    "direction": "LONG",
    "final_score": 75.5,

    # فاکتورهای aggregation
    "alignment_factor": 0.85,  # 85% هماهنگی بین تایم‌فریم‌ها
    "volume_factor": 0.90,     # 90% تایید حجم
    "htf_factor": 1.2,         # HTF aligned (افزایش 20%)
    "volatility_factor": 0.95,

    # Confidence metrics
    "confidence": {
        "level": "high",
        "overall": 0.82,
        "timeframe_consensus": 0.85,
        "score_quality": 0.78,
        "direction_clarity": 0.88,
        "htf_alignment": 0.90,
        "volume_confirmation": 0.90,
        "is_uncertain": False,
        "requires_review": False
    },

    # اطلاعات هر تایم‌فریم
    "timeframes": {
        "5m": {
            "indicators": {
                "close": 45123.50,
                "rsi": 65.2,
                "macd": 125.5,
                "macd_signal": 110.3,
                "ema_20": 44950.0,
                "ema_50": 44800.0,
                "volume": 1250000
            },
            "analyzers": {
                "trend": {
                    "direction": "bullish",
                    "strength": 7.5,
                    "phase": "developing"
                },
                "momentum": {
                    "direction": "bullish",
                    "strength": 8.0,
                    "rsi_signal": "oversold_recovery",
                    "macd_market_type": "A_bullish_strong"
                },
                "patterns": {
                    "strongest_pattern": {
                        "name": "bullish_engulfing",
                        "confidence": 0.85,
                        "candles_ago": 2
                    }
                },
                "volume": {
                    "is_confirmed": True,
                    "strength": 1.45,
                    "trend": "increasing"
                }
            },
            "signal_direction": "LONG",
            "signal_score": 72.3,
            "volume_confirmed": True,
            "htf_aligned": True
        },
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
                    "rsi_signal": "neutral",
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
                    "is_confirmed": True,
                    "strength": 1.35,
                    "trend": "increasing"
                }
            },
            "signal_direction": "LONG",
            "signal_score": 78.1,
            "volume_confirmed": True,
            "htf_aligned": True
        },
        "4h": {
            "indicators": {
                "close": 45123.50,
                "rsi": 52.1,
                "macd": 45.5,
                "macd_signal": 35.2,
                "ema_20": 44850.0,
                "ema_50": 44600.0,
                "volume": 35000000
            },
            "analyzers": {
                "trend": {
                    "direction": "bullish",
                    "strength": 7.0,
                    "phase": "early"
                },
                "momentum": {
                    "direction": "bullish",
                    "strength": 6.5,
                    "rsi_signal": "neutral",
                    "macd_market_type": "B_neutral_bullish"
                },
                "patterns": {
                    "strongest_pattern": None
                },
                "volume": {
                    "is_confirmed": True,
                    "strength": 1.25,
                    "trend": "stable"
                }
            },
            "signal_direction": "LONG",
            "signal_score": 68.5,
            "volume_confirmed": True,
            "htf_aligned": True
        }
    },

    "timeframes_used": ["5m", "1h", "4h"],
    "total_timeframes": 3
}


def print_metadata_summary(metadata: dict):
    """نمایش خلاصه metadata"""
    print("=" * 80)
    print("📊 TRADE METADATA SUMMARY")
    print("=" * 80)

    print(f"\n🎯 Signal Info:")
    print(f"  Direction: {metadata['direction']}")
    print(f"  Final Score: {metadata['final_score']:.1f}")
    print(f"  Method: {metadata['aggregation_method']}")

    print(f"\n📈 Aggregation Factors:")
    print(f"  Alignment: {metadata['alignment_factor']:.1%}")
    print(f"  Volume: {metadata['volume_factor']:.1%}")
    print(f"  HTF: {metadata['htf_factor']:.2f}x")
    print(f"  Volatility: {metadata['volatility_factor']:.2f}x")

    print(f"\n✅ Confidence:")
    conf = metadata['confidence']
    print(f"  Level: {conf['level'].upper()}")
    print(f"  Overall: {conf['overall']:.1%}")
    print(f"  TF Consensus: {conf['timeframe_consensus']:.1%}")
    print(f"  Score Quality: {conf['score_quality']:.1%}")
    print(f"  Direction Clarity: {conf['direction_clarity']:.1%}")

    print(f"\n⏱️  Timeframes Analysis ({metadata['total_timeframes']} TFs):")
    for tf_name in metadata['timeframes_used']:
        tf_data = metadata['timeframes'][tf_name]
        print(f"\n  📍 {tf_name}:")
        print(f"     Direction: {tf_data['signal_direction']}")
        print(f"     Score: {tf_data['signal_score']:.1f}")
        print(f"     Volume Confirmed: {'✅' if tf_data['volume_confirmed'] else '❌'}")

        # نمایش اندیکاتورها
        ind = tf_data['indicators']
        print(f"     Price: ${ind['close']:,.2f}")
        print(f"     RSI: {ind['rsi']:.1f}")
        print(f"     MACD: {ind['macd']:.1f} / Signal: {ind['macd_signal']:.1f}")

        # نمایش الگوها
        if tf_data['analyzers'].get('patterns', {}).get('strongest_pattern'):
            pattern = tf_data['analyzers']['patterns']['strongest_pattern']
            print(f"     Pattern: {pattern['name']} (confidence: {pattern['confidence']:.1%})")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    print("\n🔍 This is how metadata looks in backtest trades:")
    print("   Each trade in trades.csv will have a 'metadata_json' column")
    print("   containing all this information in JSON format.\n")

    # نمایش خلاصه
    print_metadata_summary(sample_metadata)

    # نمایش JSON کامل
    print("\n" + "=" * 80)
    print("📝 Full JSON (as stored in CSV):")
    print("=" * 80)
    print(json.dumps(sample_metadata, indent=2))

    print("\n" + "=" * 80)
    print("✅ With this metadata, you can analyze:")
    print("   - Why each trade was opened (which patterns, indicators)")
    print("   - Signal quality and confidence")
    print("   - Agreement between different timeframes")
    print("   - Exact indicator values at signal time")
    print("   - Market conditions (trend phase, momentum, volume)")
    print("=" * 80)
