# cya — PE/VC 融资信息自动提取与融资分析

> 仓库：Chen-yu516516/cya | 分支：week3-submission
> 第六周提交 | 2026-07-24

## 统一运行命令

```bash
# 方式一：Shell 入口
bash pipeline/run_all.sh

# 方式二：Python 入口
cd week3 && python3 week3_pipeline.py
```

**输入**：`week3/data/` 下的 Markdown 文件（由 MinerU 从 PDF 转换）与 JSONL 数据文件
**输出**：`pipeline/stages/` 下的 raw → parsed → validated 三阶段产物
**人工介入位置**：`pipeline/stages/reviewed/` 阶段需人工对照 PDF 逐条核实，修改通过 `original_value / revised_value / reason / pdf_page` 四列记录

## 完成状态

| 要素 | 状态 |
|------|------|
| 8家公司覆盖 | ✅ 全部完成 |
| Gold标准标注 | ✅ 人工逐页PDF标注，4 Sheet Excel |
| 自动化提取管道 | ✅ raw → parsed → validated 三阶段可复现 |
| 逐事件 Cross-check | ✅ per_event_check.py |
| 逐股东 Cross-check | ✅ per_shareholder_check.py |
| 股权转让补足 | ✅ fill_equity_transfers.py |
| 赛分科技单位错误 | ✅ 固定为回归测试 |
| 四阶段产出体系 | ✅ 人工修改位置明确标注 |
| 融资分析报告 | ✅ report/week6_report.md（40KB+） |
| 组内交叉复核 | ✅ 详见 review/README.md |

## 已知问题

| 问题 | 影响范围 | 说明 |
|------|---------|------|
| 赛分科技 Markdown 缺失 | 688758 | MinerU 解析质量不佳，部分表格断裂和列错位 |
| 三协电机 t0 缺失 | 920100 | 招股书正文无完整历史沿革章节，需查阅公开转让说明书 |
| 云汉芯城 A 轮拆分 | 301563 | 原文仅给合计数，三方拆分按股改比例反推 |
| 影石创新无逐笔 flow | 688775 | 招股书以股权快照方式披露，非逐笔增资流水 |
| Cross-check FAIL 总数偏高 | 全局 | 59条 FAIL 多为单位归一化差异（股 vs 万股），已在 parsed 阶段修复 |

## 第六周提交要求对照

| 提交要求 | 路径 | 说明 |
|----------|------|------|
| README.md | `/README.md` | 运行方法、完成状态和已知问题 |
| requirements.txt | `/requirements.txt` | openpyxl、pandas、numpy、pydantic |
| data/ | `/data/README.md` | PDF/Markdown 清单及可复跑输入 |
| pipeline/ | `/pipeline/` + `/week3/pipeline/` | 完整自动提取代码和 run_all.sh 统一入口 |
| prompts/ | `/prompts/README.md` | Prompt、模型参数和调用记录 |
| manual_gold/ | `/week3/manual_gold/` | 人工 Gold，不要求代码生成 |
| auto_output/ | `/week3/pipeline/stages/raw/` + `parsed/` | 未经人工修改的 raw 和 Auto 三表 |
| final/ | `/final/` | 人工及组内复核后的三表和 Excel（8家） |
| validation/ | `/week3/validation/` | schema、Cross-check、测试用例 |
| review/ | `/review/README.md` | 组内差异、处理结论和 PR/Issue 链接 |
| report/ | `/report/week6_report.md` | 上市前融资分析报告（40KB+） |
| logs/ | `/logs/README.md` | 运行记录、输出数量和文件哈希 |

## 四阶段产出体系

| 阶段 | 目录 | 内容 | 人工介入 |
|------|------|------|----------|
| **raw** | `week3/pipeline/stages/raw/` | Markdown 章节定位 + 正则提取的直接输出 | 否 |
| **parsed** | `week3/pipeline/stages/parsed/` | 类型转换、单位归一化、字段映射 | 否 |
| **validated** | `week3/pipeline/stages/validated/` | schema 校验 + cross-check 标记 | 否 |
| **reviewed** | `week3/pipeline/stages/reviewed/` | 人工对照 PDF 逐条核实的最终 Gold | **是** |

人工修改全部集中在 reviewed 阶段，每条修改保留 `original_value / revised_value / reason / pdf_page` 四列。

## 各公司处理概况

| 股票代码 | 公司 | 板 | 认缴流量 | 股权存量 | 股权转让 | Cross-check |
|----------|------|------|----------|----------|----------|-------------|
| 001282 | 三联锻造 | 深主板 | 5 | 34 | 0 | 13 |
| 301563 | 云汉芯城 | 创业板 | 6 | 84 | 10 | 35 |
| 301581 | 黄山谷捷 | 创业板 | 8 | 45 | 3 | 3 |
| 603418 | 友升股份 | 上主板 | 7 | 32 | 0 | 13 |
| 688758 | 赛分科技 | 科创板 | 22 | 201 | 5 | 10 |
| 688775 | 影石创新 | 科创板 | 2 | 104 | 1 | — |
| 920100 | 三协电机 | 北交所 | 5 | 78 | 1 | 17 |
| 920116 | 星图测控 | 北交所 | 8 | 56 | 2 | 6 |
| **合计** | | | **63** | **634** | **22** | **97** |

## 目录结构

```text
cya/
├── README.md                     # 本文件
├── requirements.txt              # Python 依赖
├── data/                         # 数据清单说明
│   └── README.md
├── pipeline/                     # 统一运行入口
│   └── run_all.sh
├── prompts/                      # Prompt、模型参数
│   └── README.md
├── final/                        # 最终复核Excel（8家）
│   ├── 001282_三联锻造_reviewed.xlsx
│   ├── 301563_云汉芯城_reviewed.xlsx
│   ├── 301581_黄山谷捷_reviewed.xlsx
│   ├── 603418_友升股份_reviewed.xlsx
│   ├── 688758_赛分科技_reviewed.xlsx
│   ├── 688775_影石创新_reviewed.xlsx
│   ├── 920100_三协电机_reviewed.xlsx
│   └── 920116_星图测控_reviewed.xlsx
├── review/                       # 组内检查流程
│   └── README.md
├── report/                       # 融资分析报告
│   └── week6_report.md
├── logs/                         # 运行记录与哈希
│   └── README.md
├── week1/                        # 第一周：公共样本
├── week2/                        # 第二周：Gold标准搭建
├── week3/                        # 第三周：管道与复核
│   ├── manual_gold/              #   人工Gold
│   ├── auto_output/              #   自动输出
│   ├── pipeline/
│   │   ├── run_all.sh
│   │   └── stages/
│   │       ├── raw/
│   │       ├── parsed/
│   │       ├── validated/
│   │       └── reviewed/
│   ├── validation/
│   │   └── cross_check/
│   ├── comparison/
│   └── data/
└── 抓取结果/                     # 抓取处理结果
```

## PR 链接

[Week3 → Week6: 按提交要求完善仓库结构，生成融资分析报告](https://github.com/Chen-yu516516/cya/compare/main...week3-submission)
