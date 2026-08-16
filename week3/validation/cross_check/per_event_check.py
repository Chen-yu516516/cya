#!/usr/bin/env python3
"""
逐事件 Cross-check
===================
对每个增资/转让事件，检查前后股权快照的差额是否等于该事件的变动量。

逻辑:
  前快照 (before_snapshot) + 事件变动 (event_delta) = 后快照 (after_snapshot)

流程:
  1. 读取 JSONL 中的 subscription_flow 和 equity_snapshot 记录
  2. 按时间排序所有事件和快照
  3. 对每个增资事件:
     - 找到该事件之前最近的一次快照 (before)
     - 找到该事件之后最近的一次快照 (after)
     - 对于事件中涉及的股东, 验证: before持股 + 事件增量 = after持股
  4. 对股权转让事件同理
  5. 输出详细的逐事件检查报告

输出: validation/cross_check/cross_check_results/per_event_check_report.csv
"""

import csv
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ── Configuration ──
SCRIPT_DIR = Path(__file__).resolve().parent
WEEK3_DIR = SCRIPT_DIR.parent.parent  # week3/
DATA_DIR = WEEK3_DIR / "data"
RESULTS_DIR = SCRIPT_DIR / "cross_check_results"

os.makedirs(RESULTS_DIR, exist_ok=True)

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

TOLERANCE = 0.01  # 容差（万元/万股）


def load_data():
    """加载所有公司的 JSONL 数据。"""
    all_records = defaultdict(lambda: {"subscription": [], "snapshot": [], "transfer": []})
    for code, name in COMPANIES:
        jsonl_path = DATA_DIR / f"{code}_{name}.jsonl"
        if not jsonl_path.exists():
            continue
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    rtype = rec.get("record_type")
                    key = (code, name)
                    if rtype == "subscription_flow":
                        all_records[key]["subscription"].append(rec)
                    elif rtype == "equity_snapshot":
                        all_records[key]["snapshot"].append(rec)
                    elif rtype in ("equity_transfer",):
                        all_records[key]["transfer"].append(rec)
                except json.JSONDecodeError:
                    continue
    return all_records


def parse_date(date_str):
    """尝试解析日期字符串，返回可排序的元组。"""
    if not date_str:
        return (9999, 99, 99)
    try:
        # Try "2021-10-28" format
        parts = date_str.split("-")
        if len(parts) == 3:
            return tuple(int(p) for p in parts)
    except (ValueError, AttributeError):
        pass
    try:
        # Try year only
        return (int(date_str[:4]), 0, 0)
    except (ValueError, AttributeError):
        pass
    return (9999, 99, 99)


def extract_time_order(time_point_str):
    """从 time_point 字段提取排序键。"""
    if not time_point_str:
        return (999,)

    tp = time_point_str.lower()
    # t0 < t_before < t1 < t2 < t3 ...
    order_map = {
        "t0": 0, "t_before": 1, "t1": 2, "t2": 3,
        "t3": 4, "t4": 5, "t5": 6, "t6": 7, "t7": 8, "t8": 9,
    }
    for prefix, order in order_map.items():
        if prefix in tp:
            return (order,)

    # Fallback: text priority
    if "设立" in tp:
        return (0,)
    if "报告期初" in tp or "before" in tp:
        return (1,)
    if "发行前" in tp:
        return (99,)
    return (50,)


def group_snapshots_by_time(snapshots):
    """将快照按时点分组，返回 {time_point: {shareholder: shares_held_wan}}。"""
    groups = defaultdict(dict)
    time_info = {}

    for rec in snapshots:
        tp = rec.get("time_point", "unknown")
        shareholder = rec.get("shareholder_name", "").strip()
        shares = rec.get("shares_held_wan")
        capital = rec.get("capital_contribution_wan")

        # 优先使用 shares_held_wan，其次 capital_contribution_wan
        val = shares if shares is not None else capital
        if val is not None and shareholder:
            groups[tp][shareholder] = val

        # Track time point metadata
        if tp not in time_info:
            total_shares = rec.get("total_shares_wan")
            total_capital = rec.get("total_capital_wan")
            time_info[tp] = {
                "total_shares": total_shares,
                "total_capital": total_capital,
            }

    return dict(groups), time_info


def find_bounding_snapshots(event_date_tuple, snapshot_groups):
    """找到事件前后的最近快照。

    简化逻辑: 按 time_order 排序后，找到事件插入位置的前后快照。
    """
    # 按时间排序快照
    sorted_tps = sorted(snapshot_groups.keys(), key=extract_time_order)

    # 找到事件日期在排序中的位置
    event_order = extract_time_order(f"t{event_date_tuple[0]}") if event_date_tuple[0] != 9999 else (99,)
    # 取事件发生年份的第一个数字来确定大致位置
    before_tp = None
    after_tp = None

    for tp in sorted_tps:
        tp_order = extract_time_order(tp)
        if tp_order < event_order:
            before_tp = tp
        elif tp_order > event_order and after_tp is None:
            after_tp = tp

    return before_tp, after_tp


def per_event_check(all_records):
    """执行逐事件检查。"""
    results = []
    summary = []

    for (code, name), data in all_records.items():
        subscriptions = data["subscription"]
        snapshots = data["snapshot"]
        transfers = data["transfer"]

        if not subscriptions and not transfers:
            continue

        # 按时点分组快照
        snapshot_groups, time_info = group_snapshots_by_time(snapshots)
        sorted_tps = sorted(snapshot_groups.keys(), key=extract_time_order)

        if not sorted_tps:
            continue

        # ── 检查每个增资事件 ──
        for evt in subscriptions:
            sub_name = evt.get("subscriber_name", "").strip()
            shares_in = evt.get("subscription_shares_wan")
            date_str = evt.get("subscription_date", "")

            # 找到前后快照
            event_date_tuple = parse_date(date_str)

            # 策略: 比较事件前的第一个快照和事件后的第一个快照
            before_tp = None
            after_tp = None
            for i, tp in enumerate(sorted_tps):
                tp_order = extract_time_order(tp)
                if tp_order < (1,):  # t0/t_before 在事件前
                    before_tp = tp
                if tp_order >= (1,):
                    if after_tp is None or tp_order < extract_time_order(after_tp):
                        after_tp = tp

            # 如果没有 before，用最早快照；如果没有 after，用最晚快照
            if before_tp is None and sorted_tps:
                before_tp = sorted_tps[0]
            if after_tp is None and sorted_tps:
                after_tp = sorted_tps[-1]

            if before_tp is None or after_tp is None:
                results.append({
                    "company": f"{code} {name}",
                    "event_type": "增资",
                    "event_date": date_str,
                    "subscriber": sub_name,
                    "before_snapshot": before_tp,
                    "after_snapshot": after_tp,
                    "check_result": "SKIP",
                    "mismatch_reason": "缺少前后快照",
                    "before_shares": None,
                    "expected_after": None,
                    "actual_after": None,
                    "delta": None,
                })
                continue

            # 检查股东持股变化
            before_shares = snapshot_groups[before_tp].get(sub_name) or 0
            actual_after = snapshot_groups[after_tp].get(sub_name)

            if actual_after is None and shares_in is not None and shares_in > 0:
                # 新股东，在后快照中应能找到
                actual_after_via_check = snapshot_groups[after_tp].get(sub_name)
                if actual_after_via_check is None:
                    results.append({
                        "company": f"{code} {name}",
                        "event_type": "增资",
                        "event_date": date_str,
                        "subscriber": sub_name,
                        "before_snapshot": before_tp,
                        "after_snapshot": after_tp,
                        "check_result": "WARN",
                        "mismatch_reason": f"新增股东 {sub_name} 在后快照中未找到",
                        "before_shares": before_shares,
                        "expected_after": (shares_in or 0),
                        "actual_after": None,
                        "delta": None,
                    })
                else:
                    expected = before_shares + (shares_in or 0)
                    delta = (actual_after_via_check or 0) - expected
                    is_ok = abs(delta) < TOLERANCE
                    results.append({
                        "company": f"{code} {name}",
                        "event_type": "增资",
                        "event_date": date_str,
                        "subscriber": sub_name,
                        "before_snapshot": before_tp,
                        "after_snapshot": after_tp,
                        "check_result": "PASS" if is_ok else "FAIL",
                        "mismatch_reason": "" if is_ok else f"差额={delta:.4f} 万股",
                        "before_shares": before_shares,
                        "expected_after": expected,
                        "actual_after": actual_after_via_check,
                        "delta": delta,
                    })
            elif actual_after is not None:
                expected = before_shares + (shares_in or 0)
                delta = actual_after - expected
                is_ok = abs(delta) < TOLERANCE
                results.append({
                    "company": f"{code} {name}",
                    "event_type": "增资",
                    "event_date": date_str,
                    "subscriber": sub_name,
                    "before_snapshot": before_tp,
                    "after_snapshot": after_tp,
                    "check_result": "PASS" if is_ok else "FAIL",
                    "mismatch_reason": "" if is_ok else f"差额={delta:.4f} 万股 (前={before_shares},预期={expected},实际={actual_after})",
                    "before_shares": before_shares,
                    "expected_after": expected,
                    "actual_after": actual_after,
                    "delta": delta,
                })
            else:
                results.append({
                    "company": f"{code} {name}",
                    "event_type": "增资",
                    "event_date": date_str,
                    "subscriber": sub_name,
                    "before_snapshot": before_tp,
                    "after_snapshot": after_tp,
                    "check_result": "SKIP",
                    "mismatch_reason": "后快照中无该股东且增资量为0",
                    "before_shares": before_shares,
                    "expected_after": None,
                    "actual_after": None,
                    "delta": None,
                })

        # ── 检查每个转让事件 ──
        for evt in transfers:
            transferor = evt.get("transferor_name", "").strip()
            transferee = evt.get("transferee_name", "").strip()
            shares_trans = evt.get("transfer_shares_wan")
            date_str = evt.get("transfer_date", "")

            # 简单策略: 用最早和最晚快照
            before_tp = sorted_tps[0] if sorted_tps else None
            after_tp = sorted_tps[-1] if len(sorted_tps) > 1 else None

            if before_tp and after_tp:
                before_tsfr = snapshot_groups[before_tp].get(transferor) or 0
                after_tsfr = snapshot_groups[after_tp].get(transferor)
                before_tsfe = snapshot_groups[before_tp].get(transferee) or 0
                after_tsfe = snapshot_groups[after_tp].get(transferee)

                if after_tsfr is not None and shares_trans:
                    expected_after = before_tsfr - shares_trans
                    delta = after_tsfr - expected_after
                    is_ok = abs(delta) < TOLERANCE
                    results.append({
                        "company": f"{code} {name}",
                        "event_type": "转让(转让方)",
                        "event_date": date_str,
                        "subscriber": transferor,
                        "before_snapshot": before_tp,
                        "after_snapshot": after_tp,
                        "check_result": "PASS" if is_ok else "FAIL",
                        "mismatch_reason": "" if is_ok else f"转让方差额={delta:.4f}",
                        "before_shares": before_tsfr,
                        "expected_after": expected_after,
                        "actual_after": after_tsfr,
                        "delta": delta,
                    })

                if after_tsfe is not None and shares_trans:
                    expected_after = before_tsfe + shares_trans
                    delta = after_tsfe - expected_after
                    is_ok = abs(delta) < TOLERANCE
                    results.append({
                        "company": f"{code} {name}",
                        "event_type": "转让(受让方)",
                        "event_date": date_str,
                        "subscriber": transferee,
                        "before_snapshot": before_tp,
                        "after_snapshot": after_tp,
                        "check_result": "PASS" if is_ok else "FAIL",
                        "mismatch_reason": "" if is_ok else f"受让方差额={delta:.4f}",
                        "before_shares": before_tsfe,
                        "expected_after": expected_after,
                        "actual_after": after_tsfe,
                        "delta": delta,
                    })

    return results


def main():
    print("=" * 60)
    print("逐事件 Cross-check 开始")
    print(f"执行时间: {datetime.now().isoformat()}")
    print("=" * 60)

    all_records = load_data()
    results = per_event_check(all_records)

    # ── 统计 ──
    total = len(results)
    passes = sum(1 for r in results if r["check_result"] == "PASS")
    fails = sum(1 for r in results if r["check_result"] == "FAIL")
    warns = sum(1 for r in results if r["check_result"] == "WARN")
    skips = sum(1 for r in results if r["check_result"] == "SKIP")

    print(f"\n统计: 总 {total} | PASS {passes} | FAIL {fails} | WARN {warns} | SKIP {skips}")

    # ── 按公司统计 ──
    company_stats = defaultdict(lambda: {"PASS": 0, "FAIL": 0, "WARN": 0, "SKIP": 0})
    for r in results:
        company_stats[r["company"]]["PASS"] += (r["check_result"] == "PASS")
        company_stats[r["company"]]["FAIL"] += (r["check_result"] == "FAIL")
        company_stats[r["company"]]["WARN"] += (r["check_result"] == "WARN")
        company_stats[r["company"]]["SKIP"] += (r["check_result"] == "SKIP")

    print(f"\n{'公司':<20} {'PASS':>5} {'FAIL':>5} {'WARN':>5} {'SKIP':>5}")
    print("-" * 45)
    for company, stats in sorted(company_stats.items()):
        print(f"{company:<20} {stats['PASS']:>5} {stats['FAIL']:>5} {stats['WARN']:>5} {stats['SKIP']:>5}")

    # ── 写入 CSV ──
    csv_path = RESULTS_DIR / "per_event_check_report.csv"
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "company", "event_type", "event_date", "subscriber",
            "before_snapshot", "after_snapshot", "check_result",
            "mismatch_reason", "before_shares", "expected_after",
            "actual_after", "delta",
        ])
        writer.writeheader()
        writer.writerows(results)
    print(f"\n详细报告: {csv_path} ({len(results)} 行)")

    # ── 写摘要 ──
    summary_path = RESULTS_DIR / "per_event_check_summary.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("逐事件 Cross-check 摘要\n")
        f.write(f"执行时间: {datetime.now().isoformat()}\n")
        f.write(f"总计: {total} 事件 | PASS {passes} | FAIL {fails} | WARN {warns} | SKIP {skips}\n\n")
        f.write(f"{'公司':<20} {'PASS':>5} {'FAIL':>5} {'WARN':>5} {'SKIP':>5}\n")
        for company, stats in sorted(company_stats.items()):
            f.write(f"{company:<20} {stats['PASS']:>5} {stats['FAIL']:>5} {stats['WARN']:>5} {stats['SKIP']:>5}\n")

        # 列出所有 FAIL
        fails_list = [r for r in results if r["check_result"] == "FAIL"]
        if fails_list:
            f.write(f"\n--- FAIL 详情 ({len(fails_list)} 条) ---\n")
            for r in fails_list:
                f.write(f"  {r['company']} | {r['event_type']} | {r['subscriber']} | {r['mismatch_reason']}\n")

    print(f"摘要: {summary_path}")

    if fails > 0:
        print(f"\n有 {fails} 条 FAIL 记录，请查看详细报告。")


if __name__ == "__main__":
    main()
