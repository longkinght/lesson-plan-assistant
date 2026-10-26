# -*- coding: utf-8 -*-
"""Optional browser interaction checks for the offline HTML dashboard."""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STACK = os.path.join(ROOT, "examples", "stack_queue", "lesson.json")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


@unittest.skipUnless(sync_playwright is not None, "需要 Playwright 与 Chromium 才能运行浏览器测试")
class DashboardUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from render_html import main_inner
        cls.temp = tempfile.TemporaryDirectory()
        cls.html_path = os.path.join(cls.temp.name, "dashboard.html")
        main_inner(STACK, cls.html_path)
        cls.playwright = sync_playwright().start()
        try:
            cls.browser = cls.playwright.chromium.launch()
        except Exception as exc:
            cls.playwright.stop()
            cls.temp.cleanup()
            raise unittest.SkipTest("Chromium 不可用：%s" % exc)
        cls.page = cls.browser.new_page(viewport={"width": 1440, "height": 1000})
        cls.page.goto("file://" + cls.html_path.replace("\\", "/"), wait_until="load")

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.temp.cleanup()

    def test_page_renders_key_sections(self):
        self.assertIn("栈和队列", self.page.title())
        self.assertEqual(self.page.locator("#stat-nodes").inner_text(), "10")
        self.assertEqual(self.page.locator(".detail-toggle").count(), 10)
        self.assertGreater(self.page.locator("#relation-body tr").count(), 0)
        self.assertGreater(self.page.locator(".glossary-item").count(), 0)

    def test_knowledge_detail_and_side_panel_update(self):
        button = self.page.locator(".detail-toggle").first
        button.click()
        wrapper = button.locator("xpath=ancestor::div[contains(concat(' ', normalize-space(@class), ' '), ' node ')][1]")
        name = wrapper.get_attribute("data-name")
        self.assertFalse(wrapper.locator(":scope > .node-detail").first.is_hidden())
        self.assertEqual(self.page.locator("#tree-aside h3").inner_text(), name)

    def test_collapse_expand_and_search(self):
        self.page.locator("#collapse-all").click()
        self.assertGreater(self.page.locator(".children.collapsed").count(), 0)
        self.page.locator("#expand-all").click()
        self.assertEqual(self.page.locator(".children.collapsed").count(), 0)
        search = self.page.locator("#tree-search")
        search.fill("循环队列")
        self.assertGreater(self.page.locator("#tree-root .node.hidden").count(), 0)
        search.fill("")
        self.assertEqual(self.page.locator("#tree-root .node.hidden").count(), 0)
        search.fill("绝对不存在的关键词")
        self.assertFalse(self.page.locator("#tree-empty").is_hidden())
        search.fill("")
        self.assertTrue(self.page.locator("#tree-empty").is_hidden())

    def test_rhythm_card_content_is_inset(self):
        """课堂节奏卡片必须沿用 .card-body 的左右内边距，条带与时长不得贴边。"""
        metrics = self.page.evaluate(
            """() => {
              const body = document.querySelector('.card-body.rhythm');
              const style = getComputedStyle(body);
              const card = body.closest('.card').getBoundingClientRect();
              const total = document.getElementById('flow-total').getBoundingClientRect();
              const rows = Array.from(document.querySelectorAll('.rhythm-row span:last-child'))
                .map(el => el.getBoundingClientRect().right);
              return {
                left: parseFloat(style.paddingLeft),
                right: parseFloat(style.paddingRight),
                cardLeft: card.left,
                cardRight: card.right,
                barLeft: document.getElementById('rhythm-bar').getBoundingClientRect().left,
                contentRight: Math.max(total.right, ...rows)
              };
            }"""
        )
        self.assertGreaterEqual(metrics["left"], 15, "节奏卡片左侧内边距丢失，内容贴边")
        self.assertGreaterEqual(metrics["right"], 15, "节奏卡片右侧内边距丢失，内容贴边")
        self.assertGreaterEqual(metrics["barLeft"] - metrics["cardLeft"], 15, "节奏条左侧贴边")
        self.assertLessEqual(metrics["contentRight"], metrics["cardRight"] - 15, "时长文字右侧贴边或被裁切")

    def test_no_horizontal_overflow_at_mobile_width(self):
        self.page.set_viewport_size({"width": 390, "height": 844})
        overflow = self.page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth + 1")
        self.assertFalse(overflow)
        self.page.set_viewport_size({"width": 1440, "height": 1000})


if __name__ == "__main__":
    unittest.main()
