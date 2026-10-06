#!/usr/bin/env python3
"""把画像数据库 181 张卡片的本地快照抓下来。

抓三类东西（对应三种失效风险）：
  1. card/<id>.html   —— 卡片页原文。字段会变、页面会下线，HTML 是唯一快照。
  2. image/<id>.jpg   —— 妖怪画本身（约 105KB/张）。图鉴的主体。
  3. iiif/<work>.json —— IIIF manifest。保留下一个访问全分辨率的正规通道，
     同一作品多个卡片共用一份，按 manifest URL 去重。

断点续跑：已存在的文件跳过。中断后重跑即可。
"""
import json
import pathlib
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = pathlib.Path("/root/workspace/yokai_research/archive")
CARD_BASE = "https://www.nichibun.ac.jp/cgi-bin/YoukaiGazou/card.cgi?identifier="
IMG_BASE = "https://www.nichibun.ac.jp/YoukaiGazou/image/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

for d in ("card", "image", "iiif"):
    (BASE / d).mkdir(parents=True, exist_ok=True)


def get(url, timeout=60, tries=3):
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


def grab_html(rec):
    cid = rec["card"]
    out = BASE / "card" / f"{cid}.html"
    if out.exists() and out.stat().st_size > 2000:
        return "html-skip", None
    b = get(CARD_BASE + cid)
    if not b:
        return "html-fail", None
    out.write_bytes(b)
    # 同时把页里出现的 IIIF manifest 记下来
    found = re.findall(r"manifest=(https://iiif\.nichibun\.ac\.jp/[^&\"]+)", b.decode("utf-8", "replace"))
    return "html-ok", found[0] if found else None


def grab_img(cid):
    out = BASE / "image" / f"{cid}.jpg"
    if out.exists() and out.stat().st_size > 5000:
        return "img-skip", 0
    b = get(IMG_BASE + cid + ".jpg")
    if not b:
        return "img-fail", 0
    out.write_bytes(b)
    return "img-ok", len(b)


def main():
    recs = json.loads(pathlib.Path("/root/workspace/yokai_research/visual/"
                                   "yokai_sample.json").read_text(encoding="utf-8"))
    print(f"卡片 {len(recs)} 张")

    # 阶段 1：卡片页 HTML（顺带提取 manifest）
    stats = {}
    manifests = {}
    with ThreadPoolExecutor(max_workers=3) as ex:
        for i, (st, mf) in enumerate(ex.map(grab_html, recs), 1):
            stats[st] = stats.get(st, 0) + 1
            if mf:
                manifests[mf] = 1
            if i % 20 == 0:
                print(f"  HTML {i}/{len(recs)}  {stats}")
    print(f"HTML 阶段完成：{stats}；发现 manifest {len(manifests)} 个")

    # 阶段 2：卡片图
    ids = [r["card"] for r in recs]
    total = 0
    with ThreadPoolExecutor(max_workers=3) as ex:
        for i, (st, n) in enumerate(ex.map(grab_img, ids), 1):
            stats[st] = stats.get(st, 0) + 1
            total += n
            if i % 20 == 0:
                print(f"  IMG {i}/{len(ids)}  {stats}")
    print(f"图片阶段完成：{stats}；本次新增 {total/1048576:.1f} MB")

    # 阶段 3：IIIF manifest（去重）
    ok = 0
    for url in manifests:
        name = url.rstrip("/").split("/")[-1] + ".json"
        out = BASE / "iiif" / name
        if out.exists() and out.stat().st_size > 500:
            ok += 1
            continue
        b = get(url)
        if b:
            out.write_bytes(b)
            ok += 1
    print(f"IIIF manifest：{ok}/{len(manifests)}")

    # 清单
    for d in ("card", "image", "iiif"):
        p = BASE / d
        n = len(list(p.glob("*"))) if p.exists() else 0
        sz = sum(f.stat().st_size for f in p.glob("*")) if p.exists() else 0
        print(f"  {d:6} {n:>4} 个文件  {sz/1048576:>7.1f} MB")


if __name__ == "__main__":
    main()