# -*- coding: utf-8 -*-
"""备课知识图谱助手 · 共享数据模型与硬校验
确定性逻辑全部集中在脚本层，LLM 只负责产出符合契约的 lesson.json。
"""
import json
import sys
import io

# 控制台 UTF-8 输出（Windows 兼容）
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
except Exception:
    pass

VALID_CATEGORIES = ["事实性", "概念性", "程序性", "元认知"]
VALID_COGNITIVE = ["记忆", "理解", "应用", "分析", "评价", "创造"]
VALID_TAGS = ["重点", "难点", "考点", "课程思政"]
NODE_TYPES = ["分类", "知识点"]

# 布鲁姆 6 级配色（HTML 信息图使用）
COGNITIVE_COLORS = {
    "记忆": "#94A3B8",
    "理解": "#38BDF8",
    "应用": "#34D399",
    "分析": "#FBBF24",
    "评价": "#FB923C",
    "创造": "#F87171",
}


def load_lesson(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def build_tree(nodes):
    """根据 level 构建树。要求节点深度优先排列（父在前）。
    幂等：每次调用都会重建 children，可安全重复调用。
    返回 (root_nodes, name_to_node)。
    """
    # 幂等：清空旧 children，避免重复调用时节点翻倍
    for n in nodes:
        n["children"] = []
    level_stack = {}
    roots = []
    for node in nodes:
        for l in list(level_stack.keys()):
            if l >= node["level"]:
                del level_stack[l]
        parent = level_stack.get(node["level"] - 1)
        if parent is not None:
            parent["children"].append(node)
        else:
            roots.append(node)
        level_stack[node["level"]] = node
    name_to_node = {n["name"]: n for n in nodes}
    return roots, name_to_node


def generate_post_relations(nodes):
    """由 pre 反向生成 post（若未填写）。"""
    name_to_node = {n["name"]: n for n in nodes}
    for node in nodes:
        for pre_name in node.get("pre", []) or []:
            target = name_to_node.get(pre_name)
            if target is not None:
                posts = target.setdefault("post", [])
                if node["name"] not in posts:
                    posts.append(node["name"])


def _join(values):
    return ";".join(str(v).strip() for v in (values or []) if str(v).strip())


def validate_lesson(data):
    """硬校验。返回 (errors, warnings)。errors 非空则禁止交付。"""
    errors = []
    warnings = []

    meta = data.get("lesson_meta", {})
    for f in ["week", "title", "course_name"]:
        if not meta.get(f):
            errors.append(f"lesson_meta.{f} 缺失")
    if not isinstance(meta.get("hours"), (int, float)) or meta["hours"] <= 0:
        errors.append("lesson_meta.hours 必须为正数")

    objectives = data.get("objectives", {})
    if not objectives.get("knowledge"):
        errors.append("objectives.knowledge 至少 1 条")
    if not objectives.get("ability"):
        errors.append("objectives.ability 至少 1 条")
    if not objectives.get("quality"):
        errors.append("objectives.quality 至少 1 条")

    nodes = data.get("knowledge_tree", [])
    if not nodes:
        errors.append("knowledge_tree 不能为空")

    # 名称唯一 + 字段合法
    names = set()
    for i, n in enumerate(nodes):
        name = n.get("name", "")
        if not name:
            errors.append(f"节点[{i}] 缺少 name")
            continue
        if name in names:
            errors.append(f"节点名称重复: {name}")
        names.add(name)
        if len(name) > 30:
            errors.append(f"节点名超过30字: {name}")
        level = n.get("level")
        if not isinstance(level, int) or level < 1 or level > 7:
            errors.append(f"节点 '{name}' level 非法: {level}")
        ntype = n.get("node_type")
        if ntype not in NODE_TYPES:
            errors.append(f"节点 '{name}' node_type 非法: {ntype}")
        if ntype == "分类" and n.get("category"):
            errors.append(f"分类节点 '{name}' category 必须为空")
        if ntype == "知识点":
            cat = n.get("category")
            if cat not in VALID_CATEGORIES:
                errors.append(f"知识点 '{name}' category 非法: {cat}")
            cog = n.get("cognitive")
            if cog not in VALID_COGNITIVE:
                errors.append(f"知识点 '{name}' cognitive 非法: {cog}")
            if level >= 4 and not n.get("objective"):
                errors.append(f"Level{level} 知识点 '{name}' 缺少 objective")

    # 树结构连续性（只读检查：不修改节点，避免 children 污染数据）
    level_seen = {}
    for n in nodes:
        parent_level = n["level"] - 1
        if parent_level >= 1 and parent_level not in level_seen:
            errors.append(
                f"层级断层: '{n['name']}' (L{n['level']}) 缺少 L{parent_level} 父节点"
            )
        for l in [k for k in level_seen if k >= n["level"]]:
            del level_seen[l]
        level_seen[n["level"]] = n["name"]

        # 关系引用有效
        name_to_node = {n["name"]: n for n in nodes}
        for n in nodes:
            for rel, label in (("pre", "前置"), ("post", "后置"), ("related", "关联")):
                for ref in n.get(rel, []) or []:
                    if ref not in name_to_node:
                        errors.append(f"节点 '{n['name']}' 的{label}引用不存在: {ref}")

    # 教案知识点 ⊆ 图谱节点（一致性红线）
    for stage in data.get("flow", {}).get("in_class", []) or []:
        for ref in stage.get("knowledge_refs", []) or []:
            if ref not in names:
                errors.append(f"课中环节 '{stage.get('stage','')}' 引用不存在的知识点: {ref}")

    flow = data.get("flow", {})
    if not flow.get("in_class"):
        errors.append("flow.in_class 至少 1 个环节")
    else:
        for stage in flow["in_class"]:
            if not stage.get("stage"):
                errors.append("存在缺少 stage 的课中环节")
            for dim in ["content", "student_activity", "teacher_activity", "design_intent"]:
                if not stage.get(dim):
                    warnings.append(f"环节 '{stage.get('stage','')}' 缺少 {dim}（建议补齐四维）")

    reflection = data.get("reflection", {})
    if not reflection.get("effect") or not reflection.get("diagnosis") or not reflection.get("improvement"):
        warnings.append("reflection 建议包含 effect/diagnosis/improvement 三段")

    return errors, warnings


def print_report(errors, warnings):
    print("=" * 56)
    print("硬校验结果")
    print("=" * 56)
    if not errors and not warnings:
        print("✅ 全部通过")
    if errors:
        print(f"❌ 错误 {len(errors)} 个（必须修复后才能交付）:")
        for e in errors:
            print(f"   - {e}")
    if warnings:
        print(f"⚠️ 建议 {len(warnings)} 条（不阻止交付）:")
        for w in warnings:
            print(f"   - {w}")
    return len(errors) == 0
