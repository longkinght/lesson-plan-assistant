# -*- coding: utf-8 -*-
"""教案 docx 生成器：lesson.json → 教案.docx
支持两种风格：
  --style standard      内置标准教案结构（七章节/五环节四维）
  --style teacher-zhang 教师风格档案驱动（封面+章节字段，见 references/teacher-style.json）
依赖: python-docx（pip install python-docx）
用法: python build_lesson_docx.py --json lesson.json --output 教案.docx [--style standard]
"""
import argparse
import json
import os
import re
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from common import load_lesson, build_tree, generate_post_relations, validate_lesson

HEAD_FONT = "黑体"
BODY_FONT = "宋体"
ACCENT = RGBColor(0x0E, 0x74, 0x90)

STYLE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "references", "teacher-style.json")


def load_style(style):
    if style == "teacher-zhang":
        with open(STYLE_DIR, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def set_run(run, font=BODY_FONT, size=12, bold=False, color=None):
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font)


def add_para(doc, text, font=BODY_FONT, size=12, bold=False, align=None, color=None, space_after=6):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    run = p.add_run(text)
    set_run(run, font, size, bold, color)
    return p


def add_heading(doc, text, size=14):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    set_run(run, HEAD_FONT, size, True, ACCENT)
    return p


def add_kv_table(doc, rows, col_widths=(Cm(3.2), Cm(6.3))):
    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for k, v in rows:
        cells = table.add_row().cells
        run = cells[0].paragraphs[0].add_run(k)
        set_run(run, HEAD_FONT, 11, True)
        cells[0].width = col_widths[0]
        run2 = cells[1].paragraphs[0].add_run("" if v is None else str(v))
        set_run(run2, BODY_FONT, 11)
        cells[1].width = col_widths[1]
    return table


def add_stage_table(doc, stage):
    headers = ["教学内容", "学生活动", "教师活动", "设计意图"]
    dims = ["content", "student_activity", "teacher_activity", "design_intent"]
    stage_name = stage.get("stage", "")
    refs = stage.get("knowledge_refs", []) or []
    title = f"环节·{stage_name}"
    if refs:
        title += f"　（知识点：{'、'.join(refs)}）"
    add_para(doc, title, HEAD_FONT, 11.5, True, color=ACCENT, space_after=3)
    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    widths = (Cm(4.6), Cm(3.6), Cm(3.6), Cm(3.6))
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.width = widths[i]
        run = cell.paragraphs[0].add_run(h)
        set_run(run, HEAD_FONT, 10.5, True)
        shd = cell._element.get_or_add_tcPr()
        el = OxmlElement("w:shd")
        el.set(qn("w:val"), "clear")
        el.set(qn("w:fill"), "CCFBF1")
        shd.append(el)
    row = table.add_row()
    for i, dim in enumerate(dims):
        cell = row.cells[i]
        cell.width = widths[i]
        run = cell.paragraphs[0].add_run("" if stage.get(dim) is None else str(stage.get(dim)))
        set_run(run, BODY_FONT, 10.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def render_teacher_style(doc, data, style, meta):
    """教师风格渲染：封面 + 章节字段（对应 teacher-style.json）"""
    cover = style.get("cover", {})
    chapter = style.get("chapter", {})
    defaults = chapter.get("defaults", {})
    objectives = data.get("objectives", {})

    # 封面
    title = cover.get("title_template", "{course_name}教案").replace(
        "{course_name}", meta.get("course_name", "课程"))
    add_para(doc, title, HEAD_FONT, 16, True, WD_ALIGN_PARAGRAPH.CENTER,
             color=RGBColor(0x15, 0x5E, 0x75), space_after=8)
    add_para(doc, cover.get("semester", ""), HEAD_FONT, 12, True,
             WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    cover_rows = []
    for f in cover.get("fields", []):
        key = f.get("value", "")
        m = re.match(r"\{(\w+)\}", key)
        if m:
            val = meta.get(m.group(1), "")
            if not val:
                val = f.get("fallback", "")
        else:
            val = key
        cover_rows.append((f["label"], val))
    add_kv_table(doc, cover_rows)
    note = cover.get("note", "")
    if note:
        add_para(doc, note, BODY_FONT, 9, color=RGBColor(0x6B, 0x72, 0x80), space_after=10)

    # 章节头
    ch_num = meta.get("chapter_num", "")
    if not ch_num:
        m = re.search(r"\d+", meta.get("week", ""))
        ch_num = m.group(0) if m else "1"
    add_heading(doc, f"{chapter.get('head_template', '第{chapter_num}章').replace('{chapter_num}', str(ch_num))}"
                f"{' ' + meta.get('title', '')}".rstrip(), 15)

    # 字段区：字段名 + 内容（字段名加粗占行，内容跟随）
    def field_block(field, text, size=12):
        add_para(doc, field, HEAD_FONT, 12, True, color=ACCENT, space_after=2)
        if isinstance(text, list):
            for it in text:
                add_para(doc, str(it), BODY_FONT, size, space_after=2)
        else:
            add_para(doc, str(text), BODY_FONT, size, space_after=4)

    field_order = chapter.get("field_order", [])
    for field in field_order:
        if field == "课时":
            field_block(field, str(meta.get("hours", "")))
        elif field == "教学方法":
            methods = data.get("methods", []) or []
            text = "  ".join(
                ("■" if any(k in "".join(methods) for k in m.split("/")) else "□") + m
                for m in ["讲授法", "讨论法", "案例教学", "参与式教学", "其他"])
            field_block(field, text)
        elif field == "教学目的及要求":
            k_list = objectives.get("knowledge", []) + objectives.get("ability", [])
            q_list = objectives.get("quality", [])
            purpose = "目的：" + "；".join(k_list) + "。"
            require = "要求：" + "；".join(q_list) + "。"
            field_block(field, [purpose, require])
        elif field == "教学环境":
            env = (data.get("resources") or [None])[0] or defaults.get("教学环境", "多媒体机房")
            field_block(field, env)
        elif field == "重点":
            field_block(field, "重点：" + "、".join(data.get("key_points", []) or []))
        elif field == "难点":
            field_block(field, "难点：" + "、".join(data.get("difficult_points", []) or []))
        elif field == "讲授内容":
            cn_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
            lines = []
            for idx, st in enumerate(data.get("flow", {}).get("in_class", []), 1):
                content = st.get("content", "")
                sec = re.search(r"第([一二三四五六七八九十\d]+)节\s*([^（；;\n]+)", content)
                if sec:
                    lines.append(f"第{sec.group(1)}节 {sec.group(2).strip()}")
                else:
                    cn = "一二三四五六七八九十"[idx - 1] if idx <= 10 else str(idx)
                    lines.append(f"第{cn}节 {st.get('stage', '')}")
                items = [s.strip() for s in re.split(r"[；;\n]", content) if s.strip()]
                items = [it for it in items if not re.match(r"^第[一二三四五六七八九十\d]+节", it)]
                auto_n = 1
                for it in items:
                    if re.match(r"^\d+[\.、]", it):
                        lines.append(it)
                    else:
                        lines.append(f"{auto_n}. {it}")
                        auto_n += 1
                sa = st.get("student_activity", "")
                if sa:
                    lines.append(f"（学生活动：{sa}）")
            field_block(field, lines)
        elif field == "思考题和作业":
            post = data.get("flow", {}).get("post_class", {})
            hw = post.get("content", "")
            hw = re.sub(r"^(思考题和作业|作业)[：:]?", "", hw).strip()
            sa = post.get("student_activity", "")
            lines = [hw] if hw else []
            if sa:
                lines.append(f"（学生课后活动：{sa}）")
            field_block(field, lines or "（待补）")
        elif field == "参考文献":
            refs = data.get("references", []) or []
            field_block(field, refs if refs else defaults.get("参考文献", ""))

    # 附加：教学反思（教师模板无此节，作为附加保留）
    refl = data.get("reflection", {})
    if refl.get("effect") or refl.get("diagnosis") or refl.get("improvement"):
        add_heading(doc, "教学反思（附加）", 13)
        field_block("教学效果", refl.get("effect", ""))
        field_block("诊断", refl.get("diagnosis", ""))
        field_block("改进", refl.get("improvement", ""))


def main_inner(json_path, output_path, style="standard"):
    data = load_lesson(json_path)
    errors, warnings = validate_lesson(data)
    if errors:
        print("❌ 校验未通过，拒绝生成教案。请先修复:")
        for e in errors:
            print(f"   - {e}")
        return 1

    nodes = data["knowledge_tree"]
    generate_post_relations(nodes)
    build_tree(nodes)

    meta = data["lesson_meta"]
    objectives = data["objectives"]
    flow = data["flow"]
    reflection = data["reflection"]

    doc = Document()
    # 页面设置 A4
    for section in doc.sections:
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(2.0)
        section.top_margin = Cm(2.2)
        section.bottom_margin = Cm(2.2)

    style_data = load_style(style)
    if style_data:
        render_teacher_style(doc, data, style_data, meta)
        doc.save(output_path)
        print(f"✅ 教师风格教案已生成（{style}）: {output_path}")
        return 0

    week_raw = meta.get("week", "")
    week_num = re.sub(r"\D", "", week_raw)
    if "周" in week_raw:
        title = f"第{week_num}周 教案" if week_num else "教案"
    else:
        title = f"{week_raw} 教案" if week_raw else "教案"
    add_para(doc, title, HEAD_FONT, 16, True, WD_ALIGN_PARAGRAPH.CENTER, color=RGBColor(0x15, 0x5E, 0x75), space_after=12)

    # 基本信息
    add_heading(doc, "一、基本信息")
    add_kv_table(doc, [
        ("课程名称", meta.get("course_name", "")),
        ("授课课题", meta.get("title", "")),
        ("周次", meta.get("week", "")),
        ("学时", meta.get("hours", "")),
        ("授课班级", meta.get("class_name", "")),
        ("授课教师", meta.get("teacher", "")),
        ("授课日期", meta.get("date", "")),
        ("课型", meta.get("course_type", "")),
    ])

    # 教学目标
    add_heading(doc, "二、教学目标")
    for label, items in (("知识目标", objectives.get("knowledge", [])),
                         ("能力目标", objectives.get("ability", [])),
                         ("素质目标", objectives.get("quality", []))):
        for i, it in enumerate(items, 1):
            add_para(doc, f"{i}. {it}", BODY_FONT, 12, space_after=2)

    # 学情分析 / 重难点 / 方法资源
    add_heading(doc, "三、学情分析")
    add_para(doc, data.get("student_analysis", "") or "（待补学情分析）")
    add_heading(doc, "四、教学重点与难点")
    add_kv_table(doc, [
        ("教学重点", "；".join(data.get("key_points", []) or [])),
        ("教学难点", "；".join(data.get("difficult_points", []) or [])),
    ])
    add_heading(doc, "五、教学方法与教学资源")
    add_kv_table(doc, [
        ("教学方法", "；".join(data.get("methods", []) or [])),
        ("教学资源", "；".join(data.get("resources", []) or [])),
    ])

    # 教学过程
    add_heading(doc, "六、教学过程")
    add_para(doc, "【课前】", HEAD_FONT, 11.5, True, color=ACCENT, space_after=3)
    pre = flow.get("pre_class", {})
    add_stage_table(doc, {"stage": "课前自主学习", "content": pre.get("content", ""),
                          "student_activity": pre.get("student_activity", ""),
                          "teacher_activity": pre.get("teacher_activity", ""),
                          "design_intent": pre.get("design_intent", "")})
    add_para(doc, "【课中】", HEAD_FONT, 11.5, True, color=ACCENT, space_after=3)
    for idx, stage in enumerate(flow.get("in_class", []), 1):
        add_stage_table(doc, stage)
    add_para(doc, "【课后】", HEAD_FONT, 11.5, True, color=ACCENT, space_after=3)
    post = flow.get("post_class", {})
    add_stage_table(doc, {"stage": "课后巩固拓展", "content": post.get("content", ""),
                          "student_activity": post.get("student_activity", ""),
                          "teacher_activity": post.get("teacher_activity", ""),
                          "design_intent": post.get("design_intent", "")})

    # 教学反思
    add_heading(doc, "七、教学反思")
    add_kv_table(doc, [
        ("教学效果", reflection.get("effect", "")),
        ("诊断", reflection.get("diagnosis", "")),
        ("改进", reflection.get("improvement", "")),
    ])

    doc.save(output_path)
    print(f"✅ 标准教案已生成: {output_path}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="教案 docx 生成器（standard / teacher-zhang）")
    parser.add_argument("--json", required=True, help="lesson.json 路径")
    parser.add_argument("--output", required=True, help="输出 .docx 路径")
    parser.add_argument("--style", default="standard",
                        help="教案风格：standard（默认）或 teacher-zhang（教师风格档案）")
    args = parser.parse_args()
    return main_inner(args.json, args.output, args.style)


if __name__ == "__main__":
    raise SystemExit(main())
