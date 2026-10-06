#!/usr/bin/env python3
"""把研究库引用的全部外部页面抓成本地快照。

理由：研究文件里全是裸 URL。对方站点改版、下线、或被 CDN 挡住时，
结论就失去可复核的依据。快照 + 清单让结论与证据一起留���。

产出：
  archive/pages/<sha1>.html   页面原文
  archive/pages/index.json    URL → 本地文件、HTTP 状态、抓取时间、SHA-256

用法：
  python3 grab_pages.py                 # 抓全部
  python3 grab_pages.py --check         # 只体检哪些还活着，不下载
"""
import hashlib
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

RESEARCH = pathlib.Path("/root/shared/novel-continuity-engine/novels/touryoke/research")
OUT = pathlib.Path("/root/workspace/yokai_research/archive/pages")
OUT.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

URL_RE = re.compile(r"https?://[^\s)`\"'，。；、]+")


def collect_urls():
    urls = set()
    for p in sorted(RESEARCH.glob("yokai_*.md")):
        text = p.read_text(encoding="utf-8")
        # 只取反引号里的 URL（正文中裸写的多是示例域名，不抓）
        for m in re.findall(r"`(https?://[^`]+)`", text):
            urls.add(m.strip().rstrip(".,;"))
        # 以及行内的真实引用
        for m in URL_RE.findall(text):
            u = m.strip().rstrip(".,;")
            if "example.com" in u or u.count("/") < 3:
                continue
            urls.add(u)
    return sorted(urls)


def key(u):
    return hashlib.sha1(u.encode()).hexdigest()


def enc(u):
    """非 ASCII 路径需百分号编码，否则 urllib 抛 UnicodeEncodeError。"""
    sp = urllib.parse.urlsplit(u)
    return urllib.parse.urlunsplit((
        sp.scheme, sp.netloc,
        urllib.parse.quote(sp.path, safe="/%:@&=+$,~"),
        urllib.parse.quote(sp.query, safe="/%:@&=+$,?~"),
        sp.fragment))


def fetch(u):
    dest = OUT / f"{key(u)}.html"
    req = urllib.request.Request(enc(u), headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "ja,en;q=0.8",
    })
    rec = {"url": u, "file": dest.name}
    for a in range(2):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                body = r.read()
                rec.update(status=r.status, bytes=len(body),
                           sha256=hashlib.sha256(body).hexdigest(),
                           final_url=r.url, fetched="2026-10-06")
                dest.write_bytes(body)
                return rec
        except urllib.error.HTTPError as e:
            rec.update(status=e.code, error=str(e), fetched="2026-10-06")
            if e.code in (403, 404, 410):
                return rec
        except Exception as e:
            rec.update(status=None, error=f"{type(e).__name__}: {e}",
                       fetched="2026-10-06")
        time.sleep(1.5)
    return rec


def main():
    urls = collect_urls()
    print(f"待抓 {len(urls)} 个 URL\n")
    only_check = "--check" in sys.argv

    if only_check:
        def probe(u):
            # 用 GET 不用 HEAD：实测 nichibun 等站点对 HEAD 返回 500，是假象
            req = urllib.request.Request(enc(u), headers={"User-Agent": UA})
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    return u, r.status, len(r.read())
            except urllib.error.HTTPError as e:
                return u, e.code, 0
            except Exception as e:
                return u, type(e).__name__, 0
        with ThreadPoolExecutor(max_workers=5) as ex:
            res = list(ex.map(probe, urls))
        for u, st, n in sorted(res, key=lambda x: str(x[1])):
            print(f"  {str(st):>14}  {n:>8}B  {u}")
        return

    recs = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        for i, r in enumerate(ex.map(fetch, urls), 1):
            recs.append(r)
            if i % 15 == 0:
                print(f"  {i}/{len(urls)}")
    (OUT / "index.json").write_text(
        json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")

    ok = [r for r in recs if r.get("status") == 200]
    bad = [r for r in recs if r.get("status") != 200]
    size = sum(r.get("bytes", 0) for r in ok)
    print(f"\n成功 {len(ok)}/{len(recs)}，共 {size/1048576:.1f} MB")
    print(f"index.json: {OUT/'index.json'}")
    if bad:
        print("\n未成功：")
        for r in bad:
            print(f"  {r.get('status')}  {r['url']}")


if __name__ == "__main__":
    main()