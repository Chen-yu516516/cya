#!/usr/bin/env python3
"""
四阶段数据迁移脚本: raw → parsed → validated → reviewed
将 week3/data 和 week3/manual_gold 的数据按阶段拆分到 pipeline/stages/ 下
"""

import json
import os
import csv
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # pipeline/stages/
PIPELINE_DIR = os.path.dirname(BASE_DIR)              # pipeline/
WEEK3_DIR = os.path.dirname(PIPELINE_DIR)             # week3/
DATA_DIR = os.path.join(WEEK3_DIR, "data")
GOLD_DIR = os.path.join(WEEK3_DIR, "manual_gold")
COMPARISON_CSV = os.path.join(WEEK3_DIR, "comparison", "comparison.csv")

STAGES = {
    "raw": os.path.join(BASE_DIR, "raw"),
    "parsed": os.path.join(BASE_DIR, "parsed"),
    "validated": os.path.join(BASE_DIR, "validated"),
    "reviewed": os.path.join(BASE_DIR, "reviewed"),
}

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

# 赛分科技 unit error: subscription_shares_wan 字段填入了股而非万股，需 /10000
# 判定标准: subscription_shares_wan > 100000 且 evidence_text 中含 "（股）"
UNIT_ERROR_THRESHOLD = 100000


def load_raw_jsonl(code, name):
    """加载原始 JSONL 数据"""
    path = os.path.join(DATA_DIR, f"{code}_{name}.jsonl")
    if not os.path.exists(path):
        return None, "源数据缺失"
    with open(path, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip() and not line.startswith("#")]
    return records, None


def load_full_jsonl(code, name):
    """加载 full JSONL (含转让)"""
    path = os.path.join(DATA_DIR, f"{code}_{name}_full.jsonl")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip() and not line.startswith("#")]


def parse_records(records):
    """
    阶段 parsed: 类型转换 + 单位归一化 + 字段映射
    - 将 subscription_shares_wan / subscription_amount_wan 转 float
    - 赛分科技: 单位检测 (股→万股 /10000)
    - 计算 subscription_price_yuan (如果缺失: amount/shares)
    """
    parsed = []
    for rec in records:
        p = dict(rec)
        p["_stage"] = "parsed"
        p["_unit_corrected"] = False
        p["_correction_detail"] = None

        # 类型转换
        for fld in ["subscription_shares_wan", "subscription_amount_wan"]:
            if fld in p and p[fld] is not None:
                try:
                    p[fld] = float(p[fld])
                except (ValueError, TypeError):
                    pass

        if "subscription_price_yuan" in p and p.get("subscription_price_yuan") is not None:
            try:
                p["subscription_price_yuan"] = float(p["subscription_price_yuan"])
            except (ValueError, TypeError):
                pass

        # 单位归一化: 赛分科技 unit error 检测
        if p.get("record_type") == "subscription_flow":
            shares = p.get("subscription_shares_wan")
            evidence = p.get("evidence_text", "")
            if (shares is not None and shares > UNIT_ERROR_THRESHOLD
                    and "（股）" in evidence):
                original = shares
                p["subscription_shares_wan"] = round(shares / 10000, 4)
                p["_unit_corrected"] = True
                p["_correction_detail"] = (
                    f"unit_error: subscription_shares_wan 从 {original} 股"
                    f" 修正为 {p['subscription_shares_wan']} 万股 (÷10000)"
                )

        # 补充 price 字段
        if p.get("record_type") == "subscription_flow":
            shares = p.get("subscription_shares_wan")
            amount = p.get("subscription_amount_wan")
            price = p.get("subscription_price_yuan")
            if price is None and shares and amount and shares > 0:
                p["subscription_price_yuan"] = round(amount / shares, 4)

        parsed.append(p)
    return parsed


def load_comparison_validation():
    """从 comparison.csv 加载每条记录的校验状态"""
    validation = {}  # key: (stock_code, row_index, column) → status
    if not os.path.exists(COMPARISON_CSV):
        return validation

    with open(COMPARISON_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row.get("stock_code", "").strip()
            try:
                idx = int(row.get("row_index", "-1"))
            except ValueError:
                continue
            col = row.get("column", "").strip()
            status = row.get("status", "").strip()
            reason = row.get("mismatch_reason", "") or row.get("missing_reason", "")
            key = (code, idx, col)
            validation[key] = {"status": status, "reason": reason}
    return validation


def validate_records(parsed_records, code):
    """
    阶段 validated: schema 校验 + cross-check 标记
    每条记录增加:
    - _validation_status: pass / warn / fail
    - _validation_errors: list of error strings
    - _validated_by: "pipeline"
    """
    validations = load_comparison_validation()

    validated = []
    for rec in parsed_records:
        v = dict(rec)
        v["_stage"] = "validated"
        errors = []
        warnings = []

        # Schema 校验: 必填字段
        if v.get("record_type") == "subscription_flow":
            required = ["subscription_date", "subscriber_name",
                        "subscription_shares_wan", "subscription_amount_wan"]
            for fld in required:
                if v.get(fld) is None:
                    errors.append(f"missing_required: {fld}")

            # 数值合理性
            shares = v.get("subscription_shares_wan")
            amount = v.get("subscription_amount_wan")
            try:
                if shares is not None and float(shares) < 0:
                    errors.append(f"negative_shares: {shares}")
            except (ValueError, TypeError):
                pass
            try:
                if amount is not None and float(amount) < 0:
                    errors.append(f"negative_amount: {amount}")
            except (ValueError, TypeError):
                pass

        elif v.get("record_type") == "equity_snapshot":
            try:
                ratio = float(v.get("shareholding_ratio")) if v.get("shareholding_ratio") is not None else None
            except (ValueError, TypeError):
                ratio = None
            if ratio is not None and (ratio < 0 or ratio > 100):
                errors.append(f"ratio_out_of_range: {ratio}")

        elif v.get("record_type") == "equity_transfer":
            required = ["transfer_date", "transferor", "transferee",
                        "transfer_shares_wan", "transfer_amount_wan"]
            for fld in required:
                if v.get(fld) is None:
                    errors.append(f"missing_required: {fld}")

        # 从 comparison.csv 注入校验标记
        # comparison.csv 用的是 Gold 的行索引对齐; 这里做 stock_code 级标记
        code_matches = [k for k in validations if k[0] == code]
        if code_matches:
            fail_count = sum(1 for k in code_matches
                            if validations[k]["status"] in ("mismatch", "missing"))
            if fail_count > 0:
                warnings.append(f"comparison_flag: {fail_count} mismatches/missing in Gold-vs-Auto")
        else:
            warnings.append("comparison_flag: no Gold comparison data available")

        if errors:
            v["_validation_status"] = "fail"
            v["_validation_errors"] = errors + warnings
        elif warnings:
            v["_validation_status"] = "warn"
            v["_validation_errors"] = warnings
        else:
            v["_validation_status"] = "pass"
            v["_validation_errors"] = []

        v["_validated_by"] = "pipeline"
        validated.append(v)

    return validated


def migrate_stage_raw():
    """阶段1: raw — 原始提取数据，只复制不做任何处理"""
    print("=== 阶段 raw: 迁移原始提取数据 ===")
    for code, name in COMPANIES:
        records, error = load_raw_jsonl(code, name)
        if error:
            with open(os.path.join(STAGES["raw"], f"{code}_{name}_raw.jsonl"), "w",
                      encoding="utf-8") as f:
                f.write(f"# RAW_STAGE: {code}_{name} — {error}\n")
                f.write(f"# 源数据缺失: 无法从 Markdown 提取原始事件\n")
                f.write(f"# 原因: PDF Markdown 转换未生成或定位失败\n")
            print(f"  {code}_{name}: {error}")
            continue

        # 为每条记录添加阶段标记
        for r in records:
            r["_stage"] = "raw"
            r["_source"] = "Markdown 章节定位 + 正则提取"

        out_path = os.path.join(STAGES["raw"], f"{code}_{name}_raw.jsonl")
        with open(out_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  {code}_{name}: {len(records)} 条 → raw")

    return True


def migrate_stage_parsed():
    """阶段2: parsed — 类型转换 + 单位归一化"""
    print("\n=== 阶段 parsed: 类型转换 + 单位归一化 ===")
    for code, name in COMPANIES:
        records = load_full_jsonl(code, name)
        if records is None:
            with open(os.path.join(STAGES["parsed"], f"{code}_{name}_parsed.jsonl"), "w",
                      encoding="utf-8") as f:
                f.write(f"# PARSED_STAGE: {code}_{name} — 源数据缺失，无法结构化解析\n")
            print(f"  {code}_{name}: 源数据缺失，跳过")
            continue

        parsed = parse_records(records)
        unit_fixed = sum(1 for p in parsed if p.get("_unit_corrected"))

        out_path = os.path.join(STAGES["parsed"], f"{code}_{name}_parsed.jsonl")
        with open(out_path, "w", encoding="utf-8") as f:
            for p in parsed:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")

        msg = f"{code}_{name}: {len(parsed)} 条"
        if unit_fixed:
            msg += f" (单位修正 {unit_fixed} 条)"
        print(f"  {msg}")

    return True


def migrate_stage_validated():
    """阶段3: validated — schema 校验 + cross-check 标记"""
    print("\n=== 阶段 validated: schema 校验 + cross-check 标记 ===")
    for code, name in COMPANIES:
        parsed_path = os.path.join(STAGES["parsed"], f"{code}_{name}_parsed.jsonl")
        if not os.path.exists(parsed_path):
            with open(os.path.join(STAGES["validated"], f"{code}_{name}_validated.jsonl"), "w",
                      encoding="utf-8") as f:
                f.write(f"# VALIDATED_STAGE: {code}_{name} — 上游 parsed 数据缺失，无法校验\n")
            print(f"  {code}_{name}: 上游缺失，跳过")
            continue

        with open(parsed_path, "r", encoding="utf-8") as f:
            parsed = []
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parsed.append(json.loads(line))

        validated = validate_records(parsed, code)
        stats = {
            "pass": sum(1 for v in validated if v["_validation_status"] == "pass"),
            "warn": sum(1 for v in validated if v["_validation_status"] == "warn"),
            "fail": sum(1 for v in validated if v["_validation_status"] == "fail"),
        }

        out_path = os.path.join(STAGES["validated"], f"{code}_{name}_validated.jsonl")
        with open(out_path, "w", encoding="utf-8") as f:
            for v in validated:
                f.write(json.dumps(v, ensure_ascii=False) + "\n")

        print(f"  {code}_{name}: pass={stats['pass']} warn={stats['warn']} fail={stats['fail']}")

    return True


def migrate_stage_reviewed():
    """阶段4: reviewed — 人工复核修订后的最终数据 (Gold Standard)"""
    print("\n=== 阶段 reviewed: 迁移人工复核 Gold 数据 ===")
    for code, name in COMPANIES:
        src = os.path.join(GOLD_DIR, f"{code}_{name}_gold.xlsx")
        dst = os.path.join(STAGES["reviewed"], f"{code}_{name}_reviewed.xlsx")
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"  {code}_{name}: Gold Excel → reviewed")
        else:
            with open(os.path.join(STAGES["reviewed"], f"{code}_{name}_reviewed.txt"), "w",
                      encoding="utf-8") as f:
                f.write(f"# REVIEWED_STAGE: {code}_{name} — Gold Standard 未就绪\n"
                        f"# 该公司的 manual_gold Excel 文件缺失或尚未完成人工复核\n")
            print(f"  {code}_{name}: Gold 文件不存在，生成占位说明")


def generate_manifest():
    """生成各阶段数据清单"""
    manifest = {
        "pipeline_version": "week3-四阶段",
        "generated_at": "2026-07-20",
        "companies": COMPANIES,
        "stages": {}
    }

    for stage_name, stage_dir in STAGES.items():
        files = sorted(os.listdir(stage_dir))
        manifest["stages"][stage_name] = {
            "path": f"pipeline/stages/{stage_name}/",
            "file_count": len(files),
            "files": files,
        }

    manifest_path = os.path.join(BASE_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\nManifest: {manifest_path}")


if __name__ == "__main__":
    os.chdir(BASE_DIR)
    migrate_stage_raw()
    migrate_stage_parsed()
    migrate_stage_validated()
    migrate_stage_reviewed()
    generate_manifest()
    print("\n=== 四阶段数据迁移完成 ===")
