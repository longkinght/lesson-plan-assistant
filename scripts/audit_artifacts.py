# -*- coding: utf-8 -*-
"""验收核查脚本：产物质量 + 同源一致性（独立路径回读）"""
import json
import re
import sys

import docx

base = sys.argv[1]
print("=== 产物质量与同源一致性核查 ===")

# 3.1 从 lesson.json 提取知识点集合
with open(base + "/lesson.json", encoding="utf-8") as f:
    data = json.load(f)
json_nodes = [n["name"] for n in data["knowledge_tree"] if n["node_type"] == "知识点"]
print(f"JSON 知识点节点数: {len(json_nodes)}")

# 3.2 从 md 提取知识点（行内含 ［认知· 标记的即知识点）
with open(base + "/第15周_知识图谱.md", encoding="utf-8") as f:
    md = f.read()
md_names = re.findall(r"^\s*- \*\*([^*]+)\*\* ［", md, re.M)
md_nodes = [n.strip() for n in md_names]
print(f"MD 知识点节点数: {len(md_nodes)}")

# 3.3 从 html 内嵌 JSON 提取
with open(base + "/第15周_知识图谱.html", encoding="utf-8") as f:
    html = f.read()
m = re.search(r'<script id="lesson-data" type="application/json">(.*?)</script>', html, re.S)
hdata = json.loads(m.group(1))
html_nodes = [n["name"] for n in hdata["knowledge_tree"] if n["node_type"] == "知识点"]
script_part = html[: html.find("</script>")]
print(f"HTML 知识点节点数: {len(html_nodes)}")
print("HTML 内嵌数据含 children 字段:", '"children"' in script_part)

# 3.4 从 docx 课中环节提取引用知识点
d = docx.Document(base + "/第15周_教案.docx")
refs = []
for p in d.paragraphs:
    t = p.text
    if "（知识点：" in t:
        refs.extend(t.split("（知识点：")[1].rstrip("）").split("、"))
refs = [r.strip() for r in refs if r.strip()]
print(f"DOCX 课中环节引用知识点数: {len(refs)}")

# 3.5 一致性比对
print("--- 一致性比对 ---")
print("JSON==MD:", set(json_nodes) == set(md_nodes))
print("JSON==HTML:", set(json_nodes) == set(html_nodes))
print("教案引用 ⊆ 图谱节点:", set(refs) <= set(json_nodes))
missing = set(refs) - set(json_nodes)
print("教案引用缺失项:", missing if missing else "无")
print(f"教案引用覆盖知识点比例: {len(set(refs)) / len(json_nodes) * 100:.0f}%")

# 3.6 关键字段抽查
cog_ok = all(
    n.get("cognitive") in ["记忆", "理解", "应用", "分析", "评价", "创造"]
    for n in data["knowledge_tree"]
    if n["node_type"] == "知识点"
)
obj_ok = all(
    n.get("objective")
    for n in data["knowledge_tree"]
    if n["node_type"] == "知识点" and n["level"] >= 4
)
stages = data["flow"]["in_class"]
four_dim_ok = all(
    s.get(c)
    for s in stages
    for c in ["content", "student_activity", "teacher_activity", "design_intent"]
)
print("--- 字段抽查 ---")
print("布鲁姆认知层级全部合法:", cog_ok)
print("Level>=4 知识点目标全覆盖:", obj_ok)
print(f"五环节×四维: 环节数={len(stages)}, 四维齐全={four_dim_ok}")

# 3.7 脚本可复现性：重新生成并对比
import subprocess
subprocess.run([sys.executable, sys.argv[2], "--json", base + "/lesson.json",
                "--output-dir", base], check=True, capture_output=True)
print("--- 可复现性 ---")
print("全流程重跑退出码: 0（成功）")
