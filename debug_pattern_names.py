#!/usr/bin/env python3
"""
Debug script to show pattern name transformation issue
"""

import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

pattern_scores = config.get('pattern_scores', {})

# Show what keys exist in config
print("=" * 70)
print("📋 Pattern keys in config.yaml:")
print("=" * 70)

double_patterns = [k for k in pattern_scores.keys() if 'double' in k.lower()]
wedge_patterns = [k for k in pattern_scores.keys() if 'wedge' in k.lower()]

print("\nDouble Top/Bottom related:")
for p in double_patterns:
    print(f"  '{p}' -> {pattern_scores[p]}")

print("\nWedge related:")
for p in wedge_patterns:
    print(f"  '{p}' -> {pattern_scores[p]}")

# Show what code is looking for
print("\n" + "=" * 70)
print("🔍 What the code looks for (after transformation):")
print("=" * 70)

# Pattern names from classes
pattern_class_names = [
    "Double Top/Bottom",  # From double_top_bottom.py line 43
    "Wedge",              # From wedge.py line 39
]

for name in pattern_class_names:
    transformed = name.lower().replace(' ', '_')  # Same as base_pattern.py line 334
    print(f"\nOriginal: '{name}'")
    print(f"Transformed: '{transformed}'")
    print(f"Exists in config? {transformed in pattern_scores}")
    print(f"Config has original? {name in pattern_scores}")

    # Try to get score
    if transformed in pattern_scores:
        print(f"✅ Would use config scores: {pattern_scores[transformed]}")
    else:
        # Simulate base_strength * 5.0
        base_strength = 3 if "double" in name.lower() else 2
        default_score = base_strength * 5.0
        print(f"❌ Would use DEFAULT score: {default_score}")
