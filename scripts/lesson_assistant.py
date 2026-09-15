# -*- coding: utf-8 -*-
"""备课知识图谱助手 · 主入口（一键三件套）
用法:
  python lesson_assistant.py --json lesson.json --output-dir 输出目录
流程: 硬校验 → Markdown 图谱 → HTML 信息图 → 标准教案 docx
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_lesson, validate_lesson, print_report  # noqa: E402
import build_graph  # noqa: E402
import render_html  # noqa: E402
import build_lesson_docx  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="备课知识图谱助手 · 一键三件套")
    parser.add_argument("--json", required=True, help="lesson.json 路径")
    parser.add_argument("--output-dir", required=True, help="产物输出目录")
    parser.add_argument("--style", default="standard",
                        help="教案风格：standard（默认）或 teacher-zhang（教师风格档案）")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    data = load_lesson(args.json)

    # 1. 硬校验（红线）
    print("步骤 1/4 · 硬校验…")
    errors, warnings = validate_lesson(data)
    ok = print_report(errors, warnings)
    if not ok:
        print("❌ 一致性红线未通过，已阻止交付。请修复 lesson.json 后重试。")
        return 1

    meta = data["lesson_meta"]
    week = meta.get("week", "")
    if "周" in week:
        base = os.path.join(args.output_dir, f"第{re.sub(r'\D', '', week)}周")
    else:
        base = os.path.join(args.output_dir, week if week else "课程")

    # 2. Markdown 图谱
    print("\n步骤 2/4 · 生成 Markdown 知识图谱…")
    md_path = base + "_知识图谱.md"
    if build_graph.main_inner(args.json, md_path) != 0:
        return 1

    # 3. HTML 信息图
    print("\n步骤 3/4 · 渲染 HTML 信息图…")
    html_path = base + "_知识图谱.html"
    if render_html.main_inner(args.json, html_path) != 0:
        return 1

    # 4. 教案 docx
    print("\n步骤 4/4 · 生成教案…")
    docx_path = base + "_教案.docx"
    if build_lesson_docx.main_inner(args.json, docx_path, args.style) != 0:
        return 1

    print("\n" + "=" * 56)
    print("✅ 三件套交付完成（同源同构）:")
    print(f"   教案:  {docx_path}")
    print(f"   图谱:  {md_path}")
    print(f"   信息图: {html_path}")
    print("=" * 56)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
