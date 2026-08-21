# 收尾检查记录（8.18-8.22）

## 四项检查结果

| # | 检查项 | 结果 |
|---|--------|------|
| 1 | 代码跑通 | 通过：temp 干净环境跑 `bash pipeline/run_all.sh`，raw→parsed→validated→reviewed 四阶段全部执行完成，不依赖本地绝对路径 |
| 2 | 目录齐全 | 通过：README 第六周提交要求 12 项全部存在（README / requirements.txt / data / pipeline / prompts / manual_gold / auto_output / final / validation / review / report / logs） |
| 3 | 报告数字回溯 | 通过：抽查 10+ 条关键数字（各公司增资金额/价格/股数、整体变更折股、资本公积转增比例等），均能在 final/ reviewed Excel 对应行溯源一致 |
| 4 | 残留本地路径扫描 | 通过：全仓库 grep `/Users/`、`/Desktop`、`/Documents`、`/home/`、`/tmp/`、`/Volumes/` 零命中 |

## 发现并修复的问题

| 问题 | 影响 | 修复 |
|------|------|------|
| 3 处脚本用 `os.system` 跑 pip 安装，路径含空格时被 shell 拆断，导致 openpyxl 装不上、管道跑挂 | week3_pipeline.py / markdown_to_excel.py / generate_comparison.py | 改为 `subprocess.check_call([sys.executable, ...])` 列表传参，不经过 shell 解析 |

## 未改动项

- cross-check 的 FAIL/异常条数（59 FAIL、109 异常）为已知情况（单位归一化差异，README 已知问题已说明），未改动数据。
- 报告数字均为人工核对后确认可溯源，无数据修正。
