---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 592e49e1106cdf0e39bf8e092141f12d_0ca0d680664911f1a99c5254007bceed
    ReservedCode1: 5Hxz4IqYlF/E8+ndArh1KOVuIGmiOvc1dIlcfSep2QkYnE/o8ExXVpnD3cO6IoIgT4Gbn4OzA0wKOmCDlrRYfS6r7O2saa99PSFPgKmGckXDbKAOJQacmJSeqlze23m8Ijl7bPC4F2dyngE/y3VgtZr7GGOD7iRA34VeKgeEyb7ybn+qH9lrvWzX45s=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 592e49e1106cdf0e39bf8e092141f12d_0ca0d680664911f1a99c5254007bceed
    ReservedCode2: 5Hxz4IqYlF/E8+ndArh1KOVuIGmiOvc1dIlcfSep2QkYnE/o8ExXVpnD3cO6IoIgT4Gbn4OzA0wKOmCDlrRYfS6r7O2saa99PSFPgKmGckXDbKAOJQacmJSeqlze23m8Ijl7bPC4F2dyngE/y3VgtZr7GGOD7iRA34VeKgeEyb7ybn+qH9lrvWzX45s=
---

# Week 2 周报：股权结构抽取流水线 — 8家新公司

**日期**：2026-06-05 ~ 2026-06-12  
**执行人**：陈雨昂

---

## 1. 完成概况

| 指标 | 数值 |
|---|---|
| 处理公司数 | 8家 |
| 总记录数 | 731条 |
| Subscription Flow | 97条 |
| Equity Snapshot | 634条 |
| Pydantic校验通过率 | 100% |
| Cross-check问题 | 2项（均为招股书原文限制，非数据错误） |

## 2. 各公司明细

| 代码 | 简称 | Sub | Eq | 总条数 | 时点数 | 备注 |
|---|---|---|---|---|---|---|
| 603418 | 友升股份 | 13 | 32 | 45 | 4 | 含t0设立至发行前完整历史 |
| 001282 | 三联锻造 | 13 | 23 | 36 | 6 | 6批次增资，完整历史 |
| 301581 | 黄山谷捷 | 3 | 21 | 24 | 5 | 2次增资，含吸收合并 |
| 301563 | 云汉芯城 | 35 | 129 | 164 | 6 | 9批次增资，数据量最大 |
| 688758 | 赛分科技 | 10 | 316 | 326 | 1 | 仅t0（发行前），股东数最多 |
| 688775 | 影石创新 | 0 | 81 | 81 | 4 | 无增资事件，纯股权变更 |
| 920100 | 三协电机 | 17 | 19 | 36 | 1 | 仅发行前结构，t0需公开转让说明书 |
| 920116 | 星图测控 | 6 | 13 | 19 | 3 | BSE招股书覆盖不完整 |

## 3. 技术方案

- **抽取方式**：file-agent逐家精确抽取（规则流水线质量不足后切换）
- **数据格式**：JSONL（每行一条记录）+ Excel汇总工作簿
- **校验**：Pydantic v2模型（subscription_flow / equity_snapshot），字符串容错（pdf_page接受"31-32"格式，shareholding_ratio自动剥离%）
- **产出**：week2/outputs/week2_jsonl/*.jsonl（8个）+ week2/outputs/week2_excel/week2_extraction.xlsx

## 4. 已知限制

1. **三协电机(920100)**：t0设立时股权结构不在本招股书中，需全国股转系统公开转让说明书补充
2. **星图测控(920116)**：BSE招股书仅记载t0设立+代持解除+发行前三个时点，中间10年历史沿革缺失
3. **赛分科技(688758)**：招股书仅有t0一个时点的股本结构
4. **三协/星图**：部分认购股数为反向推算（招股书未按认购人分别列示），精度待公开转让说明书确认

## 5. 产出物清单

| 文件 | 路径 |
|---|---|
| JSONL数据(8个) | `week2/outputs/week2_jsonl/` |
| Excel汇总 | `week2/outputs/week2_excel/week2_extraction.xlsx` |
| Pydantic模型 | `week2/schemas/extraction_models.py` |
| 校验脚本 | `week2/scripts/validate_jsonl.py` |
| Excel脚本 | `week2/scripts/jsonl_to_excel.py` |
| Cross-check脚本 | `week2/scripts/cross_check.py` |
| 校验日志 | `week2/logs/schema_validation_log_*.csv` |

## 6. 下周计划

- 补充公开转让说明书数据（三协电机、星图测控的t0中间时点）
- PDF批注截图生成
- 推GitHub更新网站
- Week 3 新公司储备
*（内容由AI生成，仅供参考）*
