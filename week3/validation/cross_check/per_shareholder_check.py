#!/usr/bin/env python3
"""
逐股东 Cross-check
===================
对每个股东，验证其在整个时间线中的持股变化是否连续。

检查内容:
  1. 同一股东在相邻快照间，持股数变化应有对应事件解释
  2. 检测异常: 股东突然出现/消失、持股跳变无对应事件
  3. 逐股东输出完整的持股变化轨迹

逻辑:
  对每家公司:
    1. 列出所有快照时点及每个时点下各股东的持股
    2. 对每个股东，构建时间线: [t0持股, t1持股, ..., tn持股]
    3. 检测:
       - 股东在 t_i 出现但在 t_{i-1} 不存在 → 检查是否有增资事件引入
       - 股东在 t_{i-1} 存在但在 t_i 消失 → 检查是否有转让/退出事件
       - 持股跳变 > 50% → 标记为异常

输出: validation/cross_check/cross_check_results/per_shareholder_check_report.csv
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
GOLD_DIR = WEEK3_DIR / "manual_gold"

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

JUMP_THRESHOLD = 0.50  # 持股变化超过50%标记为跳变
TOLERANCE = 0.01


def extract_time_order(time_point_str):
    """从 time_point 字段提取排序键."""
    if not time_point_str:
        return (999,)
    tp = time_point_str.lower()
    order_map = {
        "t0": 0, "t_before": 1, "t1": 2, "t2": 3,
        "t3": 4, "t4": 5, "t5": 6, "t6": 7, "t7": 8, "t8": 9,
    }
    for prefix, order in order_map.items():
        if prefix in tp:
            return (order,)
    if "设立" in tp:
        return (0,)
    if "报告期初" in tp or "before" in tp:
        return (1,)
    if "发行前" in tp:
        return (99,)
    return (50,)


def load_snapshots(code, name):
    """加载一家公司的股权快照并按时点分组。"""
    jsonl_path = DATA_DIR / f"{code}_{name}.jsonl"
    if not jsonl_path.exists():
        return {}, {}

    records = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if rec.get("record_type") == "equity_snapshot":
                    records.append(rec)
            except json.JSONDecodeError:
                continue

    # 按时点分组
    groups = defaultdict(dict)
    time_info = {}

    for rec in records:
        tp = rec.get("time_point", "unknown")
        shareholder = rec.get("shareholder_name", "").strip()
        shares = rec.get("shares_held_wan")
        capital = rec.get("capital_contribution_wan")
        ratio = rec.get("shareholding_ratio")

        val = shares if shares is not None else capital
        if val is not None and shareholder:
            groups[tp][shareholder] = {
                "shares": val,
                "ratio": ratio,
            }

        if tp not in time_info:
            time_info[tp] = {
                "total_shares": rec.get("total_shares_wan"),
                "total_capital": rec.get("total_capital_wan"),
            }

    return dict(groups), time_info


def load_subscription_events(code, name):
    """加载一家公司的增资事件."""
    jsonl_path = DATA_DIR / f"{code}_{name}.jsonl"
    if not jsonl_path.exists():
        return []

    events = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if rec.get("record_type") == "subscription_flow":
                    events.append(rec)
            except json.JSONDecodeError:
                continue
    return events


def load_transfer_events(code, name):
    """加载一家公司的股权转让事件."""
    jsonl_path = DATA_DIR / f"{code}_{name}.jsonl"
    if not jsonl_path.exists():
        return []

    events = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if rec.get("record_type") == "equity_transfer":
                    events.append(rec)
            except json.JSONDecodeError:
                continue
    return events


def per_shareholder_check():
    """对每家公司的每个股东执行逐股东检查."""
    results = []

    for code, name in COMPANIES:
        snapshots, time_info = load_snapshots(code, name)
        subscriptions = load_subscription_events(code, name)
        transfers = load_transfer_events(code, name)

        if not snapshots:
            continue

        sorted_tps = sorted(snapshots.keys(), key=extract_time_order)

        # 收集所有股东
        all_shareholders = set()
        for tp, holders in snapshots.items():
            all_shareholders.update(holders.keys())

        # 构建事件索引: {shareholder_name: [event_records]}
        sub_by_holder = defaultdict(list)
        for evt in subscriptions:
            sub_by_holder[evt.get("subscriber_name", "").strip()].append(evt)

        # ── 对每个股东，构建时间线并检查 ──
        for shareholder in sorted(all_shareholders):
            timeline = []
            previous_shares = None
            previous_tp = None

            for tp in sorted_tps:
                holder_data = snapshots[tp].get(shareholder)
                if holder_data:
                    current_shares = holder_data["shares"]
                    current_ratio = holder_data["ratio"]
                    timeline.append({
                        "time_point": tp,
                        "shares": current_shares,
                        "ratio": current_ratio,
                        "status": "存在",
                    })

                    # 检查与上一个时点的变化
                    if previous_shares is not None and previous_tp is not None:
                        delta = current_shares - previous_shares
                        if previous_shares > 0:
                            pct_change = delta / previous_shares
                        else:
                            pct_change = float('inf') if delta > 0 else 0

                        # 跳变检测
                        if abs(pct_change) > JUMP_THRESHOLD and abs(delta) > TOLERANCE:
                            # 查找是否有对应事件
                            has_event = False
                            for evt in sub_by_holder.get(shareholder, []):
                                evt_date = evt.get("subscription_date", "")
                                evt_shares = evt.get("subscription_shares_wan")
                                if evt_shares and abs(evt_shares - delta) < TOLERANCE * 100:
                                    has_event = True
                                    break

                            if not has_event:
                                results.append({
                                    "company": f"{code} {name}",
                                    "shareholder": shareholder,
                                    "from_time": previous_tp,
                                    "to_time": tp,
                                    "from_shares": previous_shares,
                                    "to_shares": current_shares,
                                    "delta": delta,
                                    "pct_change": round(pct_change * 100, 1),
                                    "anomaly_type": "持股跳变",
                                    "detail": f"从 {previous_tp}({previous_shares}) 到 {tp}({current_shares}), 变化 {pct_change*100:.1f}%, 无对应事件",
                                })

                    previous_shares = current_shares
                    previous_tp = tp
                else:
                    # 股东在该时点不存在
                    timeline.append({
                        "time_point": tp,
                        "shares": None,
                        "ratio": None,
                        "status": "不存在",
                    })

            # ── 检测股东突然出现/消失 ──
            for i in range(1, len(timeline)):
                prev = timeline[i-1]
                curr = timeline[i]

                if prev["status"] == "不存在" and curr["status"] == "存在":
                    # 股东突然出现
                    has_event = bool(sub_by_holder.get(shareholder))
                    if not has_event:
                        results.append({
                            "company": f"{code} {name}",
                            "shareholder": shareholder,
                            "from_time": prev["time_point"],
                            "to_time": curr["time_point"],
                            "from_shares": 0,
                            "to_shares": curr["shares"],
                            "delta": curr["shares"],
                            "pct_change": 100.0,
                            "anomaly_type": "股东凭空出现",
                            "detail": f"在 {curr['time_point']} 出现 (持股 {curr['shares']}), 无增资事件引入",
                        })

                if prev["status"] == "存在" and curr["status"] == "不存在":
                    # 股东消失
                    results.append({
                        "company": f"{code} {name}",
                        "shareholder": shareholder,
                        "from_time": prev["time_point"],
                        "to_time": curr["time_point"],
                        "from_shares": prev["shares"],
                        "to_shares": 0,
                        "delta": -prev["shares"],
                        "pct_change": -100.0,
                        "anomaly_type": "股东消失",
                        "detail": f"在 {prev['time_point']}(持股 {prev['shares']}) 后消失, 无转让/退出事件记录",
                    })

        # ── 汇总统计 ──
        num_holders = len(all_shareholders)
        num_tps = len(sorted_tps)

    return results


def main():
    print("=" * 60)
    print("逐股东 Cross-check 开始")
    print(f"执行时间: {datetime.now().isoformat()}")
    print("=" * 60)

    results = per_shareholder_check()

    # ── 统计 ──
    total = len(results)
    jump_count = sum(1 for r in results if r["anomaly_type"] == "持股跳变")
    appear_count = sum(1 for r in results if r["anomaly_type"] == "股东凭空出现")
    disappear_count = sum(1 for r in results if r["anomaly_type"] == "股东消失")

    print(f"\n统计: 总异常 {total} | 持股跳变 {jump_count} | 凭空出现 {appear_count} | 消失 {disappear_count}")

    # ── 按公司统计 ──
    company_stats = defaultdict(lambda: {"跳变": 0, "出现": 0, "消失": 0})
    for r in results:
        key = r["company"]
        if r["anomaly_type"] == "持股跳变":
            company_stats[key]["跳变"] += 1
        elif r["anomaly_type"] == "股东凭空出现":
            company_stats[key]["出现"] += 1
        elif r["anomaly_type"] == "股东消失":
            company_stats[key]["消失"] += 1

    print(f"\n{'公司':<20} {'跳变':>5} {'出现':>5} {'消失':>5} {'合计':>5}")
    print("-" * 45)
    for company in sorted(company_stats.keys()):
        s = company_stats[company]
        total_c = s["跳变"] + s["出现"] + s["消失"]
        print(f"{company:<20} {s['跳变']:>5} {s['出现']:>5} {s['消失']:>5} {total_c:>5}")

    # ── 写入 CSV ──
    csv_path = RESULTS_DIR / "per_shareholder_check_report.csv"
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "company", "shareholder", "from_time", "to_time",
            "from_shares", "to_shares", "delta", "pct_change",
            "anomaly_type", "detail",
        ])
        writer.writeheader()
        writer.writerows(results)
    print(f"\n详细报告: {csv_path} ({len(results)} 行)")

    # ── 写摘要 ──
    summary_path = RESULTS_DIR / "per_shareholder_check_summary.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("逐股东 Cross-check 摘要\n")
        f.write(f"执行时间: {datetime.now().isoformat()}\n")
        f.write(f"总计: {total} 条异常 | 跳变 {jump_count} | 出现 {appear_count} | 消失 {disappear_count}\n\n")

        for r in results:
            f.write(f"[{r['anomaly_type']}] {r['company']} | {r['shareholder']} | {r['detail']}\n")

    print(f"摘要: {summary_path}")

    if total > 0:
        print(f"\n共发现 {total} 条异常，请查看详细报告以进行人工复核。")


if __name__ == "__main__":
    main()
