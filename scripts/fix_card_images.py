#!/usr/bin/env python3
"""修 archive/card/*.html 快照里的图片断链。

卡片页抓取时保留了原站的相对路径，图片其实就躺在 archive/image/，
但 src 指着的 ../../YoukaiGazou/image/ 目录在本仓库不存在——快照自初始
提交起就是坏的。这里做两件事：

  1. 作品图 src 改写为 ../image/，指向本仓库真实位置。
  2. 删掉 parts/ 的站点装饰图（<img> 与 background 属性）。这些从未被
     归档，离线补不回来，留着只会显示破图。

只动图片。href / action / script 一律不碰——那是导航与表单，不是本次范围。
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CARD_DIR = ROOT / "archive" / "card"

ARTWORK_OLD = 'src="../../YoukaiGazou/image/'
ARTWORK_NEW = 'src="../image/'

PARTS_IMG = re.compile(
    r'<img\b[^>]*\bsrc="[^"]*YoukaiGazou/parts/[^"]*"[^>]*>[ ]?'
)
PARTS_BG = re.compile(r'[ \t]+background="[^"]*YoukaiGazou/parts/[^"]*"')
IMG_SRC = re.compile(r'<img\b[^>]*?\bsrc="([^"]+)"')


def fix(text):
    artwork = text.count(ARTWORK_OLD)
    text = text.replace(ARTWORK_OLD, ARTWORK_NEW)
    imgs = len(PARTS_IMG.findall(text))
    text = PARTS_IMG.sub("", text)
    bgs = len(PARTS_BG.findall(text))
    text = PARTS_BG.sub("", text)
    return text, artwork, imgs, bgs


def main():
    if not CARD_DIR.is_dir():
        print(f"✗ 找不到 {CARD_DIR}")
        return 1

    files = sorted(CARD_DIR.glob("*.html"))
    if not files:
        print(f"✗ {CARD_DIR} 下没有 html")
        return 1

    artwork = imgs = bgs = 0
    changed = 0
    dangling = []

    for path in files:
        original = path.read_text(encoding="utf-8")
        fixed, n_artwork, n_imgs, n_bgs = fix(original)
        artwork += n_artwork
        imgs += n_imgs
        bgs += n_bgs
        if fixed != original:
            path.write_text(fixed, encoding="utf-8")
            changed += 1
        for m in IMG_SRC.finditer(fixed):
            if not (path.parent / m.group(1)).resolve().exists():
                dangling.append(f"{path.name}: {m.group(1)}")

    print(f"✓ 作品图改写 {artwork} 处，删除装饰 <img> {imgs} 个、background 属性 {bgs} 个")
    print(f"✓ 扫描 {len(files)} 个文件，改动 {changed} 个")

    if dangling:
        print(f"✗ 仍有 {len(dangling)} 处图片 src 指向不存在的文件")
        for d in dangling[:10]:
            print(f"    {d}")
        return 1
    print("✓ 无残留断链")
    return 0


if __name__ == "__main__":
    sys.exit(main())
