# 模板映射报告：学校样本_教案模板.docx

样本包含 13 个段落、5 个表格、1 个节。以下映射由脚本自动推断，首次使用前请教师核对一次，之后同校同模板可长期复用。

## 已识别字段

| 内容字段 | 位置 | 状态 |
|---|---|---|
| `lesson_meta.course_name` | 表0[0][1] | 可直接使用 |
| `lesson_meta.credits` | 表0[0][3] | 可直接使用 |
| `lesson_meta.title` | 表0[1][1] | 可直接使用 |
| `lesson_meta.class_name` | 表0[1][3] | 可直接使用 |
| `lesson_meta.teacher` | 表0[2][1] | 可直接使用 |
| `lesson_meta.week` | 表0[2][3] | 可直接使用 |
| `lesson_meta.hours` | 表0[3][1] | 可直接使用 |
| `lesson_meta.course_type` | 表0[3][3] | 可直接使用 |
| `lesson_meta.date` | 表0[4][1] | 可直接使用 |
| `objectives.knowledge` | 表1[0][1] | 可直接使用 |
| `objectives.ability` | 表1[1][1] | 可直接使用 |
| `objectives.quality` | 表1[2][1] | 可直接使用 |
| `key_points` | 表2[0][1] | 可直接使用 |
| `difficult_points` | 表2[1][1] | 可直接使用 |
| `reflection.effect` | 表4[0][1] | 可直接使用 |
| `reflection.diagnosis` | 表4[1][1] | 可直接使用 |
| `reflection.improvement` | 表4[2][1] | 可直接使用 |
| `student_analysis` | 段落6 | 需确认 |

## 已识别重复区块

| 区块 | 表格 | 模板行 | 填充行范围 | 列映射 |
|---|---|---|---|---|
| `in_class` | 表3 | 第1行 | 第1–1行 | content→第1列，student_activity→第2列，teacher_activity→第3列，design_intent→第4列，stage_with_duration→第0列 |

> 样本的环节表未设置“跨页重复标题行”；表格跨页时表头不会自动重复，如需该效果请在 Word 中设置后重新解析。

## 下一步

1. 打开 `template-map.json`，把确认为错误的地址改掉；
2. 把顶层 `confirmed` 改为 `true`；
3. 重新执行生成命令。
