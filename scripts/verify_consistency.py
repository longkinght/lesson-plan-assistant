# -*- coding: utf-8 -*-
"""一致性校验 CLI：验证 lesson.json 是否满足硬红线。
用法: python verify_consistency.py --json lesson.json
退出码: 0=通过, 1=存在错误
"""
import argparse
from common import load_lesson, validate_lesson, print_report


def main():
    parser = argparse.ArgumentParser(description="备课知识图谱助手 · 硬校验")
    parser.add_argument("--json", required=True, help="lesson.json 路径")
    args = parser.parse_args()

    data = load_lesson(args.json)
    errors, warnings = validate_lesson(data)
    ok = print_report(errors, warnings)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
