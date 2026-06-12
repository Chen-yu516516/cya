# Week 2 提交说明

## 任务
对8家新公司进行IPO招股说明书股权结构抽取，包括：
- **subscription_flow**（认缴流量）：增资事件记录
- **equity_snapshot**（股权结构存量）：各时点股东结构

## 完成情况

| 指标 | 数值 |
|---|---|
| 处理公司数 | 8 |
| 总记录数 | 731 |
| Subscription Flow | 97 |
| Equity Snapshot | 634 |
| Pydantic校验 | 100%通过 |

## 产出物

```
week2/
├── outputs/
│   ├── week2_jsonl/         # 8个JSONL文件（731条记录）
│   └── week2_excel/         # Excel汇总工作簿
├── schemas/
│   └── extraction_models.py # Pydantic v2校验模型
├── scripts/
│   ├── validate_jsonl.py    # 校验脚本
│   ├── jsonl_to_excel.py    # Excel转换脚本
│   └── cross_check.py       # 数据一致性校验
├── company_list/
│   └── week2_public_8.csv   # 公司清单
├── weekly_reports/
│   └── week2_report_20260612.md  # 周报
└── code/
    └── week2_pipeline.py    # 早期流水线（已弃用）
```

## 数据说明

- 三协电机(920100)/星图测控(920116)：BSE招股书覆盖不完整，部分历史时点需公开转让说明书补充
- 赛分科技(688758)：仅t0一个时点，招股书限制
- 影石创新(688775)：纯股权变更，无subscription_flow记录
