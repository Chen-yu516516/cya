# Week 3 Pipeline — 自动化提取管线

> 构建者: 陈雨昂 (cya)
> 日期: 2026-06-18

---

## 一、Pipeline 设计思路

### 总体架构

```
week3/data/*.jsonl    ────→   week3_pipeline.py   ────→   outputs/
    (管道原始输出)               │                          ├── auto_excel/*.xlsx
                                 │                          ├── auto_jsonl/*.jsonl
                                 │                          └── logs/validation.log
                                 │
                           Schema 校验
                           (类型/必填/数值合理性)
```

### 核心思路：规则 + 管道混合提取 → 校验 → Excel 输出

1. **数据输入**: 8 家公司的 JSONL 文件，来自 Week 2 的模型逐页提取结果。
2. **Schema 校验**:
   - 类型检查（数值字段是否为 int/float）
   - 必填字段检查（record_type、stock_code、pdf_page 等是否缺失）
   - 数值合理性（负数检测、持股比例 0-100 范围、疑似单位错误检测）
3. **Excel 转换**: 每家公司生成一份双 Sheet Excel —— Sheet 1 认缴流量、Sheet 2 股权结构存量。
4. **Auto JSONL 输出**: 直接复制原始 JSONL 数据，**不做任何手工修正**，包括赛分科技的 unit 错误。
5. **校验日志**: 所有校验结果写入 `validation.log`。

---

## 二、自动化程度评估

### 当前自动化能力

| 能力 | 自动化 | 说明 |
|------|--------|------|
| JSONL → Excel 转换 | 全自动 | 格式映射、双 Sheet 分页 |
| Schema 类型校验 | 全自动 | int/float 类型检测、null 检测 |
| 必填字段检测 | 全自动 | record_type/stock_code/pdf_page 等 |
| 数值合理性检测 | 全自动 | 负数、比例范围、异常大值告警 |
| 单位归一化 | 手动 | 赛分科技股→万股需手工脚本修复 |
| 跨页表格拼接 | 手动 | 跨页断裂需人工逐页比对 |
| 反推值标注 | 手动 | 持股比例反推需人工判断并标注 |
| 时点命名一致性 | 半自动 | 校验可检测不一致，但修复需人工 |

### 纯自动化 vs 人工修正的差距

**自动化只能做到**: 原样搬运 JSONL → Excel + 基础校验。

**必须人工介入的环节**:
1. **单位修正** — 赛分科技 `subscription_shares_wan` 误填为股
2. **时点覆盖** — 星图测控仅 3 个时点，招股书实际有更多
3. **数据补全** — 三协电机个别认购方股数反推
4. **云汉芯城 A 轮拆分** — 按持股比例反推，非原文记载
5. **影石创新** — 无独立 subscription_flow，数据不足

---

## 三、已知缺陷

### 3.1 赛分科技 Unit 错误（自动化最典型缺陷）

- **问题**: `subscription_shares_wan` 在原始 JSONL 中填入的是股数（如 1,571,815.0），而非万股（应为 157.1815）
- **原因**: 原文表格列标题为"认购股份（股）"，但 管道未做单位归一化
- **Pipeline 检测**: validation.log 中已输出 `[WARN] subscription_shares_wan 值异常大` 告警
- **Gold Standard 修复**: 手工脚本 `fix_saifen_units.py` 逐条 /10000 修正
- **Auto 输出**: 故意保留原始错误，以展示 pipeline 局限性

### 3.2 星图测控时点覆盖不足

- **问题**: 仅提取了 3 个时点（t0, t1, t2），但招股书披露的股权变更次数实际多于 3
- **原因**: 招股书对部分变更的描述为概述性文字，无结构化表格，管道未能识别为独立时点

### 3.3 三协电机部分反推值

- **问题**: 第 1 批稳正景明/长泽创投个别股数、第 2 批 15 名员工激励对象个别股数，均通过持股比例或权益分派反向推算
- **原因**: 招股书未逐项披露各认购方具体股数

### 3.4 云汉芯城 A 轮三方拆分

- **问题**: A 轮三方共同增资中，PDF 未披露各认购方具体出资拆分，gold standard 按整体变更时持股比例反推分配
- **原因**: PDF 原文仅提供合计数

### 3.5 影石创新无 flow 记录

- **问题**: subscription_flow 为 0 条，认缴流量 Sheet 为空
- **原因**: 招股书对增资过程的披露方式为股权快照系列，无逐笔 flow

---

## 四、未来改进方向

### 4.1 短期（规则增强）

1. **单位自动检测**: 在 evidence_text 中搜索列标题关键词（如"（股）"vs"（万股）"），自动触发归一化
2. **异常值自动告警 + 自动修复**: 当 `subscription_shares_wan > 100000` 时，自动 /10000 并标注"auto-fixed"
3. **时点排序自动编号**: 按 `subscription_date` / `time_point` 中的日期自动排序并重新分配 t0/t1/...

### 4.2 中期（模型增强）

1. **Few-shot prompt 优化**: 在 prompt 中嵌入正确的单位转换示例，降低 管道单位推断错误率
2. **跨页上下文传递**: 将相邻页面的证据合并后一并发送给 模型，减少表格断裂
3. **结构化表格专用提取器**: 使用基于布局分析的表格提取（如 Camelot/Tabula），替代 管道的纯文本解析

### 4.3 长期（端到端自动化）

1. **PDF → JSONL 全流程**: 直接使用多模态视觉模型识别 PDF 表格，跳过 模型 文本解析环节
2. **自动校对闭环**: Pipeline 输出与 gold standard 做字段级 diff，自动标记差异项供人工审核
3. **增量更新**: 当招股书更新版本时，仅重新提取变更部分，保留已验证的存量数据

---

## 五、产出物清单

```
week3/pipeline/
├── week3_pipeline.py          # 主脚本（可独立运行）
└── README.md                  # 本文件

week3/prompts/
└── extraction_prompt.md       # Week 2 实际使用的提取 Prompt 文档

week3/outputs/
├── auto_excel/
│   ├── 001282_三联锻造_auto.xlsx
│   ├── 301563_云汉芯城_auto.xlsx
│   ├── 301581_黄山谷捷_auto.xlsx
│   ├── 603418_友升股份_auto.xlsx
│   ├── 688758_赛分科技_auto.xlsx    # ← 含 unit 错误的原始版
│   ├── 688775_影石创新_auto.xlsx
│   ├── 920100_三协电机_auto.xlsx
│   └── 920116_星图测控_auto.xlsx
├── auto_jsonl/
│   ├── 001282_三联锻造_auto.jsonl
│   ├── 301563_云汉芯城_auto.jsonl
│   ├── 301581_黄山谷捷_auto.jsonl
│   ├── 603418_友升股份_auto.jsonl
│   ├── 688758_赛分科技_auto.jsonl   # ← 含 unit 错误的原始版
│   ├── 688775_影石创新_auto.jsonl
│   ├── 920100_三协电机_auto.jsonl
│   └── 920116_星图测控_auto.jsonl
├── raw_llm_outputs/
│   ├── 001282_raw.jsonl
│   ├── 301563_raw.jsonl
│   ├── 301581_raw.jsonl
│   ├── 603418_raw.jsonl
│   ├── 688758_raw.jsonl
│   ├── 688775_raw.jsonl
│   ├── 920100_raw.jsonl
│   └── 920116_raw.jsonl
└── logs/
    └── validation.log
```
