# 四阶段产出体系 (raw → parsed → validated → reviewed)

> 教授第四条修改意见：保存 raw、parsed、validated、reviewed 各阶段结果，说明人工修改发生在哪里。

---

## 一、目录结构

```
pipeline/stages/
├── README.md                    # 本文件
├── manifest.json                # 各阶段数据清单
├── migrate_stages.py            # 数据迁移脚本（可重复运行）
├── raw/                         # 阶段1: 原始提取
│   ├── 001282_三联锻造_raw.jsonl
│   ├── 301563_云汉芯城_raw.jsonl
│   ├── ...
│   └── 920116_星图测控_raw.jsonl
├── parsed/                      # 阶段2: 结构解析
│   ├── 001282_三联锻造_parsed.jsonl
│   └── ...
├── validated/                   # 阶段3: 校验标记
│   ├── 001282_三联锻造_validated.jsonl
│   └── ...
└── reviewed/                    # 阶段4: 人工复核 (最终数据)
    ├── 001282_三联锻造_reviewed.xlsx
    └── ...
```

---

## 二、阶段定义

| 阶段 | 名称 | 内容说明 | 来源 | 人工介入？ |
|------|------|----------|------|-----------|
| **raw** | 原始提取 | Markdown 章节定位 + 正则/规则提取的直接输出，保留原文数值和文本，不经过任何处理 | pipeline 自动 | 否 |
| **parsed** | 结构解析 | raw 数据经类型转换（string→float）、单位归一化（股→万股）、字段映射后的结构化数据 | pipeline 自动 | 否 |
| **validated** | 校验标记 | parsed 数据经 schema 校验 + cross-check，每条记录增加 `_validation_status` 和 `_validation_errors` 列 | pipeline 自动 | 否 |
| **reviewed** | 人工复核 | validated 基础上人工对照 PDF 逐条核实、修正错误、补充遗漏。**人工修改发生在此阶段** | **人工对照 PDF** | **是** |

### 2.1 Raw — 原始提取

- **输入**: Markdown 格式的招股书文本
- **处理**: 章节定位（正则匹配"历史沿革"/"股本和股东变化"）+ 事件提取（table regex + 大语言模型）
- **输出**: JSONL，每条记录包含 `record_type`、`stock_code`、原始数值、`evidence_text`（原文摘录）
- **特点**: 保留所有原始值和文本——包括赛分科技的单位错误（`subscription_shares_wan` 填入的是"股"而非"万股"）
- **标记**: 每条记录带 `_stage: "raw"` 和 `_source: "Markdown 章节定位 + 正则提取"`

### 2.2 Parsed — 结构解析

- **输入**: raw JSONL
- **处理**:
  1. 类型转换: `subscription_shares_wan`、`subscription_amount_wan` 从 str → float
  2. 单位归一化: 检测 evidence_text 中的"（股）"列标题，自动触发 ÷10000 修正
  3. 字段映射: 合并 subscription_flow + equity_snapshot + equity_transfer
  4. 补充计算: 当 `subscription_price_yuan` 缺失时，由 amount/shares 计算
- **标记**: 
  - `_stage: "parsed"`
  - `_unit_corrected: true/false` — 标识该条是否被单位修正
  - `_correction_detail` — 修正前后值对比（如 "从 1571815.0 股 修正为 157.1815 万股"）

### 2.3 Validated — 校验标记

- **输入**: parsed JSONL + comparison.csv（Gold-vs-Auto 对比）
- **处理**:
  1. Schema 校验: 必填字段检查、数值范围合理性（负值检测、持股比例 0-100）
  2. Cross-check 标记: 注入 per_event_check 和 per_shareholder_check 的状态
  3. 逐字段对比: 从 comparison.csv 提取 Gold-vs-Auto 的 match/mismatch/missing 标记
- **标记**:
  - `_validation_status`: `pass` / `warn` / `fail`
  - `_validation_errors`: 错误/警告列表
  - `_validated_by: "pipeline"`
- 校验失败的记录不会在此阶段修改数据，仅标记问题供 reviewed 阶段处理

### 2.4 Reviewed — 人工复核

- **输入**: validated JSONL + Gold Standard Excel
- **处理**: **人工对照 PDF 逐条核实**，在 Excel 中修正错误、补充遗漏、标注差异
- **产物**: 双 Sheet Excel（Sheet 1: 认缴流量, Sheet 2: 股权结构存量），额外包含股权转让 Sheet
- **人工修改记录规范**（每条修改保留以下四列）:
  - `original_value` — 修改前的值
  - `revised_value` — 修改后的值
  - `reason` — 修改原因（如"单位错误：原文标注为'股'，应除以10000转为万股"）
  - `pdf_page` — 对应的 PDF 页码证据
- **标记**: Excel 每条记录已含 data_source、evidence_text 和 notes 字段

---

## 三、数据流转

```
Markdown 招股书文本
      │
      ▼
 [阶段1: raw] ──── 章节定位 + 正则/规则提取 ──── raw/*.jsonl
      │              (保留原始数值, 不做处理)
      │
      ▼
 [阶段2: parsed] ─ 类型转换 + 单位归一化 + 字段映射 ── parsed/*.jsonl
      │              (自动修正可检测的 unit error)
      │
      ▼
 [阶段3: validated] ─ schema校验 + cross-check标记 ── validated/*.jsonl
      │                (标记问题, 不修改数据)
      │
      ▼
 [阶段4: reviewed] ─ 人工对照PDF逐条核实 ── reviewed/*.xlsx
      │                ◀── 人工修改发生在此
      │
      ▼
      最终数据 (Final / Gold Standard)
```

**关键原则**：
- 前三个阶段（raw → parsed → validated）全自动可复现，任何人运行 `migrate_stages.py` 能得到一致结果
- 第四个阶段（reviewed）需要人工对照 PDF，不要求代码复现，但每次修改必须有 original_value / revised_value / reason / pdf_page 四列记录

---

## 四、可复现性承诺

| 阶段 | 可复现性 | 说明 |
|------|----------|------|
| raw | 可复现 | 运行 pipeline 从 Markdown 重新提取即可 |
| parsed | 可复现 | 运行 `migrate_stages.py` 对 raw 数据做确定性转换 |
| validated | 可复现 | 运行 `migrate_stages.py` + `per_event_check.py` + `per_shareholder_check.py` |
| reviewed | 不可代码复现 | 需人工对照 PDF；但修改记录已通过 original_value/revised_value/reason/pdf_page 四列保留 |

### 验证命令

```bash
# 重新生成 parsed + validated（从 raw 开始）
cd week3/pipeline/stages
python3 migrate_stages.py

# 重新运行 cross-check
cd week3/validation/cross_check
python3 per_event_check.py
python3 per_shareholder_check.py
```

---

## 五、赛分科技单位错误处理

赛分科技是四阶段体系最典型的验证案例：

| 阶段 | subscription_shares_wan 值 | 单位 |
|------|---------------------------|------|
| raw | 1571815.0 | 股（未归一化） |
| parsed | 157.1815 | 万股（自动修正） |
| validated | 157.1815 | 万股（校验通过） |
| reviewed | Gold Standard 核实 | 万股（人工确认） |

parsed 阶段通过检测 evidence_text 中的 `（股）` 列标题 + `subscription_shares_wan > 100000` 阈值，自动识别并修正了 8 条 unit error。`migrate_stages.py` 中 `parse_records()` 的 `UNIT_ERROR_THRESHOLD = 100000` 和 `"（股）" in evidence` 双重判据即为固定测试逻辑。

---

## 六、人工修改标注位置

人工修改**全部集中**在 `reviewed/` 阶段。

每条人工修改记录在 Excel 中需保留以下信息：

| 列名 | 示例 | 说明 |
|------|------|------|
| original_value | 1571815.0 | parsed 阶段的原始值（股） |
| revised_value | 157.1815 | 人工核实后的正确值（万股） |
| reason | 单位错误：原文标注为"股"，除以10000转为万股 | 修改原因 |
| pdf_page | 第51页 | PDF 页码证据 |

### 人工修改类型（常见）

1. **单位修正**: 赛分科技股→万股 (parsed 阶段已自动修正 8 条, reviewed 确认)
2. **数值补全**: 三协电机部分认购方股数反推
3. **时点补充**: 星图测控招股书实际有更多时点
4. **事件拆分**: 云汉芯城 A 轮三方拆分
5. **日期对齐**: Gold 使用"YYYY年M月"格式 vs Auto 使用"YYYY-MM-DD"

---

## 七、已知限制

1. **comparison.csv 对齐**: validated 阶段从 comparison.csv 注入校验标记时，Gold 和 Auto 的行索引对齐并非 1:1（Auto 可能多抽或少抽记录），comparison_flag 为公司级汇总标记
2. **reviewed 产物格式**: 当前 reviewed 阶段存储 Gold Standard Excel，人工修改记录已通过 Excel 中的备注列和原文列保留；尚未实现结构化的人工修改 diff 记录
3. **parsed 的单位修正覆盖**: 仅覆盖能通过 `evidence_text` 中 `（股）` 关键词识别的情况；如果原文未标注列标题，需要 validated 阶段的大值告警 + reviewed 阶段人工核实
