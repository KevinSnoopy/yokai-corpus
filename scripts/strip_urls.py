#!/usr/bin/env python3
"""把研究文件里的远程链接全部换成本地快照引用。

理由：材料应自足。读者不该被导向外部站点——对方改版、下线、或被墙时，
结论就失去可复核依据。证据已于 2026-10-06 抓成本地快照。

处理原则：
  A. 出处引用（`https://...`）→ 换成快照编号 + 本地路径。
     原始 URL 仅保留在机器可读的 archive/pages/index.json，不进正文。
  B. 数据库用法示例（URL 路径本身就是内容）→ 改写为不含域名的路径描述，
     并指向本地快照。直接删掉会毁掉「这个库怎么查」的信息。

用法：python3 strip_urls.py [--check]
"""
import hashlib
import json
import pathlib
import re
import sys

RESEARCH = pathlib.Path("/root/shared/novel-continuity-engine/novels/touryoke/research")
IDX = pathlib.Path("/root/workspace/yokai_research/archive/pages/index.json")

# 用法示例：URL 的**路径**是内容，域名不是。改为描述路径形态。
USAGE = [
    (r"`https://sekiei\.nichibun\.ac\.jp/cgi-bin/YoukaiDB3/msearch/msearch\.cgi\?query=河童`",
     "`YoukaiDB3/msearch/msearch.cgi?query=<词>`（全文检索，返回命中总数＋分页）"),
    (r"`https://www\.nichibun\.ac\.jp/cgi-bin/YoukaiGazou/search\.cgi\?query=NILL&ychar=鬼`",
     "`YoukaiGazou/search.cgi?query=NILL&ychar=<妖名>`（画像库名称检索）"),
    (r"`https://www\.nichibun\.ac\.jp/cgi-bin/YoukaiGazou/card\.cgi\?identifier=<id>`",
     "`YoukaiGazou/card.cgi?identifier=<卡片ID>`（画像库卡片页）"),
]

DOMAIN = re.compile(r"`https?://[^`]+`")


def snap_id(url):
    return hashlib.sha1(url.encode()).hexdigest()[:12]


def load_index():
    if not IDX.exists():
        return {}
    return {r["url"]: r for r in json.loads(IDX.read_text(encoding="utf-8"))}


def strip_file(p, idx, report):
    s = p.read_text(encoding="utf-8")
    orig = s

    # B. 先处理用法示例（在 A 之前，避免被通用规则吞掉）
    for pat, repl in USAGE:
        s = re.sub(pat, repl, s)

    # A. 其余一律换成快照引用
    def repl(m):
        u = m.group(0).strip("`")
        rec = idx.get(u)
        sid = snap_id(u)
        if rec and rec.get("status") == 200:
            report["ok"] += 1
            return f"【存档 `pages/{sid}.html`】"
        report["nosnap"] += 1
        return f"【未存档｜快照号 {sid}】"

    s = DOMAIN.sub(repl, s)
    if s != orig:
        p.write_text(s, encoding="utf-8")
    return s


def main():
    idx = load_index()
    if not idx:
        print("✗ 找不到快照索引，先跑 grab_pages.py")
        sys.exit(1)

    check = "--check" in sys.argv
    if check:
        total = 0
        for p in sorted(RESEARCH.glob("yokai_*.md")):
            n = len(DOMAIN.findall(p.read_text(encoding="utf-8")))
            if n:
                total += n
                print(f"  {p.name}: {n} 处远程链接")
        print(f"合计 {total} 处")
        return

    report = {"ok": 0, "nosnap": 0}
    for p in sorted(RESEARCH.glob("yokai_*.md")):
        before = len(DOMAIN.findall(p.read_text(encoding="utf-8")))
        strip_file(p, idx, report)
        after = len(DOMAIN.findall(p.read_text(encoding="utf-8")))
        if before:
            print(f"  {p.name}: {before} → {after}")

    print(f"\n换成已有快照 {report['ok']} 处；标为未存档 {report['nosnap']} 处")

    # 断言：正文不得再有远程链接
    left = 0
    for p in sorted(RESEARCH.glob("yokai_*.md")):
        left += len(DOMAIN.findall(p.read_text(encoding="utf-8")))
    print(f"剩余远程链接：{left}")
    sys.exit(1 if left else 0)


if __name__ == "__main__":
    main()