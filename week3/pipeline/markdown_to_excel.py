#!/usr/bin/env python3
"""
Week 3 自动化 Pipeline — 从招股书 Markdown 到 4-Sheet Excel
============================================================
流程: Markdown → 章节定位 → 段落切分 → 事件提取 → Excel输出

核心原则：
- 所有 Auto 数据必须从 Markdown 定位结果中直接提取
- 禁止读取 JSONL 后原样写入 Auto Sheet
- 数据缺失处留空，不填旧数据
- JSONL 仅用于对比参考（Auto-vs-Gold），不参与 Auto 生成

输入: 招股书 Markdown 文件（PDF 经由 MinerU 转换）
输出: 4-Sheet Excel（认缴流量 / 股权结构存量 / 交叉校验 / 股权转让）
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

# ── Dependencies ──
try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl", "-q"])
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side


# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════

WEEK3_DIR = Path(__file__).resolve().parent.parent  # week3/ directory
DATA_DIR = WEEK3_DIR / "data"
SCRATCH_DIR = DATA_DIR / "scratch_results"  # Markdown 源文件目录
AUTO_EXCEL_DIR = WEEK3_DIR / "auto_output" / "auto_excel"
AUTO_JSONL_DIR = WEEK3_DIR / "auto_output" / "auto_jsonl"
LOG_DIR = WEEK3_DIR / "outputs" / "logs"

os.makedirs(AUTO_EXCEL_DIR, exist_ok=True)
os.makedirs(AUTO_JSONL_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

COMPANIES = {
    "001282": {
        "name": "三联锻造",
        "md_subdir": "MB001_三联锻造",
        "md_filename": "001282_三联锻造_IPO招股说明书.md",
        "history_pages": (31, 37),
    },
    "301563": {
        "name": "云汉芯城",
        "md_subdir": "GEM002_云汉芯城",
        "md_filename": "301563_云汉芯城_IPO招股说明书.md",
        "history_pages": (54, 66),
    },
    "301581": {
        "name": "黄山谷捷",
        "md_subdir": "GEM001_黄山谷捷",
        "md_filename": "301581_黄山谷捷_IPO招股说明书.md",
        "history_pages": (39, 46),
    },
    "603418": {
        "name": "友升股份",
        "md_subdir": "MB002_友升股份",
        "md_filename": "603418_友升股份_IPO招股说明书.md",
        "history_pages": (42, 44),
    },
    "688758": {
        "name": "赛分科技",
        "md_subdir": None,
        "md_filename": None,
        "history_pages": (51, 55),
        "note": "Markdown 源文件缺失 — 无法进行自动提取，Auto 产出为空",
    },
    "688775": {
        "name": "影石创新",
        "md_subdir": "STAR002_影石创新",
        "md_filename": "688775_影石创新_IPO招股说明书.md",
        "history_pages": (63, 66),
    },
    "920100": {
        "name": "三协电机",
        "md_subdir": "BSE001_三协电机",
        "md_filename": "920100_三协电机_IPO招股说明书.md",
        "history_pages": (35, 39),
    },
    "920116": {
        "name": "星图测控",
        "md_subdir": "BSE002_星图测控",
        "md_filename": "920116_星图测控_IPO招股说明书.md",
        "history_pages": (36, 48),
    },
}

# ── Excel Styles ──
HEADER_FONT = Font(name="微软雅黑", bold=True, size=11)
HEADER_FILL = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")
HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
CELL_ALIGN = Alignment(vertical="top", wrap_text=True)
NOTE_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
THIN_BORDER = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"), bottom=Side(style="thin"),
)

# ═══════════════════════════════════════════════════════════════
# Step 1: Markdown Loading & Chapter Location
# ═══════════════════════════════════════════════════════════════

def read_markdown(filepath: Path) -> str:
    """读取 Markdown 文件全文"""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def locate_history_section(text: str) -> Optional[str]:
    """
    定位「历史沿革」章节文本。
    招股书结构：第四章 发行人基本情况 → 第四节 发行人设立及报告期内股本演变
    返回该章节的完整文本，找不到则返回 None。
    """
    keywords_priority = [
        "发行人设立及报告期内股本演变",
        "发行人设立以来的股本演变",
        "股本和股东变化情况",
        "历史沿革",
        "发行人股本情况",
        "发行人设立及股本演变",
    ]

    best_idx = None
    for kw in keywords_priority:
        idx = text.find(kw)
        if idx != -1:
            best_idx = idx
            break

    if best_idx is None:
        basics_idx = text.find("发行人基本情况")
        if basics_idx != -1:
            sub_text = text[basics_idx:basics_idx + 80000]
            for kw in ["股本演变", "股本和股东", "历史沿革", "设立及"]:
                sub_idx = sub_text.find(kw)
                if sub_idx != -1:
                    best_idx = basics_idx + sub_idx
                    break

    if best_idx is None:
        return None

    section = text[best_idx:best_idx + 80000]

    # 在下一个大节标题处截断（## 第 X 页 或 ### N、标题）
    truncate_markers = [
        r'\n#+\s+(?:[五六七八九十]、|第[五六七八九]节)',
        r'\n##\s+第\s*\d+\s+页',
    ]
    truncate_pos = len(section)
    for marker in truncate_markers:
        m = re.search(marker, section[100:])
        if m:
            truncate_pos = min(truncate_pos, m.start() + 100)

    return section[:truncate_pos]


# ═══════════════════════════════════════════════════════════════
# Step 2: Event Extraction from Markdown Text
# ═══════════════════════════════════════════════════════════════

def normalize_number(s: str) -> float:
    """将数字字符串转为浮点数"""
    s = s.strip().replace(",", "").replace("，", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _safe_float(s: str) -> Optional[float]:
    """安全地将字符串转为 float，失败返回 None"""
    if not s:
        return None
    try:
        return float(s.replace(",", "").replace("，", "").strip())
    except (ValueError, AttributeError):
        return None


def _infer_time_point(text: str, position: int) -> str:
    """从附近文本推断时点标签"""
    ctx_start = max(0, position - 2000)
    ctx = text[ctx_start:position + 500]
    date_matches = list(re.finditer(r'(\d{4})\s*年\s*(\d{1,2})\s*月', ctx))
    if date_matches:
        last = date_matches[-1]
        return f"{last.group(1)}-{last.group(2).zfill(2)}"
    for kw in ["设立后", "增资后", "股改后", "发行前", "报告期初"]:
        if kw in ctx[-500:]:
            return kw
    return ""


def extract_subscription_events(section_text: str, stock_code: str,
                                 company_name: str) -> list[dict]:
    """
    从历史沿革章节文本中提取认缴流量（增资事件）。

    策略:
    1. 按空行切分段落
    2. 识别含增资语义的段落
    3. 从段落中匹配日期、认购方、金额
    4. 按认购方逐条输出，无法区分则标记 [待提取]
    """
    events = []
    segments = re.split(r'\n\s*\n', section_text)

    for seg in segments:
        seg = seg.strip()
        if len(seg) < 30:
            continue
        if not re.search(r'(?:增资|增加注册|新增注册|注册资本.*增|变更为?\s*\d)', seg):
            continue

        # 提取日期
        date_match = re.search(
            r'(\d{4})\s*年\s*(\d{1,2})\s*月(?:\s*(\d{1,2})\s*日)?', seg
        )
        subscription_date = ""
        if date_match:
            y, m, d = date_match.group(1), date_match.group(2), date_match.group(3)
            subscription_date = f"{y}-{m.zfill(2)}"
            if d:
                subscription_date += f"-{d.zfill(2)}"

        # 提取认购方 + 金额
        subscriber_pattern = re.compile(
            r'([^，。,\.\s]{2,30}(?:有限|股份)?(?:公司|企业|合伙|基金)?'
            r'(?:\(有限合伙\))?(?:\(有限公[司]\))?)'
            r'(?:以|用)?[^，。]{0,20}?'
            r'(?:出资|认购|投入|缴付|增[资加])[^\d]{0,10}?'
            r'(\d[\d,.]*(?:\.\d+)?)\s*万[元股]'
        )

        found = set()
        for match in subscriber_pattern.finditer(seg):
            subscriber = match.group(1).strip()
            amount = normalize_number(match.group(2))
            if len(subscriber) < 2 or amount <= 0 or subscriber in found:
                continue
            found.add(subscriber)

            ev_start = max(0, match.start() - 100)
            ev_end = min(len(seg), match.end() + 300)

            events.append({
                "record_type": "subscription_flow",
                "stock_code": stock_code,
                "company_name": company_name,
                "pdf_page": None,
                "subscription_date": subscription_date,
                "batch_label": "",
                "subscriber_name": subscriber,
                "subscription_shares_wan": None,
                "subscription_amount_wan": amount,
                "subscription_price_yuan": None,
                "evidence_text": seg[ev_start:ev_end].strip()[:2000],
                "notes": "Markdown自动提取",
                "_source": "markdown_extraction",
            })

        # 未匹配到具体认购方则记录总增资
        if not found:
            cap_match = re.search(
                r'(?:注册资本|增[资加]).*?(\d[\d,.]*(?:\.\d+)?)\s*万[元]?', seg
            )
            events.append({
                "record_type": "subscription_flow",
                "stock_code": stock_code,
                "company_name": company_name,
                "pdf_page": None,
                "subscription_date": subscription_date,
                "batch_label": "",
                "subscriber_name": "[待提取]",
                "subscription_shares_wan": None,
                "subscription_amount_wan": normalize_number(cap_match.group(1)) if cap_match else None,
                "subscription_price_yuan": None,
                "evidence_text": seg[:2000],
                "notes": "Markdown自动提取-未识别具体认购方",
                "_source": "markdown_extraction",
            })

    return events


def extract_equity_snapshots(section_text: str, stock_code: str,
                              company_name: str) -> list[dict]:
    """
    从 Markdown 中提取股权结构快照。

    策略:
    1. 解析 Markdown 表格（|...| 格式），识别股权结构表
    2. 对文本描述型股权结构做正则匹配（"XXX持股XX%，XXX持股XX%"）
    """
    snapshots = []

    # ── 策略1：Markdown 表格解析 ──
    table_pattern = re.compile(r'((?:^\|.+?\|.*$\n)+)', re.MULTILINE)

    for table_match in table_pattern.finditer(section_text):
        table_text = table_match.group(1).strip()
        lines = [l.strip() for l in table_text.split('\n') if l.strip()]
        if len(lines) < 3:
            continue

        headers = [h.strip() for h in lines[0].split('|')[1:-1]]
        is_equity = any(kw in ''.join(headers) for kw in ["股东", "持股", "出资", "比例"])
        if not is_equity:
            continue

        col_map = {}
        for i, h in enumerate(headers):
            if any(kw in h for kw in ["股东名称", "股东姓名", "股东", "名称", "姓名"]):
                col_map["shareholder"] = i
            elif any(kw in h for kw in ["持股数", "股数", "股份数", "持股数量"]):
                col_map["shares"] = i
            elif any(kw in h for kw in ["出资额", "出资金额", "注册资本", "出资"]):
                col_map["capital"] = i
            elif any(kw in h for kw in ["持股比例", "出资比例", "占比", "比例"]):
                col_map["ratio"] = i

        if "shareholder" not in col_map:
            continue

        time_point = _infer_time_point(section_text, table_match.start())
        data_lines = lines[2:]

        for row_line in data_lines:
            cells = [c.strip() for c in row_line.split('|')[1:-1]]
            if len(cells) < len(headers):
                continue
            shareholder = cells[col_map["shareholder"]]
            if not shareholder or shareholder in ["合计", "总计", "-", "--", ""]:
                continue

            snap = {
                "record_type": "equity_snapshot",
                "stock_code": stock_code,
                "company_name": company_name,
                "pdf_page": None,
                "time_point": time_point or "",
                "equity_structure_scope": "有限公司注册资本",
                "total_shares_wan": None,
                "total_capital_wan": None,
                "shareholder_name": shareholder,
                "shares_held_wan": None,
                "capital_contribution_wan": None,
                "shareholding_ratio": None,
                "evidence_text": row_line[:500],
                "notes": "Markdown表格自动提取",
                "_source": "markdown_extraction",
            }
            if "shares" in col_map and col_map["shares"] < len(cells):
                snap["shares_held_wan"] = _safe_float(cells[col_map["shares"]])
            if "capital" in col_map and col_map["capital"] < len(cells):
                snap["capital_contribution_wan"] = _safe_float(cells[col_map["capital"]])
            if "ratio" in col_map and col_map["ratio"] < len(cells):
                snap["shareholding_ratio"] = _safe_float(
                    cells[col_map["ratio"]].replace("%", ""))
            snapshots.append(snap)

    # ── 策略2：文本描述型股权结构 ──
    non_table = re.sub(table_pattern, '', section_text)
    text_pattern = re.compile(
        r'([^，。,\.\s]{2,30}(?:有限|股份)?(?:公司|企业|合伙|基金)?(?:\(有限合伙\))?)'
        r'(?:持有|持股|占|出资)[^\d]{0,5}?'
        r'(\d[\d,.]*(?:\.\d+)?)\s*(?:万[元股]|%)'
    )
    for match in text_pattern.finditer(non_table):
        shareholder = match.group(1).strip()
        value = _safe_float(match.group(2).replace(",", ""))
        if not shareholder or len(shareholder) < 2 or not value:
            continue
        is_pct = "%" in match.group(0)
        tp = _infer_time_point(non_table, match.start())
        ctx_s = max(0, match.start() - 80)
        ctx_e = min(len(non_table), match.end() + 200)
        snapshots.append({
            "record_type": "equity_snapshot",
            "stock_code": stock_code,
            "company_name": company_name,
            "pdf_page": None,
            "time_point": tp or "",
            "equity_structure_scope": "有限公司注册资本",
            "total_shares_wan": None,
            "total_capital_wan": None,
            "shareholder_name": shareholder,
            "shares_held_wan": value if not is_pct else None,
            "capital_contribution_wan": value if not is_pct else None,
            "shareholding_ratio": value if is_pct else None,
            "evidence_text": non_table[ctx_s:ctx_e].strip()[:500],
            "notes": "Markdown文本自动提取",
            "_source": "markdown_extraction",
        })

    return snapshots


def extract_transfer_events(section_text: str, stock_code: str,
                             company_name: str) -> list[dict]:
    """从 Markdown 中提取股权转让事件"""
    transfers = []
    segments = re.split(r'\n\s*\n', section_text)

    for seg in segments:
        seg = seg.strip()
        if len(seg) < 30:
            continue
        if not re.search(r'(?:股权转让|股份转让|股权变动|转让.*股权|受让)', seg):
            continue

        date_match = re.search(
            r'(\d{4})\s*年\s*(\d{1,2})\s*月(?:\s*(\d{1,2})\s*日)?', seg
        )
        transfer_date = ""
        if date_match:
            y, m, d = date_match.group(1), date_match.group(2), date_match.group(3)
            transfer_date = f"{y}-{m.zfill(2)}"
            if d:
                transfer_date += f"-{d.zfill(2)}"

        to_match = re.search(
            r'([^，。,\.\s]{2,20}(?:有限|股份)?(?:公司|企业|合伙)?)'
            r'(?:将其?所?持|将|把)[^。]{0,30}?'
            r'(?:转让给|转让至|转让与|出让给|转给)'
            r'([^，。,\.\s]{2,20}(?:有限|股份)?(?:公司|企业|合伙)?)',
            seg
        )
        transferor = to_match.group(1).strip() if to_match else "[待提取]"
        transferee = to_match.group(2).strip() if to_match else "[待提取]"

        amt_match = re.search(
            r'(\d[\d,.]*(?:\.\d+)?)\s*万[元股]', seg
        )
        amount = normalize_number(amt_match.group(1)) if amt_match else None

        transfers.append({
            "record_type": "equity_transfer",
            "stock_code": stock_code,
            "company_name": company_name,
            "pdf_page": None,
            "transfer_date": transfer_date,
            "transferor": transferor,
            "transferee": transferee,
            "transfer_shares_wan": amount,
            "transfer_price_yuan": None,
            "transfer_amount_wan": amount,
            "evidence_text": seg[:2000],
            "notes": "Markdown自动提取",
            "_source": "markdown_extraction",
        })

    return transfers


# ═══════════════════════════════════════════════════════════════
# Step 3: JSONL Reference (comparison only, NOT for filling Auto)
# ═══════════════════════════════════════════════════════════════

def load_jsonl(filepath: Path) -> list[dict]:
    """加载 JSONL 参考数据（仅用于验证对比，不用于填充 Auto）"""
    records = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


# ═══════════════════════════════════════════════════════════════
# Step 4: Cross Validation
# ═══════════════════════════════════════════════════════════════

def generate_cross_validation(subscription_records: list[dict],
                               equity_records: list[dict]) -> list[dict]:
    """生成交叉校验数据"""
    validation = []

    batches = {}
    for rec in subscription_records:
        batch = rec.get("batch_label") or "unknown"
        if batch not in batches:
            batches[batch] = {"subscribers": [], "total_amount": 0, "total_shares": 0}
        batches[batch]["subscribers"].append(rec.get("subscriber_name", ""))
        amt = rec.get("subscription_amount_wan")
        if isinstance(amt, (int, float)):
            batches[batch]["total_amount"] += amt
        shares = rec.get("subscription_shares_wan")
        if isinstance(shares, (int, float)):
            batches[batch]["total_shares"] += shares

    for batch, info in batches.items():
        validation.append({
            "check_type": "批次汇总",
            "batch": batch,
            "subscriber_count": len(info["subscribers"]),
            "total_amount_wan": round(info["total_amount"], 2) if info["total_amount"] else "",
            "total_shares_wan": round(info["total_shares"], 2) if info["total_shares"] else "",
            "notes": "Markdown提取",
        })

    time_points = {}
    for rec in equity_records:
        tp = rec.get("time_point") or "unknown"
        if tp not in time_points:
            time_points[tp] = {"total_shares_held": 0, "total_capital": 0}
        shares = rec.get("shares_held_wan")
        if isinstance(shares, (int, float)):
            time_points[tp]["total_shares_held"] += shares
        capital = rec.get("capital_contribution_wan")
        if isinstance(capital, (int, float)):
            time_points[tp]["total_capital"] += capital

    for tp, info in time_points.items():
        validation.append({
            "check_type": "股东持股加总",
            "batch": tp,
            "subscriber_count": 0,
            "total_amount_wan": round(info["total_shares_held"], 2) if info["total_shares_held"] else "",
            "total_shares_wan": round(info["total_capital"], 2) if info["total_capital"] else "",
            "notes": "Markdown提取",
        })

    return validation


# ═══════════════════════════════════════════════════════════════
# Step 5: Excel Generation
# ═══════════════════════════════════════════════════════════════

def style_header_row(ws, headers: list[str], col_widths: list[int]):
    for col_idx, (h, w) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=1, column=col_idx, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGN
        cell.border = THIN_BORDER
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = w


def style_data_cell(ws, row: int, col: int, value):
    cell = ws.cell(row=row, column=col, value=value if value is not None else "")
    cell.alignment = CELL_ALIGN
    cell.border = THIN_BORDER
    return cell


def add_note_row(ws, row: int, col_count: int, message: str):
    cell = ws.cell(row=row, column=1, value=message)
    cell.alignment = NOTE_ALIGN
    cell.font = Font(italic=True, color="808080", size=10)
    cell.border = THIN_BORDER
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=col_count)


def write_4sheet_excel(filepath: Path, stock_code: str, company_name: str,
                        subscription_records: list[dict], equity_records: list[dict],
                        cross_validation: list[dict], transfer_records: list[dict],
                        data_status: str) -> None:
    wb = openpyxl.Workbook()

    # ── Sheet 1: 认缴流量 ──
    ws1 = wb.active
    ws1.title = "1_认缴流量"
    h1 = ["PDF页码", "增资日期", "批次标签", "认购方",
          "认购数量(万股)", "认购金额(万元)", "认购价格(元/股)", "原文证据"]
    w1 = [10, 16, 14, 28, 18, 18, 18, 80]
    style_header_row(ws1, h1, w1)
    if subscription_records:
        for ri, rec in enumerate(subscription_records, 2):
            style_data_cell(ws1, ri, 1, rec.get("pdf_page"))
            style_data_cell(ws1, ri, 2, rec.get("subscription_date"))
            style_data_cell(ws1, ri, 3, rec.get("batch_label"))
            style_data_cell(ws1, ri, 4, rec.get("subscriber_name"))
            style_data_cell(ws1, ri, 5, rec.get("subscription_shares_wan"))
            style_data_cell(ws1, ri, 6, rec.get("subscription_amount_wan"))
            style_data_cell(ws1, ri, 7, rec.get("subscription_price_yuan"))
            style_data_cell(ws1, ri, 8, (rec.get("evidence_text") or "")[:32767])
    else:
        add_note_row(ws1, 2, len(h1), data_status)

    # ── Sheet 2: 股权结构存量 ──
    ws2 = wb.create_sheet("2_股权结构存量")
    h2 = ["PDF页码", "时点", "股权结构口径", "总股本(万股)", "总出资额(万元)",
          "股东名称", "持股数(万股)", "出资额(万元)", "持股比例", "原文证据"]
    w2 = [10, 24, 18, 16, 16, 26, 16, 16, 12, 80]
    style_header_row(ws2, h2, w2)
    if equity_records:
        for ri, rec in enumerate(equity_records, 2):
            style_data_cell(ws2, ri, 1, rec.get("pdf_page"))
            style_data_cell(ws2, ri, 2, rec.get("time_point"))
            style_data_cell(ws2, ri, 3, rec.get("equity_structure_scope"))
            style_data_cell(ws2, ri, 4, rec.get("total_shares_wan"))
            style_data_cell(ws2, ri, 5, rec.get("total_capital_wan"))
            style_data_cell(ws2, ri, 6, rec.get("shareholder_name"))
            style_data_cell(ws2, ri, 7, rec.get("shares_held_wan"))
            style_data_cell(ws2, ri, 8, rec.get("capital_contribution_wan"))
            style_data_cell(ws2, ri, 9, rec.get("shareholding_ratio"))
            style_data_cell(ws2, ri, 10, (rec.get("evidence_text") or "")[:32767])
    else:
        add_note_row(ws2, 2, len(h2), data_status)

    # ── Sheet 3: 交叉校验 ──
    ws3 = wb.create_sheet("3_交叉校验")
    h3 = ["校验类型", "批次/时点", "认购方数量", "合计金额(万元)", "合计股数(万股)", "备注"]
    w3 = [20, 24, 14, 18, 18, 40]
    style_header_row(ws3, h3, w3)
    if cross_validation:
        for ri, rec in enumerate(cross_validation, 2):
            style_data_cell(ws3, ri, 1, rec.get("check_type"))
            style_data_cell(ws3, ri, 2, rec.get("batch"))
            style_data_cell(ws3, ri, 3, rec.get("subscriber_count"))
            style_data_cell(ws3, ri, 4, rec.get("total_amount_wan"))
            style_data_cell(ws3, ri, 5, rec.get("total_shares_wan"))
            style_data_cell(ws3, ri, 6, rec.get("notes"))
    else:
        add_note_row(ws3, 2, len(h3), data_status)

    # ── Sheet 4: 股权转让 ──
    ws4 = wb.create_sheet("4_股权转让")
    h4 = ["PDF页码", "转让日期", "转让方", "受让方",
          "转让数量(万股)", "转让价格(元/股)", "转让金额(万元)", "原文证据"]
    w4 = [10, 16, 24, 24, 18, 18, 18, 80]
    style_header_row(ws4, h4, w4)
    if transfer_records:
        for ri, rec in enumerate(transfer_records, 2):
            style_data_cell(ws4, ri, 1, rec.get("pdf_page"))
            style_data_cell(ws4, ri, 2, rec.get("transfer_date"))
            style_data_cell(ws4, ri, 3, rec.get("transferor"))
            style_data_cell(ws4, ri, 4, rec.get("transferee"))
            style_data_cell(ws4, ri, 5, rec.get("transfer_shares_wan"))
            style_data_cell(ws4, ri, 6, rec.get("transfer_price_yuan"))
            style_data_cell(ws4, ri, 7, rec.get("transfer_amount_wan"))
            style_data_cell(ws4, ri, 8, (rec.get("evidence_text") or "")[:32767])
    else:
        add_note_row(ws4, 2, len(h4), data_status)

    wb.save(filepath)


# ═══════════════════════════════════════════════════════════════
# Main Pipeline
# ═══════════════════════════════════════════════════════════════

def main():
    log_lines = []

    def log(msg):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {msg}"
        log_lines.append(line)
        print(line)

    log("=" * 70)
    log("Week 3 Markdown Pipeline — 从招股书Markdown直接提取到4-Sheet Excel")
    log(f"执行时间: {datetime.now().isoformat()}")
    log("输入: 招股书 Markdown 文件（位于 scratch_results/）")
    log("输出: 4-Sheet Excel（认缴流量/股权结构存量/交叉校验/股权转让）")
    log("原则: 所有数据从Markdown定位结果直接提取，不使用JSONL填充Auto")
    log("=" * 70)
    log("")

    total_stats = {
        "subscription": 0, "equity": 0, "transfers": 0,
        "validation": 0, "from_markdown": 0, "markdown_missing": 0,
    }

    for stock_code, info in COMPANIES.items():
        name = info["name"]
        md_subdir = info.get("md_subdir")
        md_filename = info.get("md_filename")

        log(f"处理: {stock_code} {name}")

        if md_subdir and md_filename:
            md_path = SCRATCH_DIR / md_subdir / md_filename
        else:
            md_path = None

        subscription_records = []
        equity_records = []
        transfer_records = []

        md_available = md_path and md_path.exists()

        if md_available:
            log(f"  Markdown: {md_path}")
            md_text = read_markdown(md_path)
            log(f"  文本长度: {len(md_text)} 字符")

            history_section = locate_history_section(md_text)
            if history_section:
                log(f"  历史沿革章节: 已定位 ({len(history_section)} 字符)")

                log("  提取认缴流量...")
                subscription_records = extract_subscription_events(
                    history_section, stock_code, name)
                log(f"    认缴流量: {len(subscription_records)} 条")

                log("  提取股权结构快照...")
                equity_records = extract_equity_snapshots(
                    history_section, stock_code, name)
                log(f"    股权存量: {len(equity_records)} 条")

                log("  提取股权转让...")
                transfer_records = extract_transfer_events(
                    history_section, stock_code, name)
                log(f"    股权转让: {len(transfer_records)} 条")

                data_status = f"来源: Markdown 直接提取 ({md_filename})"
                if not subscription_records and not equity_records:
                    data_status = (
                        f"Markdown已加载但自动提取未产出数据。"
                        f"历史沿革章节已定位({len(history_section)}字符)，"
                        f"但正则匹配未能提取到结构化事件。请人工核对Markdown格式。"
                    )
            else:
                log("  [WARNING] 未能定位历史沿革章节")
                data_status = (
                    f"Markdown已加载({md_filename})，"
                    f"但未能定位到「历史沿革」/「股本演变」章节。"
                    f"请检查招股书结构。"
                )
                total_stats["markdown_missing"] += 1
        else:
            note = info.get("note")
            if note:
                log(f"  [SKIP] {note}")
                data_status = note
            else:
                scratch_relative = f"{md_subdir}/{md_filename}" if md_subdir else "N/A"
                log(f"  [WARNING] Markdown 文件不存在")
                data_status = (
                    f"Markdown源文件缺失({scratch_relative})，无法进行自动提取。"
                    f"请先将PDF通过MinerU转换为Markdown，"
                    f"放入{SCRATCH_DIR / (md_subdir or '')}/ 目录。"
                )
            total_stats["markdown_missing"] += 1

        # JSONL 仅做统计对比，不用于填充 Auto
        jsonl_path = DATA_DIR / f"{stock_code}_{name}.jsonl"
        if jsonl_path.exists():
            j_records = load_jsonl(jsonl_path)
            j_sub = len([r for r in j_records if r.get("record_type") == "subscription_flow"])
            j_eq = len([r for r in j_records if r.get("record_type") == "equity_snapshot"])
            j_tr = len([r for r in j_records if r.get("record_type") == "equity_transfer"])
            log(f"  JSONL参考(仅对比): 认缴{j_sub} | 股权{j_eq} | 转让{j_tr}")

        total_stats["subscription"] += len(subscription_records)
        total_stats["equity"] += len(equity_records)
        total_stats["transfers"] += len(transfer_records)
        if md_available:
            total_stats["from_markdown"] += 1

        cross_validation = generate_cross_validation(subscription_records, equity_records)
        total_stats["validation"] += len(cross_validation)

        excel_path = AUTO_EXCEL_DIR / f"{stock_code}_{name}_auto.xlsx"
        write_4sheet_excel(
            excel_path, stock_code, name,
            subscription_records, equity_records,
            cross_validation, transfer_records,
            data_status
        )
        log(f"  输出: {excel_path.name}")

        # 保存从 Markdown 提取的 JSONL（非旧 JSONL 拷贝）
        all_extracted = subscription_records + equity_records + transfer_records
        auto_jsonl_path = AUTO_JSONL_DIR / f"{stock_code}_{name}_auto.jsonl"
        with open(auto_jsonl_path, "w", encoding="utf-8") as f:
            for rec in all_extracted:
                rec_clean = {k: v for k, v in rec.items() if not k.startswith("_")}
                f.write(json.dumps(rec_clean, ensure_ascii=False) + "\n")
        log(f"  输出: {auto_jsonl_path.name} ({len(all_extracted)} 条)")

        log("")

    log("=" * 70)
    log("Pipeline 执行完毕")
    log(f"  从Markdown成功提取: {total_stats['from_markdown']}/{len(COMPANIES)} 家")
    log(f"  Markdown不可用:      {total_stats['markdown_missing']}/{len(COMPANIES)} 家")
    log(f"  认缴流量总记录: {total_stats['subscription']}")
    log(f"  股权存量总记录: {total_stats['equity']}")
    log(f"  股权转让总记录: {total_stats['transfers']}")
    log(f"  交叉校验项:     {total_stats['validation']}")
    log(f"  生成Excel: {len(COMPANIES)} 份")
    log("=" * 70)

    log_path = LOG_DIR / "markdown_process.log"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))
    print(f"\n日志已写入: {log_path}")


if __name__ == "__main__":
    main()
