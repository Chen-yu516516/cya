# Prompts — Prompt 与模型调用记录

## 使用的 Prompt 策略

### 信息提取 Prompt

在 Week 2 阶段，使用 大语言模型 辅助从招股书 Markdown 中提取 PE/VC 融资事件。Prompt 设计采用 Few-Shot 策略：

**核心指令要点**：
1. 角色设定：以金融数据分析师身份，从招股书"历史沿革"章节提取融资事件
2. 输出格式：JSONL，每条记录包含 record_type、stock_code、pdf_page、subscription_date 等字段
3. 单位要求：统一转换为"万股"/"万元"/"元/股"
4. 证据保留：每条提取结果必须附带 evidence_text（原文摘录）
5. 不确定性标注：当数据为间接推算时，需在备注中标注推理依据

### Cross-check Prompt

在 Week 3 阶段，使用规则引擎（非大语言模型）进行逐事件和逐股东的 Cross-check：

- `per_event_check.py`：通过前后快照对比，验证每笔增资的认购方股数变化是否一致
- `per_shareholder_check.py`：验证每个股东在各时点的持股数与快照披露是否吻合

### Prompt 设计经验总结

| 经验 | 说明 |
|------|------|
| Few-Shot > Zero-Shot | 提供 2-3 个标注示例能显著提升单位归一化的准确率 |
| 表格优先 | 明确指示 大语言模型 优先从结构化表格提取，表外文字作为补充 |
| 页码必须 | 要求每条记录输出页码，为人工复核提供定位锚点 |
| 单位关键词 | 在 Prompt 中增加"（股）/（万元）/（万股）"列标题识别指令，减少 unit error |

## 模型参数

| 参数 | 值 | 说明 |
|------|-----|------|
| model | hunyuan-pro | 腾讯混元大模型 |
| temperature | 0 | 确定性输出，确保可复现 |
| max_tokens | 4096 | 单页文本足够 |


## 调用记录

### Week 2 提取阶段

- 调用方式：通过 Pipeline Python 脚本批量调用 API
- 输入：Markdown 章节文本（每页约 1000-3000 tokens）
- 输出：JSONL 结构化记录
- 调用统计：8 家公司 × 平均 3.5 批 = 约 28 次调用

### Week 3 分析阶段

- 调用方式：本地 Python 脚本（openpyxl + pandas）
- 未使用 大语言模型 调用

## 注意事项

1. **不要提交 API 密钥**：密钥通过环境变量读取，不在仓库中存储
2. **raw response 保留**：每次 大语言模型 调用的原始响应保存在 `week3/outputs/raw_extraction_outputs/` 目录
3. **外部服务不可用时**：可读取已保存的 raw response 重新生成 Auto、Schema 和 Cross-check 结果
