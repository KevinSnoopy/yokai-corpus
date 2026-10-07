#!/usr/bin/env python3
"""按 data/card_ids.json 全量抓取卡片图录的页面与图片。

181 张只是站点 3,030 张里已入库的部分，本脚本补齐其余条目。对每张卡抓两样：
页面（抽字段后写成图鉴条目，与既有 181 页同一模板）与 JPEG 本体。

页面来源是 card.cgi?identifier=，不是 YoukaiCard/<id>.html——后者对任何 id
都返回同一个通用模板页，字段全空。裸 urllib 不带 User-Agent 会被 403。

并发默认 3：这是学术服务器，按它的承受力来。可 --resume 断点续跑，已存在的
文件跳过，重复运行只补缺的。
"""
import argparse
import json
import pathlib
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from slim_card_pages import extract, render

ROOT = pathlib.Path(__file__).resolve().parents[1]
CARD_DIR = ROOT / "archive" / "card"
IMG_DIR = ROOT / "archive" / "image"
IIIF_DIR = ROOT / "archive" / "iiif"
IDS_FILE = ROOT / "data" / "card_ids.json"
MANIFEST = CARD_DIR / "manifest.json"

CARD_BASE = "https://www.nichibun.ac.jp/cgi-bin/YoukaiGazou/card.cgi?identifier="
IMG_BASE = "https://www.nichibun.ac.jp/YoukaiGazou/image/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
MANIFEST_RE = re.compile(r"manifest=(https://iiif\.nichibun\.ac\.jp/[^&\"]+)")

for d in (CARD_DIR, IMG_DIR, IIIF_DIR):
    d.mkdir(parents=True, exist_ok=True)


def get(url, timeout=60, tries=3):
    """取回字节；三次重试都失败返回 None（404 也是 None）。"""
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception:
            if a == tries - 1:
                return None
            time.sleep(2 * (a + 1))
    return None


def fetch_one(cid, want_image=True, delay=0.0):
    page = CARD_DIR / f"{cid}.html"
    img = IMG_DIR / f"{cid}.jpg"
    rec = {"card": cid}
    wrote_page = wrote_img = False

    if page.exists() and page.stat().st_size > 400:
        rec["page"] = "skip"
    else:
        raw = get(CARD_BASE + cid)
        if raw is None:
            rec["page"] = "fail"
        else:
            text = raw.decode("utf-8", "replace")
            d = extract(text)
            mf = MANIFEST_RE.search(text)
            if mf:
                rec["manifest"] = mf.group(1)
            if not d["タイトル"] or not d["内容記述"]:
                rec["page"] = "empty"
                rec["missing"] = [k for k in ("タイトル", "内容記述") if not d[k]]
            else:
                d["image"] = f"../image/{cid}.jpg"
                page.write_text(render(d), encoding="utf-8")
                wrote_page = True
                rec["page"] = "ok"
            rec["title"] = d["タイトル"]
            rec["subject"] = d["主題"]
            rec["yokai"] = d["タイトル"].split("；")[0]

    if not want_image:
        rec["image"] = "skip"
    elif img.exists() and img.stat().st_size > 5000:
        rec["image"] = "skip"
        rec["bytes"] = img.stat().st_size
    else:
        b = get(IMG_BASE + f"{cid}.jpg")
        if b and len(b) > 5000:
            img.write_bytes(b)
            wrote_img = True
            rec["image"] = "ok"
            rec["bytes"] = len(b)
        else:
            rec["image"] = "fail"

    if delay:
        time.sleep(delay)
    rec["_wrote"] = (wrote_page, wrote_img)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--delay", type=float, default=0.2)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="", help="逗号分隔的 id 前缀，只抓这些")
    ap.add_argument("--no-images", action="store_true")
    ap.add_argument("--pending-only", action="store_true",
                    help="只抓页或图缺失的条目")
    a = ap.parse_args()

    ids = json.loads(IDS_FILE.read_text(encoding="utf-8"))
    if a.only:
        pref = tuple(p.strip() for p in a.only.split(","))
        ids = [i for i in ids if i.startswith(pref)]
    if a.pending_only:
        ids = [i for i in ids
               if not (CARD_DIR / f"{i}.html").exists()
               or not (IMG_DIR / f"{i}.jpg").exists()]
    if a.limit:
        ids = ids[:a.limit]

    print(f"目标 {len(ids)} 张  并发 {a.workers}  延迟 {a.delay}s"
          f"{'  不抓图' if a.no_images else ''}")

    stats = {}
    recs = []
    manifests = {}
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for i, rec in enumerate(ex.map(
                lambda c: fetch_one(c, not a.no_images, a.delay), ids), 1):
            for k in ("page", "image"):
                stats[f"{k}-{rec.get(k, '-')}"] = stats.get(f"{k}-{rec.get(k, '-')}", 0) + 1
            if rec.get("manifest"):
                manifests[rec["manifest"]] = 1
            recs.append(rec)
            if i % 50 == 0:
                mb = sum(r.get("bytes", 0) for r in recs) / 1048576
                print(f"  {i}/{len(ids)}  {stats}  图 {mb:.0f} MB")

    for url in manifests:
        name = url.rstrip("/").split("/")[-1] + ".json"
        out = IIIF_DIR / name
        if out.exists() and out.stat().st_size > 500:
            continue
        b = get(url)
        if b:
            out.write_bytes(b)

    prev = {}
    if MANIFEST.exists():
        prev = {r["card"]: r for r in json.loads(MANIFEST.read_text(encoding="utf-8"))}
    for r in recs:
        prev[r["card"]] = {k: v for k, v in r.items() if k != "_wrote"}
    allr = sorted(prev.values(), key=lambda r: r["card"])
    MANIFEST.write_text(json.dumps(allr, ensure_ascii=False, indent=1), encoding="utf-8")

    npage = sum(1 for r in allr if (CARD_DIR / f"{r['card']}.html").exists())
    nimg = sum(1 for r in allr if (IMG_DIR / f"{r['card']}.jpg").exists())
    mb = sum((IMG_DIR / f"{r['card']}.jpg").stat().st_size
             for r in allr if (IMG_DIR / f"{r['card']}.jpg").exists()) / 1048576
    print(f"\n{stats}")
    print(f"manifest {len(allr)} 条  页面 {npage}  图 {nimg}（{mb:.0f} MB）  IIIF {len(manifests)}")
    bad = [r for r in allr if r.get("page") in ("fail", "empty") or r.get("image") == "fail"]
    if bad:
        print(f"异常 {len(bad)} 条，明细写入 {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())