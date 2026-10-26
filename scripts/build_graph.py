# -*- coding: utf-8 -*-
"""Render a review-friendly Markdown knowledge asset from lesson.json."""
import argparse

from common import (
    LessonInputError, build_tree, generate_post_relations, load_lesson,
    objective_items, objective_refs, objective_text, validate_lesson,
)


def md(value):
    """Escape user content that would otherwise break Markdown tables."""
    return str(value if value is not None else "").replace("|", "\\|").replace("\r", " ").replace("\n", "<br>").strip()


def render_tree_md(node):
    lines = []
    indent = "  " * (node["level"] - 1)
    label = "**%s**" % md(node["name"])
    if node["node_type"] == "知识点":
        parts = [x for x in [node.get("cognitive", ""), node.get("category", ""), node.get("tags", "")] if x]
        if parts:
            label += " ` %s `" % " / ".join(md(x) for x in parts)
        if node.get("objective"):
            label += " — %s" % md(node["objective"])
    lines.append(indent + "- " + label)
    for child in node.get("children", []):
        lines.extend(render_tree_md(child))
    return lines


def main_inner(json_path, output_path):
    data = load_lesson(json_path)
    errors, _ = validate_lesson(data)
    if errors:
        print("校验未通过，拒绝生成 Markdown：")
        for item in errors:
            print("  - %s" % item)
        return 1

    nodes = data["knowledge_tree"]
    generate_post_relations(nodes)
    roots, _ = build_tree(nodes)
    meta = data["lesson_meta"]
    knowledge_count = sum(1 for n in nodes if n["node_type"] == "知识点")
    out = [
        "# %s · %s" % (md(meta["week"]), md(meta["title"])),
        "",
        "> **课程**：%s  |  **学时**：%s  |  **知识节点**：%d  |  **数据契约**：v%s" % (
            md(meta["course_name"]), md(meta["hours"]), knowledge_count, md(data.get("schema_version", "2.0"))),
        "",
        "## 1. 知识树",
        "",
    ]
    for root in roots:
        out.extend(render_tree_md(root))

    out.extend(["", "## 2. 课堂时间轴", "", "| 环节 | 时长（分钟） | 对应知识点 |", "|---|---:|---|"])
    for stage in data["flow"]["in_class"]:
        out.append("| %s | %s | %s |" % (
            md(stage["stage"]), md(stage["duration_minutes"]),
            md("；".join(stage.get("knowledge_refs", [])) or "课程导入/总结"),
        ))

    out.extend(["", "## 3. 知识关系", "", "| 节点 | 前置 | 后置 | 关联 | 认知层级 | 知识分类 |", "|---|---|---|---|---|---|"])
    for node in nodes:
        if node["node_type"] != "知识点":
            continue
        out.append("| %s | %s | %s | %s | %s | %s |" % (
            md(node["name"]), md(";".join(node.get("pre", []))), md(";".join(node.get("post", []))),
            md(";".join(node.get("related", []))), md(node.get("cognitive", "")), md(node.get("category", "")),
        ))

    out.extend(["", "## 4. 教学目标与知识点映射", "", "| 目标类型 | 教学目标 | 绑定知识点 |", "|---|---|---|"])
    for group, label in [("knowledge", "知识"), ("ability", "能力"), ("quality", "素质")]:
        for item in objective_items(data, group):
            out.append("| %s | %s | %s |" % (label, md(objective_text(item)), md("；".join(objective_refs(item)))))

    out.extend(["", "## 5. 节点目标索引", "", "| 节点 | 节点目标 | 认知层级 | 标签 |", "|---|---|---|---|"])
    for node in nodes:
        if node["node_type"] == "知识点":
            out.append("| %s | %s | %s | %s |" % (
                md(node["name"]), md(node.get("objective", "")), md(node.get("cognitive", "")), md(node.get("tags", "")),
            ))

    glossary = data.get("glossary", [])
    if glossary:
        out.extend(["", "## 6. 术语表", "", "| 术语 | 定义 |", "|---|---|"])
        for item in glossary:
            out.append("| %s | %s |" % (md(item.get("term", "")), md(item.get("definition", ""))))

    out.extend(["", "---", "", "*由同一份 lesson.json 生成。AI 辅助内容需由授课教师审核后使用。*", ""])
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("Markdown 已生成：%s（%d 个节点）" % (output_path, len(nodes)))
    return 0


def main():
    parser = argparse.ArgumentParser(description="Markdown 知识图谱生成器")
    parser.add_argument("--json", required=True, help="lesson.json 路径")
    parser.add_argument("--output", required=True, help="输出 .md 路径")
    args = parser.parse_args()
    try:
        return main_inner(args.json, args.output)
    except (LessonInputError, ValueError, OSError) as exc:
        print("生成失败：%s" % exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
