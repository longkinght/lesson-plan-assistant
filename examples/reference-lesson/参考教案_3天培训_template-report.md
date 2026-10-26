# 模板映射报告：参考教案_3天培训.docx

样本包含 36 个段落、11 个表格、1 个节。以下映射由脚本自动推断，首次使用前请教师核对一次，之后同校同模板可长期复用。

## 已识别字段

| 内容字段 | 位置 | 状态 |
|---|---|---|
| `lesson_meta.course_name` | 表0[0][1] | 需确认 |
| `lesson_meta.title` | 表0[1][1] | 需确认 |
| `lesson_meta.week` | 表0[2][1] | 需确认 |
| `lesson_meta.hours` | 表0[3][1] | 需确认 |
| `lesson_meta.class_name` | 表0[4][1] | 需确认 |
| `lesson_meta.teacher` | 表0[5][1] | 可直接使用 |
| `lesson_meta.date` | 表0[6][1] | 可直接使用 |
| `lesson_meta.course_type` | 表0[7][1] | 需确认 |
| `key_points` | 表1[0][1] | 需确认 |
| `difficult_points` | 表1[1][1] | 需确认 |
| `methods` | 表2[0][1] | 需确认 |
| `resources` | 表2[1][1] | 需确认 |
| `reflection.effect` | 表10[0][1] | 需确认 |
| `reflection.diagnosis` | 表10[1][1] | 需确认 |
| `reflection.improvement` | 表10[2][1] | 需确认 |
| `objectives.all` | 段落 3–12（编号列表） | 需确认 |
| `student_analysis` | 段落14 | 需确认 |

## 已识别重复区块

| 区块 | 表格 | 模板行 | 填充行范围 | 列映射 |
|---|---|---|---|---|
| `in_class`（单元模式，样本 7 组） | 标题段+独立小表 | — | — | content→第0列，student_activity→第1列，teacher_activity→第2列，design_intent→第3列 |

> 样本的环节表未设置“跨页重复标题行”；表格跨页时表头不会自动重复，如需该效果请在 Word 中设置后重新解析。

## 下一步

1. 打开 `template-map.json`，把确认为错误的地址改掉；
2. 把顶层 `confirmed` 改为 `true`；
3. 重新执行生成命令。
