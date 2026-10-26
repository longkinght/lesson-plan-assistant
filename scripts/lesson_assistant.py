# -*- coding: utf-8 -*-
"""Lesson Plan Assistant v2: validate once, render atomically, deliver three files.

© 2026 黄彬 (Huang Bin) · MIT License
"""
import argparse
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    LessonInputError, load_lesson, print_report, safe_file_stem, validate_lesson,
)
import build_graph  # noqa: E402
import render_html  # noqa: E402
import build_lesson_docx  # noqa: E402

VERSION = "2.2.4"


def run(args):
    try:
        data = load_lesson(args.json)
    except LessonInputError as exc:
        print("输入错误：%s" % exc)
        return 2
    print("步骤 1/4 · 数据契约与备课质量校验")
    errors, warnings = validate_lesson(data)
    if not print_report(errors, warnings):
        print("校验未通过，未生成或覆盖任何正式产物。请根据字段路径修复 lesson.json。")
        return 1
    if args.verify_only:
        return 0

    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    stem = safe_file_stem(data["lesson_meta"])
    filenames = {
        "md": stem + "_知识图谱.md",
        "html": stem + "_知识图谱.html",
        "docx": stem + "_教案.docx",
    }
    try:
        with tempfile.TemporaryDirectory(prefix=".lesson-build-", dir=output_dir) as temp_dir:
            paths = {key: os.path.join(temp_dir, name) for key, name in filenames.items()}
            print("\n步骤 2/4 · 生成 Markdown 知识图谱")
            if build_graph.main_inner(args.json, paths["md"]) != 0:
                return 1
            print("\n步骤 3/4 · 渲染离线 HTML 信息图")
            if render_html.main_inner(args.json, paths["html"]) != 0:
                return 1
            print("\n步骤 4/4 · 生成 DOCX 教案")
            if build_lesson_docx.main_inner(args.json, paths["docx"], args.style, args.style_config,
                                            args.template, args.template_map) != 0:
                return 1
            for path in paths.values():
                os.replace(path, os.path.join(output_dir, os.path.basename(path)))
    except (LessonInputError, OSError, ValueError) as exc:
        print("生成失败：%s" % exc)
        print("正式产物未被部分更新；请修复后重试。")
        return 2

    print("\n" + "=" * 60)
    print("三件套已生成。内容仍需授课教师进行事实与教学适用性审核：")
    for key in ["docx", "md", "html"]:
        print("  %s" % os.path.join(output_dir, filenames[key]))
    print("=" * 60)
    return 0


def main():
    parser = argparse.ArgumentParser(description="备课知识图谱助手 v2 · 一键生成教案与知识图谱")
    parser.add_argument("--json", required=True, help="lesson.json 路径")
    parser.add_argument("--output-dir", required=True, help="产物输出目录")
    parser.add_argument("--style", default="standard", help="standard、chapter 或旧版别名 teacher-zhang")
    parser.add_argument("--style-config", help="自定义章节风格 JSON；提供后自动使用 chapter 渲染器")
    parser.add_argument("--template", help="学校/教师提供的样本 DOCX；提供后严格按样本格式填充，忽略 --style")
    parser.add_argument("--template-map", help="已确认的模板映射 JSON；缺省则自动推断并在输出目录留档")
    parser.add_argument("--verify-only", action="store_true", help="只校验，不生成文件")
    parser.add_argument("--version", action="version", version=VERSION)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
