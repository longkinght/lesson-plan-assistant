# lesson.json 数据契约 v2.0

> 一份 `lesson.json` 是教案 DOCX、Markdown 知识图谱和 HTML 课程看板的唯一事实源。所有字段先通过脚本校验，再进入渲染。

## 1. 顶层结构

```json
{
  "schema_version": "2.0",
  "lesson_meta": {},
  "objectives": {},
  "student_analysis": "学情分析",
  "key_points": ["教学重点"],
  "difficult_points": ["教学难点"],
  "methods": ["教学方法"],
  "resources": ["教学资源"],
  "knowledge_tree": [],
  "flow": {},
  "reflection": {},
  "glossary": []
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `schema_version` | string | 是 | 新内容使用 `"2.0"`；`"1.0"` 仅用于旧版兼容校验 |
| `lesson_meta` | object | 是 | 课程与课时元信息 |
| `objectives` | object | 是 | 三维教学目标，必须绑定知识点 |
| `student_analysis` | string | 建议 | 学情分析；缺失时 DOCX 显示待补 |
| `key_points` | string[] | 建议 | 教学重点 |
| `difficult_points` | string[] | 建议 | 教学难点，从学生认知误区描述 |
| `methods` | string[] | 建议 | 教学方法 |
| `resources` | string[] | 建议 | 教学资源 |
| `knowledge_tree` | object[] | 是 | 深度优先排列的知识节点 |
| `flow` | object | 是 | 课前、课中、课后教学过程 |
| `reflection` | object | 是 | 备课预案或课后反思，状态必须明确 |
| `glossary` | object[] | 否 | 术语表 |

## 2. lesson_meta

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `week` | string | 是 | 周次或培训周期，如 `"第15周"` |
| `title` | string | 是 | 本课课题 |
| `course_name` | string | 是 | 课程名称 |
| `hours` | number | 是 | 总学时，必须大于 0 |
| `minutes_per_hour` | number | 否 | 每学时分钟数，默认 `45` |
| `class_name` | string | 否 | 授课班级 |
| `teacher` | string | 否 | 授课教师 |
| `date` | string | 否 | 授课日期，建议 `YYYY-MM-DD` |
| `course_type` | string | 否 | 理论课 / 理实一体课 / 企业工作坊等 |
| `chapter_num` | string | 否 | 章节模板使用的章号 |
| `semester` | string | 否 | 章节模板封面学期 |
| `college` | string | 否 | 学院或单位 |
| `department` | string | 否 | 教研室或部门 |
| `credits` | string | 否 | 学分说明 |
| `total_hours` | string | 否 | 课程总学时说明 |
| `weekly_hours` | string | 否 | 周学时说明 |

输出文件名由 `week` 与 `title` 组成，会自动移除路径分隔符和非法字符。

## 3. objectives

每条目标使用对象结构：

```json
{
  "text": "能够解释栈后进先出与队列先进先出的区别",
  "knowledge_refs": ["栈的定义与基本操作", "队列的定义与基本操作"]
}
```

```json
{
  "knowledge": [{ "text": "…", "knowledge_refs": ["…"] }],
  "ability":   [{ "text": "…", "knowledge_refs": ["…"] }],
  "quality":   [{ "text": "…", "knowledge_refs": ["…"] }]
}
```

硬规则：

1. 三个目标组每组至少 1 条；
2. `text` 长度至少 6 个字符；
3. 知识、能力目标必须包含可观察行为动词；
4. 每条目标至少绑定 1 个已存在的知识点；
5. `quality` 允许使用“树立、养成、增强”等长期素质表述，但不得声称已实现。

## 4. knowledge_tree

节点必须按深度优先排列：父节点位于所有子节点之前，子节点紧邻父节点。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | 是 | 全局唯一，建议不超过 20 字，硬上限 30 字 |
| `level` | integer | 是 | 1–7，父节点层级必须恰好比子节点少 1 |
| `node_type` | string | 是 | `"分类"` 或 `"知识点"` |
| `category` | string | 知识点必填 | 事实性 / 概念性 / 程序性 / 元认知 |
| `cognitive` | string | 知识点必填 | 记忆 / 理解 / 应用 / 分析 / 评价 / 创造 |
| `objective` | string | 知识点必填 | 可观察、可验收的节点目标 |
| `description` | string | 建议 | 依据、解释、应用场景、学生易错点 |
| `pre` | string[] | 否 | 前置知识点，必须指向知识点节点 |
| `post` | string[] | 否 | 后置知识点，可由 `pre` 自动补齐 |
| `related` | string[] | 否 | 关联节点 |
| `tags` | string | 否 | 英文分号分隔：`重点;难点;考点;课程思政` |

分类节点不得填写 `category`、`cognitive` 或 `objective`。只能有一个 Level 1 根节点。关系引用必须精确匹配节点名称。

### 节点尺度建议

| 层级 | 常见用途 |
|---|---|
| L1 | 课程或课题根节点 |
| L2 | 模块、天次、主题单元 |
| L3 | 章节或知识簇 |
| L4–L7 | 可教学、可练习、可评价的知识点 |

层级编号不是质量标志。每个知识点都必须有目标，不再只检查 Level≥4。

## 5. flow

```json
{
  "structure": "five_stage",
  "pre_class": {
    "content": "课前任务",
    "student_activity": "学生活动",
    "teacher_activity": "教师准备",
    "design_intent": "设计依据"
  },
  "in_class": [
    {
      "stage": "导入",
      "role": "intro",
      "duration_minutes": 5,
      "content": "教学内容",
      "student_activity": "学生活动",
      "teacher_activity": "教师活动",
      "design_intent": "设计意图",
      "knowledge_refs": []
    }
  ],
  "post_class": {
    "content": "课后作业与拓展",
    "student_activity": "学生活动",
    "teacher_activity": "教师安排",
    "design_intent": "设计依据"
  }
}
```

### 环节角色

`role` 只能取 `intro`、`instruction`、`practice`、`summary`、`other`。

`structure: "five_stage"` 时，`in_class` 必须恰好 5 项，并依次为：

| 顺序 | role | 常见标题 |
|---:|---|---|
| 1 | `intro` | 导入 |
| 2 | `instruction` | 新授一 |
| 3 | `instruction` | 新授二 |
| 4 | `practice` | 互动练习 |
| 5 | `summary` | 小结与作业 |

需要不同课堂结构时，使用 `structure: "custom"`，并自行保证每项都有合法 `role`。

### 时长硬校验

所有课中环节的 `duration_minutes` 之和必须等于：

```
lesson_meta.hours × lesson_meta.minutes_per_hour
```

允许浮点数，例如半学时 22.5 分钟。时间不吻合时停止生成，并同时报告实际值与目标值。

### 知识点引用

`knowledge_refs` 必须引用知识点节点，不得引用分类节点。除导入外，建议每个环节声明引用。未进入任何课中环节的知识点会产生提醒，应删除或明确为课外拓展。

## 6. reflection：真实性边界

```json
{
  "status": "pre_class",
  "effect": "待课后填写：记录课堂练习结果与目标达成情况",
  "diagnosis": "待课后填写：记录学生实际误解与环节执行情况",
  "improvement": "待课后填写：依据课堂记录确定下一轮改进",
  "evidence": ""
}
```

| status | 含义 | 硬规则 |
|---|---|---|
| `pre_class` | 尚未上课，生成备课预案 | 三段均必须包含“待课后”，不得写已发生的正确率、达成率 |
| `post_class` | 已上课，记录事实 | 应提供 `evidence`，如课堂观察、作业、测验或访谈来源 |

示例数据中的量化结果不能作为新教案的默认内容。

## 7. 风格配置

使用 `--style chapter` 或 `--style-config <json>` 渲染章节制教案。自定义配置结构见 `teacher-style.json`。配置文件只描述封面字段、字段顺序和默认值，不包含学校或教师隐私信息。

## 8. 校验分级

- **错误**：阻断生成，字段路径会直接输出；
- **提醒**：允许生成，但必须由 Agent 或教师复核。

公共分享前运行：

```bash
python scripts/verify_consistency.py --json lesson.json
python scripts/lesson_assistant.py --json lesson.json --output-dir output --verify-only
```

## 9. v1 到 v2 迁移

1. `schema_version` 改为 `2.0`；
2. 每条教学目标从字符串改为 `{text, knowledge_refs}`；
3. 每个课中环节增加 `role` 和 `duration_minutes`；
4. 增加 `flow.structure`；
5. 所有知识点补齐 `objective`；
6. 教学反思增加 `status`，备课时三段写成“待课后填写”。

v1 文件仍可读取，但无法通过 v2 的完整教学目标、时长与真实性校验。迁移后再进行正式交付。
