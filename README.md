# team-xxx 仓库结构

## 仓库目录

├── README.md
├── company_lists/
│   ├── week1_public_samples.csv
│   ├── week2_2025_company_list.csv
│   └── week3_extended_company_list.csv
├── source_notes/
│   ├── data_sources.md
│   ├── prospectus_download_method.md
│   ├── website_collection_method.md
│   └── version_rules.md
├── code/
│   ├── 01_build_company_list/
│   ├── 02_fetch_prospectus_urls/
│   ├── 03_download_pdfs/
│   ├── 04_parse_pdf_to_markdown/
│   ├── 05_locate_relevant_sections/
│   ├── 06_extract_pevc_info/
│   └── 07_validate_outputs/
├── outputs/
├── logs/
├── review/
├── weekly_reports/
└── presentation/

## 数据字段（表一：含 sample_id）

| 字段名 | 说明 |
|--------|------|
| sample_id | 样本编号 |
| company_name | 公司名称 |
| stock_code | 股票代码 |
| exchange | 交易所 |
| board | 板块 |
| listing_date | 上市日期 |
| ipo_year | IPO年份 |
| source_platform | 来源平台 |
| source_page_url | 来源页面URL |
| prospectus_title | 招股书标题 |
| prospectus_url | 招股书URL |
| prospectus_version | 招股书版本 |
| prospectus_date | 招股书日期 |
| download_status | 下载状态 |
| parse_status | 解析状态 |
| locate_status | 定位状态 |
| extract_status | 提取状态 |

## 数据字段（表二：含 review_status + notes）

| 字段名 | 说明 |
|--------|------|
| company_name | 公司名称 |
| stock_code | 股票代码 |
| exchange | 交易所 |
| board | 板块 |
| listing_date | 上市日期 |
| ipo_year | IPO年份 |
| source_platform | 来源平台 |
| source_page_url | 来源页面URL |
| prospectus_title | 招股书标题 |
| prospectus_url | 招股书URL |
| prospectus_version | 招股书版本 |
| prospectus_date | 招股书日期 |
| download_status | 下载状态 |
| parse_status | 解析状态 |
| locate_status | 定位状态 |
| extract_status | 提取状态 |
| review_status | 审阅状态 |
| notes | 备注 |

---

## Week 1 公共样本最小闭环提交

> 提交时间: 2026-06-07 | 状态: ✅ 完成

### 总体概况

| 指标 | 数值 |
|------|------|
| 总样本数 | 8 |
| 成功处理 | 8 |
| 结构化JSON输出 | 8 |
| 总页数 | 2,972 |
| 候选文本段数 | 290 |

### 各公司处理结果

| 公司 | 板块 | 页数 | 候选文本 | JSON |
|------|------|------|----------|------|
| [大鹏工业](week1/BSE001_大鹏工业_structured.json) | 北交所 | 391 | 27 | ✅ |
| [太湖远大](week1/BSE002_太湖远大_structured.json) | 北交所 | 336 | 52 | ✅ |
| [佰维存储](week1/STAR001_佰维存储_structured.json) | 科创板 | 467 | 67 | ✅ |
| [百利天恒](week1/STAR002_百利天恒_structured.json) | 科创板 | 556 | 22 | ✅ |
| [富乐德](week1/GEM001_富乐德_structured.json) | 创业板 | 494 | 53 | ✅ |
| [维峰电子](week1/GEM002_维峰电子_structured.json) | 创业板 | 331 | 28 | ✅ |
| [信达证券](week1/MAIN001_信达证券_structured.json) | 沪主板 | 158 | 32 | ✅ |
| [慕思股份](week1/MAIN002_慕思股份_structured.json) | 深主板 | 239 | 9 | ✅ |

### 产出物

| 文件 | 说明 |
|------|------|
| [week1_company_list.csv](week1/week1_company_list.csv) | 公共样本清单 |
| [week1_all_outputs.json](week1/week1_all_outputs.json) | 全部结构化JSON汇总 |
| [week1_candidate_texts.json](week1/week1_candidate_texts.json) | 候选文本汇总 |
| [week1_report.md](week1/week1_report.md) | 完整处理报告 |
| [download_log.csv](week1/download_log.csv) | 下载日志 |
| [parse_log.md](week1/parse_log.md) | 解析日志 |
| [locate_log.md](week1/locate_log.md) | 定位日志 |
| [extraction_log.md](week1/extraction_log.md) | 提取日志 |
| [validation_log.md](week1/validation_log.md) | 校验日志 |

### 代码脚本

| 文件 | 说明 |
|------|------|
| [week1_pipeline.py](week1/week1_pipeline.py) | Week 1 完整处理脚本 (PDF→Markdown→定位→JSON) |
