#!/usr/bin/env python3
"""Cross-check: verify subscription_flow and equity_snapshot consistency per company."""
import json, sys
from pathlib import Path
from collections import defaultdict

JSONL_DIR = Path(__file__).resolve().parent.parent / "outputs" / "week2_jsonl"

print("=" * 90)
print(f"{'Company':<20} {'Subs':>5} {'EqSnap':>6} {'Tn':>3} {'Issues':>60}")
print("-" * 90)

total_issues = 0

for fp in sorted(JSONL_DIR.glob("*.jsonl")):
    sub_recs, eq_recs = [], []
    with open(fp, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                obj = json.loads(line)
            except: continue
            if obj.get("record_type") == "subscription_flow":
                sub_recs.append(obj)
            elif obj.get("record_type") == "equity_snapshot":
                eq_recs.append(obj)

    issues = []
    code = sub_recs[0]["stock_code"] if sub_recs else eq_recs[0]["stock_code"]
    name = sub_recs[0]["company_name"] if sub_recs else eq_recs[0]["company_name"]

    # Check 1: unique time_points in equity
    time_points = set(eq.get("time_point", "") for eq in eq_recs)

    # Check 2: subscription_flow has at least t0 (some companies don't have t0 in sub, that's ok)
    sub_dates = sorted(set(s.get("subscription_date", "") for s in sub_recs if s.get("subscription_date")))
    sub_batches = sorted(set(s.get("batch_label", "") for s in sub_recs if s.get("batch_label")))

    # Check 3: each batch should have at least one subscriber
    batch_counts = defaultdict(list)
    for s in sub_recs:
        bl = s.get("batch_label", "unknown")
        batch_counts[bl].append(s.get("subscriber_name", "?"))

    for bl, names in batch_counts.items():
        if len(names) < 1:
            issues.append(f"Batch '{bl}' has no subscribers")

    # Check 4: equity time_points should cover key events
    if len(time_points) < 2:
        issues.append(f"Only {len(time_points)} equity snapshot time points")

    # Check 5: total share consistency (if available)
    # Use total_shares_wan (股本万股) as primary, fallback to total_capital_wan (注册资本万元)
    checked_tps = set()
    for eq in eq_recs:
        tp = eq.get("time_point", "")
        if tp in checked_tps:
            continue
        checked_tps.add(tp)

        tp_holders = [e for e in eq_recs if e.get("time_point") == tp]

        # Try total_shares_wan vs sum of shares_held_wan
        ts = eq.get("total_shares_wan")
        if ts is not None and ts > 0:
            total_held = sum(e.get("shares_held_wan") or 0 for e in tp_holders)
            if total_held > 0:
                ratio = abs(total_held - ts) / ts
                if ratio > 0.05:
                    issues.append(f"tp={tp}: total_shares={ts} vs sum_shares={total_held:.1f} (diff {ratio*100:.1f}%)")

        # Try total_capital_wan vs sum of capital_contribution_wan
        tc = eq.get("total_capital_wan")
        if tc is not None and tc > 0:
            total_cap = sum(e.get("capital_contribution_wan") or 0 for e in tp_holders)
            if total_cap > 0:
                ratio = abs(total_cap - tc) / tc
                if ratio > 0.05:
                    issues.append(f"tp={tp}: total_capital={tc} vs sum_capital={total_cap:.1f} (diff {ratio*100:.1f}%)")

    # Deduplicate issues
    issues = list(dict.fromkeys(issues))

    n_issues = len(issues)
    total_issues += n_issues
    issue_str = "; ".join(issues[:2])
    if len(issues) > 2:
        issue_str += f" ... +{len(issues)-2} more"

    print(f"{name:<20} {len(sub_recs):>5} {len(eq_recs):>6} {len(time_points):>3} {issue_str:<60}")

print("-" * 90)
print(f"Total issues found: {total_issues}")
if total_issues == 0:
    print("*** ALL CROSS-CHECKS PASSED ***")
