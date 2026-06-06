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
