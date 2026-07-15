#!/usr/bin/env python3
"""
Week 3 对比分析 — 手动 Gold 标准 vs 自动化产出
================================================
输出: comparison.csv（字段级对比）+ comparison_summary.csv（公司级汇总）
"""

import csv
import os
from pathlib import Path

try:
    import openpyxl
except ImportError:
    os.system("python3 -m pip install openpyxl -q")
    import openpyxl

WEEK3 = Path("/Users/chenyuang/Library/Application Support/com.tencent.mac.marvis/MarvisData/User/oAN1i2dK-PWdQG0K0G95clCfK3pg/workspace/conv_19e9bfeabd9_078488edb7a3/output/cya/week3")
GOLD_DIR = WEEK3 / "manual_gold"
AUTO_DIR = WEEK3 / "auto_output" / "auto_excel"
COMP_DIR = WEEK3 / "comparison"

os.makedirs(COMP_DIR, exist_ok=True)

COMPANIES = {
    "001282": "三联锻造",
    "301563": "云汉芯城",
    "301581": "黄山谷捷",
    "603418": "友升股份",
    "688758": "赛分科技",
    "688775": "影石创新",
    "920100": "三协电机",
    "920116": "星图测控",
}

SHEET_MAP = {
    "认缴流量": ("认缴流量", "1_认缴流量"),
    "股权存量": ("股权存量", "2_股权结构存量"),
    "交叉校验": ("交叉校验", "3_交叉校验"),
    "股权转让": ("股权转让", "4_股权转让"),
}


def read_sheet_rows(filepath, sheet_keyword):
    """读取 Excel 指定 Sheet 的所有行（表头+数据）"""
    wb = openpyxl.load_workbook(filepath, data_only=True)
    target = None
    for s in wb.sheetnames:
        if sheet_keyword in s:
            target = s
            break
    if target is None:
        return [], []
    
    ws = wb[target]
    rows = []
    for row in ws.iter_rows(min_row=1, values_only=True):
        rows.append([str(c) if c is not None else "" for c in row])
    
    if not rows:
        return [], []
    
    headers = rows[0]
    data = rows[1:]
    wb.close()
    return headers, data


def field_match(gold_val, auto_val):
    """判断两个字段值是否匹配"""
    g = str(gold_val).strip()
    a = str(auto_val).strip()
    
    if g == a:
        return True
    if not g and not a:
        return True
    if not g:
        return False  # gold有auto空 → missing
    if not a:
        return False  # gold空auto有 → extra
    
    # 数值容差匹配（5%）
    try:
        gv = float(g.replace(",", "").replace("万", "").replace("元", "").replace("股", "").replace("%", "").replace(" ", ""))
        av = float(a.replace(",", "").replace("万", "").replace("元", "").replace("股", "").replace("%", "").replace(" ", ""))
        if gv == 0 and av == 0:
            return True
        if gv == 0:
            return False
        return abs(gv - av) / abs(gv) < 0.05
    except (ValueError, ZeroDivisionError):
        pass
    
    # 字符串模糊匹配
    if len(g) > 3 and len(a) > 3:
        if g[:min(10, len(g))] == a[:min(10, len(a))]:
            return True
    
    return False


def main():
    comp_rows = []
    summary_rows = []
    
    for code, name in COMPANIES.items():
        gold_file = GOLD_DIR / f"{code}_{name}_gold.xlsx"
        auto_file = AUTO_DIR / f"{code}_{name}_auto.xlsx"
        
        print(f"对比: {code} {name}")
        
        sheet_stats = {}
        
        for sheet_label, (gold_kw, auto_kw) in SHEET_MAP.items():
            g_headers, g_data = read_sheet_rows(str(gold_file), gold_kw)
            a_headers, a_data = read_sheet_rows(str(auto_file), auto_kw)
            
            g_count = len(g_data)
            a_count = len(a_data)
            
            # 按行对比
            max_rows = max(g_count, a_count)
            match_count = 0
            mismatch_count = 0
            missing_count = 0
            
            for i in range(max_rows):
                g_row = g_data[i] if i < g_count else []
                a_row = a_data[i] if i < a_count else []
                
                max_cols = max(len(g_row), len(a_row))
                
                for j in range(max_cols):
                    g_val = g_row[j] if j < len(g_row) else ""
                    a_val = a_row[j] if j < len(a_row) else ""
                    
                    col_name = g_headers[j] if j < len(g_headers) else f"Col{j}"
                    
                    if not g_val and not a_val:
                        continue  # 双方都空，不录入
                    
                    if field_match(g_val, a_val):
                        status = "match"
                        match_count += 1
                    elif not g_val and a_val:
                        status = "extra"
                        mismatch_count += 1
                    elif g_val and not a_val:
                        status = "missing"
                        missing_count += 1
                        mismatch_count += 1
                    else:
                        status = "mismatch"
                        mismatch_count += 1
                    
                    comp_rows.append({
                        "stock_code": code,
                        "company_name": name,
                        "sheet": sheet_label,
                        "row_index": i,
                        "column": col_name,
                        "gold_value": g_val,
                        "auto_value": a_val,
                        "status": status,
                    })
            
            total_fields = match_count + mismatch_count
            match_rate = round(match_count / total_fields * 100, 1) if total_fields > 0 else 0
            
            sheet_stats[sheet_label] = {
                "gold_records": g_count,
                "auto_records": a_count,
                "match": match_count,
                "mismatch": mismatch_count,
                "missing": missing_count,
                "total_fields": total_fields,
                "match_rate": match_rate,
            }
        
        # 公司级汇总
        total_fields = sum(s["total_fields"] for s in sheet_stats.values())
        total_match = sum(s["match"] for s in sheet_stats.values())
        total_mismatch = sum(s["mismatch"] for s in sheet_stats.values())
        total_missing = sum(s["missing"] for s in sheet_stats.values())
        overall_rate = round(total_match / total_fields * 100, 1) if total_fields > 0 else 0
        
        summary_rows.append({
            "stock_code": code,
            "company_name": name,
            "total_fields": total_fields,
            "match": total_match,
            "mismatch": total_mismatch,
            "missing": total_missing,
            "overall_match_rate": overall_rate,
            "认缴流量_match_rate": sheet_stats.get("认缴流量", {}).get("match_rate", 0),
            "股权存量_match_rate": sheet_stats.get("股权存量", {}).get("match_rate", 0),
            "交叉校验_match_rate": sheet_stats.get("交叉校验", {}).get("match_rate", 0),
            "股权转让_match_rate": sheet_stats.get("股权转让", {}).get("match_rate", 0),
        })
        
        print(f"  {name}: 总字段{total_fields} | match{total_match} | mismatch{total_mismatch} | missing{total_missing} | {overall_rate}%")
    
    # ── 写入 comparison.csv ──
    comp_path = COMP_DIR / "comparison.csv"
    with open(comp_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "stock_code", "company_name", "sheet", "row_index",
            "column", "gold_value", "auto_value", "status",
        ])
        writer.writeheader()
        writer.writerows(comp_rows)
    print(f"\n字段级对比: {comp_path} ({len(comp_rows)} 行)")
    
    # ── 写入 comparison_summary.csv ──
    summary_path = COMP_DIR / "comparison_summary.csv"
    with open(summary_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "stock_code", "company_name", "total_fields",
            "match", "mismatch", "missing", "overall_match_rate",
            "认缴流量_match_rate", "股权存量_match_rate",
            "交叉校验_match_rate", "股权转让_match_rate",
        ])
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"公司级汇总: {summary_path} ({len(summary_rows)} 行)")
    
    # ── Print summary table ──
    print("\n" + "=" * 80)
    print("公司级对比汇总")
    print("=" * 80)
    print(f"{'公司':<10} {'总字段':>6} {'Match':>6} {'Mismatch':>8} {'Missing':>7} {'Match率':>8}")
    print("-" * 80)
    for s in summary_rows:
        print(f"{s['company_name']:<10} {s['total_fields']:>6} {s['match']:>6} "
              f"{s['mismatch']:>8} {s['missing']:>7} {s['overall_match_rate']:>7}%")
    print("=" * 80)


if __name__ == "__main__":
    main()
