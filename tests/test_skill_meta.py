# -*- coding: utf-8 -*-
"""SKILL.md frontmatter 与 skill.json 的元数据一致性检查。

平台上架校验要求 frontmatter 具备 version、display_name、display_name_en、
description_zh、description_en，且版本号需与清单文件一致。这里把要求固化成测试，
避免改版本时漏同步。
"""
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_MD = os.path.join(ROOT, "SKILL.md")
MANIFEST = os.path.join(ROOT, "skill.json")

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

REQUIRED = ["version", "display_name", "display_name_en", "description_zh", "description_en"]


def read_frontmatter(path):
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        raise AssertionError("SKILL.md 缺少 YAML frontmatter")
    return yaml.safe_load(match.group(1))


@unittest.skipUnless(yaml is not None, "需要 PyYAML 才能解析 frontmatter")
class SkillMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta = read_frontmatter(SKILL_MD)
        with open(MANIFEST, "r", encoding="utf-8") as handle:
            cls.manifest = json.load(handle)

    def test_required_fields_are_present_and_non_empty(self):
        for key in REQUIRED:
            value = self.meta.get(key)
            self.assertIsInstance(value, str, "%s 必须是字符串" % key)
            self.assertTrue(value.strip(), "%s 不能为空" % key)

    def test_name_matches_manifest(self):
        self.assertEqual(self.meta["name"], self.manifest["name"],
                         "SKILL.md 与 skill.json 的 name 不一致")
        self.assertRegex(self.meta["name"], r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$",
                         "name 必须是 kebab-case，只用小写字母、数字和连字符")

    def test_version_matches_manifest(self):
        self.assertEqual(self.meta["version"], self.manifest["version"],
                         "SKILL.md 与 skill.json 的 version 不一致")

    def test_display_names_are_short(self):
        # 展示名用于列表卡片，过长会被截断
        self.assertLessEqual(len(self.meta["display_name"]), 20, "中文展示名建议不超过 20 字")
        self.assertLessEqual(len(self.meta["display_name_en"]), 40, "英文展示名建议不超过 40 字符")

    def test_descriptions_are_language_specific(self):
        zh = self.meta["description_zh"]
        en = self.meta["description_en"]
        self.assertGreater(len(re.findall(r"[\u4e00-\u9fff]", zh)), 20, "description_zh 中文内容过少")
        self.assertLess(len(re.findall(r"[\u4e00-\u9fff]", en)), 5, "description_en 不应包含大量中文")
        self.assertGreater(len(re.findall(r"[A-Za-z]", en)), 80, "description_en 英文内容过少")
        self.assertNotEqual(zh.strip(), en.strip(), "中英文描述不能重复")


if __name__ == "__main__":
    unittest.main()
