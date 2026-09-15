---
name: lesson-plan-assistant
description: 备课知识图谱助手。输入"周次+课题+要点"（或教材/课标/PPT文本），一键产出三件套：标准教案 docx（填好可直接交）、Markdown 知识图谱（知识树+关系表+教学目标索引）、HTML 信息图（交互式一课一图，离线可用）。触发场景：备课、写教案、生成教案、做知识图谱、一课一图、整理课题知识点。关键词：备课、教案、知识图谱、知识树、教学目标、布鲁姆、课程设计。
---

# 备课知识图谱助手（Lesson Plan Assistant）

## 它解决什么
教师备课的真正痛点不是"写不出教案"，而是：
- 教案、知识图谱各写各的，知识点对不上
- 风格每次漂移，今天写的和上周不像同一个人写的
- 格式要手动填模板，反复返工
- 备完就扔，课程知识无法沉淀

本 Skill 的核心信念：**教案不是知识清单，是一堂可执行的课；知识图谱不是装饰，是学生怎么学会的结构底座。** 一份结构化 JSON 驱动三件套，从源头保证教案与图谱同源同构。

## 触发条件
用户说类似：
- "帮我备第15周的课，栈和队列"
- "生成一份教案 + 知识图谱，课题：XXX，要点：……"
- "把这份教材/课标整理成一课一图"
- "上周的课备好了，这周接着来"

## 输入要求（开始前必须确认）
1. **课题**（必填）：本周讲什么
2. **周次与学时**（必填）：第几周、几个学时
3. **要点**（推荐）：核心知识点；可多可少，缺则从课题推断并告知用户
4. **补充材料**（可选）：教材 docx/pdf 文本、课标、PPT 提取文本——有则依据更扎实

## 执行流程

### 步骤 0 · 骨架理解（轻确认）
若提供教材/课标文本：先通读并产出"课程骨架理解"（模块划分 + 本周重点方向），简要展示给用户确认，再继续。若只有一句话输入，跳过此步。

### 步骤 1 · 教学结构化（LLM 核心步骤）
**MANDATORY - 读取完整文件**：先读 `references/lesson-json-schema.md`（JSON 契约）与 `references/extraction-prompt.md`（抽取规则）。
依据输入产出 `lesson.json`，关键纪律：
- **学生视角**：每个知识点问三遍——课标/教材有依据吗？能写可衡量目标吗？学生真的需要学吗
- **布鲁姆绑定**：Level≥4 知识点必须有 cognitive（记忆/理解/应用/分析/评价/创造）+ 可衡量的 objective
- **课堂时间轴**：flow.in_class 五环节（导入→新授→新授→互动练习→小结作业）× 四维（内容/学生活动/教师活动/设计意图）
- **易错点**写学生认知误区（如"栈后进先出 vs 队列先进先出易混淆"），不写"内容难"
- 课中环节用 `knowledge_refs` 声明引用的知识点（一致性校验锚点）

### 步骤 2 · 备课质检（Agent 自检并自动修正）
**MANDATORY - 读取完整文件**：读 `references/quality-checklist.md`（17 项清单）。
对照清单逐项检查，发现问题直接用 Edit 修正 lesson.json，循环直到通过。被降级/删除的候选知识点记录到 `rejected-notes.md`（不静默丢弃）。

### 步骤 3 · 一键生成三件套
```bash
python scripts/lesson_assistant.py --json lesson.json --output-dir 输出目录 [--style teacher-zhang]
```
自动执行：硬校验（红线）→ Markdown 图谱 → HTML 信息图 → 教案 docx。
`--style` 默认 `standard`（内置标准教案结构）；传入 `teacher-zhang` 时切换为**教师风格档案**驱动（封面+章节字段，见 `references/teacher-style-profile.md`），输出与用户历史教案同风格的成品。

**硬红线（违反即阻止交付）**：
- 教案引用的知识点必须存在于图谱节点（一致性）
- 层级连续无断层；节点名唯一；关系引用精确匹配
- Level≥4 知识点目标齐全；分类节点 category 为空

### 步骤 4 · 交付与沉淀
- 交付三件套：`第X周_教案.docx`、`第X周_知识图谱.md`、`第X周_知识图谱.html`
- 建议把 `lesson.json` 与 `glossary` 归档，形成课程级知识资产（跨周次累积）
- 用户提供学校模板/历史教案后，提炼为风格档案（见 `references/teacher-style.json`），渲染器按档案输出

## 输出约定
| 产物 | 内容 | 用途 |
|------|------|------|
| 第X周_教案.docx | 标准教案：基本信息/三维目标/学情/重难点/方法资源/课前课中课后/反思 | 直接上交 |
| 第X周_知识图谱.md | 知识树（嵌套列表）+ 关系表 + 教学目标索引 + 术语表 | 可审、可版本管理 |
| 第X周_知识图谱.html | 交互信息图：知识树可折叠、布鲁姆配色、点击查看详情 | 演示、课件、打印 |

## 关键 Anti-Patterns（禁止）
1. **不写"了解……"式目标**——必须可衡量："能够说出/解释/操作/分析……"
2. **不把教材目录整章抄成知识树**——每个节点过"学生真的需要学吗"
3. **不改写课中环节为"讲知识点一/二"两行**——五环节 × 四维齐全
4. **不跳过校验**——硬红线不通过禁止交付
5. **不静默丢弃候选知识点**——降级/删除要进 rejected-notes.md

## 目录结构
```
lesson-plan-assistant/
├── SKILL.md                     # 本文件
├── skill.json                   # 技能元数据
├── README.md                    # 用户使用说明
├── references/
│   ├── lesson-json-schema.md    # 同源 JSON 契约（必须读）
│   ├── extraction-prompt.md     # 教学结构化抽取规则（必须读）
│   ├── quality-checklist.md     # 17 项备课质检清单（必须读）
│   ├── standard-lesson-template.md  # 标准教案结构说明
│   ├── teacher-style-profile.md # 教师风格档案说明（张冬冬·章节教案风格）
│   └── teacher-style.json       # 教师风格机器可读档案（渲染器读取）
├── scripts/
│   ├── lesson_assistant.py      # 主入口：一键三件套（--style 支持）
│   ├── common.py                # 共享数据模型与硬校验
│   ├── verify_consistency.py    # 硬校验 CLI
│   ├── build_graph.py           # JSON → Markdown 图谱
│   ├── render_html.py           # JSON → HTML 信息图
│   └── build_lesson_docx.py     # JSON → 教案 docx（standard/teacher-zhang）
├── templates/
│   └── knowledge-graph.html     # 信息图模板（单文件离线）
└── examples/
    ├── stack_queue/             # 完整示例（栈和队列，标准风格）
    ├── ai_training/             # 企业 AI 培训示例（3 天 12 模块）
    └── ai_generative_art/       # 教师风格示例（人工智能生成艺术·第1章导论）
```

## 兼容性
- Python 3.8+，依赖仅 `python-docx`（Markdown/HTML 用标准库）
- HTML 信息图零外部依赖，离线可用；可用无头浏览器截图导出 PNG
- 教案默认用内置标准结构；学校模板接入后自动切换模板填充
