# 学校样本示例（school-template）

这个目录演示「模板通道」：把一份学校规定的 Word 教案样本作为版式来源，严格按其格式生成。

**样本是示意图，不是任何真实学校的规定文件。** `学校样本_教案模板.docx` 由 `tests/template_fixture.py` 生成，刻意做成常见高校教案的样子：仿宋 12pt 正文、黑体表头、5 列表格式课中环节表（含“备注”表尾行）、固定页眉页脚、2.5cm 页边距。

## 目录内容

| 文件 | 说明 |
|---|---|
| `学校样本_教案模板.docx` | 供解析的样本，含空待填格子 |
| `学校样本_教案模板_template-map.json` | 解析出的映射，已标记 `confirmed: true` |
| `学校样本_教案模板_template-report.md` | 核对报告：每个字段落在哪个格子 |
| `第15周_栈和队列_教案.docx` | 按该样本格式填出的成品 |
| `第15周_栈和队列_知识图谱.md` / `.html` | 同源知识资产，不受样本版式约束 |

## 复现

```bash
python scripts/analyze_template.py --template examples/school-template/学校样本_教案模板.docx \
  --out-dir examples/school-template

python scripts/lesson_assistant.py --json examples/stack_queue/lesson.json \
  --output-dir examples/school-template \
  --template examples/school-template/学校样本_教案模板.docx \
  --template-map examples/school-template/学校样本_教案模板_template-map.json
```

## 换成自己学校的样本

1. 把学校的样本 DOCX 放进来，执行 `analyze_template.py`；
2. 打开生成的 `*_template-report.md`，确认每个字段指向的格子对不对；
3. 不对就改 `*_template-map.json` 里的地址，改完把 `confirmed` 设为 `true`；
4. 之后同校同模板一直复用这份映射。

地址格式与列键说明见 [`references/template-mapping.md`](../../references/template-mapping.md)。
