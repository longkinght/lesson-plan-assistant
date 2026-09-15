# 同源 JSON 契约规范（lesson.json）

> 本文件定义备课知识图谱助手的**唯一事实源**：一份 `lesson.json` 同时驱动教案 docx、知识图谱 md、信息图 html 三件产物。任何产物都不得绕过此契约。

## 顶层结构

```json
{
  "schema_version": "1.0",
  "lesson_meta": { "...": "课程与课时元信息" },
  "objectives": { "...": "三维教学目标" },
  "student_analysis": "学情分析",
  "key_points": ["教学重点"],
  "difficult_points": ["教学难点"],
  "methods": ["教学方法"],
  "resources": ["教学资源"],
  "knowledge_tree": [ "知识节点数组（深度优先顺序）" ],
  "flow": { "pre_class": "...", "in_class": ["课中环节"], "post_class": "..." },
  "reflection": { "effect": "...", "diagnosis": "...", "improvement": "..." },
  "glossary": [ "术语表" ]
}
```

## 字段明细

### lesson_meta（课程与课时元信息）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| week | string | 是 | 周次，如"第15周" |
| title | string | 是 | 本课课题，如"栈和队列" |
| course_name | string | 是 | 课程名称 |
| hours | number | 是 | 学时数（建议 1-4） |
| class_name | string | 否 | 授课班级 |
| teacher | string | 否 | 授课教师 |
| date | string | 否 | 授课日期，YYYY-MM-DD |
| course_type | string | 否 | 课型：理论课 / 理实一体课 / 实训课 等 |

### objectives（三维教学目标）

| 字段 | 类型 | 说明 |
|------|------|------|
| knowledge | string[] | 知识目标（建议 3-4 条），动词：说出/解释/描述/列举… |
| ability | string[] | 能力目标（建议 3-4 条），动词：操作/分析/设计/使用… |
| quality | string[] | 素质目标（建议 2-3 条），动词：养成/树立/增强… |

**目标质量红线**：每条目标必须包含行为动词、必须可衡量、必须与 knowledge_tree 中至少一个节点对应。

### knowledge_tree（知识节点数组）

**顺序约束：深度优先（父节点必须在其所有子节点之前，兄弟节点相邻）。**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 节点名称（≤30 字，全局唯一） |
| level | int | 是 | 层级 1-7（1=课程/课题，逐级细分） |
| node_type | string | 是 | "分类"（结构容器）或"知识点"（可教学单元） |
| category | string | 条件 | 知识点必填：事实性/概念性/程序性/元认知；分类节点留空 |
| cognitive | string | 条件 | 知识点必填：记忆/理解/应用/分析/评价/创造（布鲁姆） |
| pre | string[] | 否 | 前置知识点（学习依赖，名称必须精确匹配树中节点） |
| post | string[] | 否 | 后置知识点（可由脚本自动反向生成） |
| related | string[] | 否 | 关联知识点（并列/对比/相似原理） |
| tags | string | 否 | 标签：重点/难点/考点/课程思政（英文分号分隔） |
| objective | string | 条件 | Level≥4 的知识点必填：具体可衡量的教学目标，含行为动词 |
| description | string | 否 | 节点说明（≤100 字）：出处/解读/应用/易错点 |

**层级约定**：Level 1-3 通常为"分类"（课题/模块/章节容器），Level 4-7 为"知识点"。教案"课中环节"引用的知识点必须取自 knowledge_tree 中的知识点节点。

### flow（教学过程）

```json
"flow": {
  "pre_class": {
    "content": "课前预习任务",
    "student_activity": "学生课前活动",
    "teacher_activity": "教师课前准备",
    "design_intent": "设计意图"
  },
  "in_class": [
    {
      "stage": "导入",
      "content": "环节内容",
      "student_activity": "学生活动",
      "teacher_activity": "教师活动",
      "design_intent": "设计意图"
    }
  ],
  "post_class": {
    "content": "课后作业与拓展",
    "student_activity": "学生课后活动",
    "teacher_activity": "教师课后安排",
    "design_intent": "设计意图"
  }
}
```

**课中环节标准五段**：导入 → 新授(知识点一) → 新授(知识点二) → 互动练习 → 小结作业。每个环节四个维度齐全（教学内容/学生活动/教师活动/设计意图）。

**knowledge_refs（一致性校验锚点）**：每个 in_class 环节可加 `knowledge_refs: ["节点名"]`，声明该环节实际讲授/练习的知识点（必须与 knowledge_tree 节点 name 精确一致）。校验脚本据此执行"教案知识点 ⊆ 图谱节点"的一致性红线。

### reflection（教学反思）

```json
"reflection": {
  "effect": "教学效果（含可量化的数据）",
  "diagnosis": "诊断：问题与原因",
  "improvement": "改进：具体措施"
}
```

### glossary（术语表）

```json
[ { "term": "术语", "definition": "定义" } ]
```

## 一致性红线（违反即阻止交付）

1. **知识点集合一致**：教案 flow 中出现/引用的知识点名称 ⊆ knowledge_tree 节点名称集合。
2. **层级连续**：树中父子层级差必须为 1，不允许断层（level 1 → level 3 跳过 level 2）。
3. **名称唯一**：knowledge_tree 中 name 全局唯一。
4. **关系引用有效**：pre/post/related 中的每个名称都真实存在于 knowledge_tree。
5. **目标覆盖**：Level≥4 的知识点节点必须有非空 objective。
6. **分类清洁**：node_type="分类" 的节点 category 必须为空。
