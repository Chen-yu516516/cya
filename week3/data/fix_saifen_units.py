#!/usr/bin/env python3
"""
赛分科技 (688758) subscription_shares_wan 单位修复脚本
=====================================================
问题: Week 2 JSONL 中赛分科技的 subscription_shares_wan 字段填入的是原始股数
     （如 1571815.0），应为万股（157.1815）。
     原文明确写着 "1,571,815 股"、"628,726 股" 等。

修复: 将 subscription_flow 类型记录的 subscription_shares_wan 值除以 10000
"""

import json
import os
import sys
from datetime import datetime

# ── Configuration ──
WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(WORKSPACE, "data")  # week3/data/
LOG_DIR = os.path.join(WORKSPACE, "outputs", "logs")

INPUT_FILE = os.path.join(DATA_DIR, "688758_赛分科技.jsonl")
OUTPUT_FILE = os.path.join(DATA_DIR, "688758_赛分科技.jsonl")  # in-place fix
LOG_FILE = os.path.join(LOG_DIR, "saifen_unit_fix.log")

# ── Ensure log dir ──
os.makedirs(LOG_DIR, exist_ok=True)

# ── Main ──
def fix_units():
    log_lines = []
    log_lines.append("=" * 60)
    log_lines.append("赛分科技 (688758) subscription_shares_wan 单位修复日志")
    log_lines.append(f"执行时间: {datetime.now().isoformat()}")
    log_lines.append(f"输入文件: {INPUT_FILE}")
    log_lines.append(f"输出文件: {OUTPUT_FILE} (in-place)")
    log_lines.append("=" * 60)
    log_lines.append("")

    # Read all records
    records = []
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    # Fix
    fix_count = 0
    for rec in records:
        if rec.get("record_type") == "subscription_flow":
            old_val = rec.get("subscription_shares_wan")
            if old_val is not None and old_val > 1000:
                new_val = old_val / 10000.0
                log_lines.append(
                    f"  [{rec.get('subscriber_name'):20s}] "
                    f"subscription_shares_wan: {old_val:>12.0f} -> {new_val:>12.6f}"
                )
                rec["subscription_shares_wan"] = new_val
                existing_note = rec.get("notes") or ""
                if "已修正" not in existing_note:
                    rec["notes"] = existing_note + " | 已修正：原数据误填为股，已转换为万股"
                fix_count += 1

    log_lines.append("")
    log_lines.append(f"共修复 {fix_count} 条 subscription_flow 记录")
    log_lines.append(f"修复标准: subscription_shares_wan / 10000 (股 -> 万股)")
    log_lines.append(f"判断依据: evidence_text 写明 '1,571,815 股' 等以股为单位")
    log_lines.append("")

    # Write back
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Write log
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    print(f"Fixed {fix_count} records.")
    print(f"Log written to: {LOG_FILE}")
    return fix_count

if __name__ == "__main__":
    fix_units()
