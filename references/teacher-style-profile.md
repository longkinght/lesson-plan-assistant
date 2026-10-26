# 自定义章节教案风格

> 用于章节制、学期课程或学校固定字段的教案。内置 `references/teacher-style.json` 是通用模板，不包含任何真实学校或教师信息。

## 使用方式

```bash
python scripts/lesson_assistant.py \
  --json lesson.json \
  --output-dir output \
  --style-config references/teacher-style.json
```

`--style chapter` 使用内置通用章节模板；传入 `--style-config` 时，以指定 JSON 为准。旧版别名 `teacher-zhang` 仍可运行，但新内容应使用 `chapter`。

## 配置结构

```json
{
  "name": "school-chapter",
  "label": "学校章节教案",
  "cover": {
    "title_template": "{course_name}教案",
    "semester": "",
    "fields": [
      { "label": "学院（部）", "value": "{college}", "fallback": "—" }
    ],
    "note": "可选说明"
  },
  "chapter": {
    "head_template": "第{chapter_num}章",
    "field_order": ["课时", "教学方法", "教学目的及要求", "教学环境", "重点", "难点", "讲授内容", "思考题和作业", "参考文献"],
    "defaults": {
      "教学环境": "多媒体教室",
      "参考文献": ""
    }
  }
}
```

## 字段映射

| 教案字段 | 数据来源 |
|---|---|
| 课时 | `lesson_meta.hours` |
| 教学方法 | `methods`，按内置选项做勾选样式 |
| 教学目的及要求 | `objectives`，知识+能力合并为“目的”，素质为“要求” |
| 教学环境 | `resources[0]` 或配置默认值 |
| 重点 / 难点 | `key_points` / `difficult_points` |
| 讲授内容 | `flow.in_class` 按环节重排 |
| 思考题和作业 | `flow.post_class.content` |
| 参考文献 | `references` 或配置默认值 |
| 封面字段 | 大括号变量取自 `lesson_meta` |

## 定制规则

1. 复制 `teacher-style.json`，修改 `name`、`label` 和封面字段；
2. 变量必须在 `lesson_meta` 中存在，否则使用 `fallback`；
3. 不要写入教师手机号、家庭信息或学生个人信息；
4. 不要上传整份学校内部制度作为公共示例；
5. 需要保留原学校 DOCX 表格样式时，应另行做模板填充，当前生成器只复刻字段与章节逻辑。

## 边界

当前版本不包含：

- 学校原版 DOCX 表头、合并单元格和 Logo 的逐格复刻；
- 学期教学计划汇总表；
- 自动套打、盖章和签名；
- 多章合并为一份教学实施计划。

上述需求应作为独立适配工作评估，不应通过修改少量 JSON 来假装已经支持。
