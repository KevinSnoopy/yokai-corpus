#!/usr/bin/env python3
"""抓取传承库的全文检索结果与记录页，使跨地域统计可在库内复核。

原先 yokai_02／yokai_03 的河童・天狗地域空缺率与异名频次表标【A】，但那批
记录不在库内、只存在于不可达的容器里。本脚本把它们取回来。

检索页参数（当年未记录，此处已复原并写入文档）：
    msearch.cgi?query=<词>&num=100&set=<页码>
记录页：
    https://www.nichibun.ac.jp/YoukaiCard/<7位ID>.html

用法：
    python3 scripts/fetch_records.py 河童 天狗            # 抓取
    python3 scripts/fetch_records.py 河童 --list-only     # 只列 ID 不抓
并发默认 3，对学术服务器友好；已存在的文件会跳过，可断点续跑。
"""
import argparse
import concurrent.futures as futures
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "archive" / "record"
SEARCH = "https://sekiei.nichibun.ac.jp/cgi-bin/YoukaiDB3/msearch/msearch.cgi"
CARD = "https://www.nichibun.ac.jp/YoukaiCard/{}.html"
PER_PAGE = 100

IDS = re.compile(r"YoukaiCard/(\d{7})\.html")
HITS = re.compile(r"(\d+)件ヒットしました")


def get(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "yokai-corpus/1.0"})
            with urllib.request.urlopen(req, timeout=45) as r:
                raw = r.read()
            for enc in ("utf-8", "cp932", "euc-jp"):
                try:
                    return raw.decode(enc), r.status
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", "replace"), r.status
        except Exception as e:
            if i == retries - 1:
                print(f"    放弃 {url}: {e}", file=sys.stderr)
                return None, 0
            time.sleep(1.5 * (i + 1))


def enumerate_ids(term):
    """翻页拿全部记录 ID 与命中总数。"""
    ids, total, page = [], None, 1
    while True:
        q = urllib.parse.quote(term)
        text, status = get(f"{SEARCH}?query={q}&num={PER_PAGE}&set={page}")
        if not text:
            break
        m = HITS.search(re.sub(r"\s+", " ", text))
        if total is None and m:
            total = int(m.group(1))
        found = list(dict.fromkeys(IDS.findall(text)))
        if not found:
            break
        ids.extend(found)
        if total and len(ids) >= total:
            break
        page += 1
        if page > 200:
            break
    return list(dict.fromkeys(ids)), total, page


ROW = re.compile(r"<TR[^>]*>(.*?)</TR>", re.S | re.I)
CELL = re.compile(r"<TD[^>]*>(.*?)</TD>", re.S | re.I)


def cells(row):
    return [
        re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c)).strip() for c in CELL.findall(row)
    ]


def field(text, label):
    """按行取「标签单元格 → 下一个单元格」。

    该库的卡片页是三列 TD 行（■ ｜ 标签 ｜ 值），没有 TH；
    标签单元格内还包着 <FONT>，值单元格也可能为空。
    """
    for row in ROW.findall(text):
        cs = cells(row)
        for i, c in enumerate(cs[:-1]):
            if c == label:
                return cs[i + 1]
    return ""


def fetch_one(term, cid):
    dest = OUT / term / f"{cid}.html"
    if not dest.exists():
        text, status = get(CARD.format(cid))
        if not text or status != 200:
            return cid, None
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
    else:
        text = dest.read_text(encoding="utf-8")
    title = re.search(r"<title>(.*?)</title>", text, re.S)
    return cid, {
        "card": cid,
        "query": term,
        "title": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", title.group(1))).strip()
        if title
        else "",
        "yomi": field(text, "呼称（ヨミ）"),
        "area": field(text, "地域（都道府県名）"),
        "url": CARD.format(cid),
    }


LABELS = (
    "呼称（ヨミ）",
    "呼称（漢字）",
    "地域（都道府県名）",
    "地域（市・郡名）",
    "地域（区町村名）",
)


def extract(text, cid, term):
    title = re.search(r"<title>(.*?)</title>", text, re.S)
    rec = {
        "card": cid,
        "query": term,
        "title": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", title.group(1))).strip()
        if title
        else "",
        "url": CARD.format(cid),
    }
    for lab in LABELS:
        key = {"呼称（ヨミ）": "yomi", "呼称（漢字）": "kanji"}.get(
            lab, "area_" + lab.split("（")[1].rstrip("）")
        )
        rec[key] = field(text, lab)
    return rec


def write_index(update):
    """按检索词浅合并写入。

    每个词一条记录，里面同时存检索元数据（hits/pages/ids）与抽取结果
    （records）。所以必须逐词合并：整份重写会冲掉其它词，逐词替换会
    冲掉该词已抽好的 records。
    """
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "index.json"
    manifest = {}
    if path.exists():
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}
    for term, entry in update.items():
        merged = dict(manifest.get(term, {}))
        merged.update(entry)
        manifest[term] = merged
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def reextract(terms):
    """从已在盘上的 HTML 重抽字段，不联网。

    抽取规则修正过（该库卡片页是三列 TD 行，不是 TH/TD），已抓的文件无需重取。
    """
    manifest = {}
    for term in terms:
        files = sorted((OUT / term).glob("*.html"))
        if not files:
            print(f"  {term}: 盘上无记录，先跑抓取")
            continue
        recs = [extract(p.read_text(encoding="utf-8"), p.stem, term) for p in files]
        keys = [k for k in recs[0] if k.startswith("area_")] if recs else []
        print(f"  {term}: {len(recs)} 条")
        for k in ["yomi", "kanji"] + keys:
            have = sum(1 for r in recs if r.get(k))
            print(f"      {k:16s} 有值 {have:5d}  空 {len(recs) - have:5d}"
                  f"  空缺率 {(len(recs) - have) / len(recs) * 100:5.1f}%")
        manifest[term] = {"fetched": len(recs), "records": recs}
    path = write_index(manifest)
    print(f"\n✓ 清单已更新 {path.relative_to(ROOT)}（共 {len(json.loads(path.read_text(encoding='utf-8')))} 个检索词）")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("terms", nargs="+")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--list-only", action="store_true")
    ap.add_argument(
        "--reextract", action="store_true", help="只从盘上已有 HTML 重抽字段，不联网"
    )
    args = ap.parse_args()

    if args.reextract:
        return reextract(args.terms)

    manifest = {}
    for term in args.terms:
        ids, total, pages = enumerate_ids(term)
        print(f"\n=== {term} ===")
        print(f"  检索页 {pages} 页，命中 {total}，枚举到 ID {len(ids)}")
        # 命中数与页数是检索时的元数据，必须并入已有条目；
        # 直接替换会把 records 抽好的字段冲掉。
        manifest[term] = {"hits": total, "pages": pages, "ids": ids}
        if args.list_only:
            continue

        recs, done, failed = [], 0, []
        with futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(fetch_one, term, c): c for c in ids}
            for fut in futures.as_completed(futs):
                cid, rec = fut.result()
                done += 1
                if rec is None:
                    failed.append(cid)
                else:
                    recs.append(rec)
                if done % 200 == 0 or done == len(ids):
                    print(f"  {done}/{len(ids)}（失败 {len(failed)}）")
        recs.sort(key=lambda r: r["card"])
        witharea = sum(1 for r in recs if r["area"])
        print(f"  完成 {len(recs)} 条；有地域 {witharea}，空 {len(recs) - witharea}")
        print(f"  有呼称 {sum(1 for r in recs if r['yomi'])}")
        manifest[term] = {
            "hits": total,
            "pages": pages,
            "fetched": len(recs),
            "failed": failed,
            "with_area": witharea,
            "records": recs,
        }

    path = write_index(manifest)
    print(f"\n✓ 清单已更新 {path.relative_to(ROOT)}（共 {len(json.loads(path.read_text(encoding='utf-8')))} 个检索词）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
