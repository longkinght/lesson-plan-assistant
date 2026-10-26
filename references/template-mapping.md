# 模板映射契约（template-map.json）

用于「严格按学校/教师提供的 Word 样本格式生成」的场景。样本是版式的唯一来源，脚本只往里写文字，不新建样式。

## 一、为什么需要一份映射

学校样本的差异不在“字体好不好看”，而在两处：

1. **格式藏在哪**：字体字号在 run 级 `rPr`，单元格底纹/对齐在 `tcPr`，列宽边框在 `tblPr`，页面设置在 `sectPr`，还有 `styles.xml`。只有整链继承，成品才像同一份文件；
2. **哪个格子填什么**：列名各校不同（“学生活动”可能写作“学生任务”），也有“标签格 + 右侧空格”与“一个大格写多行”两种排法。

因此流程是：**自动解析出候选映射 → 教师确认一次 → 同校同模板长期复用**。不承诺任意样本零确认适配。

## 二、三步流程

```bash
# 1. 解析样本，产出映射与核对报告
python scripts/analyze_template.py --template 学校样本.docx --out-dir ./模板

# 2. 人工核对 <样本名>_template-map.json，把 confirmed 改为 true
#    核对要点见 <样本名>_template-report.md

# 3. 按样本格式生成
python scripts/lesson_assistant.py --json lesson.json --output-dir output \
  --template 学校样本.docx --template-map 模板/学校样本_template-map.json
```

只生成 DOCX 时用 `scripts/build_lesson_docx.py --template ... --template-map ...`。
省略 `--template-map` 会自动推断，并在输出目录留档，同时打印“尚未确认”提示——仅用于首次试用。

## 三、地址格式

字段值指向一个真实存在的位置，越界会报可读错误，不会静默跳过。

```json
{ "kind": "cell", "table": 0, "row": 0, "col": 1 }
{ "kind": "paragraph", "index": 6 }
```

- `table` 是文档中第几个表格（从 0 开始，只数正文表格）；
- `row` / `col` 从 0 开始，合并单元格按网格坐标计；
- `paragraph.index` 是 `document.paragraphs` 的下标，**只含正文段落，不含表格内段落**。

## 四、fields：单值字段

键名决定取什么内容：

| 键 | 取值 | 形态 |
|---|---|---|
| `lesson_meta.*` | 元数据，如 `course_name`、`week`、`hours`、`class_name` | 纯文本 |
| `objectives.knowledge` / `.ability` / `.quality` | 该组目标 | `1. ` 编号，多行 |
| `objectives.all` | 三组目标 | 带“知识目标：”等小标题 |
| `objectives_compact` | 三组目标合并 | 分号连接，单行 |
| `key_points` / `difficult_points` | 重点/难点 | 每项一行，前缀 `·` |
| `methods` / `resources` / `references` | 方法/资源/参考文献 | 每项一行，前缀 `·` |
| `student_analysis` | 学情分析 | 原文本 |
| `in_class_summary` | 课中环节概要 | `1. 导入（5 分钟）` + 内容 |
| `pre_class_summary` / `post_class_summary` | 课前/课后 | 内容 + 学生活动 |
| `reflection.effect` / `.diagnosis` / `.improvement` | 教学反思三段 | 原文本 |
| `knowledge_outline` | 知识树缩进文本 | 多行 |
| `flow.total_minutes` | 课中总时长 | 数字 |

可选项（写在地址对象里）：

```json
{ "kind": "cell", "table": 0, "row": 0, "col": 1, "prefix": "课题：", "suffix": "", "empty": "—" }
```

- `prefix` / `suffix`：拼接固定文字；
- `empty`：内容为空时写入的占位符。

## 五、blocks 之一：一张表多行（rows 模式）

适用于课中环节表、目标表、知识点表。模板行提供格式，行数按内容决定：不够就复制行，多了就删除行。

```json
"blocks": {
  "in_class": {
    "table": 3,
    "template_row": 1,
    "last_row": 1,
    "columns": { "stage_with_duration": 0, "content": 1, "student_activity": 2,
                 "teacher_activity": 3, "design_intent": 4 }
  }
}
```

| 键 | 含义 |
|---|---|
| `table` | 表格序号 |
| `template_row` | 提供格式的样板行 |
| `last_row` | 可被填充/删除的最后一行，默认到表尾 |
| `columns` | 列键 → 列序号 |
| `keep_extra_rows` | 设为 true 时保留多余空行，默认删除 |
| `repeat_header` | 设为 true 时给表头行加 `w:tblHeader`，跨页自动重复标题行；默认继承样本 |
| `keep_row_together` | 设为 true 时给数据行加 `w:cantSplit`，避免一行被页边切断；默认继承样本 |

后两项只影响分页行为，不改字体、边框与列宽。样本本身没有设置重复标题行时，分析报告会给出提示。

`source` 可用：`in_class`、`pre_class`、`post_class`、`objectives_knowledge`、`objectives_ability`、`objectives_quality`、`knowledge_outline`。除 `in_class` 外，缺失时会按 `source` 推断。

列键可用：`index`、`stage`、`stage_with_duration`、`duration`、`content`、`student_activity`、`teacher_activity`、`design_intent`、`knowledge_refs`、`text`、`refs`、`level`、`name`、`cognitive`、`category`、`objective`。未知列键会直接报错，避免写错列。

## 六、blocks 之二：一组「标题 + 独立小表」（units 模式）

不少教案（尤其是教师自己写的参考教案）把每个环节做成「标题段 + 一张独立四维小表」，重复若干组。这种结构不能靠行克隆处理，需整体配对。

```json
"blocks": {
  "in_class": {
    "mode": "units",
    "source": "flow",
    "columns": { "content": 0, "student_activity": 1, "teacher_activity": 2, "design_intent": 3 },
    "heading_template": "环节·{stage}（知识点：{refs}）",
    "signature": ["教学内容", "学生活动", "教师活动", "设计意图"]
  }
}
```

| 键 | 含义 |
|---|---|
| `mode` | 固定写 `units` |
| `source` | `flow`（课前 + 课中 + 课后）或 `in_class`（仅课中） |
| `columns` | 小表内列键 → 列序号 |
| `heading_template` | 标题段模板，可用 `{stage}`、`{refs}`、`{duration}`、`{index}`；无知识点时自动去掉「（知识点：…）」 |
| `signature` | 用于筛出同一类单元的表头文字，避免把反思表误当环节表 |
| `pre_label` / `post_label` | 课前/课后单元的显示名，默认「课前」「课后」 |

行为：

- 单元数与内容条数一致 → 逐组替换，不增删；
- 样本单元不足 → 复制最后一组（含标题段）补齐；
- 样本单元多余 → 整组删除（标题段与小表一起删）；
- 【课前】【课中】这类分隔标记不属于单元，原样保留。

分析脚本会自动识别这种结构：连续出现 ≥2 组「有文字的段落 + 含 ≥2 个四维列名的小表」时，直接给出 `mode: "units"`，不会误判成 rows 模式。

## 七、fields 补充：编号段落区间与列表连接

教学目标经常写成不带标签的编号段落。用一个区间整体替换，避免只改掉第一行、留下重复内容：

```json
"objectives.all": { "kind": "paragraph_range", "start": 3, "end": 12 }
```

- `start` / `end` 是 `document.paragraphs` 的下标（含两端）；
- 相邻的编号列表会自动合并成一个区间；
- 写入前先清空区间内旧段落，再按内容展开。

列表字段（重点、难点、方法、资源、参考文献）默认每条一行并加 `·` 前缀。要还原成「一整段连续文字」，加 `joiner`：

```json
"key_points": { "kind": "cell", "table": 1, "row": 0, "col": 1, "joiner": "；" }
```

## 八、clear：清掉不需要的固定文字

```json
"clear": [ { "kind": "paragraph", "index": 11 } ]
```

用于样本里“此处填写……”“（可自行增减）”这类提示语。正式生成时可清空，也可保留。

## 九、格式保留机制与边界

保留方式：写入时复用原 run 的 `w:rPr`；多行内容按原段落复制，行距缩进不变；表格行用 `deepcopy(tr)` 复制，行高、底纹、边框随行继承；页眉、页脚、页面设置、`styles.xml` 完全不改。

| 边界 | 说明 |
|---|---|
| 空格的字体 | 若样本空格自身没有 `rPr`，写入文字继承该格所在样式（与手工输入一致）；样本里带格式的空 run 会自动作为格式捐赠者 |
| 合并单元格 | 按网格坐标寻址，跨行单元格可能被重复写入，需在映射中避开 |
| 一段多行的嵌套结构 | 支持 `\n` 分行；不支持在单元格内重建列表编号格式 |
| 超长内容 | 会自然撑开行高、可能跨页，无法与原样本逐像素一致 |
| 一个表多个区块 | rows 模式下一个表只对应一个区块；units 模式按「标题+表」配对，不受此限 |
| 无标签的目标列表 | 只能整体替换并补「知识目标／能力目标／素质目标」标签，无法还原原件分组 |
| 跨页 | 默认继承样本设置；可用 `repeat_header` 与 `keep_row_together` 打开重复标题行与整行不拆分 |
| 严格模式输出 | 只填样本已有位置，不追加知识图谱附录、不加页眉页脚说明 |

## 十、失败处理

| 现象 | 处理 |
|---|---|
| `指向的表/行/段不存在` | 样本已改版，重新解析或修正索引 |
| `没有找到「环节标题 + 表格」结构` | units 模式要求表格放在标题段之后，检查样本是否有空表或表格被放进文本框 |
| `的列键 'x' 不支持` | 改成支持的列键 |
| `fields 与 blocks 都为空` | 映射没写对，检查 JSON 结构 |
| 生成后某格仍是空的 | 该字段在 lesson.json 中无内容，或地址指向了标签格 |
| 字体变了 | 样本该格没有格式可供继承，先在样本里打一个字并设好格式，再解析 |
