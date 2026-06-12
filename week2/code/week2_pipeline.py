"""
Week 2 Extraction Pipeline v2 - Enhanced with pdfplumber for table extraction.
从 IPO 招股说明书 PDF 中抽取认缴流量和股权结构存量。
"""
import pdfplumber
import json
import re
import csv
import os
import sys
from pathlib import Path
from datetime import datetime

# ── 配置 ──────────────────────────────────────────────
PDF_MAP = {
    "001282": "/Users/chenyuang/Desktop/马威斯抓取巨潮网结果/2023/001282_三联锻造_2023-05-17.pdf",
    "603418": "/Users/chenyuang/Desktop/抓取结果/MB002_友升股份/603418_友升股份_IPO招股说明书.pdf",
    "301581": "/Users/chenyuang/Desktop/抓取结果/GEM001_黄山谷捷/301581_黄山谷捷_IPO招股说明书.pdf",
    "301563": "/Users/chenyuang/Desktop/抓取结果/GEM002_云汉芯城/301563_云汉芯城_IPO招股说明书.pdf",
    "688758": "/Users/chenyuang/Desktop/抓取结果/STAR001_赛分科技/688758_赛分科技_IPO招股说明书.pdf",
    "688775": "/Users/chenyuang/Desktop/马威斯抓取巨潮网结果/2025/688775_影石创新_2025-06-06.pdf",
    "920100": "/Users/chenyuang/Desktop/抓取结果/BSE001_三协电机/920100_三协电机_IPO招股说明书.pdf",
    "920116": "/Users/chenyuang/Desktop/抓取结果/BSE002_星图测控/920116_星图测控_IPO招股说明书.pdf",
}

COMPANY_NAMES = {
    "001282": "三联锻造", "603418": "友升股份", "301581": "黄山谷捷",
    "301563": "云汉芯城", "688758": "赛分科技", "688775": "影石创新",
    "920100": "三协电机", "920116": "星图测控",
}

SCRIPT_DIR = Path(__file__).resolve().parent.parent
JSONL_DIR = SCRIPT_DIR / "outputs" / "week2_jsonl"
LOGS_DIR = SCRIPT_DIR / "logs"
JSONL_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ── 章节定位关键词 ────────────────────────────────────
SECTION_KEYWORDS = [
    "发行人设立及报告期内股本和股东变化",
    "发行人设立以来的股本及股东变化",
    "发行人设立及股本演变",
    "发行人设立及报告期内的股本和股东变化情况",
    "发行人设立及历史沿革",
    "股本形成及变化",
    "历次增资及股权转让",
    "设立以来股本的形成及变化",
    "发行人基本情况",
]


def extract_section_pages(pdf, keywords):
    """查找包含关键章节的页码范围。先从目录定位，再回退到全文搜索。"""
    found_pages = []
    
    # 方案1：搜索全部页面找到章节标题
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        for kw in keywords:
            if kw in text:
                # 验证是标题行（位置靠前、独立成行）
                lines = text.strip().split('\n')
                for line in lines[:10]:
                    if kw in line and len(line.strip()) < 60:
                        found_pages.append(i)
                        break
                break
    
    if not found_pages:
        return None
    
    # 找到"发行人基本情况"章节的起始页
    base_page = None
    for p in found_pages:
        text = pdf.pages[p].extract_text() or ""
        if "发行人基本情况" in text:
            base_page = p
            break
    if base_page is None:
        base_page = found_pages[0]

    # 在该节内搜索"股本"相关子章节
    equity_start = None
    for p in range(base_page, min(base_page + 150, len(pdf.pages))):
        text = pdf.pages[p].extract_text() or ""
        for kw in ["股本形成", "历次增资", "股本及股东变化", "股本演变", "设立以来股本"]:
            if kw in text:
                equity_start = p
                break
        if equity_start:
            break

    if equity_start is None:
        equity_start = base_page

    # 确定结束位置
    equity_end = min(equity_start + 80, len(pdf.pages))
    for p in range(equity_start + 5, min(equity_start + 80, len(pdf.pages))):
        text = pdf.pages[p].extract_text() or ""
        if re.search(r'(第六节|第七节|业务和技术|财务会计|管理层讨论)', text):
            equity_end = p
            break

    return equity_start, equity_end


def extract_tables_from_section(pdf, section_start, section_end):
    """从指定页码范围提取所有表格。"""
    all_tables = []
    for page_num in range(section_start, section_end):
        page = pdf.pages[page_num]
        tables = page.extract_tables()
        if tables:
            for t in tables:
                # 过滤非空表格
                non_empty = sum(1 for row in t if any(c and c.strip() for c in row))
                if non_empty >= 2:
                    all_tables.append({
                        "page": page_num + 1,
                        "table": t,
                        "row_count": non_empty,
                    })
    return all_tables


def extract_section_text(pdf, section_start, section_end):
    """提取章节全文文本。"""
    full = []
    for p in range(section_start, section_end):
        text = pdf.pages[p].extract_text() or ""
        full.append(f"=== PAGE {p + 1} ===\n{text}")
    return '\n'.join(full)


def parse_tables_to_records(tables, section_text, stock_code, company_name):
    """将提取的表格和文本解析为 subscription_flow 和 equity_snapshot 记录。"""
    sub_records = []
    eq_records = []
    
    # 按页组织表格
    pages_with_tables = {}
    for t in tables:
        pages_with_tables.setdefault(t["page"], []).append(t)
    
    # 先识别每页表格类型
    for page_num, page_tables in sorted(pages_with_tables.items()):
        page_text = ""
        for block in section_text.split('=== PAGE '):
            if block.startswith(f"{page_num} ==="):
                page_text = block.split(' ===\n', 1)[-1] if ' ===\n' in block else block
                break
        
        for t_data in page_tables:
            table = t_data["table"]
            if len(table) < 2:
                continue

            header = [str(c).strip() if c else "" for c in table[0]]
            header_text = ' '.join(header)

            # 判断表格类型
            is_equity = any(kw in header_text for kw in ['股东名称', '出资额', '持股数', '持股比例', '股权结构', '出资比例'])
            is_subscription = any(kw in header_text for kw in ['认购', '增资', '新增', '认缴', '增发'])
            # 如果都有，优先判断为股权结构
            if is_equity:
                # ── 股权结构表 ──
                time_point = "t0/报告期初"
                scope = None
                
                # 尝试从页面文本中识别时点
                if re.search(r'增资后|变更后', page_text):
                    date_matches = re.findall(r'(\d{4}\s*年\s*\d{1,2}\s*月)', page_text)
                    if date_matches:
                        time_point = date_matches[-1] + "增资后"
                    else:
                        time_point = "增资后"
                elif re.search(r'报告期初|设立时', page_text):
                    time_point = "t0/报告期初"

                # 提取总股本/注册资本
                total_shares_match = re.search(r'(?:总股本|股本总额)[^\d]*(\d+\.?\d*)', page_text)
                total_capital_match = re.search(r'(?:注册资本|出资总额)[^\d]*(\d+\.?\d*)', page_text)
                total_shares = float(total_shares_match.group(1)) if total_shares_match else None
                total_capital = float(total_capital_match.group(1)) if total_capital_match else None

                # 确定列索引
                col_map = {}
                for idx, col_name in enumerate(header):
                    col_name = col_name.replace('\n', '')
                    if '股东' in col_name or '姓名' in col_name:
                        col_map['name'] = idx
                    elif '持股' in col_name or '股数' in col_name:
                        col_map['shares'] = idx
                    elif '出资额' in col_name or '注册资本' in col_name:
                        col_map['capital'] = idx
                    elif '比例' in col_name or '占比' in col_name:
                        col_map['ratio'] = idx
                    elif '金额' in col_name:
                        col_map['amount'] = idx

                for row in table[1:]:
                    if not row or all(not c for c in row):
                        continue
                    
                    name_idx = col_map.get('name', 0)
                    if name_idx >= len(row):
                        continue
                    name = str(row[name_idx]).strip() if row[name_idx] else ""
                    if not name or name in ['合计', '总计', '-', '']:
                        continue
                    # 跳过非股东行
                    if re.match(r'^(?:序号|编号|项目|—)', name):
                        continue

                    shares = None
                    capital_val = None
                    ratio = None

                    if 'shares' in col_map:
                        try:
                            s = str(row[col_map['shares']]).replace(',', '').strip()
                            shares = float(s) if s else None
                        except:
                            pass
                    if 'capital' in col_map:
                        try:
                            s = str(row[col_map['capital']]).replace(',', '').strip()
                            capital_val = float(s) if s else None
                        except:
                            pass
                    if 'ratio' in col_map:
                        try:
                            s = str(row[col_map['ratio']]).replace('%', '').replace(',', '').strip()
                            ratio = float(s) if s else None
                        except:
                            pass

                    eq_records.append({
                        "record_type": "equity_snapshot",
                        "stock_code": stock_code,
                        "company_name": company_name,
                        "pdf_page": page_num,
                        "time_point": time_point,
                        "equity_structure_scope": scope,
                        "total_shares_wan": total_shares,
                        "total_capital_wan": total_capital,
                        "shareholder_name": name,
                        "shares_held_wan": shares,
                        "capital_contribution_wan": capital_val,
                        "shareholding_ratio": ratio,
                        "evidence_text": page_text[:600] if page_text else str(table)[:600],
                        "notes": None,
                    })

            elif is_subscription:
                # ── 认购/增资表 ──
                sub_date = None
                batch = None
                sub_price = None

                date_matches = re.findall(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', page_text)
                if date_matches:
                    dp = date_matches[0]
                    sub_date = f"{dp[0]}-{dp[1].zfill(2)}-{dp[2].zfill(2)}"

                price_match = re.search(r'(\d+\.?\d*)\s*元\s*/\s*股', page_text)
                if price_match:
                    sub_price = float(price_match.group(1))

                # 确定列索引
                col_map = {}
                for idx, col_name in enumerate(header):
                    col_name = col_name.replace('\n', '')
                    if '认购方' in col_name or '股东' in col_name or '投资者' in col_name:
                        col_map['name'] = idx
                    elif '认购' in col_name and '股' in col_name:
                        col_map['shares'] = idx
                    elif '认购' in col_name and ('金额' in col_name or '元' in col_name):
                        col_map['amount'] = idx
                    elif '股数' in col_name or '数量' in col_name:
                        col_map['shares'] = idx
                    elif '金额' in col_name or '出资额' in col_name:
                        col_map['amount'] = idx

                for row in table[1:]:
                    if not row or all(not c for c in row):
                        continue
                    name_idx = col_map.get('name', 0)
                    if name_idx >= len(row):
                        continue
                    name = str(row[name_idx]).strip() if row[name_idx] else ""
                    if not name or name in ['合计', '总计', '-']:
                        continue

                    shares = None
                    amount = None
                    if 'shares' in col_map:
                        try:
                            s = str(row[col_map['shares']]).replace(',', '').strip()
                            shares = float(s) if s else None
                        except:
                            pass
                    if 'amount' in col_map:
                        try:
                            s = str(row[col_map['amount']]).replace(',', '').strip()
                            amount = float(s) if s else None
                        except:
                            pass

                    sub_records.append({
                        "record_type": "subscription_flow",
                        "stock_code": stock_code,
                        "company_name": company_name,
                        "pdf_page": page_num,
                        "subscription_date": sub_date,
                        "batch_label": batch,
                        "subscriber_name": name,
                        "subscription_shares_wan": shares,
                        "subscription_amount_wan": amount,
                        "subscription_price_yuan": sub_price,
                        "evidence_text": page_text[:600] if page_text else str(table)[:600],
                        "notes": None,
                    })

    return sub_records, eq_records


def process_company(pdf, stock_code, company_name):
    """完整处理单家公司。"""
    print(f"[{stock_code}] {company_name} — {len(pdf.pages)} pages", flush=True)

    # Step 1: 定位章节
    result = extract_section_pages(pdf, SECTION_KEYWORDS)
    if result is None:
        print(f"  [WARN] Section not found", flush=True)
        return [], []

    section_start, section_end = result
    print(f"  Section: pages {section_start+1}-{section_end}", flush=True)

    # Step 2: 提取表格
    tables = extract_tables_from_section(pdf, section_start, section_end)
    print(f"  Tables found: {len(tables)}", flush=True)

    # Step 3: 提取文本
    section_text = extract_section_text(pdf, section_start, section_end)

    # Step 4: 解析记录
    sub_records, eq_records = parse_tables_to_records(tables, section_text, stock_code, company_name)
    print(f"  Subscription: {len(sub_records)}, Equity: {len(eq_records)}", flush=True)

    return sub_records, eq_records


def write_jsonl(records, stock_code, company_name):
    """写 JSONL 文件。"""
    filepath = JSONL_DIR / f"{stock_code}_{company_name}.jsonl"
    with open(filepath, 'w', encoding='utf-8') as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    return filepath


def main():
    all_validation = []
    for stock_code in PDF_MAP:
        company_name = COMPANY_NAMES[stock_code]
        path = PDF_MAP[stock_code]
        if not os.path.exists(path):
            print(f"[SKIP] {stock_code} PDF not found: {path}", flush=True)
            all_validation.append({
                "stock_code": stock_code, "company_name": company_name,
                "subscription_flow_count": 0, "equity_snapshot_count": 0,
                "total_records": 0, "has_records": False, "has_t0": False,
                "error": "PDF not found",
            })
            continue

        with pdfplumber.open(path) as pdf:
            sub, eq = process_company(pdf, stock_code, company_name)
        
        all_records = sub + eq
        write_jsonl(all_records, stock_code, company_name)
        
        all_validation.append({
            "stock_code": stock_code,
            "company_name": company_name,
            "subscription_flow_count": len(sub),
            "equity_snapshot_count": len(eq),
            "total_records": len(all_records),
            "has_records": len(all_records) > 0,
            "has_t0": any(r.get("time_point", "").startswith("t0") for r in eq),
        })

    # 写 CSV 日志
    val_path = LOGS_DIR / "schema_validation_log.csv"
    with open(val_path, 'w', newline='', encoding='utf-8') as f:
        if all_validation:
            w = csv.DictWriter(f, fieldnames=all_validation[0].keys())
            w.writeheader()
            w.writerows(all_validation)
    print(f"\nDone. Validation log: {val_path}", flush=True)


if __name__ == "__main__":
    main()
