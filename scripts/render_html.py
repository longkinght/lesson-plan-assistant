# -*- coding: utf-8 -*-
"""HTML 信息图渲染器：lesson.json + templates/knowledge-graph.html → 第X周_知识图谱.html
单文件、内联样式、零外部依赖，可离线打开；亦可无头浏览器截图导出 PNG。
用法: python render_html.py --json lesson.json --output 第X周_知识图谱.html [--template 模板路径]
"""
import argparse
import json
import os
from common import load_lesson, build_tree, generate_post_relations, validate_lesson

TEMPLATE_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "templates", "knowledge-graph.html")


def main_inner(json_path, output_path, template=None):
    if template is None:
        template = TEMPLATE_DEFAULT
    data = load_lesson(json_path)
    errors, _ = validate_lesson(data)
    if errors:
        print("❌ 校验未通过，拒绝渲染。请先修复:")
        for e in errors:
            print(f"   - {e}")
        return 1

    nodes = data["knowledge_tree"]
    generate_post_relations(nodes)
    # 注意：此处不调用 build_tree —— 树由前端 JS 独立构建。
    # 若在 Python 侧挂 children 会随 JSON 序列化进 HTML，导致前端二次挂载、节点重复。

    with open(template, "r", encoding="utf-8") as f:
        template_content = f.read()

    # JSON 内嵌安全处理：防止 "</script>" 序列破坏页面
    payload = json.dumps(data, ensure_ascii=False, indent=1).replace("</", "<\\/")
    html = template_content.replace("{{JSON}}", payload)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ HTML 信息图已生成: {output_path}（{len(nodes)} 个节点，单文件离线可用）")
    return 0


def main():
    parser = argparse.ArgumentParser(description="HTML 知识图谱信息图渲染器")
    parser.add_argument("--json", required=True, help="lesson.json 路径")
    parser.add_argument("--output", required=True, help="输出 .html 路径")
    parser.add_argument("--template", default=TEMPLATE_DEFAULT, help="信息图模板路径")
    args = parser.parse_args()
    return main_inner(args.json, args.output, args.template)


if __name__ == "__main__":
    raise SystemExit(main())
