# auto_output — 自动化产出

## 数据来源

所有 Auto 产出 **必须且仅能从招股书 Markdown 文件独立提取**，严禁从 JSONL 原样拷贝。

- **实现方式**：`pipeline/markdown_to_excel.py` 将 Markdown 文本经章节定位 → 正则提取 → 结构化写入 Excel 4 Sheet
- **JSONL 角色**：仅用于统计对比参考（日志输出记录数差异），不参与 Auto 数据填充
- **Markdown 缺失时**：对应 Sheet 保留空白结构 + 数据缺失说明，不填入任何旧 JSONL 数据

## 处理管道

- `pipeline/markdown_to_excel.py` — 主处理脚本
  - 流程：Markdown 文件 → `locate_history_section()` 章节定位 → `extract_subscription_events()` / `extract_equity_snapshots()` / `extract_transfer_events()` 直接提取 → 4-Sheet Excel
  - 无 JSONL 中间产物参与

## 产出状态

### 当前运行结果（2026-07-20）

| 公司 | Markdown | 认缴流量 | 股权存量 | 股权转让 | 说明 |
|------|----------|---------|---------|---------|------|
| 三联锻造 (001282) | 缺失 | 0 | 0 | 0 | Markdown 源文件未提交到仓库 |
| 云汉芯城 (301563) | 缺失 | 0 | 0 | 0 | Markdown 源文件未提交到仓库 |
| 黄山谷捷 (301581) | 缺失 | 0 | 0 | 0 | Markdown 源文件未提交到仓库 |
| 友升股份 (603418) | 缺失 | 0 | 0 | 0 | Markdown 源文件未提交到仓库 |
| 赛分科技 (688758) | 缺失 | 0 | 0 | 0 | Markdown 源文件缺失 — 无法进行自动提取，Auto 产出为空 |
| 影石创新 (688775) | 缺失 | 0 | 0 | 0 | Markdown 源文件未提交到仓库 |
| 三协电机 (920100) | 缺失 | 0 | 0 | 0 | Markdown 源文件未提交到仓库 |
| 星图测控 (920116) | 缺失 | 0 | 0 | 0 | Markdown 源文件未提交到仓库 |

> **原因**：招股书 Markdown 源文件（`data/scratch_results/MB001_三联锻造/001282_三联锻造_IPO招股说明书.md` 等）未随仓库提交。这些文件由 PDF 经由 MinerU 转换生成，文件体积过大（单份 3-15MB），未纳入 Git 版本控制。

### 恢复方法

将 MinerU 转换产物放入 `data/scratch_results/` 对应子目录后重新运行：

```bash
cd week3
python pipeline/markdown_to_excel.py
```

子目录结构：

```
data/scratch_results/
├── MB001_三联锻造/001282_三联锻造_IPO招股说明书.md
├── GEM002_云汉芯城/301563_云汉芯城_IPO招股说明书.md
├── GEM001_黄山谷捷/301581_黄山谷捷_IPO招股说明书.md
├── MB002_友升股份/603418_友升股份_IPO招股说明书.md
├── STAR002_影石创新/688775_影石创新_IPO招股说明书.md
├── BSE001_三协电机/920100_三协电机_IPO招股说明书.md
└── BSE002_星图测控/920116_星图测控_IPO招股说明书.md
```

## 已知局限

- **赛分科技 (688758)**：本次实验中 Markdown 源文件缺失，Auto 产出为空白 Sheet。不填入旧 JSONL 数据。需补足 Markdown 后才能重新生成。
- **股权转让 Sheet**：当前正则提取策略对股权转让覆盖有限，多数公司招股书以文字描述转让、无表格，自动提取命中率低。
