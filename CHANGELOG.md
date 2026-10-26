# Changelog

## 2.2.4 · 2026-10-26

技能标识改名：`lesson-plan-assistant` 在平台上已被占用。

### 变更

- `SKILL.md` 与 `skill.json` 的 `name` 改为 `hb-lesson-plan-assistant`，加入作者缩写避免重名；
- `README.md` 安装路径与目录树、SKILL.md 目录树同步改名；
- `tests/test_skill_meta.py` 新增 `test_name_matches_manifest`：校验两处 name 一致且符合 kebab-case；
- 分发包顶层目录与文件名同步为 `hb-lesson-plan-assistant`。

展示名（`display_name` / `display_name_en`）保持「备课知识图谱助手 / Lesson Plan Assistant」不变，标识与展示分离。

## 2.2.3 · 2026-10-26

补齐平台上架要求的 Skill 元数据字段。

### 变更

- `SKILL.md` frontmatter 新增 `version`、`display_name`（备课知识图谱助手）、`display_name_en`（Lesson Plan Assistant）、`description_zh`、`description_en`；原 `description` 保留为完整中文描述；
- 中英文描述均用双引号包裹，避免正文里的冒号被 YAML 误解析成映射；
- 新增 `tests/test_skill_meta.py`：校验五个必填字段非空、`SKILL.md` 与 `skill.json` 版本一致、展示名不超长、中英文描述语言不串味；
- `skill.json` 登记新测试文件，`automated_tests` 更新为 48。

## 2.2.2 · 2026-10-26

加入个人版权署名。许可协议不变，仍是 MIT。

### 变更

- `LICENSE`：版权人改为 `Copyright (c) 2026 黄彬 (Huang Bin)`；
- `skill.json` 与 `SKILL.md` frontmatter：`author: 黄彬`；
- `README.md`：标题下加作者行，License 段补版权说明；
- HTML 看板页脚新增 `© 2026 黄彬 · MIT License`（`.foot-copy`，金棕色小字，随打印保留）；
- `scripts/lesson_assistant.py` 模块文档串补版权行。

### 边界

- 署名只落在 Skill 自身与离线看板页脚，不写进教师教案正文；
- DOCX 文档属性的作者仍取授课教师，不改成 Skill 作者，避免教案上交时署名错位。

## 2.2.1 · 2026-10-26

修复离线 HTML 看板的版式缺陷：课堂节奏卡片内容压到卡片边框。

### 修复

- `.rhythm` 与 `.card-body` 是同权重单类选择器且写在其后，`padding: 4px 0 0` 把左右各 22px 的内边距覆盖成了 0，
  导致节奏条通栏贴边、时长数字（`5 min` / `25 min`）右侧几乎顶到卡片边框；
- 改为 `.card-body.rhythm { padding-top: 8px; }`，只收紧上内边距，左右与底部继续沿用 `.card-body`；
- 窄屏（≤520px）同样恢复 15px 内边距，文字不再被裁切。

### 测试与示例

- 新增浏览器回归测试 `test_rhythm_card_content_is_inset`：同时校验计算内边距与几何位置（节奏条左缘、时长右缘相对卡片边框的间距）；
- 用旧样式反向复跑确认该测试会失败（旧值：左右 0px、内容右缘距边框 1px），新样式为 22px / 23px；
- 5 份示例 HTML 与 `docs/知识图谱看板.png` 按新模板重新生成；
- 全部测试 44 项。

## 2.2.0 · 2026-10-26

支持「参考教案」作为样本：不只是空白模板，已经写满内容的教案也能当版式来源。

### 新增能力

- `units` 模式：每个环节是「标题段 + 独立四维小表」的文档，按整组配对、克隆或删除；
- `paragraph_range` 地址：教学目标写成编号段落时整体替换区间，不会只改第一行留下重复；
- 相邻编号列表自动合并成一个区间；
- `joiner` 字段选项：把重点、难点、方法、资源还原成一整段连续文字；
- 列表拼接、段落区间、单元模式都有对应测试。

### 正确性修正

- 行模式与单元模式并存时，被单元占用的表不再被当成行区块重复处理；
- 单元模式删除时按「组」计数，克隆时复用整组元素；
- 目标字段的 `objectives.all` 视为已覆盖三个分组，不再误报「未定位」。

### 示例与文档

- 新增 `examples/reference-lesson/`：三天企业培训参考教案 + 映射 + 成品；
- `references/template-mapping.md` 补齐 units、paragraph_range、joiner 与失败处理；
- 全部测试 43 项。

## 2.1.0 · 2026-10-26

新增「模板通道」：把学校或教师提供的 Word 样本作为版式来源，严格按其格式生成。
不替换 v2.0 的内置版式路径，两者并存。

### 新增能力

- `scripts/docx_template.py`：样本解析、按样本填充、行克隆与裁剪；
- `scripts/analyze_template.py`：样本 → `template-map.json` + 核对报告；
- `lesson_assistant.py` / `build_lesson_docx.py` 新增 `--template`、`--template-map`；
- `references/template-mapping.md`：映射契约、地址格式、列键、边界与失败处理；
- `examples/school-template/`：样本、映射、核对报告与按样本生成的成品。

### 格式保真

- 写入复用原 run 的 `w:rPr`，不用 `cell.text = value`（后者会丢格式）；
- 多行内容按原段落复制，行距与缩进不变；
- 表格行深拷贝，行高、底纹、边框随行继承；
- 页眉、页脚、页面设置、`styles.xml` 全程不改；
- 课中环节表按内容增减行，`备注`类表尾行自动排除；
- 严格模式不追加知识结构附录，不加页眉页脚说明文字；
- 新增 `repeat_header` / `keep_row_together` 两个区块选项：跨页重复标题行、整行不拆分，默认继承样本。

### 正确性修正

- 单元格去重从 `id()` 改为元素引用，避免代理对象回收后误判；
- 标题后紧跟表格时不再往空段落写内容，避免与表内内容重复；
- 目标类字段优先写入标签右侧的值格，不覆盖学校模板的标签文字。

### 测试

- 新增 16 项模板测试（分析、格式保留、行增删、跨页选项、映射序列化、错误路径）；
- 全部测试共 37 项。

## 2.0.0 · 2026-10-26

相对初版 `lesson-plan-assistant-main` 的升级。原目录保留，本项目为独立 v2。

### 不兼容变更

- `schema_version` 升级为 `2.0`；
- 教学目标从字符串数组改为 `{text, knowledge_refs}` 对象；
- 每个课中环节新增 `role` 和 `duration_minutes`；
- `flow` 新增 `structure`，新内容使用 `five_stage` 或 `custom`；
- `reflection` 新增 `status` 与 `evidence`，备课时必须标“待课后”；
- 输出文件名由“周次”改为“周次_课题”，避免同周多课互相覆盖；
- 教师风格参数从 `teacher-zhang` 改为 `chapter` 或 `--style-config`，旧别名暂时兼容。

### 质量与可靠性

- 所有知识点都必须有可观察目标，不再只校验 Level≥4；
- 三维目标必须绑定真实知识点；
- 五环节数量、四维完整度、环节角色、总时长进入硬校验；
- 课堂总时长必须等于学时 × 每学时分钟数；
- 关系校验修复重复报错和缩进错误；
- 缺字段、错误类型、非对象节点不会触发 traceback；
- JSON 格式错误返回行列号；
- 生成过程使用临时目录，三件全部成功后再移动；
- 输出文件名清理非法字符和路径穿越；
- 未知风格、模板缺失、样式配置损坏返回可操作错误。

### 内容真实性

- 备课反思禁止写课堂正确率、达成率等未发生结果；
- 示例中的量化结果全部替换为待课后占位；
- 移除示例中的真实教师与学院默认信息；
- 所有交付文案改为“教师审核后使用”。

### 视觉与产物

- HTML 重构为课程看板：封面区、指标、课程信息、课堂节奏、目标、知识树、节点解读、关系、目标映射、术语；
- HTML 知识树支持真正的子树折叠、全部展开/收起、知识点筛选、详情展开；
- HTML 支持移动端单列布局与 A4 打印样式；
- DOCX 重构封面、信息网格、章节编号、四维表、页眉页码和知识结构附录；
- DOCX 表格禁止跨页断行，表头跨页重复；
- Markdown 增加课堂时间轴、目标映射和节点目标索引，并转义表格分隔符。

### 工程与分享

- 新增 21 项自动化测试，覆盖契约、CLI、成品一致性和浏览器交互；
- 新增独立 `audit_artifacts.py`，回读 DOCX、Markdown、HTML 与源 JSON 比对；
- 新增 `requirements.txt`、`LICENSE`、公开 README、版本说明；
- `SKILL.md` 补齐触发条件、执行流程、失败处理、依赖和公开边界；
- 更新三个示例到 v2 契约，并重新生成三件套；
- 删除个人化和过时的公共展示材料。

### 已知未实现

- 学校原版 DOCX 表格逐格填充；
- 学期教学计划汇总表；
- 多章合并输出；
- DOCX 转 PDF / 自动截图流水线。
