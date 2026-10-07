#!/usr/bin/env python3
"""从 archive/card 的瘦身页重建 data/image_index.json。

瘦身页是唯一真源：卡片页入库后不再回源改写，所以索引必须能从页面反解出来，
否则新增条目无从进索引。页面模板由 slim_card_pages.py 生成，结构固定，
出处行是「著作者／出典／日付／資源識別子」拼成的一段，按全角分隔符拆回字段。

顺带报出同妖名的多卡情况——全量入库后一个妖名往往对应多张卡，
这与早先「每个妖名取首张」的口径不同，统计时必须区分条目数与卡片数。
"""
import html
import json
import pathlib
import re
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
CARD_DIR = ROOT / "archive" / "card"
IMG_DIR = ROOT / "archive" / "image"
OUT = ROOT / "data" / "image_index.json"

H1 = re.compile(r"<h1>(.*?)</h1>", re.S)
SUBJ = re.compile(r'<p><a href="index\.html">.*?</a></p>\s*<p>(.*?)</p>', re.S)
IMG = re.compile(r'<img[^>]+src="\.\./image/([^"]+)"')
DESC = re.compile(r"</p>\s*<p>(.*?)</p>", re.S)
PROV = re.compile(r"<p>著作者：(.*?)</p>", re.S)


def plain(fragment):
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def main():
    pages = sorted(p for p in CARD_DIR.glob("*.html") if p.name != "index.html")
    rows = []
    problems = []
    for p in pages:
        text = p.read_text(encoding="utf-8")
        cid = p.stem
        title = plain(H1.search(text).group(1)) if H1.search(text) else ""
        if not title:
            problems.append(f"{cid}: 无标题")
            continue
        m = IMG.search(text)
        if not m:
            problems.append(f"{cid}: 无图片引用")
            continue
        if not (IMG_DIR / m.group(1)).exists():
            problems.append(f"{cid}: 图片不在盘上 {m.group(1)}")
            continue
        prov = {}
        pm = PROV.search(text)
        if pm:
            for part in plain(pm.group(1)).split("／"):
                if "：" in part:
                    k, v = part.split("：", 1)
                    prov[k] = v
        rows.append({
            "card": cid,
            "yokai": title.split("；")[0],
            "title": title,
            "author": prov.get("著作者") or "—",
            "source": prov.get("出典") or "—",
            "date": prov.get("日付") or "—",
            "image": f"archive/image/{m.group(1)}",
            "bytes": (IMG_DIR / m.group(1)).stat().st_size,
            "exists": True,
        })

    rows.sort(key=lambda r: (r["yokai"], r["card"]))
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")

    names = Counter(r["yokai"] for r in rows)
    dup = {k: v for k, v in names.items() if v > 1}
    mb = sum(r["bytes"] for r in rows) / 1048576
    print(f"✓ 索引 {len(rows)} 条  妖名 {len(names)} 个  图 {mb:.0f} MB")
    print(f"  同名多卡：{len(dup)} 个妖名占 {sum(dup.values())} 张"
          f"（最多 {max(names.values())} 张：{max(names, key=names.get)}）")
    if problems:
        print(f"✗ {len(problems)} 页抽取不全：")
        for x in problems[:10]:
            print(f"    {x}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())