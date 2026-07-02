# Week 3 — Auto Output（自动化 Pipeline 产出）

> 来源: Week 3 Pipeline (`week3/pipeline/week3_pipeline.py`)
> 输入: Week 2 JSONL 数据（`week3/data/*.jsonl`）
> 处理流程: 模型原始提取 → Schema 校验 → Excel 转换
> 日期: 2026-06-18

---

## 一、产出说明

本目录包含 Week 3 自动化 Pipeline 的全部产出，分为两个子目录：

| 子目录 | 格式 | 说明 |
|--------|------|------|
| `auto_jsonl/` | JSONL | 模型原始提取结果（未做任何手工修正），直接复制自 Week 2 的提取数据 |
| `auto_excel/` | Excel | Pipeline 脚本自动生成的 Excel，包含「认缴流量」和「股权结构存量」两个 Sheet |

Pipeline 仅做「搬运 + 格式转换 + 基础 Schema 校验」，不做数据修正。所有已知问题（如赛分科技单位错误、影石创新无认购流量等）均保留在 Auto 输出中，用于展示纯自动化产出的局限性。

---

## 二、文件清单（8 家公司）

| 股票代码 | 公司简称 | JSONL | Excel |
|---------|---------|-------|-------|
| 001282 | 三联锻造 | `auto_jsonl/001282_三联锻造_auto.jsonl` | `auto_excel/001282_三联锻造_auto.xlsx` |
| 301563 | 云汉芯城 | `auto_jsonl/301563_云汉芯城_auto.jsonl` | `auto_excel/301563_云汉芯城_auto.xlsx` |
| 301581 | 黄山谷捷 | `auto_jsonl/301581_黄山谷捷_auto.jsonl` | `auto_excel/301581_黄山谷捷_auto.xlsx` |
| 603418 | 友升股份 | `auto_jsonl/603418_友升股份_auto.jsonl` | `auto_excel/603418_友升股份_auto.xlsx` |
| 688758 | 赛分科技 | `auto_jsonl/688758_赛分科技_auto.jsonl` | `auto_excel/688758_赛分科技_auto.xlsx` |
| 688775 | 影石创新 | `auto_jsonl/688775_影石创新_auto.jsonl` | `auto_excel/688775_影石创新_auto.xlsx` |
| 920100 | 三协电机 | `auto_jsonl/920100_三协电机_auto.jsonl` | `auto_excel/920100_三协电机_auto.xlsx` |
| 920116 | 星图测控 | `auto_jsonl/920116_星图测控_auto.jsonl` | `auto_excel/920116_星图测控_auto.xlsx` |

---

## 三、Auto vs Gold Standard 差异概览

| 指标 | 数值 |
|------|------|
| 总记录数 | 731 |
| 完全匹配率 | ~62%（含手工修正前差异） |
| 主要差异来源 | 单位归一化（赛分科技）、出资额计算口径、跨页表格拼接 |
| 赛分科技 | 0% 匹配率（单位错误，需手工 /10000 修正） |
| 三协电机 | 100% 匹配率（Pipeline 理想案例） |

详细对比结果见 `week3/comparison/comparison.csv`。
