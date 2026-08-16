#!/usr/bin/env python3
"""
Week 3 — Auto vs Gold 对比脚本
===============================
对比 auto_jsonl（未经手工修正）与 gold_jsonl（data/ 修正后）之间的差异。
赛分科技 gold 侧自动在内存中应用 unit fix（股→万股 /10000）。

输出: comparison.csv（逐记录差异）+ 汇总统计。
"""

import json
import csv
import os
from pathlib import Path
from typing import Any

# ── Path config ──
SCRIPT_DIR = Path(__file__).resolve().parent
WEEK3_DIR = SCRIPT_DIR.parent
DATA_DIR = WEEK3_DIR / "data"
AUTO_JSONL_DIR = WEEK3_DIR / "outputs" / "auto_jsonl"
EVAL_DIR = WEEK3_DIR / "evaluation"
EVAL_DIR.mkdir(parents=True, exist_ok=True)

COMPANIES = [
    ("001282", "三联锻造"),
    ("301563", "云汉芯城"),
    ("301581", "黄山谷捷"),
    ("603418", "友升股份"),
    ("688758", "赛分科技"),
    ("688775", "影石创新"),
    ("920100", "三协电机"),
    ("920116", "星图测控"),
]

# 赛分科技 unit fix: 哪些 subscriber 需要 /10000
SAIFEN_FIX_MAP = {
    "源峰磐赛": 1571815.0, "珠海峦恒": 628726.0, "高瓴祈睿": 628726.0,
    "国药中生": 461846.0, "圣成投资": 9699.0, "国药二期": 155625.0,
    "圣祁投资": 1556.0, "夏尔巴二期": 392954.0, "甘李药业": 235772.0,
    "吴征涛": 157182.0,
}

FLOW_KEY_FIELDS = [
    "subscription_date", "subscriber_name", "batch_label"
]
FLOW_COMPARE_FIELDS = [
    "subscription_shares_wan", "subscription_amount_wan",
    "subscription_price_yuan"
]

EQUITY_KEY_FIELDS = [
    "time_point", "shareholder_name"
]
EQUITY_COMPARE_FIELDS = [
    "total_shares_wan", "total_capital_wan",
    "shares_held_wan", "capital_contribution_wan", "shareholding_ratio"
]


def load_jsonl(path: Path) -> list[dict]:
    recs = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return recs


def apply_gold_fix(rec: dict, code: str) -> dict:
    """Apply known manual corrections to gold records (in-memory)."""
    r = dict(rec)  # shallow copy
    if code == "688758" and r.get("record_type") == "subscription_flow":
        sub = r.get("subscriber_name", "")
        if sub in SAIFEN_FIX_MAP and r.get("subscription_shares_wan") is not None:
            old_val = r["subscription_shares_wan"]
            r["subscription_shares_wan"] = old_val / 10000.0
    return r


def make_key(rec: dict, rtype: str) -> tuple:
    if rtype == "subscription_flow":
        return tuple(str(rec.get(k, "")) for k in FLOW_KEY_FIELDS)
    else:
        return tuple(str(rec.get(k, "")) for k in EQUITY_KEY_FIELDS)


def compare_values(v1: Any, v2: Any) -> str:
    """Compare two values, return match status."""
    if v1 is None and v2 is None:
        return "both_null"
    if v1 is None:
        return "gold_null"
    if v2 is None:
        return "auto_null"

    # Float comparison with tolerance
    if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
        if abs(v1 - v2) < 1e-6:
            return "match"
        return "diff"
    if str(v1).strip() == str(v2).strip():
        return "match"
    return "diff"


# ── Main ──
def main():
    rows = []
    stats = {}  # company -> {total, match, diff, field_diffs: {...}}

    for code, name in COMPANIES:
        gold_path = DATA_DIR / f"{code}_{name}.jsonl"
        auto_path = AUTO_JSONL_DIR / f"{code}_{name}_auto.jsonl"

        if not gold_path.exists():
            print(f"[SKIP] Gold missing: {gold_path}")
            continue
        if not auto_path.exists():
            print(f"[SKIP] Auto missing: {auto_path}")
            continue

        gold_recs = [apply_gold_fix(r, code) for r in load_jsonl(gold_path)]
        auto_recs = load_jsonl(auto_path)

        # Build index by composite key
        gold_by_key = {}
        for r in gold_recs:
            k = make_key(r, r.get("record_type", ""))
            if k in gold_by_key:
                gold_by_key[k].append(r)
            else:
                gold_by_key[k] = [r]

        auto_by_key = {}
        for r in auto_recs:
            k = make_key(r, r.get("record_type", ""))
            if k in auto_by_key:
                auto_by_key[k].append(r)
            else:
                auto_by_key[k] = [r]

        comp_stats = {
            "total_records": len(auto_recs),
            "total_matched": 0,
            "total_diff": 0,
            "only_in_gold": 0,
            "only_in_auto": 0,
            "field_diffs": {},
        }

        # Compare matched keys
        matched_keys = set(gold_by_key.keys()) & set(auto_by_key.keys())

        for key in sorted(matched_keys):
            g_list = gold_by_key[key]
            a_list = auto_by_key[key]

            # Take first match for simplicity
            g = g_list[0]
            a = a_list[0]
            rtype = g.get("record_type", "")
            compare_fields = FLOW_COMPARE_FIELDS if rtype == "subscription_flow" else EQUITY_COMPARE_FIELDS

            all_match = True
            for field in compare_fields:
                status = compare_values(g.get(field), a.get(field))
                if status != "match":
                    all_match = False
                    comp_stats["field_diffs"][field] = comp_stats["field_diffs"].get(field, 0) + 1
                    rows.append({
                        "stock_code": code,
                        "company_name": name,
                        "record_type": rtype,
                        "record_key": "|".join(str(x) for x in key),
                        "field": field,
                        "gold_value": repr(g.get(field)),
                        "auto_value": repr(a.get(field)),
                        "status": status,
                    })

            if all_match:
                comp_stats["total_matched"] += 1
            else:
                comp_stats["total_diff"] += 1

        comp_stats["only_in_gold"] = len(set(gold_by_key.keys()) - matched_keys)
        comp_stats["only_in_auto"] = len(set(auto_by_key.keys()) - matched_keys)
        stats[f"{code}_{name}"] = comp_stats

    # Write comparison CSV
    csv_path = EVAL_DIR / "comparison.csv"
    if rows:
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "stock_code", "company_name", "record_type", "record_key",
                "field", "gold_value", "auto_value", "status"
            ])
            writer.writeheader()
            writer.writerows(rows)
        print(f"Comparison CSV written: {csv_path} ({len(rows)} difference rows)")

    # Print summary
    print("\n" + "=" * 70)
    print("Auto vs Gold 对比汇总")
    print("=" * 70)
    total_records = sum(s["total_records"] for s in stats.values())
    total_match = sum(s["total_matched"] for s in stats.values())
    total_diff = sum(s["total_diff"] for s in stats.values())

    for comp_name, s in stats.items():
        match_pct = s["total_matched"] / max(s["total_matched"] + s["total_diff"], 1) * 100
        print(f"  {comp_name}: {s['total_matched']} match / {s['total_diff']} diff "
              f"({match_pct:.1f}% match rate)")
        if s["field_diffs"]:
            for f, c in sorted(s["field_diffs"].items(), key=lambda x: -x[1]):
                print(f"    {f}: {c} diffs")

    if total_records:
        overall_match = total_match / max(total_match + total_diff, 1) * 100
        print(f"\n  [TOTAL] {total_match} match / {total_diff} diff ({overall_match:.1f}%)")
    print(f"\n  Comparison CSV: {csv_path}")


if __name__ == "__main__":
    main()
