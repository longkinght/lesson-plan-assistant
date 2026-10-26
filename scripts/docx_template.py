# -*- coding: utf-8 -*-
"""Template channel: fill a school-provided DOCX instead of building our own layout.

Design contract
---------------
The sample document is the single source of layout truth. This module never
creates styles, fonts, borders, headers, footers or page setup; it only writes
text into paragraphs and table cells that already exist, cloning a table row
when a block needs more rows than the sample provides.

Run-level formatting survives because every write reuses the original run's
``w:rPr``. Writing through ``cell.text = value`` would silently drop it, which is
the single most common way template filling destroys a school's format.
"""
import copy
import json
from collections import Counter
import os
import re

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.table import Table, _Row
from docx.text.paragraph import Paragraph

from common import (
    DIMENSIONS, LessonInputError, objective_items, objective_refs,
    objective_text,
)

MAP_VERSION = "1.0"

SOURCE_KEYS = [
    "in_class", "pre_class", "post_class",
    "objectives_knowledge", "objectives_ability", "objectives_quality",
    "knowledge_outline",
]

COLUMN_KEYS = [
    "index", "stage", "stage_with_duration", "duration", "content",
    "student_activity", "teacher_activity", "design_intent",
    "knowledge_refs", "text", "refs", "level", "name", "cognitive",
    "category", "objective",
]

# Field keys that need assembly instead of a direct dictionary lookup.
FIELD_ALIASES = {
    "key_points_text": "key_points",
    "difficult_points_text": "difficult_points",
    "methods_text": "methods",
    "resources_text": "resources",
    "references_text": "references",
}

LIST_FIELDS = ["key_points", "difficult_points", "methods", "resources", "references"]


# --------------------------------------------------------------------------
# low-level text writing that preserves formatting
# --------------------------------------------------------------------------

def _split_lines(text):
    value = "" if text is None else str(text)
    return value.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _run_rpr(run):
    rpr = run._r.find(qn("w:rPr"))
    return copy.deepcopy(rpr) if rpr is not None else None


def _first_run(paragraph):
    for run in paragraph.runs:
        if run.text.strip():
            return run
    return paragraph.runs[0] if paragraph.runs else None


def paragraph_rpr(paragraph):
    """Prefer a run that carries real formatting, even when its text is empty.

    School templates often leave a styled empty run in every blank cell; that run
    is the format donor we must reuse.
    """
    for run in paragraph.runs:
        rpr = _run_rpr(run)
        if rpr is not None:
            return rpr
    return None


def _clear_runs(paragraph, keep=None):
    for run in list(paragraph.runs):
        if run is not keep:
            run._r.getparent().remove(run._r)


def _append_run_with_rpr(paragraph, text, rpr):
    run = paragraph.add_run(text)
    if rpr is not None:
        existing = run._r.find(qn("w:rPr"))
        if existing is not None:
            run._r.remove(existing)
        run._r.insert(0, copy.deepcopy(rpr))
    return run


def write_paragraph(paragraph, text, donor_rpr=None):
    """Replace paragraph text while keeping the sample's character formatting.

    A multi-line value becomes several paragraphs cloned from the original so
    line spacing, indentation and numbering stay identical to the sample.
    """
    lines = _split_lines(text)
    rpr = donor_rpr if donor_rpr is not None else paragraph_rpr(paragraph)
    anchor = paragraph._p
    for index, line in enumerate(lines):
        if index == 0:
            target = paragraph
        else:
            new_p = copy.deepcopy(paragraph._p)
            for child in list(new_p):
                if child.tag == qn("w:r") or child.tag == qn("w:hyperlink"):
                    new_p.remove(child)
            anchor.addnext(new_p)
            anchor = new_p
            target = Paragraph(new_p, paragraph._parent)
        _clear_runs(target)
        _append_run_with_rpr(target, line, rpr)
    return paragraph


def write_cell(cell, text, donor_rpr=None):
    """Fill a table cell, keeping the sample's font, size and paragraph format."""
    paragraphs = cell.paragraphs
    if not paragraphs:
        paragraphs = [cell.add_paragraph()]
    first = paragraphs[0]
    rpr = donor_rpr if donor_rpr is not None else paragraph_rpr(first)
    for extra in paragraphs[1:]:
        extra._p.getparent().remove(extra._p)
    write_paragraph(first, text, rpr)
    return cell


def clone_row_after(table, row):
    new_tr = copy.deepcopy(row._tr)
    row._tr.addnext(new_tr)
    return _Row(new_tr, table)


def delete_row(table, row):
    row._tr.getparent().remove(row._tr)


def _row_properties(row):
    tr_pr = row._tr.find(qn("w:trPr"))
    if tr_pr is None:
        tr_pr = OxmlElement("w:trPr")
        row._tr.insert(0, tr_pr)
    return tr_pr


def set_repeat_header(row):
    """Mark a row as a header that repeats on every page (w:tblHeader)."""
    tr_pr = _row_properties(row)
    if tr_pr.find(qn("w:tblHeader")) is None:
        tr_pr.append(OxmlElement("w:tblHeader"))


def set_cant_split(row):
    """Prevent a row from breaking across pages (w:cantSplit)."""
    tr_pr = _row_properties(row)
    if tr_pr.find(qn("w:cantSplit")) is None:
        tr_pr.append(OxmlElement("w:cantSplit"))


# --------------------------------------------------------------------------
# address resolution
# --------------------------------------------------------------------------

def resolve_address(document, address, label=""):
    """Turn a static address from the map into a live paragraph or cell object."""
    if not isinstance(address, dict):
        raise LessonInputError("%s 的地址必须是对象" % (label or "字段"))
    kind = address.get("kind")
    try:
        if kind == "paragraph_range":
            start = int(address["start"])
            end = int(address["end"])
            paragraphs = document.paragraphs
            if start < 0 or end >= len(paragraphs) or end < start:
                raise LessonInputError(
                    "%s 指向的段落区间 %d–%d 不存在（样本共 %d 段）"
                    % (label, start, end, len(paragraphs)))
            return "paragraph_range", (paragraphs[start], paragraphs[end])
        if kind == "paragraph":
            index = int(address["index"])
            paragraphs = document.paragraphs
            if index < 0 or index >= len(paragraphs):
                raise LessonInputError(
                    "%s 指向的第 %d 段不存在（样本共 %d 段），请更新 template-map.json"
                    % (label, index, len(paragraphs)))
            return "paragraph", paragraphs[index]
        if kind == "cell":
            table_index = int(address["table"])
            row_index = int(address["row"])
            col_index = int(address["col"])
            tables = document.tables
            if table_index < 0 or table_index >= len(tables):
                raise LessonInputError("%s 指向的表 %d 不存在（样本共 %d 个表）"
                                       % (label, table_index, len(tables)))
            table = tables[table_index]
            if row_index < 0 or row_index >= len(table.rows):
                raise LessonInputError("%s 指向表 %d 的第 %d 行不存在（该表共 %d 行）"
                                       % (label, table_index, row_index, len(table.rows)))
            row = table.rows[row_index]
            if col_index < 0 or col_index >= len(row.cells):
                raise LessonInputError("%s 指向表 %d 第 %d 行的第 %d 列不存在"
                                       % (label, table_index, row_index, col_index))
            return "cell", row.cells[col_index]
    except LessonInputError:
        raise
    except (KeyError, TypeError, ValueError):
        raise LessonInputError("%s 的地址格式不正确：%s" % (label, json.dumps(address, ensure_ascii=False)))
    raise LessonInputError("%s 的 kind 必须是 paragraph 或 cell" % (label or "字段"))


# --------------------------------------------------------------------------
# value resolution from lesson.json
# --------------------------------------------------------------------------

def _dotted(data, key):
    node = data
    for part in key.split("."):
        if isinstance(node, dict):
            node = node.get(part, "")
        elif isinstance(node, list) and part.isdigit():
            index = int(part)
            node = node[index] if index < len(node) else ""
        else:
            return ""
    if isinstance(node, list):
        return "\n".join(str(x) for x in node)
    return "" if node is None else str(node)


def _numbered(items):
    return "\n".join("%d. %s" % (i, objective_text(item)) for i, item in enumerate(items, 1))


def field_value(key, data):
    """Resolve one map key into the text that should be written."""
    if key.startswith("objectives."):
        group = key.split(".", 1)[1]
        if group == "all":
            blocks = []
            for name, label in [("knowledge", "知识目标"), ("ability", "能力目标"), ("quality", "素质目标")]:
                items = objective_items(data, name)
                if items:
                    blocks.append("%s：\n%s" % (label, _numbered(items)))
            return "\n".join(blocks)
        return _numbered(objective_items(data, group))
    if key == "objectives_compact":
        merged = [objective_text(x) for group in ["knowledge", "ability", "quality"]
                  for x in objective_items(data, group)]
        return "；".join(x for x in merged if x)
    if key == "knowledge_outline":
        return _outline_text(data)
    if key == "in_class_summary":
        lines = []
        for index, stage in enumerate(data.get("flow", {}).get("in_class", []), 1):
            minutes = stage.get("duration_minutes")
            head = "%d. %s" % (index, stage.get("stage", ""))
            if minutes:
                head += "（%s 分钟）" % _trim_number(minutes)
            lines.append(head)
            if stage.get("content"):
                lines.append(stage["content"])
        return "\n".join(lines)
    if key in ["pre_class_summary", "post_class_summary"]:
        stage = data.get("flow", {}).get(key.split("_summary")[0], {})
        return "\n".join(x for x in [stage.get("content", ""),
                                     "学生活动：" + stage.get("student_activity", "")
                                     if stage.get("student_activity") else ""] if x)
    if key == "flow.total_minutes":
        total = sum(s.get("duration_minutes", 0) for s in data.get("flow", {}).get("in_class", []))
        return _trim_number(total)
    if key in FIELD_ALIASES:
        key = FIELD_ALIASES[key]
    if key in LIST_FIELDS:
        value = data.get(key, [])
        if isinstance(value, list):
            return "\n".join("· %s" % x for x in value if str(x).strip())
        return str(value)
    if key in data and not isinstance(data[key], (dict, list)):
        return str(data[key])
    return _dotted(data, key)


def list_items(key, data):
    """Raw list behind a list field, used when the map wants inline joining."""
    key = FIELD_ALIASES.get(key, key)
    if key in LIST_FIELDS:
        value = data.get(key, [])
        if isinstance(value, list):
            return [str(x).strip() for x in value if str(x).strip()]
    return []


def _trim_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return str(int(number)) if number == int(number) else str(number)


def _outline_text(data):
    from common import build_tree

    lines = []

    def walk(node, depth):
        prefix = "　" * depth
        mark = "§ " if node.get("node_type") == "分类" else "· "
        extra = []
        if node.get("cognitive"):
            extra.append(node["cognitive"])
        if node.get("category"):
            extra.append(node["category"])
        suffix = "（%s）" % " / ".join(extra) if extra else ""
        lines.append("%s%s%s%s" % (prefix, mark, node.get("name", ""), suffix))
        for child in node.get("children", []):
            walk(child, depth + 1)

    roots, _ = build_tree(data.get("knowledge_tree", []))
    for root in roots:
        walk(root, 0)
    return "\n".join(lines)


def block_rows(source, data):
    """Return the ordered row items a block should render."""
    flow = data.get("flow", {}) or {}
    if source == "in_class":
        return list(flow.get("in_class", []) or [])
    if source in ["pre_class", "post_class"]:
        stage = flow.get(source, {}) or {}
        return [stage] if stage else []
    if source.startswith("objectives_"):
        group = source.split("objectives_", 1)[1]
        return list(objective_items(data, group))
    if source == "knowledge_outline":
        from common import build_tree

        rows = []

        def walk(node, depth):
            rows.append({"level": depth + 1, "name": node.get("name", ""),
                         "cognitive": node.get("cognitive", ""),
                         "category": node.get("category", ""),
                         "objective": node.get("objective", "")})
            for child in node.get("children", []):
                walk(child, depth + 1)

        roots, _ = build_tree(data.get("knowledge_tree", []))
        for root in roots:
            walk(root, 0)
        return rows
    raise LessonInputError("未知的内容块来源：%s（可选 %s）" % (source, "、".join(SOURCE_KEYS)))


def block_cell_text(item, column_key, index):
    if column_key == "index":
        return str(index)
    if isinstance(item, dict):
        if column_key == "stage":
            return str(item.get("stage", ""))
        if column_key == "stage_with_duration":
            minutes = item.get("duration_minutes")
            name = str(item.get("stage", ""))
            return "%s（%s 分钟）" % (name, _trim_number(minutes)) if minutes else name
        if column_key == "duration":
            return _trim_number(item.get("duration_minutes", ""))
        if column_key in DIMENSIONS:
            return str(item.get(column_key, ""))
        if column_key in ["knowledge_refs", "refs"]:
            return "、".join(objective_refs(item)) if column_key == "refs" else "、".join(item.get("knowledge_refs", []) or [])
        if column_key == "text":
            return objective_text(item)
        if column_key in ["name", "level", "cognitive", "category", "objective"]:
            return str(item.get(column_key, ""))
    return ""


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def load_map(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            mapping = json.load(f)
    except FileNotFoundError:
        raise LessonInputError("找不到 template-map.json：%s" % path)
    except json.JSONDecodeError as exc:
        raise LessonInputError("template-map.json 格式错误：第 %s 行 %s" % (exc.lineno, exc.msg))
    except OSError as exc:
        raise LessonInputError("无法读取 template-map.json：%s" % exc)
    if not isinstance(mapping, dict):
        raise LessonInputError("template-map.json 顶层必须是对象")
    return mapping


def render_from_template(template_path, data, mapping, output_path):
    """Fill the sample DOCX and save the result. Returns a summary dict."""
    if not os.path.isfile(template_path):
        raise LessonInputError("找不到样本 DOCX：%s" % template_path)
    document = Document(template_path)

    fields = mapping.get("fields", {}) or {}
    blocks = mapping.get("blocks", {}) or {}
    if not fields and not blocks:
        raise LessonInputError("template-map.json 中 fields 与 blocks 都为空，无法填充")

    # Resolve everything before mutating anything: writing text can add
    # paragraphs and cloning rows can shift indices.
    resolved_fields = []
    for key, address in fields.items():
        spec = dict(address) if isinstance(address, dict) else {}
        target_kind, target = resolve_address(document, address, key)
        resolved_fields.append((key, spec, target_kind, target))

    unit_specs = {source: spec for source, spec in blocks.items()
                  if isinstance(spec, dict) and spec.get("mode") == "units"}
    resolved_blocks = []
    for source, spec in blocks.items():
        if source in unit_specs:
            continue
        if not isinstance(spec, dict):
            raise LessonInputError("blocks.%s 配置必须是对象" % source)
        table_index = int(spec.get("table", -1))
        tables = document.tables
        if table_index < 0 or table_index >= len(tables):
            raise LessonInputError("blocks.%s 指向的表 %d 不存在（样本共 %d 个表）"
                                   % (source, table_index, len(tables)))
        table = tables[table_index]
        first_row = int(spec.get("template_row", 0))
        if first_row < 0 or first_row >= len(table.rows):
            raise LessonInputError("blocks.%s 的 template_row %d 超出表 %d 的行数"
                                   % (source, first_row, table_index))
        last_row = int(spec.get("last_row", len(table.rows) - 1))
        last_row = min(last_row, len(table.rows) - 1)
        if last_row < first_row:
            last_row = first_row
        columns = spec.get("columns", {}) or {}
        if not columns:
            raise LessonInputError("blocks.%s 缺少 columns 映射" % source)
        for column_key in columns:
            if column_key not in COLUMN_KEYS:
                raise LessonInputError("blocks.%s 的列键 '%s' 不支持（可选 %s）"
                                       % (source, column_key, "、".join(COLUMN_KEYS)))
        donors = {}
        for column_key, col_index in columns.items():
            col_index = int(col_index)
            row_cells = table.rows[first_row].cells
            if col_index < 0 or col_index >= len(row_cells):
                raise LessonInputError("blocks.%s 的列序号 %d 超出表 %d 的列数"
                                       % (source, col_index, table_index))
            donors[column_key] = paragraph_rpr(row_cells[col_index].paragraphs[0])
        resolved_blocks.append((source, spec, table, first_row, last_row, columns, donors))

    # 1. Fields first: paragraph objects stay valid through later row cloning.
    filled_fields = 0
    for key, spec, kind, target in resolved_fields:
        value = field_value(key, data)
        if spec.get("joiner"):
            items = list_items(key, data)
            if items:
                value = spec["joiner"].join(items)
        if not value and spec.get("empty"):
            value = spec["empty"]
        if spec.get("prefix"):
            value = spec["prefix"] + value
        if spec.get("suffix") and value:
            value = value + spec["suffix"]
        if kind == "paragraph":
            write_paragraph(target, value)
        elif kind == "paragraph_range":
            # 先删掉区间里的旧段落，再写入：写入会把多行拆成新段落，
            # 若顺序颠倒，新段落会被随后的删除一并清掉。
            first, last = target
            element = first._p.getnext()
            while element is not None and element is not last._p:
                following = element.getnext()
                if element.tag == qn("w:p"):
                    element.getparent().remove(element)
                element = following
            if last._p.getparent() is not None:
                last._p.getparent().remove(last._p)
            write_paragraph(first, value)
        else:
            write_cell(target, value)
        filled_fields += 1

    # 2. Blocks: fill the sample's own rows first, then clone or trim.
    filled_blocks = 0
    cloned_rows = 0
    removed_rows = 0
    for source, spec, table, first_row, last_row, columns, donors in resolved_blocks:
        items = block_rows(source, data)
        capacity = last_row - first_row + 1
        if not items:
            for _ in range(capacity):
                delete_row(table, table.rows[first_row])
                removed_rows += 1
            continue
        rows = [table.rows[first_row]]
        while len(rows) < len(items):
            rows.append(clone_row_after(table, rows[-1]))
            cloned_rows += 1
        if len(items) < capacity and not spec.get("keep_extra_rows"):
            for _ in range(capacity - len(items)):
                delete_row(table, table.rows[first_row + len(items)])
                removed_rows += 1
        for index, item in enumerate(items, 1):
            row = rows[index - 1]
            for column_key, col_index in columns.items():
                write_cell(row.cells[int(col_index)],
                           block_cell_text(item, column_key, index),
                           donors.get(column_key))
            if spec.get("keep_row_together"):
                set_cant_split(row)
        if spec.get("repeat_header") and first_row > 0:
            set_repeat_header(table.rows[first_row - 1])
        filled_blocks += 1

    # 3. Repeated heading+table units: pair, clone or trim whole units.
    unit_summary = {"units": 0, "cloned": 0, "removed": 0}
    for source, spec in unit_specs.items():
        result = render_units(document, data, spec, source)
        unit_summary["units"] += result["units"]
        unit_summary["cloned"] += result["cloned"]
        unit_summary["removed"] += result["removed"]
        filled_blocks += 1

    # 4. Optional cleanup of fixed guidance text the teacher does not want.
    for address in mapping.get("clear", []) or []:
        kind, target = resolve_address(document, address, "clear")
        if kind == "paragraph":
            write_paragraph(target, "")
        else:
            write_cell(target, "")

    document.save(output_path)
    return {
        "fields": filled_fields, "blocks": filled_blocks,
        "cloned_rows": cloned_rows, "removed_rows": removed_rows,
        "units": unit_summary["units"], "cloned_units": unit_summary["cloned"],
        "removed_units": unit_summary["removed"],
        "template": os.path.basename(template_path),
    }


# --------------------------------------------------------------------------
# structure analysis: propose a map from a foreign sample
# --------------------------------------------------------------------------

LABEL_SYNONYMS = {
    "lesson_meta.course_name": ["课程名称", "课程名", "课程", "所属课程"],
    "lesson_meta.title": ["课题", "授课课题", "教学主题", "章标题", "课程内容", "教学单元"],
    "lesson_meta.week": ["周次", "授课周次", "教学周次", "第几周"],
    "lesson_meta.hours": ["学时", "课时", "授课学时", "课程学时", "学时数"],
    "lesson_meta.class_name": ["班级", "授课班级", "教学班级", "上课班级", "教学对象"],
    "lesson_meta.teacher": ["教师", "授课教师", "任课教师", "主讲教师", "授课人"],
    "lesson_meta.date": ["日期", "授课日期", "上课时间", "授课时间"],
    "lesson_meta.course_type": ["课型", "课程类型", "授课类型", "课程性质"],
    "lesson_meta.semester": ["学期", "开课学期", "学年学期"],
    "lesson_meta.college": ["学院", "院系", "学院（部）", "所属学院"],
    "lesson_meta.department": ["教研室", "系部", "教研室（系）", "系"],
    "lesson_meta.credits": ["学分", "课程学分"],
    "lesson_meta.total_hours": ["总学时", "课程总学时"],
    "lesson_meta.weekly_hours": ["周学时", "课程周学时"],
    "student_analysis": ["学情分析", "学习者分析", "学生情况分析", "学情"],
    "key_points": ["教学重点", "重点", "教学重点分析"],
    "difficult_points": ["教学难点", "难点", "教学难点分析"],
    "methods": ["教学方法", "教学手段", "教学方法与手段"],
    "resources": ["教学资源", "教学准备", "教学条件", "教学媒体"],
    "references": ["参考文献", "参考资料", "参考书目"],
    "objectives_compact": ["教学目标", "教学目的", "教学目的及要求", "学习目标"],
    "objectives.knowledge": ["知识目标"],
    "objectives.ability": ["能力目标"],
    "objectives.quality": ["素质目标", "素养目标", "思政目标"],
    "reflection.effect": ["教学效果", "教学效果分析", "效果"],
    "reflection.diagnosis": ["教学诊断", "问题分析", "诊断"],
    "reflection.improvement": ["教学改进", "改进措施", "改进"],
}

HEADER_SYNONYMS = {
    "content": ["教学内容", "教学内容与方法", "教学过程", "教学活动", "活动内容", "主要内容"],
    "student_activity": ["学生活动", "学生任务", "学生的活动", "学生行为"],
    "teacher_activity": ["教师活动", "教师指导", "教师行为", "教的活动"],
    "design_intent": ["设计意图", "设计说明", "设计思路", "设计依据", "意图"],
    "stage": ["教学环节", "环节", "步骤", "教学步骤"],
    "duration": ["时间", "时长", "分钟", "时间分配", "用时"],
    "knowledge_refs": ["知识点", "对应知识点", "关联知识点"],
}

FOOTER_HINTS = ["备注", "说明", "注释", "合计", "总计", "注："]


def normalize(text):
    return re.sub(r"[\s：:（）()【】\[\]。.．、,，;；“”\"'—_]+", "", str(text or ""))


_NUMBER_PREFIX = re.compile(
    r"^\s*(?:第[一二三四五六七八九十百\d]+[章节部分讲]|[一二三四五六七八九十百]+[、.．)）]|\d+[、.．)）]|\d+\s+)")


def lookup_label(text, index):
    """Match a label even when the school prefixes it with 一、/1. 之类序号。"""
    value = normalize(text)
    if value in index:
        return index[value]
    stripped = _NUMBER_PREFIX.sub("", str(text or "").strip())
    return index.get(normalize(stripped))


def _looks_like_heading(text):
    raw = str(text or "").strip()
    if not raw:
        return False
    return bool(_NUMBER_PREFIX.match(raw)) or len(raw) <= 12 and raw.endswith(("分析", "目标", "过程", "反思", "难点", "方法"))


def _label_index():
    index = {}
    for key, labels in LABEL_SYNONYMS.items():
        for label in labels:
            index.setdefault(normalize(label), key)
    return index


def _header_index():
    index = {}
    for key, labels in HEADER_SYNONYMS.items():
        for label in labels:
            index.setdefault(normalize(label), key)
    return index


def _cell_signature(cell):
    return cell._tc


def _body_children(document):
    return list(document.element.body.iterchildren())


def _table_header_signature(table):
    try:
        row = table.rows[0]
    except IndexError:
        return ()
    return tuple(normalize(c.text) for c in row.cells)


def _columns_from_header(table):
    headers = _header_index()
    columns, seen = {}, set()
    for index, cell in enumerate(table.rows[0].cells):
        if cell._tc in seen:
            continue
        seen.add(cell._tc)
        key = headers.get(normalize(cell.text))
        if key and key not in columns:
            columns[key] = index
    return columns


def collect_units(document):
    """Find repeated "heading paragraph + table" units.

    Many school and teacher documents put one small table under each stage
    heading instead of one long table. That pattern cannot be handled by row
    cloning, so it gets its own mode.
    """
    children = _body_children(document)
    units = []
    index = 0
    while index < len(children):
        element = children[index]
        if element.tag == qn("w:p") and _text_of(element).strip():
            nxt = index + 1
            while (nxt < len(children) and children[nxt].tag == qn("w:p")
                   and not _text_of(children[nxt]).strip()):
                nxt += 1
            if nxt < len(children) and children[nxt].tag == qn("w:tbl"):
                table = Table(children[nxt], document._body)
                columns = _columns_from_header(table)
                if len([k for k in columns if k in DIMENSIONS]) >= 2:
                    units.append({
                        "heading": element, "table": children[nxt], "table_obj": table,
                        "columns": columns, "signature": _table_header_signature(table),
                        "start": index, "end": nxt,
                    })
                    index = nxt + 1
                    continue
        index += 1
    return units


_NUMBERED_LINE = re.compile(r"^\s*(?:\d+[.、．)）]|（\d+）|\(\d+\))")


def numbered_ranges(document):
    """Find consecutive numbered paragraphs, merging adjacent groups.

    Objective lists in real lesson plans are plain numbered paragraphs, often
    with no group label. Replacing only the first line would leave stale
    duplicates behind, so the whole contiguous range is treated as one field.
    """
    paragraphs = document.paragraphs
    ranges = []
    index = 0
    while index < len(paragraphs):
        if _NUMBERED_LINE.match(paragraphs[index].text.strip()):
            end = index
            while end + 1 < len(paragraphs) and _NUMBERED_LINE.match(paragraphs[end + 1].text.strip()):
                end += 1
            if ranges and ranges[-1][1] + 1 == index:
                ranges[-1] = (ranges[-1][0], end)
            else:
                ranges.append((index, end))
            index = end + 1
        else:
            index += 1
    return ranges


def _unit_heading_template(text):
    """Turn a sample heading into a template the teacher can edit."""
    left, sep, right = text.partition("（")
    suffix = "（知识点：{refs}）" if "知识点" in right else ""
    if "·" in left:
        return left[:left.rfind("·") + 1] + "{stage}" + suffix
    return "{stage}" + suffix


def _format_unit_heading(template, item, index):
    values = {
        "stage": str(item.get("stage") or item.get("_label") or ""),
        "refs": "、".join(item.get("knowledge_refs") or []) or "—",
        "duration": _trim_number(item.get("duration_minutes") or ""),
        "index": str(index),
    }
    text = str(template)
    for key, value in values.items():
        text = text.replace("{%s}" % key, value)
    if not item.get("knowledge_refs"):
        text = text.replace("（知识点：—）", "").replace("(知识点：—)", "")
    return text


def unit_items(source, data, spec):
    flow = data.get("flow", {}) or {}
    if source in ["flow", "in_class"]:
        items = []
        if source == "flow":
            pre_class = flow.get("pre_class") or {}
            if pre_class:
                items.append(dict(pre_class, _label=spec.get("pre_label", "课前")))
        for stage in flow.get("in_class") or []:
            items.append(dict(stage))
        if source == "flow":
            post_class = flow.get("post_class") or {}
            if post_class:
                items.append(dict(post_class, _label=spec.get("post_label", "课后")))
        return items
    raise LessonInputError("units 模式的 source 只支持 flow 或 in_class")


def render_units(document, data, spec, source):
    """Pair, clone or trim whole heading+table units, then fill each one."""
    items = unit_items(spec.get("source", "flow"), data, spec)
    if not items:
        raise LessonInputError("blocks.%s 没有可渲染的内容" % source)
    units = collect_units(document)
    signature = spec.get("signature")
    if signature:
        units = [u for u in units if list(u["signature"]) == list(signature)]
    if not units:
        raise LessonInputError(
            "blocks.%s 声明为 units 模式，但样本中没有找到「环节标题 + 表格」结构的单元" % source)
    columns = spec.get("columns") or units[0]["columns"]
    template = spec.get("heading_template") or _unit_heading_template(_text_of(units[0]["heading"]))
    children = _body_children(document)

    removed = 0
    for unit in units[len(items):]:
        for element in children[unit["start"]:unit["end"] + 1]:
            if element.getparent() is not None:
                element.getparent().remove(element)
        removed += 1
    keep = [{"heading": u["heading"], "table": u["table"],
             "elements": children[u["start"]:u["end"] + 1],
             "columns": u["columns"]} for u in units[:len(items)]]

    cloned = 0
    while len(keep) < len(items):
        last = keep[-1]
        anchor = last["elements"][-1]
        new_elements = []
        for element in last["elements"]:
            new_element = copy.deepcopy(element)
            anchor.addnext(new_element)
            anchor = new_element
            new_elements.append(new_element)
        cloned += 1
        keep.append({"heading": new_elements[0], "table": new_elements[-1],
                     "elements": new_elements, "columns": columns})

    for index, (unit, item) in enumerate(zip(keep, items), 1):
        heading = Paragraph(unit["heading"], document._body)
        write_paragraph(heading, _format_unit_heading(template, item, index))
        table = Table(unit["table"], document._body)
        row = table.rows[1] if len(table.rows) > 1 else table.rows[0]
        for column_key, col_index in columns.items():
            if column_key not in COLUMN_KEYS:
                raise LessonInputError("blocks.%s 的列键 '%s' 不支持" % (source, column_key))
            col_index = int(col_index)
            if col_index < len(row.cells):
                write_cell(row.cells[col_index], block_cell_text(item, column_key, index))
    return {"units": len(keep), "cloned": cloned, "removed": removed}


def _table_directly_follows(paragraph):
    """True when the very next block after this paragraph is a table."""
    element = paragraph._p.getnext()
    return element is not None and element.tag == qn("w:tbl")


def _text_of(element):
    return "".join(node.text or "" for node in element.iter(qn("w:t")))


def _table_before_next_text(paragraph):
    """True when the next block after a blank paragraph is a table, not prose."""
    element = paragraph._p.getnext()
    while element is not None:
        if element.tag == qn("w:tbl"):
            return True
        if element.tag == qn("w:p") and _text_of(element).strip():
            return False
        element = element.getnext()
    return False


def analyze_sample(template_path):
    """Return a structural report plus a best-effort map for the sample."""
    if not os.path.isfile(template_path):
        raise LessonInputError("找不到样本 DOCX：%s" % template_path)
    document = Document(template_path)
    report = {
        "template": os.path.basename(template_path),
        "paragraphs": len(document.paragraphs),
        "tables": len(document.tables),
        "sections": len(document.sections),
        "table_shapes": [],
        "candidates": [],
        "ambiguous": [],
    }
    for index, table in enumerate(document.tables):
        header = [normalize(c.text) for c in table.rows[0].cells] if table.rows else []
        report["table_shapes"].append({
            "table": index, "rows": len(table.rows), "cols": len(table.columns),
            "header": header,
        })

    labels = _label_index()
    headers = _header_index()
    fields, blocks = {}, {}

    # 0. 先看是否存在「环节标题 + 独立小表」重复出现的单元结构。
    #    这种结构不能用“一张表多行”处理，必须整体配对、克隆或裁剪。
    detected_units = collect_units(document)
    unit_tables = set()
    if len(detected_units) >= 2:
        signature, count = Counter(u["signature"] for u in detected_units).most_common(1)[0]
        if count >= 2:
            same = [u for u in detected_units if u["signature"] == signature]
            unit_tables = {id(u["table"]) for u in same}
            rich = next((u for u in same if "知识点" in _text_of(u["heading"])), same[0])
            blocks["in_class"] = {
                "mode": "units",
                "source": "flow",
                "columns": same[0]["columns"],
                "heading_template": _unit_heading_template(_text_of(rich["heading"])),
                "signature": list(signature),
                "unit_count": len(same),
            }
            report["candidates"].append({
                "kind": "block", "target": "in_class", "mode": "units",
                "table": None, "template_row": None, "last_row": None,
                "columns": same[0]["columns"], "confidence": "high",
                "units": len(same),
                "heading_template": blocks["in_class"]["heading_template"],
            })

    # 1. Header-row tables become repeatable blocks.
    for table_index, table in enumerate(document.tables):
        if len(table.rows) < 2:
            continue
        if id(table._tbl) in unit_tables:
            continue
        found = None
        for row_index in range(min(3, len(table.rows))):
            row = table.rows[row_index]
            columns = {}
            for col_index, cell in enumerate(row.cells):
                key = headers.get(normalize(cell.text))
                if key and key not in columns and _cell_signature(cell) not in [row.cells[c]._tc for c in columns.values()]:
                    columns[key] = col_index
            dimensions = [k for k in columns if k in DIMENSIONS + ["stage", "duration", "knowledge_refs"]]
            if len(columns) >= 2 and dimensions:
                found = (row_index, columns)
                break
        if not found:
            continue
        header_row, columns = found
        if header_row + 1 >= len(table.rows):
            continue
        last_row = len(table.rows) - 1
        for row_index in range(header_row + 1, len(table.rows)):
            first_cell = normalize(table.rows[row_index].cells[0].text)
            if any(hint in first_cell for hint in FOOTER_HINTS):
                last_row = row_index - 1
                break
        if last_row <= header_row:
            last_row = header_row + 1
        source = "in_class"
        if "stage" not in columns and "content" not in columns and "index" not in columns:
            continue
        if "stage" in columns:
            columns["stage_with_duration"] = columns.pop("stage")
        header_row_element = table.rows[header_row]._tr
        repeat_header = header_row_element.find(qn("w:trPr")) is not None and \
            header_row_element.find(qn("w:trPr")).find(qn("w:tblHeader")) is not None
        blocks[source] = {
            "table": table_index,
            "template_row": header_row + 1,
            "last_row": last_row,
            "columns": columns,
            "source": source,
        }
        report["candidates"].append({
            "kind": "block", "target": source, "table": table_index,
            "template_row": header_row + 1, "last_row": last_row,
            "columns": columns, "confidence": "high",
            "repeat_header": repeat_header,
        })

    # 2. Label/value pairs inside tables.
    used_cells = set()
    for table_index, table in enumerate(document.tables):
        for row_index, row in enumerate(table.rows):
            for col_index, cell in enumerate(row.cells):
                text = cell.text
                key = lookup_label(text, labels)
                if not key or cell._tc in used_cells:
                    continue
                if key.startswith("objectives.") or key in ["objectives_compact"]:
                    used_cells.add(cell._tc)
                    # 目标类字段既可能是"标签格 + 右侧值格"，也可能是整格双行；
                    # 有右侧独立格时一律写到值格，避免覆盖学校模板里的标签文字。
                    target = {"kind": "cell", "table": table_index,
                              "row": row_index, "col": col_index}
                    if (col_index + 1 < len(row.cells)
                            and row.cells[col_index + 1]._tc is not cell._tc):
                        target = {"kind": "cell", "table": table_index,
                                  "row": row_index, "col": col_index + 1}
                    fields[key] = target
                    report["candidates"].append({"kind": "field", "target": key,
                                                 "where": "表%d[%d][%d]" % (table_index, row_index, target["col"]),
                                                 "confidence": "high"})
                    continue
                value_address, value_cell = None, None
                if col_index + 1 < len(row.cells) and row.cells[col_index + 1]._tc is not cell._tc:
                    value_address = {"kind": "cell", "table": table_index,
                                     "row": row_index, "col": col_index + 1}
                    value_cell = row.cells[col_index + 1]
                elif row_index + 1 < len(table.rows) and table.rows[row_index + 1].cells[col_index]._tc is not cell._tc:
                    value_address = {"kind": "cell", "table": table_index,
                                     "row": row_index + 1, "col": col_index}
                    value_cell = table.rows[row_index + 1].cells[col_index]
                if value_address is None:
                    continue
                fields[key] = value_address
                # 右侧格子是空的，说明它就是学校留出的待填位，可信度最高
                blank = value_cell is not None and not value_cell.text.strip()
                report["candidates"].append({
                    "kind": "field", "target": key,
                    "where": "表%d[%d][%d]" % (value_address["table"], value_address["row"], value_address["col"]),
                    "confidence": "high" if blank else "medium",
                    "needs_confirmation": not blank,
                })

    # 2b. 编号段落列表：教学目标常写成不带标签的编号段落。
    for start, end in numbered_ranges(document):
        if end <= start:
            continue
        if start > 0:
            group = lookup_label(document.paragraphs[start - 1].text, labels)
        else:
            group = None
        key = group if group in ["objectives.knowledge", "objectives.ability",
                                 "objectives.quality"] else "objectives.all"
        if key in fields:
            continue
        fields[key] = {"kind": "paragraph_range", "start": start, "end": end}
        report["candidates"].append({
            "kind": "field", "target": key,
            "where": "段落 %d–%d（编号列表）" % (start, end),
            "confidence": "medium", "needs_confirmation": True,
        })

    # 3. Body paragraphs acting as label lines: the next paragraph is the blank
    #    the teacher is expected to fill, so an empty one is the best candidate.
    paragraphs = document.paragraphs
    for index, paragraph in enumerate(paragraphs):
        key = lookup_label(paragraph.text, labels)
        if not key or key in fields:
            continue
        candidate = index + 1
        if candidate >= len(paragraphs):
            continue
        if _table_directly_follows(paragraph):
            # 标题下面紧跟表格：内容在表里，不应再往段落里写字
            continue
        following = paragraphs[candidate].text
        if following.strip() and _looks_like_heading(following):
            continue
        if not following.strip() and _table_before_next_text(paragraphs[candidate]):
            # 空段落后面是表格而不是正文：这只是排版留白
            continue
        fields[key] = {"kind": "paragraph", "index": candidate}
        report["candidates"].append({"kind": "field", "target": key,
                                     "where": "段落%d" % candidate,
                                     "confidence": "medium",
                                     "needs_confirmation": True})

    # Anything a school template usually has but we could not locate.
    expected = ["lesson_meta.course_name", "lesson_meta.title", "lesson_meta.week",
                "lesson_meta.hours", "lesson_meta.class_name", "lesson_meta.teacher",
                "objectives.knowledge", "objectives.ability", "objectives.quality"]
    merged_objectives = "objectives.all" in fields or "objectives_compact" in fields
    report["ambiguous"] = [
        key for key in expected
        if key not in fields and not (merged_objectives and key.startswith("objectives."))
    ]

    mapping = {
        "template_version": MAP_VERSION,
        "template_file": os.path.basename(template_path),
        "generated_by": "analyze_template.py（自动推断，需教师确认一次）",
        "confirmed": False,
        "fields": fields,
        "blocks": blocks,
    }
    return mapping, report


def map_report_markdown(mapping, report):
    lines = ["# 模板映射报告：%s" % report["template"], ""]
    lines.append("样本包含 %d 个段落、%d 个表格、%d 个节。以下映射由脚本自动推断，"
                 "首次使用前请教师核对一次，之后同校同模板可长期复用。"
                 % (report["paragraphs"], report["tables"], report["sections"]))
    lines.append("")
    lines.append("## 已识别字段")
    lines.append("")
    lines.append("| 内容字段 | 位置 | 状态 |")
    lines.append("|---|---|---|")
    for item in report["candidates"]:
        if item["kind"] != "field":
            continue
        status = "需确认" if item.get("needs_confirmation") else "可直接使用"
        lines.append("| `%s` | %s | %s |" % (item["target"], item["where"], status))
    if not [x for x in report["candidates"] if x["kind"] == "field"]:
        lines.append("| — | 未识别到字段 | 需手工补充 |")
    lines.append("")
    lines.append("## 已识别重复区块")
    lines.append("")
    lines.append("| 区块 | 表格 | 模板行 | 填充行范围 | 列映射 |")
    lines.append("|---|---|---|---|---|")
    for item in report["candidates"]:
        if item["kind"] != "block":
            continue
        columns = "，".join("%s→第%d列" % (k, v) for k, v in item["columns"].items())
        if item.get("mode") == "units":
            lines.append("| `%s`（单元模式，样本 %d 组） | 标题段+独立小表 | — | — | %s |"
                         % (item["target"], item.get("units", 0), columns))
            continue
        lines.append("| `%s` | 表%d | 第%d行 | 第%d–%d行 | %s |"
                     % (item["target"], item["table"], item["template_row"],
                        item["template_row"], item["last_row"], columns))
    if not [x for x in report["candidates"] if x["kind"] == "block"]:
        lines.append("| — | 未识别到课中环节表 | 需手工补充 |")
    lines.append("")
    no_repeat = [x for x in report["candidates"] if x["kind"] == "block" and not x.get("repeat_header")]
    if no_repeat:
        report.setdefault("notes", []).append(
            "样本的环节表未设置“跨页重复标题行”；表格跨页时表头不会自动重复，如需该效果请在 Word 中设置后重新解析。")
    for note in report.get("notes", []):
        lines.append("> %s" % note)
        lines.append("")
    if report["ambiguous"]:
        lines.append("## 需要人工补充")
        lines.append("")
        for key in report["ambiguous"]:
            lines.append("- `%s`：样本中未找到可对应位置" % key)
        lines.append("")
    lines.append("## 下一步")
    lines.append("")
    lines.append("1. 打开 `template-map.json`，把确认为错误的地址改掉；")
    lines.append("2. 把顶层 `confirmed` 改为 `true`；")
    lines.append("3. 重新执行生成命令。")
    return "\n".join(lines) + "\n"
