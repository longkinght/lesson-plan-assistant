---
name: hb-lesson-plan-assistant
display_name: 备课知识图谱助手
display_name_en: Lesson Plan Assistant
description: 将课题、周次、学时和教学要点整理为结构化 lesson.json，并同源生成可编辑教案 DOCX、Markdown 知识图谱和离线 HTML 课程看板；可按学校提供的 Word 样本严格复刻版式。用于备课、写教案、设计课堂时间轴、整理知识树、建立教学目标与知识点映射、生成教师可直接修改的课程材料。
description_zh: "把「周次 + 课题 + 要点」整理成结构化课程数据，一次同源产出可编辑教案 DOCX、Markdown 知识图谱与单文件离线 HTML 看板；可按学校提供的 Word 样本严格复刻版式。覆盖目标—知识点绑定、课中时长合计、五环节四维结构与反思真实性校验。用于备课、写教案、课堂时间轴、知识树、教学目标映射、生成教师可直接修改的课程材料。"
description_en: "Turn a topic, week and period count into a structured lesson.json, then render three same-source artifacts — an editable Word lesson plan (built-in layout, or strict fill into a school-provided DOCX sample), a Markdown knowledge map, and a single-file offline HTML dashboard. Validates that objectives bind to knowledge points, that in-class durations sum to the scheduled periods, and that the five-stage / four-dimension structure holds. Use for lesson planning, lesson plan documents, class timelines, knowledge trees, objective-to-knowledge mapping, and teacher-editable course material."
version: "2.2.4"
license: MIT
author: 黄彬
agent_created: true
---

# 备课知识图谱助手 v2

## 用途

把“周次 + 课题 + 要点”整理成一堂可执行的课，并生成三种同源产物：

| 产物 | 用途 |
|---|---|
| `<周次>_<课题>_教案.docx` | 可编辑教案初稿：内置版式，或严格按学校样本 DOCX 输出 |
| `<周次>_<课题>_知识图谱.md` | 可审阅、可版本管理的课程知识资产 |
| `<周次>_<课题>_知识图谱.html` | 单文件离线课程看板，可筛选、折叠、打印为 PDF |

核心原则：LLM 负责教学结构化，脚本负责校验、渲染和一致性验收。内容仍需授课教师审核，不能声称无需复核即可上交。

## 何时使用

用户提出以下需求时使用：

- “帮我备第 15 周的课，课题是栈和队列”
- “生成教案和知识图谱，要点是……”
- “把这份教材/课标整理成一课一图”
- “检查这份 lesson.json 的课堂时长和知识点映射”
- “把上次的教案改成这一周的内容”

不适用于：只需要一段教学设计文字，或只需要学科知识问答。

需要贴合学校规定的 Word 版式时，走「模板通道」：上传学校样本 DOCX，解析一次映射后复用。

## 输入

开始前确认：

1. **课题**：必填；
2. **周次或培训周期**：必填；
3. **学时与每学时分钟数**：必填，默认 45 分钟/学时；
4. **教学对象与要点**：强烈建议提供；
5. **教材、课标、PPT 文本或旧教案**：可选，有则作为事实依据。

缺失信息只做最小推断，并在交付时明确标出推断项。不得编造教材章节、课标条目、课堂结果或学生数据。

## 执行流程

### 1. 读取契约

必须先完整读取：

- `references/lesson-json-schema.md`
- `references/extraction-prompt.md`
- `references/quality-checklist.md`

需要章节模板时再读 `references/teacher-style-profile.md`。

### 2. 建立 lesson.json

按 v2 契约生成，重点执行：

- 每条教学目标写成 `{text, knowledge_refs}`，引用真实知识点；
- 每个知识点都有 `category`、`cognitive`、可观察的 `objective`；
- 知识树深度优先，只有一个 Level 1 根节点；
- 默认五环节：`intro → instruction → instruction → practice → summary`；
- 每环节四维齐全，并填写 `duration_minutes`；
- 课中总分钟必须等于 `hours × minutes_per_hour`；
- 尚未上课时 `reflection.status = "pre_class"`，三段都以“待课后填写：”开头。

需要保存时写入工作目录的 `lesson.json`，不覆盖用户已有源文件；涉及旧文件时建立新版本。

### 3. 机器校验

```bash
python scripts/verify_consistency.py --json lesson.json
```

错误必须按字段路径修复。提醒项逐条判断，不能为了让命令通过而删除必要内容或绕过脚本。

### 4. 生成三件套

```bash
python scripts/lesson_assistant.py --json lesson.json --output-dir output
```

使用通用章节模板：

```bash
python scripts/lesson_assistant.py --json lesson.json --output-dir output --style chapter
```

使用自定义风格：

```bash
python scripts/lesson_assistant.py --json lesson.json --output-dir output \
  --style-config references/teacher-style.json
```

按学校样本严格生成（先读 `references/template-mapping.md`）：

```bash
# 首次：解析样本，产出映射与核对报告
python scripts/analyze_template.py --template 学校样本.docx --out-dir ./模板

# 教师核对后把 confirmed 改为 true，再生成
python scripts/lesson_assistant.py --json lesson.json --output-dir output \
  --template 学校样本.docx --template-map 模板/学校样本_template-map.json
```

模板模式下脚本不新建样式、不加页眉页脚、不追加附录，只往样本已有位置写文字；课中环节表按内容自动增减行，`备注`类表尾行不动。

样本可以是空模板，也可以是**已填好内容的参考教案**。两种常见结构都能自动识别：

| 结构 | 识别结果 |
|---|---|
| 一张表多行 | rows 模式：行克隆/裁剪 |
| 每个环节一张独立小表 | units 模式：按「标题 + 小表」整组配对、克隆或删除 |
| 教学目标写成编号段落 | `paragraph_range`：整段区间替换，避免留下重复行 |

生成器先写入临时目录，三件全部成功后再移动到正式输出目录。失败时不得报告“部分完成”。

### 5. 成品验收

```bash
python scripts/audit_artifacts.py --json lesson.json --output-dir output
```

必须确认：

- Markdown 覆盖全部知识点；
- HTML 内嵌数据与源 JSON 一致；
- DOCX 包含全部课中环节与三维目标；
- 文件名使用 `week_title`，没有路径穿越；
- HTML 可离线打开，知识树可折叠，移动端无横向溢出。

### 6. 交付说明

交付时说明：

1. 三种文件的实际路径；
2. 校验通过、提醒项和人工复核项；
3. 哪些内容是推断或有待补充来源；
4. 反思区是备课占位，不是课堂事实；
5. 下一步建议：教师审核、补教材依据、上课后补真实记录。

## 输出命名

```text
<周次>_<课题>_教案.docx
<周次>_<课题>_知识图谱.md
<周次>_<课题>_知识图谱.html
```

文件名会清理 `/ \ : * ? " < > |` 和路径穿越片段。

## 失败处理

| 现象 | 处理 |
|---|---|
| JSON 解析失败 | 报告行列号，修复 JSON，不生成 |
| 契约校验有错误 | 按字段路径修复后重跑，不跳过 |
| 时长不匹配 | 重分配环节分钟，保持总分钟一致 |
| 目标未绑定知识点 | 补 `knowledge_refs`，不得填不存在节点 |
| 反思写成已发生结果 | 改回“待课后填写”，或提供真实证据后改 `post_class` |
| DOCX 依赖缺失 | 执行 `pip install -r requirements.txt` |
| 风格配置无法读取 | 检查路径与 JSON 结构，或改用 `standard` |
| 模板地址越界 | 样本已改版，重新执行 `analyze_template.py` 或按报告修正索引 |
| 模板某格仍为空 | 该字段在 lesson.json 中无内容，或地址指向了标签格 |
| 模板生成后字体不对 | 样本该格没有可继承的格式，先在样本内给一个字设好字体再解析 |

## 依赖与运行

- Python 3.8+
- 运行依赖：`python-docx`
- 测试依赖：`pytest`，可选 `playwright` 做浏览器交互测试
- HTML 不加载外部字体、脚本或图片，可离线打开

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

## 公开边界

- 生成的是教案初稿，不是学校审核结论；
- 不承诺提升学生成绩、培训 ROI 或组织能力；
- 模板通道需要一次映射确认，不承诺零配置适配任意学校样本；超长内容无法保证与原样本逐像素一致；
- 不默认包含任何真实学校、教师或学生信息；
- 公开分享示例前，移除教师姓名、班级名单、内部资料和未授权案例。

## 目录

```text
hb-lesson-plan-assistant/
├── SKILL.md
├── README.md
├── CHANGELOG.md
├── references/       # 契约、抽取规则、质量清单、版式、风格与模板映射说明
├── scripts/          # 校验、三种渲染器、模板解析与填充、独立验收
├── templates/        # 单文件离线 HTML 看板
├── examples/         # 三个完整示例、成品与学校样本示例
├── tests/            # 契约、CLI、产物和浏览器交互测试
└── docs/             # 公开展示截图
```
