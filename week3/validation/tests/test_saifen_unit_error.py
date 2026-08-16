#!/usr/bin/env python3
"""
赛分科技 (688758) 单位错误固定测试
===================================
将 subscription_shares_wan 的单位错误检测逻辑固定为可重复运行的测试用例。

问题背景:
  赛分科技 JSONL 中 subscription_shares_wan 字段曾填入原始股数
  (如 1,571,815 股), 但字段语义为"万股", 正确值应为 157.1815。
  原因是 HTML→Markdown 转换时从 PDF 表格中提取了"股"而非"万股"。

测试内容:
  1. 检测逻辑: subscription_shares_wan > 100,000 应标记为疑似单位错误
  2. 已知错误案例: 验证赛分科技 10 条 subscription_flow 均被正确识别
  3. 正确案例: 验证正常值不会被误报
  4. 修复逻辑: 验证 ÷10000 修复后的值在合理范围内
  5. 边缘案例: 检验阈值边界

运行方式:
  cd week3
  python3 validation/tests/test_saifen_unit_error.py
"""

import json
import os
import sys
from pathlib import Path

# ── Configuration ──
SCRIPT_DIR = Path(__file__).resolve().parent
WEEK3_DIR = SCRIPT_DIR.parent.parent  # week3/
DATA_DIR = WEEK3_DIR / "data"

UNIT_ERROR_THRESHOLD = 100_000  # >100k 视为疑似单位为股而非万股

# ── 赛分科技已知错误案例 ──
# (subscriber_name, raw_shares_wan, raw_evidence_mentions_gu)
SAIFEN_KNOWN_ERRORS = [
    ("源峰磐赛", 1571815.0, True),     # 原文 "1,571,815 股"
    ("珠海峦恒", 628726.0, True),      # 原文 "628,726 股"
    ("高瓴祈睿", 628726.0, True),      # 原文 "628,726 股"
    ("国药中生", 461846.0, True),      # 原文 "461,846 股"
    ("圣成投资", 9699.0, False),       # 9,699 < 100k, 但实际也是股
    ("国药二期", 155625.0, True),      # 原文 "155,625 股"
    ("圣祁投资", 1556.0, False),       # 1,556 < 100k, 但实际也是股
    ("夏尔巴二期", 392954.0, True),    # 原文 "392,954 股"
    ("甘李药业", 235772.0, True),      # 原文 "235,772 股"
    ("吴征涛", 157182.0, True),        # 原文 "157,182 股"
]

# ── 正确案例 (其他公司) ──
NORMAL_CASES = [
    # 三联锻造: 正常万股值
    {"subscriber": "孙国奉", "shares": 175.0, "source": "001282"},
    {"subscriber": "孙国敏", "shares": 162.5, "source": "001282"},
    # 星图测控: 正常万股值
    {"subscriber": "四方股份", "shares": 1200.0, "source": "920116"},
]


def detect_unit_error(shares_wan):
    """检测 subscription_shares_wan 是否存在单位错误（值异常大）。"""
    if shares_wan is None:
        return False
    return shares_wan > UNIT_ERROR_THRESHOLD


def fix_unit_error(shares_wan):
    """将疑似以股为单位的数值转换为万股。"""
    return shares_wan / 10000.0


def is_reasonable_after_fix(shares_wan, evidence_text=""):
    """检查修复后的持股数是否在合理范围内。

    合理范围判断:
    - 对于 pre-IPO 增资，每笔入股数量通常在 10~5000 万股之间
    - 异常低的 (<0.01 万 = 100 股) 或极高的 (>100000 万 = 10亿股) 仍标记可疑
    """
    if shares_wan is None:
        return False, "值为 None"
    if shares_wan < 0:
        return False, f"负值: {shares_wan}"
    if shares_wan > 5000:
        return False, f"异常高：{shares_wan:.2f} 万股，可能仍存在单位问题"
    if shares_wan < 0.05:
        return False, f"异常低：{shares_wan:.6f} 万股 (~{int(shares_wan*10000)} 股)"
    return True, "合理"


# ── Test Runner ──
class Color:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def run_tests():
    """运行所有测试并返回 (pass_count, fail_count, details)。"""
    details = []
    passed = 0
    failed = 0

    def assert_true(condition, test_name, detail=""):
        nonlocal passed, failed
        if condition:
            details.append(f"{Color.GREEN}[PASS]{Color.RESET} {test_name}")
            passed += 1
        else:
            details.append(f"{Color.RED}[FAIL]{Color.RESET} {test_name} - {detail}")
            failed += 1

    # ── Test 1: 检测逻辑 ──
    print(f"\n{Color.BOLD}{'='*60}{Color.RESET}")
    print(f"{Color.BOLD}  Test Suite: 赛分科技单位错误检测与修复{Color.RESET}")
    print(f"{Color.BOLD}{'='*60}{Color.RESET}")

    print(f"\n{Color.BOLD}--- Test 1: 单位错误检测 (阈值={UNIT_ERROR_THRESHOLD}) ---{Color.RESET}")

    # 已知错误应被检测到
    for name, raw_val, _ in SAIFEN_KNOWN_ERRORS:
        detected = detect_unit_error(raw_val)
        assert_true(detected, f"检测 {name}: {raw_val} -> 应标记为错误",
                    f"预期 True 但 detect_unit_error 返回 False (阈值={UNIT_ERROR_THRESHOLD})")

    print(f"\n{Color.BOLD}--- Test 2: 正常值不被误报 ---{Color.RESET}")

    for case in NORMAL_CASES:
        detected = detect_unit_error(case["shares"])
        assert_true(not detected,
                    f"正常值 {case['subscriber']}: {case['shares']} (来自 {case['source']})",
                    f"预期 False 但被误报为 True")

    # 阈值边界测试
    assert_true(not detect_unit_error(99999.0), "阈值下界: 99999 不应标记")
    assert_true(not detect_unit_error(100000.0), "阈值边界: 100000 不应标记 (<=阈值)")
    assert_true(detect_unit_error(100001.0), "阈值上界: 100001 应标记")

    print(f"\n{Color.BOLD}--- Test 3: 修复逻辑 (÷10000) ---{Color.RESET}")

    # 验证已知错误的修复值
    expected_after_fix = {
        "源峰磐赛": 157.1815,
        "珠海峦恒": 62.8726,
        "高瓴祈睿": 62.8726,
        "国药中生": 46.1846,
        "国药二期": 15.5625,
        "夏尔巴二期": 39.2954,
        "甘李药业": 23.5772,
        "吴征涛": 15.7182,
    }
    for name, raw_val, _ in SAIFEN_KNOWN_ERRORS:
        fixed = fix_unit_error(raw_val)
        expected = expected_after_fix.get(name)
        if expected:
            assert_true(abs(fixed - expected) < 0.001,
                        f"修复 {name}: {raw_val} / 10000 = {fixed} ≈ {expected}",
                        f"修复值 {fixed} 与预期 {expected} 偏差过大")

    print(f"\n{Color.BOLD}--- Test 4: 修复后合理范围 ---{Color.RESET}")

    # 所有修复后的值应在合理范围内
    for name, raw_val, mentions_gu in SAIFEN_KNOWN_ERRORS:
        if raw_val > UNIT_ERROR_THRESHOLD:
            fixed = fix_unit_error(raw_val)
            reasonable, msg = is_reasonable_after_fix(fixed)
            assert_true(reasonable, f"修复后合理 {name}: {fixed:.4f} 万股",
                        f"不合理: {msg}")

    # 圣成投资 9699 -> 0.9699, 圣祁投资 1556 -> 0.1556 低于阈值但也是错误
    assert_true(is_reasonable_after_fix(9699.0/10000)[0], "边缘: 圣成投资 0.9699 万股合理")
    assert_true(is_reasonable_after_fix(1556.0/10000)[0], "边缘: 圣祁投资 0.1556 万股合理")

    print(f"\n{Color.BOLD}--- Test 5: JSONL 文件验证 ---{Color.RESET}")

    # 验证实际 JSONL 文件中赛分科技数据
    jsonl_path = DATA_DIR / "688758_赛分科技.jsonl"
    if jsonl_path.exists():
        records = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

        saifen_sub = [r for r in records
                      if r.get("record_type") == "subscription_flow"
                      and r.get("stock_code") == "688758"]
        assert_true(len(saifen_sub) == 10,
                    f"JSONL 含 {len(saifen_sub)} 条赛分科技 subscription_flow",
                    f"预期 10 条，实际 {len(saifen_sub)}")

        error_detected_count = 0
        for rec in saifen_sub:
            if detect_unit_error(rec.get("subscription_shares_wan")):
                error_detected_count += 1
        assert_true(error_detected_count == 8,
                    f"检测到 {error_detected_count} 条单位错误 (预期 8)",
                    f"预期 8，实际 {error_detected_count}")

        # 检查是否已修复 (被 /10000 过)
        fixed_count = 0
        for rec in saifen_sub:
            if rec.get("notes") and "已修正" in str(rec.get("notes")):
                fixed_count += 1
        if fixed_count > 0:
            print(f"  {Color.YELLOW}[INFO]{Color.RESET} JSONL 中已有 {fixed_count} 条被标记为已修正")
    else:
        print(f"  {Color.YELLOW}[SKIP]{Color.RESET} JSONL 文件不存在: {jsonl_path}")

    print(f"\n{Color.BOLD}{'='*60}{Color.RESET}")
    print(f"{Color.BOLD}  结果: {passed} PASS / {failed} FAIL{Color.RESET}")
    print(f"{Color.BOLD}{'='*60}{Color.RESET}")

    return passed, failed, details


def main():
    passed, failed, details = run_tests()

    # 写入结果文件
    results_dir = SCRIPT_DIR.parent / "cross_check" / "cross_check_results"
    os.makedirs(results_dir, exist_ok=True)
    result_path = results_dir / "test_saifen_unit_error_result.txt"
    with open(result_path, "w", encoding="utf-8") as f:
        f.write(f"Test: test_saifen_unit_error.py\n")
        f.write(f"Results: {passed} PASS / {failed} FAIL\n")
        f.write(f"Threshold: subscription_shares_wan > {UNIT_ERROR_THRESHOLD}\n\n")
        for d in details:
            # Strip color codes for file output
            clean = d.replace("\033[92m","").replace("\033[91m","").replace("\033[93m","").replace("\033[0m","")
            f.write(clean + "\n")

    print(f"\n结果已写入: {result_path}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
