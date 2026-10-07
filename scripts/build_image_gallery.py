#!/usr/bin/env python3
"""向 yokai_07_图像清单.md 注入图像画廊（markdown 图片嵌入）。

清单表格只给路径，读者看不到图。本脚本按 data/image_index.json 补一节
画廊，把每张图真正渲染出来。路径全是仓库内相对路径，不含任何网址，
沿用「正文不载网址」的规矩。生成块用 HTML 注释夹住，可重复运行。
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "image_index.json"
DOC = ROOT / "yokai_07_图像清单.md"

BEGIN = "<!-- gallery:begin -->"
END = "<!-- gallery:end -->"

# 一次铺开太长；40 行一屏读得下。
CHUNK = 40


def load_rows():
    """读索引，并逐条确认图片真的在盘上——绝不给死链写进文档。"""
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    missing = [r for r in rows if not (ROOT / r["image"]).exists()]
    if missing:
        print(f"✗ 有 {len(missing)} 条索引指向不存在的图片，停止生成")
        for r in missing[:10]:
            print(f"    {r.get('card', '?')}  {r['image']}")
        sys.exit(1)
    return rows


def cell(value):
    """表格单元格与 alt 文本的转义：竖线会断表，方括号会截断 alt。"""
    text = value if value else "—"
    return text.replace("|", "／").replace("[", "（").replace("]", "）")


def alt_of(row):
    """妖名 + 画家 + 出典；无署名的记录自然退化为两项。"""
    parts = [row["yokai"]]
    if row["author"] and row["author"] != "—":
        parts.append(row["author"])
    if row["source"] and row["source"] != "—":
        parts.append(row["source"])
    return cell("　".join(parts))


def render(rows):
    """生成画廊块。只用 ## 与 ###，避开 check_yokai.py 的层级断裂规则。"""
    out = [
        BEGIN,
        "",
        f"## 图像画廊（{len(rows)} 张）",
        "",
    ]
    ordered = sorted(rows, key=lambda r: r["yokai"])
    for start in range(0, len(ordered), CHUNK):
        part = ordered[start : start + CHUNK]
        out += [
            f"### {start + 1}–{start + len(part)}",
            "",
            "| 妖名 | 画家 | 出典 | 年份 | 图 |",
            "|---|---|---|---|---|",
        ]
        for r in part:
            out.append(
                f"| {cell(r['yokai'])} | {cell(r['author'])} | {cell(r['source'])} | "
                f"{cell(r['date'])} | ![{alt_of(r)}]({r['image']}) |"
            )
        out.append("")
    out += [END]
    return "\n".join(out)


def strip_gallery(text):
    """剥掉上一轮的生成块，使重复运行不堆出第二份画廊。"""
    i = text.find(BEGIN)
    if i == -1:
        return text
    j = text.find(END, i)
    if j == -1:
        print("✗ 有 gallery:begin 却没有 gallery:end，文档可能被手工改坏，停止")
        sys.exit(1)
    j += len(END)
    while j < len(text) and text[j] == "\n":
        j += 1
    return text[:i] + text[j:]


def main():
    if not DOC.exists():
        print(f"✗ 找不到 {DOC}，先跑 build_image_index.py")
        return 1

    rows = load_rows()
    before = DOC.read_text(encoding="utf-8")
    body = strip_gallery(before).rstrip("\n")
    after = f"{body}\n\n{render(rows)}\n"

    changed = after != before
    if changed:
        DOC.write_text(after, encoding="utf-8")

    embeds = after.count("![")
    print(f"✓ 索引 {len(rows)} 条，嵌入 {embeds} 张，文档{'已更新' if changed else '无变化'}")
    if embeds != len(rows):
        print(f"✗ 嵌入数 {embeds} 与索引数 {len(rows)} 不符")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
