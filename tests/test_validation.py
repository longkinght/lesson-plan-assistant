# -*- coding: utf-8 -*-
"""Validation regression tests: valid contract, malformed input, teaching gates."""
import copy
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from common import load_lesson, safe_file_stem, validate_lesson  # noqa: E402

STACK = os.path.join(ROOT, "examples", "stack_queue", "lesson.json")


class ValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.valid = load_lesson(STACK)

    def errors_for(self, data):
        errors, _ = validate_lesson(data)
        return errors

    def test_bundled_examples_pass(self):
        for name in ["stack_queue", "ai_training", "ai_generative_art"]:
            with self.subTest(example=name):
                data = load_lesson(os.path.join(ROOT, "examples", name, "lesson.json"))
                errors, _ = validate_lesson(data)
                self.assertEqual(errors, [])

    def test_missing_hours_returns_error_instead_of_crashing(self):
        data = copy.deepcopy(self.valid)
        del data["lesson_meta"]["hours"]
        errors = self.errors_for(data)
        self.assertTrue(any("hours" in item for item in errors))

    def test_wrong_top_level_types_do_not_crash(self):
        cases = [
            {"schema_version": "2.0"},
            {"schema_version": "2.0", "lesson_meta": None, "objectives": [], "knowledge_tree": {}, "flow": []},
            {"schema_version": 2.0, "lesson_meta": "x", "knowledge_tree": [None, 1], "flow": {}},
        ]
        for data in cases:
            with self.subTest(data=str(data)[:50]):
                errors, warnings = validate_lesson(data)
                self.assertIsInstance(errors, list)
                self.assertIsInstance(warnings, list)
                self.assertTrue(errors)

    def test_duplicate_and_broken_tree_are_rejected(self):
        data = copy.deepcopy(self.valid)
        data["knowledge_tree"][2]["name"] = data["knowledge_tree"][1]["name"]
        data["knowledge_tree"][3]["level"] = 5
        errors = self.errors_for(data)
        self.assertTrue(any("重复" in x for x in errors))
        self.assertTrue(any("层级" in x for x in errors))

    def test_objective_requires_node_and_behavior_verb(self):
        data = copy.deepcopy(self.valid)
        data["objectives"]["knowledge"][0] = {"text": "了解栈", "knowledge_refs": ["不存在的节点"]}
        errors = self.errors_for(data)
        self.assertTrue(any("空洞" in x or "笼统" in x for x in errors))
        self.assertTrue(any("不存在" in x for x in errors))

    def test_duration_must_match_lesson_hours(self):
        data = copy.deepcopy(self.valid)
        data["flow"]["in_class"][0]["duration_minutes"] = 1
        errors = self.errors_for(data)
        self.assertTrue(any("课中时长合计" in x for x in errors))

    def test_five_stage_requires_four_dimensions(self):
        data = copy.deepcopy(self.valid)
        del data["flow"]["in_class"][2]["student_activity"]
        errors = self.errors_for(data)
        self.assertTrue(any("student_activity" in x for x in errors))

    def test_lesson_with_four_stages_fails_five_stage_profile(self):
        data = copy.deepcopy(self.valid)
        del data["flow"]["in_class"][-1]
        errors = self.errors_for(data)
        self.assertTrue(any("恰好包含 5 个" in x for x in errors))

    def test_reflection_cannot_fabricate_pre_class_results(self):
        data = copy.deepcopy(self.valid)
        data["reflection"]["effect"] = "课堂练习正确率达到 92%"
        errors = self.errors_for(data)
        self.assertTrue(any("待课后" in x for x in errors))

    def test_relation_must_not_point_to_missing_node(self):
        data = copy.deepcopy(self.valid)
        data["knowledge_tree"][3]["pre"] = ["不存在的先修知识"]
        errors = self.errors_for(data)
        self.assertTrue(any("引用不存在" in x for x in errors))

    def test_unsafe_meta_cannot_escape_output_directory(self):
        stem = safe_file_stem({"week": "第1周", "title": "../../恶意:标题?"})
        self.assertNotIn("/", stem)
        self.assertNotIn("\\", stem)
        self.assertNotIn("..", stem)
        self.assertNotIn(":", stem)
        self.assertNotIn("?", stem)


if __name__ == "__main__":
    unittest.main()
