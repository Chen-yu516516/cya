# Logs — 运行记录、输出数量和文件哈希

## 各阶段日志文件

| 日志文件 | 描述 | 大小 |
|----------|------|------|
| `week3/outputs/logs/validation.log` | Schema 校验日志 | - |
| `week3/outputs/logs/markdown_pipeline.log` | Markdown→Excel 管道运行日志 | - |
| `week3/outputs/logs/fill_equity_transfers.log` | 股权转让补充日志 | - |
| `week3/outputs/logs/saifen_unit_fix.log` | 赛分科技单位修正日志 | - |
| `week3/outputs/logs/markdown_process.log` | 四阶段迁移处理日志 | - |

## 运行统计

### Pipeline 运行记录

| 时间 | 阶段 | 认缴流量 | 股权存量 | Schema 错误 | 警告 |
|------|------|----------|----------|-------------|------|
| 2026-06-18 | Auto | 97 | 634 | 34 | 8 |
| 2026-07-17 | Markdown | 97 | 634 | - | - |
| 2026-07-20 | 四阶段迁移 | 97 | 634 | - | - |

### 各公司输出统计

| 股票代码 | 公司 | 认缴流量 | 股权存量 | 股权转让 | 交叉校验项 |
|----------|------|----------|----------|----------|------------|
| 001282 | 三联锻造 | 5 | 34 | 0 | 13 |
| 301563 | 云汉芯城 | 6 | 84 | 10 | 35 |
| 301581 | 黄山谷捷 | 8 | 45 | 3 | 3 |
| 603418 | 友升股份 | 7 | 32 | 0 | 13 |
| 688758 | 赛分科技 | 22 | 201 | 5 | 10 |
| 688775 | 影石创新 | 2 | 104 | 1 | - |
| 920100 | 三协电机 | 5 | 78 | 1 | 17 |
| 920116 | 星图测控 | 8 | 56 | 2 | 6 |
| **合计** | | **63** | **634** | **22** | **97** |

## 最终产物文件哈希

### final/ 目录 (SHA256)

```
001282_三联锻造_reviewed.xlsx:  ed20c581c9e50843c19210df3e7e70ae650a3182114e30f8c6cf6dd0773dd866
301563_云汉芯城_reviewed.xlsx:  9785405d6c49ab16db4d6153521897ed0340b96c6eceb5e69d97ae9309946bca
301581_黄山谷捷_reviewed.xlsx:  7e6db1940187144d13ffbfdedaaee16eac71247d2550537116eed062b971a302
603418_友升股份_reviewed.xlsx:  814c6c5bde3540e907fa13b238d7b994ac39cd915c86ecf90054a7fa9fb25403
688758_赛分科技_reviewed.xlsx:  3c8ea2e22e13ba8bf40b05f2f5fb49fdae36db4370d1a6900b56ca43d611efec
688775_影石创新_reviewed.xlsx:  273495cf8fa945a5458385865a9a5e46a4efd1a92352748cbc108718e7179cad
920100_三协电机_reviewed.xlsx:  ead029059af532450a9c9481f03fd9f85e49c2ceff11787855f2f31d0bef84b5
920116_星图测控_reviewed.xlsx:  b414522f7434cbcc721a4e665abe7beb180e8b17ecaacc2bd644b8d83c860811
```
