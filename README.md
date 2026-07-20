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

## 项目制作流程

这三周踩了不少坑，写下这篇算是给自己一个交代，也给后面继续做这个项目（或者接手这个仓库）的人一个路线图。

### 核心教训：Gold标准必须独立

Week2我犯的最大的错，就是把Gold和自动化搅在一起。

当时我的做法是这样的：先让自动化流程从PDF抽出JSONL，然后人工打开JSONL文件修修改改，改完就把这个JSONL当Gold标准拿去跟自动化结果对比。看起来省事，实际上完全歪了——Gold和Auto共享同一个源头，对比出来的"匹配率"毫无意义，因为你只是在跟自己的变体比较而已。

Week3纠正之后的正确做法是两路独立：

```
PDF → 人工逐页读 → Gold标准（Excel四个Sheet）
PDF → 自动化流程 → Auto结果（Excel四个Sheet）
Gold ← 对比 → Auto → 找差距 → 改进自动化
```

Gold必须直接从PDF人工标注，不能经过任何自动化中间产物。自动化也必须从PDF开始跑完整流程，不能用人工预处理过的数据。两路各走各的，最后才碰头对比。

### 制作流程

整个流程我分成七步，每一步踩过什么坑我会顺带写出来。

**第一步：选公司。** 我选了8家，覆盖主板/科创板/创业板/北交所四个板块。重点是要拉开难度——三联锻造历史沿革就几段话，半小时能翻完；赛分科技增资和转让缠在一起写，我花了一整个下午。选公司的时候别都挑简单的，挑几个难的才能测出自动化的上限。

**第二步：建立Gold标准。** 这是整个流程里最重要也最累的一步，而且必须最先做——因为做完Gold你才能客观评估自动化。具体做法是翻开招股书，找到"历史沿革"或"发行人设立以来的股本和股东变化"章节，逐页逐行读，用Excel记录四类数据。

第一个Sheet记增资事件（认缴流量）：谁、什么时候、出了多少钱、拿了多少股、每股价格。每条记录标注PDF页码、摘录原文，并且标明是"直接披露"还是"计算得出"——比如原文写的是"股"你除了一万转成"万股"，就要标"计算得出"。

第二个Sheet记股权结构存量：每个关键时点的股东清单。关键时点包括公司设立、每次增资后、每次转让后、股改时、发行前。这个Sheet的作用是让你后面能做交叉校验——某个时点所有股东的持股加总是否等于总股本，对不上就说明可能漏了人。

第三个Sheet做交叉校验：就是上面说的，检查每个时点的股东持股加总、每批增资的认购方和合计认购数。这一步能帮你发现自己翻书过程中的遗漏。

第四个Sheet记股权转让：转让方、受让方、时间、转让数量、价格、金额，同样标注页码和原文。友升股份和三联锻造我翻了很久确实没找到发行人层面的转让，这种情况留空表但要备注说明。

翻书的时候有个原则：不确定的地方不要硬填，写"不太确定，回头查"。比如云汉芯城A轮的三方拆分，原文只给了合计数，我是按股改时的持股比例反推分配的，这个必须在备注里标清楚。三协电机更极端——招股书正文里根本没有完整历史沿革，只能从发行前股东表和第35-39页的定向发行拼凑，t0时点直接缺失。

还有一个小细节：每条记录标注原文摘录的时候，尽量原样抄，不要自己概括。后面做对比分析的时候，原文摘录是判断争议的最可靠依据。

**第三步：跑自动化流程。** 自动化的起点必须是PDF（或者PDF转出来的Markdown），不能从已有的JSONL开始。Week3我犯的错误就是pipeline从week2的JSONL起步，等于跳过了PDF解析和章节定位这两步，流程不完整。

完整的自动化步骤应该是：PDF/Markdown解析 → 章节定位 → 候选表格/事件切块 → 规则/信息抽取 → 校验 → 失败复核。关键要求是：流程必须能从PDF一键或分步复现。不能说我跑了一次、生成了结果、但换了台机器就跑不出来了。

**第四步：三层目录分离。** 这个教训是从Week2的混乱里学来的。目录结构必须严格遵守：

```
week3/
  manual_gold/      ← 只放人工确认的Gold标准
  auto_output/      ← 只放自动化流程的原始输出
  comparison/        ← 放对比结果
```

Gold和Auto严格分离，不能混在同一个文件里，不能互相引用。comparison里逐字段对比，标记match/mismatch/missing。这样出问题的时候你能一眼看出来是谁的问题——是Gold标错了还是自动化抽错了。

**第五步：做对比分析。** 生成两个文件：comparison.csv做字段级对比，comparison_summary.csv做公司级汇总。分析的时候关注三类差异——match说明自动化做对了，mismatch说明数值对不上（得回PDF核实到底谁对），missing说明自动化没抽到（要分析是定位失败、分类失败还是格式问题）。

我的对比结果里，match率最好的是三协电机（100%，因为它格式规范、表格清晰），最差的是赛分科技（0%，因为单位错误和大量手工调整）。这个结果本身就有信息量：它告诉你哪些公司的招股书格式对自动化友好、哪些不友好。

**第六步：问题归因。** 按公司逐条分析missing和mismatch的原因。我碰到的常见问题有这几类：单位混淆（股 vs 万股，赛分科技最典型，10条记录全错在同一批次，直接把原文的"股"照搬过来没做转换）、跨页表格断裂（表格被分页后解析时对不齐）、事件分类错误（增资当成转让）、章节定位失败（目录匹配不准导致搜到了错误的章节）。

**第七步：迭代。** 根据对比结果改自动化流程，用新流程重新跑，再对比，直到match率稳定在可接受水平。这一步我还没完全做到——Week3时间不够，只做了对比和归因，改进和重新跑留给下一轮。

**第七步补充（2026-07-17 迭代）：** 本次迭代对 Week3 做了三项细化：

1. **comparison 层归因分类**：原来的 match/mismatch/missing 三分类过于粗糙。现在 mismatch 拆分为 unit_error（单位混淆）、value_error（数值偏差）、shareholder_name_mismatch（股东名称不一致）、date_mismatch（日期不匹配）、price_mismatch（价格不一致）五类；missing 拆分为 section_not_found（章节定位失败）、event_not_recognized（事件未识别）、table_parse_failed（表格解析失败）、mixed_paragraph（混合段落未拆开）、no_source_data（源数据缺失）五类。comparison_summary 同步增加了各类细分计数、总记录数、match_rate 和 key_issues 字段。

2. **manual_gold 补充列**：认缴流量 Sheet 增加了"数据来源类型"（直接披露/计算得出/推算估计）和"备注"列；股权转让 Sheet 增加了"转让类型"列（股东间转让/增资附带转让/继承/其他）；股权存量 Sheet 增加了"时点说明"列（说明为何选取该时点——设立后/增资后/转让后/股改/发行前）。

3. **新增问题归因分析文档**：在 week3/ 目录下生成 `问题归因分析.md`，按 8 家公司逐家分析整体情况、mismatch 原因、missing 原因和改进建议，附带跨公司共性问题总结。


### 教授的核心要求（备忘）

组会上老师提了几个硬性要求，我逐条记下来，免得后面忘了：

- Gold必须从PDF标注，不是改JSONL → 对应第二步人工逐页读PDF
- 股权转让必须纳入 → 对应第二步Sheet 4覆盖所有转让事件
- 每条记录要有PDF页码+原文 → 对应第二步的标注要求
- 自动化和Gold要分开 → 对应第四步三层目录分离
- 自动化要从PDF开始 → 对应第三步从PDF解析做起
- 流程要能复现 → 对应第三步提供完整处理代码
- 失败要能定位和返工 → 对应第五步逐条归因

---

## 四阶段产出体系 (raw → parsed → validated → reviewed)

> 教授第四条修改意见（2026-07-17）要求建立分阶段产出体系，明确标注人工修改位置。

### 四阶段概览

| 阶段 | 目录 | 内容 | 人工介入 |
|------|------|------|----------|
| **raw** | `pipeline/stages/raw/` | Markdown 章节定位 + 正则提取的直接输出，保留原文数值 | 否 |
| **parsed** | `pipeline/stages/parsed/` | 类型转换、单位归一化、字段映射后的结构化数据 | 否 |
| **validated** | `pipeline/stages/validated/` | schema 校验 + cross-check 标记（每条有 validation_status） | 否 |
| **reviewed** | `pipeline/stages/reviewed/` | 人工对照 PDF 逐条核实的最终 Gold 数据 | **是** |

**人工修改全部集中在 reviewed 阶段**，每条修改保留 `original_value` / `revised_value` / `reason` / `pdf_page` 四列。

详细说明见 [pipeline/stages/README.md](week3/pipeline/stages/README.md)。

### 提交要求对齐

| 第六周要求 | 对应四阶段 |
|------------|-----------|
| `manual_gold/` | **reviewed** — 人工对照 PDF 逐条核实的 Gold Excel |
| `auto_output/` | **raw + parsed** — 未经人工修改的自动提取和结构解析 |
| `final/` | **reviewed** — 人工及组内复核后的最终数据 |
| `validation/` | **validated** — schema、cross-check、逐字段对比 |

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

