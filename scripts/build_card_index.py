#!/usr/bin/env python3
"""生成 archive/card/index.html——图鉴索引页。

卡片页已瘦身为图鉴条目，但 181 个文件只能靠文件名或 yokai_07 找。
本页按妖名排序给出入口，配缩略图与画家名。

顺序与 yokai_07 的全部图像表一致（都按 data/image_index.json 的 yokai 排序），
两处对照阅读不会错位。缩略图用 lazy loading，本地文件，不走网络。
"""
import html
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "image_index.json"
CARD_DIR = ROOT / "archive" / "card"
OUT = CARD_DIR / "index.html"

THUMB_WIDTH = 200


def main():
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    if not rows:
        print("✗ 索引为空")
        return 1

    missing = [r for r in rows if not (ROOT / r["image"]).exists()]
    cards = [r for r in rows if (CARD_DIR / f"{r['card']}.html").exists()]
    if missing or len(cards) != len(rows):
        print(f"✗ 有 {len(missing)} 张图或 {len(rows) - len(cards)} 份卡片页缺失，停止生成")
        return 1

    e = html.escape
    out = [
        "<!DOCTYPE html>",
        '<html lang="ja">',
        "<head>",
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>妖怪图鉴 {len(cards)} 条</title>",
        "<style>",
        "body{font-family:system-ui,sans-serif;margin:2rem;line-height:1.6}",
        ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(15rem,1fr));gap:1.5rem}",
        "figure{margin:0}",
        "img{width:100%;height:auto;background:#f4f2ec;border:1px solid #ddd}",
        "figcaption{font-size:.85rem;margin-top:.4rem}",
        ".a{color:#990000}",
        "</style>",
        "</head>",
        "<body>",
        "",
        f"<h1>妖怪图鉴 {len(cards)} 条</h1>",
        "",
        '<div class="grid">',
    ]
    for r in sorted(rows, key=lambda x: x["yokai"]):
        name = e(r["yokai"])
        card = f"{r['card']}.html"
        who = r["author"] if r["author"] and r["author"] != "—" else "无署名"
        out += [
            "<figure>",
            f'<a href="{e(card)}"><img src="../image/{e(r["image"].split("/")[-1])}" '
            f'width="{THUMB_WIDTH}" loading="lazy" decoding="async" alt="{name}"></a>',
            f'<figcaption><a class="a" href="{e(card)}">{name}</a><br>{e(who)}</figcaption>',
            "</figure>",
        ]
    out += ["</div>", "", "</body>", "</html>", ""]

    text = "\n".join(out)
    changed = not OUT.exists() or OUT.read_text(encoding="utf-8") != text
    if changed:
        OUT.write_text(text, encoding="utf-8")
    print(f"✓ 图鉴索引 {len(cards)} 条，{'已写入' if changed else '无变化'} {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
