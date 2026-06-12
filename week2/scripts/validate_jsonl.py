#!/usr/bin/env python3
"""Pydantic validation for Week 2 JSONL extraction outputs."""
import json, sys, csv, os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "schemas"))
from extraction_models import SubscriptionFlow, EquitySnapshot

JSONL_DIR = Path(__file__).resolve().parent.parent / "outputs" / "week2_jsonl"
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_CSV = LOG_DIR / f"schema_validation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

stats = defaultdict(lambda: {"sub_ok": 0, "sub_fail": 0, "eq_ok": 0, "eq_fail": 0, "errors": []})
grand_total = {"sub_ok": 0, "sub_fail": 0, "eq_ok": 0, "eq_fail": 0}

jsonl_files = sorted(JSONL_DIR.glob("*.jsonl"))
print(f"Found {len(jsonl_files)} JSONL files in {JSONL_DIR}")

rows = []

for fp in jsonl_files:
    with open(fp, "r", encoding="utf-8") as f:
        line_num = 0
        for line in f:
            line = line.strip()
            if not line:
                continue
            line_num += 1
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                stats[fp.stem]["errors"].append(f"Line {line_num}: JSON parse error: {e}")
                continue

            rt = obj.get("record_type", "")
            record = obj.copy()
            record["_file"] = fp.name
            record["_line"] = line_num

            if rt == "subscription_flow":
                try:
                    SubscriptionFlow(**obj)
                    stats[fp.stem]["sub_ok"] += 1
                    grand_total["sub_ok"] += 1
                    rows.append({**record, "_status": "OK"})
                except Exception as e:
                    stats[fp.stem]["sub_fail"] += 1
                    grand_total["sub_fail"] += 1
                    rows.append({**record, "_status": "FAIL", "_error": str(e)})
            elif rt == "equity_snapshot":
                try:
                    EquitySnapshot(**obj)
                    stats[fp.stem]["eq_ok"] += 1
                    grand_total["eq_ok"] += 1
                    rows.append({**record, "_status": "OK"})
                except Exception as e:
                    stats[fp.stem]["eq_fail"] += 1
                    grand_total["eq_fail"] += 1
                    rows.append({**record, "_status": "FAIL", "_error": str(e)})
            else:
                stats[fp.stem]["errors"].append(f"Line {line_num}: unknown record_type={rt}")

# Write CSV log
fieldnames = [
    "_file", "_line", "_status", "_error", "record_type", "stock_code", "company_name",
    "pdf_page", "subscription_date", "batch_label", "subscriber_name",
    "subscription_shares_wan", "subscription_amount_wan", "subscription_price_yuan",
    "time_point", "shareholder_name", "shares_held_wan", "capital_contribution_wan",
    "shareholding_ratio", "total_shares_wan", "total_capital_wan",
    "evidence_text", "notes"
]

with open(LOG_CSV, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") or "" for k in fieldnames})

# Print summary
print("\n" + "=" * 80)
print(f"{'Company':<25} {'Sub_OK':>7} {'Sub_FAIL':>8} {'Eq_OK':>6} {'Eq_FAIL':>7} {'Total':>6}")
print("-" * 80)
for stem in sorted(stats.keys()):
    s = stats[stem]
    total = s["sub_ok"] + s["sub_fail"] + s["eq_ok"] + s["eq_fail"]
    print(f"{stem:<25} {s['sub_ok']:>7} {s['sub_fail']:>8} {s['eq_ok']:>6} {s['eq_fail']:>7} {total:>6}")
    if s["errors"]:
        for err in s["errors"]:
            print(f"  [WARN] {err}")
print("-" * 80)
gt = grand_total
print(f"{'GRAND TOTAL':<25} {gt['sub_ok']:>7} {gt['sub_fail']:>8} {gt['eq_ok']:>6} {gt['eq_fail']:>7} {gt['sub_ok']+gt['sub_fail']+gt['eq_ok']+gt['eq_fail']:>6}")
print(f"\nValidation log: {LOG_CSV}")

if gt["sub_fail"] + gt["eq_fail"] == 0:
    print("\n*** ALL RECORDS PASSED VALIDATION ***")
    sys.exit(0)
else:
    print(f"\n*** {gt['sub_fail'] + gt['eq_fail']} FAILURES FOUND ***")
    sys.exit(1)
