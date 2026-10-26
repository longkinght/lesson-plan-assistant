# -*- coding: utf-8 -*-
"""Render a single-file, offline HTML course knowledge dashboard."""
import argparse
import json
import os

from common import LessonInputError, generate_post_relations, load_lesson, validate_lesson

TEMPLATE_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "templates", "knowledge-graph.html")


def main_inner(json_path, output_path, template=None):
    template = template or TEMPLATE_DEFAULT
    data = load_lesson(json_path)
    errors, _ = validate_lesson(data)
    if errors:
        print("校验未通过，拒绝渲染 HTML：")
        for item in errors:
            print("  - %s" % item)
        return 1
    generate_post_relations(data["knowledge_tree"])
    try:
        with open(template, "r", encoding="utf-8") as f:
            template_content = f.read()
    except OSError as exc:
        raise ValueError("无法读取 HTML 模板：%s" % exc)
    if "{{JSON}}" not in template_content:
        raise ValueError("HTML 模板缺少 {{JSON}} 数据占位符")
    payload = json.dumps(data, ensure_ascii=False, indent=1).replace("</", "<\\/")
    html = template_content.replace("{{JSON}}", payload)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML 已生成：%s（%d 个节点，单文件离线可用）" % (output_path, len(data["knowledge_tree"])))
    return 0


def main():
    parser = argparse.ArgumentParser(description="离线 HTML 知识图谱渲染器")
    parser.add_argument("--json", required=True, help="lesson.json 路径")
    parser.add_argument("--output", required=True, help="输出 .html 路径")
    parser.add_argument("--template", default=TEMPLATE_DEFAULT, help="信息图模板路径")
    args = parser.parse_args()
    try:
        return main_inner(args.json, args.output, args.template)
    except (LessonInputError, ValueError, OSError) as exc:
        print("生成失败：%s" % exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
