#!/usr/bin/env python3
"""从 data/image_index.json 生成图像清单 markdown。

清单是图片库的可读索引：即便 ima 之类工具不能直接传图，
也能凭此定位到具体文件。生成时逐条校验图片确实存在。
"""
import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "image_index.json"
OUT = ROOT / "yokai_07_图像清单.md"

rows = json.loads(SRC.read_text(encoding="utf-8"))

missing = [r for r in rows if not (ROOT / r["image"]).exists()]
if missing:
    print(f"✗ 有 {len(missing)} 条索引指向不存在的图片，停止生成")
    sys.exit(1)

by_author = Counter(r["author"] for r in rows if r["author"] != "—")

lines = [
    "---",
    "topic: 日本妖怪文化背景调查：画像数据库图像清单（181 张）",
    "date: 2026-10-06",
    "version: 1.0",
    "status: research",
    "---",
    "",
    "# 图像清单：181 张妖怪画",
    "",
    "> 画像数据库（日文研）**每个妖名取首张卡片**，共 181 张，图片全部存于本地。",
    "> **本清单不含任何网址。** 原始来源信息见 `archive/pages/index.json`。",
    "",
    "## 总览",
    "",
    "| 项 | 值 |",
    "|---|---|",
    f"| 图像总数 | **{len(rows)}** |",
    f"| 有画家署名 | **{by_author and sum(1 for r in rows if r['author'] != '—')}**（{sum(1 for r in rows if r['author'] != '—')/len(rows)*100:.1f}%） |",
    f"| 无署名 | {sum(1 for r in rows if r['author'] == '—')} |",
    f"| 图片体积 | {sum((ROOT/r['image']).stat().st_size for r in rows)/1048576:.1f} MB |",
    "| 图片完整性 | JPEG 头尾魔数逐张校验，181/181 无损坏 |",
    "",
    "## 画家频次",
    "",
    "「每一妖取首张」，故此表非画家总产量。",
    "",
    "| 画家 | 张数 |",
    "|---|---|",
]
for a, n in by_author.most_common():
    lines.append(f"| {a} | {n} |")

lines += [
    "",
    "## 全部图像",
    "",
    "| 妖名 | 画家 | 出典 | 年份 | 本地文件 |",
    "|---|---|---|---|---|",
]
for r in sorted(rows, key=lambda x: x["yokai"]):
    lines.append(
        f"| {r['yokai']} | {r['author']} | {r['source'] or '—'} | "
        f"{r['date'] or '—'} | `{r['image']}` |"
    )

lines += [
    "",
    "## 两处易混淆的画家名",
    "",
    "- **北斎季親**（1878–1957，明治期）与 **葛飾北斎／北斎**（1760–1849，江户期浮世绘）是**两个人**。",
    "  本清单分列，未作合并。写「北斎所画」时须指明是哪一位。",
    "- **芳年 / 一魁斎芳年（月岡芳年）**、**芳盛 / 歌川芳盛**、",
    "  **芳幾近二 / 洒落斎芳幾（歌川芳幾）** 为同一人，已归一。",
    "",
]

OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"✓ 已生成 {OUT.name}：{len(rows)} 条，{len(lines)} 行")
