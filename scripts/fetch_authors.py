#!/usr/bin/env python3
"""补齐画像库 197 个卡片页的「著作者」与「内容記述」字段。

页面结构固定：<th><p>字段名</p></th> 后紧跟 <td valign="top"><p>值</p></td>
服务端约 5.5 秒/请求，3 路并发，预计 20 分钟以内。
进度写入同目录 .progress.json，中断后可续跑。
"""
import json
import pathlib
import re
import html
import sys
import time
from concurrent.futures import ThreadPoolExecutor
import urllib.request

BASE = pathlib.Path("/root/workspace/yokai_research/visual")
SRC = BASE / "yokai_sample.json"
OUT = BASE / "yokai_authors.json"
PROG = BASE / ".progress.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

FIELDS = ["タイトル", "著作者", "寄与者", "日付", "主題", "内容記述", "公開者", "情報源"]


def strip_tags(x):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", x))).strip()


def parse(page):
    """把页面解析成 {字段: 值}。结构：<th><p>名</p></th> <td valign="top"><p>值</p></td>"""
    out = {}
    for name in FIELDS:
        m = re.search(
            r"<th[^>]*>\s*<p>\s*" + re.escape(name) + r"\s*</p>\s*</th>\s*"
            r"<td[^>]*>\s*<p>(.*?)</p>",
            page, re.S)
        out[name] = strip_tags(m.group(1)) if m else ""
    return out


def fetch(rec):
    url = rec["url"]
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                page = r.read().decode("utf-8", "replace")
            if "403 Forbidden" in page[:300] or len(page) < 800:
                time.sleep(3 * (attempt + 1))
                continue
            return rec, parse(page), ""
        except Exception as e:
            if attempt == 2:
                return rec, None, f"{type(e).__name__}: {e}"
            time.sleep(3 * (attempt + 1))
    return rec, None, "retry exhausted"


def save(d):
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(OUT)


def main():
    recs = json.loads(SRC.read_text(encoding="utf-8"))
    done = {}
    if PROG.exists() and OUT.exists():
        done = {r["card"]: r for r in json.loads(OUT.read_text(encoding="utf-8"))}
    todo = [r for r in recs if r["card"] not in done]
    print(f"总计 {len(recs)}，已完成 {len(done)}，待抓 {len(todo)}", flush=True)
    if not todo:
        return 0

    n = 0
    with ThreadPoolExecutor(max_workers=3) as ex:
        for rec, parsed, err in ex.map(fetch, todo):
            n += 1
            if parsed is None:
                done[rec["card"]] = {
                    "card": rec["card"], "yokai": rec["yokai"],
                    "author_raw": "", "author_norm": "", "date": "",
                    "description": "", "status": "ERROR", "error": err,
                }
            else:
                a = parsed["著作者"]
                status = "OK" if a else "EMPTY"
                done[rec["card"]] = {
                    "card": rec["card"], "yokai": rec["yokai"],
                    "author_raw": a, "author_norm": a,
                    "date": parsed["日付"], "description": parsed["内容記述"],
                    "contributor": parsed["寄与者"],
                    "status": status,
                }
            if n % 5 == 0 or n == len(todo):
                save(done)
                print(f"  {n}/{len(todo)}  已存 {len(done)}", flush=True)

    save(done)
    st = {}
    for r in done.values():
        st[r["status"]] = st.get(r["status"], 0) + 1
    print("状态分布：", st)
    return 0


if __name__ == "__main__":
    sys.exit(main())