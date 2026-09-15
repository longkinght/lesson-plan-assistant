# -*- coding: utf-8 -*-
"""Markdown 知识图谱生成器：lesson.json → 知识图谱 .md
三层结构：知识树（嵌套列表）→ 关系表（机器可解析）→ 教学目标索引 → 术语表
用法: python build_graph.py --json lesson.json --output 第X周_知识图谱.md
"""
import argparse
from common import (
    load_lesson, build_tree, generate_post_relations, validate_lesson,
    VALID_CATEGORIES, VALID_COGNITIVE,
)


def render_tree_md(node, level):
    """把树渲染为嵌套列表。分类节点与知识点用不同前缀。"""
    lines = []
    indent = "  " * (level - 1)
    prefix = "- "
    if node["node_type"] == "分类":
        label = f"**{node['name']}**"
        if node.get("tags"):
            label += f" 〖{node['tags']}〗"
        lines.append(f"{indent}{prefix}{label}")
    else:
        label = f"**{node['name']}**"
        parts = []
        if node.get("cognitive"):
            parts.append(f"认知·{node['cognitive']}")
        if node.get("category"):
            parts.append(node["category"])
        if node.get("tags"):
            parts.append(node["tags"])
        if parts:
            label += f" ［{' / '.join(parts)}］"
        if node.get("objective"):
            label += f" 🎯 {node['objective']}"
        lines.append(f"{indent}{prefix}{label}")
    for child in node.get("children", []) or []:
        lines.extend(render_tree_md(child, level + 1))
    return lines


def main_inner(json_path, output_path):
    data = load_lesson(json_path)
    errors, _ = validate_lesson(data)
    if errors:
        print("❌ 校验未通过，拒绝生成。请先修复:")
        for e in errors:
            print(f"   - {e}")
        return 1

    nodes = data["knowledge_tree"]
    generate_post_relations(nodes)
    roots, name_to_node = build_tree(nodes)
    meta = data["lesson_meta"]

    out = []
    week_raw = meta.get("week", "")
    if "周" in week_raw:
        week_head = f"第{week_raw.replace('第','').replace('周','')}周"
    else:
        week_head = week_raw if week_raw else ""
    out.append(f"# {week_head} 知识图谱：{meta['title']}")
    out.append("")
    out.append(f"> 课程：{meta.get('course_name','')} ｜ 学时：{meta.get('hours','')} ｜ 课题：{meta['title']}")
    out.append("")
    out.append("## 一、知识树")
    out.append("")
    for r in roots:
        out.extend(render_tree_md(r, 1))
    out.append("")

    # 关系表
    out.append("## 二、关系表")
    out.append("")
    out.append("| 节点 | 前置 | 后置 | 关联 | 认知层级 | 分类 |")
    out.append("|---|---|---|---|---|---|")
    for n in nodes:
        if n["node_type"] != "知识点":
            continue
        out.append(
            f"| {n['name']} | {';'.join(n.get('pre',[]) or [])} | "
            f"{';'.join(n.get('post',[]) or [])} | {';'.join(n.get('related',[]) or [])} | "
            f"{n.get('cognitive','')} | {n.get('category','')} |"
        )
    out.append("")

    # 教学目标索引
    out.append("## 三、教学目标索引")
    out.append("")
    out.append("| 节点 | 教学目标 | 认知层级 | 标签 |")
    out.append("|---|---|---|---|")
    for n in nodes:
        if n["node_type"] == "知识点" and n.get("objective"):
            out.append(
                f"| {n['name']} | {n['objective']} | {n.get('cognitive','')} | {n.get('tags','')} |"
            )
    out.append("")

    # 术语表
    glossary = data.get("glossary", []) or []
    if glossary:
        out.append("## 四、术语表")
        out.append("")
        out.append("| 术语 | 定义 |")
        out.append("|---|---|")
        for g in glossary:
            out.append(f"| {g.get('term','')} | {g.get('definition','')} |")
        out.append("")

    out.append("---")
    out.append(f"*由同一份 lesson.json 生成 · 与教案、HTML 信息图同源同构*")

    text = "\n".join(out)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"✅ Markdown 知识图谱已生成: {output_path}（{len(nodes)} 个节点）")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Markdown 知识图谱生成器")
    parser.add_argument("--json", required=True, help="lesson.json 路径")
    parser.add_argument("--output", required=True, help="输出 .md 路径")
    args = parser.parse_args()
    return main_inner(args.json, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
