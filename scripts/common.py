# -*- coding: utf-8 -*-
"""Shared data helpers and deterministic quality gates.

v2 changes: safe malformed-input handling, objective-to-node links, timed lesson
flows, reflection status, relationship checks, and safe output filenames.
"""
import io
import json
import re
import sys

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
except Exception:
    pass

VALID_CATEGORIES = ["事实性", "概念性", "程序性", "元认知"]
VALID_COGNITIVE = ["记忆", "理解", "应用", "分析", "评价", "创造"]
VALID_TAGS = ["重点", "难点", "考点", "课程思政"]
NODE_TYPES = ["分类", "知识点"]
OBJECTIVE_GROUPS = ["knowledge", "ability", "quality"]
STAGE_ROLES = ["intro", "instruction", "practice", "summary", "other"]
FIVE_STAGE_ROLES = ["intro", "instruction", "instruction", "practice", "summary"]
DIMENSIONS = ["content", "student_activity", "teacher_activity", "design_intent"]
BEHAVIOR_VERBS = [
    "说出", "解释", "阐述", "列举", "识别", "比较", "描述", "复述", "归类",
    "操作", "实现", "运用", "分析", "设计", "评价", "编写", "演示", "判断",
    "制定", "提出", "完成", "构建", "搭建", "生成", "拆解", "绘制", "区分",
    "明确", "验证", "说明", "掌握",
]

COGNITIVE_COLORS = {
    "记忆": "#64748B", "理解": "#0284C7", "应用": "#059669",
    "分析": "#B45309", "评价": "#C2410C", "创造": "#BE123C",
}


class LessonInputError(ValueError):
    """Raised when lesson JSON cannot be read as a JSON object."""


def load_lesson(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise LessonInputError("找不到 lesson.json：%s" % path)
    except json.JSONDecodeError as exc:
        raise LessonInputError("JSON 格式错误：第 %s 行第 %s 列，%s" % (exc.lineno, exc.colno, exc.msg))
    except OSError as exc:
        raise LessonInputError("无法读取 lesson.json：%s" % exc)
    if not isinstance(data, dict):
        raise LessonInputError("lesson.json 顶层必须是 JSON 对象")
    return data


def objective_items(data, group):
    objectives = data.get("objectives", {})
    if not isinstance(objectives, dict):
        return []
    items = objectives.get(group, [])
    return items if isinstance(items, list) else []


def objective_text(item):
    if isinstance(item, dict):
        return str(item.get("text", "")).strip()
    return str(item).strip() if isinstance(item, str) else ""


def objective_refs(item):
    if not isinstance(item, dict) or not isinstance(item.get("knowledge_refs"), list):
        return []
    return [x for x in item["knowledge_refs"] if isinstance(x, str) and x.strip()]


def build_tree(nodes):
    """Build a depth-first tree; reset children so repeated calls stay idempotent."""
    for node in nodes:
        node["children"] = []
    stack = []
    roots = []
    for node in nodes:
        while stack and stack[-1]["level"] >= node["level"]:
            stack.pop()
        if stack:
            stack[-1]["children"].append(node)
        else:
            roots.append(node)
        stack.append(node)
    return roots, {node["name"]: node for node in nodes}


def generate_post_relations(nodes):
    """Complete reverse post relations from pre without duplicating entries."""
    by_name = {node["name"]: node for node in nodes}
    for node in nodes:
        for pre_name in node.get("pre", []) or []:
            target = by_name.get(pre_name)
            if target is not None:
                posts = target.setdefault("post", [])
                if node["name"] not in posts:
                    posts.append(node["name"])


def safe_file_stem(meta):
    """Create a readable, collision-resistant, platform-safe output stem."""
    raw = "%s_%s" % (meta.get("week", "课程"), meta.get("title", "教案"))
    value = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", raw)
    value = re.sub(r"\s+", "", value).strip(" ._")
    while ".." in value:
        value = value.replace("..", ".")
    value = value.strip(" ._")
    return (value or "课程_教案")[:100]


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _mapping(value, path, errors):
    if not isinstance(value, dict):
        errors.append("%s 必须是对象" % path)
        return {}
    return value


def _string_list(value, path, errors):
    if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
        errors.append("%s 必须是字符串数组" % path)
        return []
    return value


def _validate_objectives(data, knowledge_names, is_v2, errors, warnings):
    objectives = _mapping(data.get("objectives"), "objectives", errors)
    for group in OBJECTIVE_GROUPS:
        items = objectives.get(group)
        if not isinstance(items, list) or not items:
            errors.append("objectives.%s 至少 1 条" % group)
            continue
        for index, item in enumerate(items):
            path = "objectives.%s[%d]" % (group, index)
            text = objective_text(item)
            if not text:
                errors.append("%s 缺少非空 text" % path)
                continue
            if len(text) < 6:
                errors.append("%s 目标过于笼统，需写明可观察的学习结果" % path)
            if group != "quality" and not any(verb in text for verb in BEHAVIOR_VERBS):
                errors.append("%s 缺少可观察行为动词" % path)
            refs = objective_refs(item)
            if is_v2:
                if not isinstance(item, dict):
                    errors.append("%s 必须是 {text, knowledge_refs} 对象" % path)
                if not refs:
                    errors.append("%s 至少绑定 1 个 knowledge_refs" % path)
            elif not refs:
                warnings.append("%s 使用旧版字符串目标，建议升级为对象并绑定知识点" % path)
            for ref in refs:
                if ref not in knowledge_names:
                    errors.append("%s 引用了不存在的知识点：%s" % (path, ref))


def _validate_nodes(data, errors, warnings):
    nodes = data.get("knowledge_tree")
    if not isinstance(nodes, list) or not nodes:
        errors.append("knowledge_tree 必须是非空数组")
        return [], set(), {}
    valid_nodes = []
    names = set()
    by_name = {}
    for index, node in enumerate(nodes):
        path = "knowledge_tree[%d]" % index
        if not isinstance(node, dict):
            errors.append("%s 必须是对象" % path)
            continue
        valid_nodes.append(node)
        name = node.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append("%s.name 必须是非空字符串" % path)
            name = ""
        else:
            name = name.strip()
            if len(name) > 30:
                errors.append("节点名超过 30 字：%s" % name)
            if name in names:
                errors.append("节点名称重复：%s" % name)
            names.add(name)
            by_name[name] = node
        level = node.get("level")
        if not isinstance(level, int) or isinstance(level, bool) or not 1 <= level <= 7:
            errors.append("节点 '%s' level 必须是 1-7 的整数" % name)
        node_type = node.get("node_type")
        if node_type not in NODE_TYPES:
            errors.append("节点 '%s' node_type 必须是 分类 或 知识点" % name)
        for rel in ["pre", "post", "related"]:
            _string_list(node.get(rel, []), "%s.%s" % (path, rel), errors)
        tags = node.get("tags", "")
        if not isinstance(tags, str):
            errors.append("%s.tags 必须是英文分号分隔的字符串" % path)
        else:
            for tag in [x.strip() for x in tags.split(";") if x.strip()]:
                if tag not in VALID_TAGS:
                    warnings.append("节点 '%s' 使用非标准标签：%s" % (name, tag))
        if node_type == "分类":
            for field in ["category", "cognitive", "objective"]:
                if node.get(field):
                    errors.append("分类节点 '%s' 的 %s 必须为空" % (name, field))
        elif node_type == "知识点":
            if node.get("category") not in VALID_CATEGORIES:
                errors.append("知识点 '%s' category 非法" % name)
            if node.get("cognitive") not in VALID_COGNITIVE:
                errors.append("知识点 '%s' cognitive 非法" % name)
            objective = node.get("objective")
            if not isinstance(objective, str) or len(objective.strip()) < 6:
                errors.append("知识点 '%s' 缺少具体教学目标" % name)
            elif not any(verb in objective for verb in BEHAVIOR_VERBS):
                errors.append("知识点 '%s' 的目标缺少可观察行为动词" % name)
    knowledge_names = {n.get("name") for n in valid_nodes if n.get("node_type") == "知识点" and n.get("name")}

    if valid_nodes and valid_nodes[0].get("level") != 1:
        errors.append("knowledge_tree 首个节点必须是 Level 1 根节点")
    if sum(1 for n in valid_nodes if n.get("level") == 1) != 1:
        errors.append("knowledge_tree 必须且只能有一个 Level 1 根节点")
    stack = []
    for node in valid_nodes:
        level = node.get("level")
        if not isinstance(level, int) or isinstance(level, bool) or not 1 <= level <= 7:
            continue
        while stack and stack[-1].get("level") >= level:
            stack.pop()
        if level > 1:
            if not stack or stack[-1].get("level") != level - 1:
                errors.append("层级或顺序错误：'%s' 缺少紧邻的 Level %d 父节点" % (node.get("name", ""), level - 1))
        stack.append(node)

    for node in valid_nodes:
        name = node.get("name", "")
        for rel, label in [("pre", "前置"), ("post", "后置"), ("related", "关联")]:
            refs = node.get(rel, [])
            if not isinstance(refs, list):
                continue
            for ref in refs:
                if not isinstance(ref, str):
                    continue
                if ref not in names:
                    errors.append("节点 '%s' 的%s引用不存在：%s" % (name, label, ref))
                elif rel in ["pre", "post"] and ref not in knowledge_names:
                    errors.append("节点 '%s' 的%s引用必须指向知识点：%s" % (name, label, ref))
                if rel in ["pre", "post"] and ref == name:
                    errors.append("节点 '%s' 不能把自身设为%s" % (name, label))
        for pre in node.get("pre", []) if isinstance(node.get("pre", []), list) else []:
            target = by_name.get(pre)
            if target and name not in (target.get("post", []) or []):
                warnings.append("关系已可由脚本补齐：'%s' 的 post 建议包含 '%s'" % (pre, name))
    return valid_nodes, knowledge_names, by_name


def _validate_flow(data, knowledge_names, minutes_per_hour, is_v2, errors, warnings):
    flow = _mapping(data.get("flow"), "flow", errors)
    for section in ["pre_class", "post_class"]:
        stage = _mapping(flow.get(section), "flow.%s" % section, errors)
        for dim in DIMENSIONS:
            if not isinstance(stage.get(dim), str) or not stage.get(dim).strip():
                message = "flow.%s 缺少 %s" % (section, dim)
                (errors if is_v2 else warnings).append(message)
    stages = flow.get("in_class")
    if not isinstance(stages, list) or not stages:
        errors.append("flow.in_class 必须是非空数组")
        return
    structure = flow.get("structure", "five_stage")
    if structure not in ["five_stage", "custom"]:
        errors.append("flow.structure 必须是 five_stage 或 custom")
        structure = "five_stage"
    if structure == "five_stage" and len(stages) != 5:
        errors.append("five_stage 模式必须恰好包含 5 个课中环节")
    total_minutes = 0.0
    covered = set()
    for index, stage in enumerate(stages):
        path = "flow.in_class[%d]" % index
        if not isinstance(stage, dict):
            errors.append("%s 必须是对象" % path)
            continue
        name = stage.get("stage", "环节%d" % (index + 1))
        if not isinstance(name, str) or not name.strip():
            errors.append("%s.stage 必须是非空字符串" % path)
        role = stage.get("role")
        if is_v2 and role not in STAGE_ROLES:
            errors.append("%s.role 必须是 %s 之一" % (path, "/".join(STAGE_ROLES)))
        if structure == "five_stage" and is_v2 and index < 5 and role != FIVE_STAGE_ROLES[index]:
            errors.append("%s.role 应为 %s" % (path, FIVE_STAGE_ROLES[index]))
        for dim in DIMENSIONS:
            if not isinstance(stage.get(dim), str) or not stage.get(dim).strip():
                (errors if is_v2 else warnings).append("%s 缺少 %s" % (path, dim))
        duration = stage.get("duration_minutes")
        if not _is_number(duration) or duration <= 0:
            errors.append("%s.duration_minutes 必须是正数" % path)
        else:
            total_minutes += duration
        refs = stage.get("knowledge_refs", [])
        refs = _string_list(refs, "%s.knowledge_refs" % path, errors)
        if role != "intro" and not refs:
            warnings.append("%s 未声明知识点，建议补充 knowledge_refs" % path)
        for ref in refs:
            if ref not in knowledge_names:
                errors.append("课中环节 '%s' 引用不存在或不是知识点的节点：%s" % (name, ref))
            covered.add(ref)
    expected = data.get("lesson_meta", {}).get("hours", 0) * minutes_per_hour
    if _is_number(expected) and abs(total_minutes - expected) > 0.01:
        errors.append("课中时长合计 %.2f 分钟，与 %s 学时应有的 %.2f 分钟不一致" % (total_minutes, data.get("lesson_meta", {}).get("hours"), expected))
    uncovered = sorted(knowledge_names - covered)
    if uncovered:
        warnings.append("以下知识点未进入课中环节（可作为拓展，否则建议删除）：%s" % "、".join(uncovered))


def _validate_reflection(data, is_v2, errors, warnings):
    reflection = _mapping(data.get("reflection"), "reflection", errors)
    status = reflection.get("status", "pre_class")
    if status not in ["pre_class", "post_class"]:
        errors.append("reflection.status 必须是 pre_class 或 post_class")
        return
    for field in ["effect", "diagnosis", "improvement"]:
        value = reflection.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append("reflection.%s 必须是非空字符串" % field)
            continue
        if status == "pre_class" and is_v2 and "待课后" not in value:
            errors.append("备课阶段 reflection.%s 必须标注“待课后”，不得写成已发生的课堂结果" % field)
    if status == "post_class" and not str(reflection.get("evidence", "")).strip():
        warnings.append("课后反思建议填写 evidence，说明课堂记录或作业数据来源")


def validate_lesson(data):
    """Return (errors, warnings); errors block all deliverables."""
    errors, warnings = [], []
    if not isinstance(data, dict):
        return ["lesson.json 顶层必须是对象"], warnings
    version = data.get("schema_version")
    if version not in ["1.0", "2.0"]:
        errors.append("schema_version 必须是 1.0 或 2.0")
    is_v2 = version == "2.0"
    if version == "1.0":
        warnings.append("当前为 v1 兼容校验；公共新内容请使用 schema_version 2.0")
    meta = _mapping(data.get("lesson_meta"), "lesson_meta", errors)
    for field in ["week", "title", "course_name"]:
        if not isinstance(meta.get(field), str) or not meta.get(field).strip():
            errors.append("lesson_meta.%s 必须是非空字符串" % field)
    hours = meta.get("hours")
    if not _is_number(hours) or hours <= 0:
        errors.append("lesson_meta.hours 必须是正数")
    minutes_per_hour = meta.get("minutes_per_hour", 45)
    if not _is_number(minutes_per_hour) or minutes_per_hour <= 0:
        errors.append("lesson_meta.minutes_per_hour 必须是正数")
        minutes_per_hour = 45
    nodes, knowledge_names, _ = _validate_nodes(data, errors, warnings)
    _validate_objectives(data, knowledge_names, is_v2, errors, warnings)
    _validate_flow(data, knowledge_names, minutes_per_hour, is_v2, errors, warnings)
    _validate_reflection(data, is_v2, errors, warnings)
    return errors, warnings


def print_report(errors, warnings):
    print("=" * 60)
    print("备课质量校验")
    print("=" * 60)
    if not errors and not warnings:
        print("通过：结构、目标、关系、课堂流程与反思边界均符合契约")
    if errors:
        print("错误 %d 个（修复后才能生成）：" % len(errors))
        for item in errors:
            print("  - %s" % item)
    if warnings:
        print("提醒 %d 条（不阻止生成，交付前需复核）：" % len(warnings))
        for item in warnings:
            print("  - %s" % item)
    return not errors
