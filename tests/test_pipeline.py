# -*- coding: utf-8 -*-
"""End-to-end tests for rendering, artifact auditing, and a safe CLI failure path."""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
STACK = os.path.join(ROOT, "examples", "stack_queue", "lesson.json")
CHAPTER = os.path.join(ROOT, "examples", "ai_generative_art", "lesson.json")
sys.path.insert(0, SCRIPTS)
from common import safe_file_stem  # noqa: E402


def run_cli(script, *args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] + list(args),
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env=env, timeout=90)


class PipelineTests(unittest.TestCase):
    def test_standard_pipeline_and_audit(self):
        with tempfile.TemporaryDirectory() as out:
            result = run_cli("lesson_assistant.py", "--json", STACK, "--output-dir", out)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            stem = safe_file_stem({"week": "第15周", "title": "栈和队列"})
            names = [stem + suffix for suffix in ["_教案.docx", "_知识图谱.md", "_知识图谱.html"]]
            for name in names:
                self.assertTrue(os.path.isfile(os.path.join(out, name)), name)
            self.assertFalse(any(name.startswith(".lesson-build-") for name in os.listdir(out)))
            with zipfile.ZipFile(os.path.join(out, names[0])) as archive:
                self.assertIn("word/document.xml", archive.namelist())
            with open(os.path.join(out, names[2]), "r", encoding="utf-8") as f:
                html = f.read()
            self.assertIn("LESSON ATLAS", html)
            self.assertIn("data-name=", html)
            audit = run_cli("audit_artifacts.py", "--json", STACK, "--output-dir", out)
            self.assertEqual(audit.returncode, 0, audit.stdout + audit.stderr)
            self.assertIn("DOCX 包含三维教学目标", audit.stdout)

    def test_chapter_style_pipeline(self):
        with tempfile.TemporaryDirectory() as out:
            result = run_cli("lesson_assistant.py", "--json", CHAPTER, "--output-dir", out, "--style", "chapter")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("章节模板", result.stdout)
            stem = safe_file_stem({"week": "第1周", "title": "导论"})
            self.assertTrue(os.path.isfile(os.path.join(out, stem + "_教案.docx")))

    def test_invalid_contract_does_not_touch_existing_artifacts(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as out:
            source = os.path.join(source_dir, "bad.json")
            with open(source, "w", encoding="utf-8") as f:
                json.dump({"schema_version": "2.0", "lesson_meta": {}, "knowledge_tree": []}, f)
            sentinel = os.path.join(out, "keep.txt")
            with open(sentinel, "w", encoding="utf-8") as f:
                f.write("unchanged")
            result = run_cli("lesson_assistant.py", "--json", source, "--output-dir", out)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(os.listdir(out), ["keep.txt"])
            with open(sentinel, encoding="utf-8") as f:
                self.assertEqual(f.read(), "unchanged")

    def test_malformed_json_returns_clear_error(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as out:
            source = os.path.join(source_dir, "broken.json")
            with open(source, "w", encoding="utf-8") as f:
                f.write("{\"schema_version\":")
            result = run_cli("lesson_assistant.py", "--json", source, "--output-dir", out)
            self.assertEqual(result.returncode, 2)
            self.assertIn("JSON 格式错误", result.stdout)
            self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_unknown_style_is_actionable(self):
        with tempfile.TemporaryDirectory() as out:
            result = run_cli("lesson_assistant.py", "--json", STACK, "--output-dir", out,
                             "--style", "does-not-exist")
            self.assertEqual(result.returncode, 2)
            self.assertIn("未知风格", result.stdout)
            self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_html_escapes_script_closing_sequences(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as out:
            with open(STACK, encoding="utf-8") as f:
                data = json.load(f)
            data["lesson_meta"]["title"] = "测试</script><script>alert(1)</script>"
            source = os.path.join(source_dir, "lesson.json")
            with open(source, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            result = run_cli("render_html.py", "--json", source,
                             "--output", os.path.join(out, "safe.html"))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            with open(os.path.join(out, "safe.html"), encoding="utf-8") as f:
                html = f.read()
            payload_match = re.findall(r"<script>alert\(1\)</script>", html)
            self.assertEqual(payload_match, [])
            self.assertIn("<\\/script>", html)


if __name__ == "__main__":
    unittest.main()
