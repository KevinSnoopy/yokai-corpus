#!/usr/bin/env python3
"""把各文档出处节里重复的通用来源清单收敛到 yokai_00 一处。

12 个快照（维基百科日文『妖怪』『妖怪談義』『柳田國男』、中文 Category 两项、
英文数据库、NDL Search、nccjapan、YOKAI.JP、中文学术综述、妖怪学访谈、
付丧神说明）在 5–7 份文档的出处节里逐字重复。它们的信息保留一次，写进
yokai_00 的出处清单；其余文档换成一行指针。

只动出处节，且只删「整条目的快照全部属于通用集合」的条目——部分含通用快照
的条目保留原样，避免丢描述文字。
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
HUB = "yokai_00_读法与判据.md"

GENERIC = {
    "2ef4c1b4bd60", "3801e13f1017", "3f420715d6ee", "62025d8d8518",
    "65a7bfb5ce9a", "7e9faa0e556c", "a32e01380c3a", "a383a8b4ad85",
    "b1832cf392dd", "c23e709007f6", "c340bd5eced0", "f08dbb46dff0",
}
POINTER = (
    "通用来源（维基百科日文『妖怪』『妖怪談義』『柳田國男』、中文 Category 两项、"
    "英文数据库、NDL Search、nccjapan、YOKAI.JP、中文学术综述、妖怪学访谈、"
    "付丧神说明共 12 项）见 " + f"《{HUB[:-3]}》" + " 的出处清单。\n"
)
BLOCK = """**通用来源（全库共用，只此一处列出）**

| 来源 | 快照 |
|---|---|
| 中文维基 `Category:日本妖怪` | `pages/f08dbb46dff0.html` |
| 中文维基 `Category:妖怪` | `pages/c23e709007f6.html` |
| 日文维基『妖怪談義』 | `pages/65a7bfb5ce9a.html` |
| 日文维基『妖怪』 | `pages/2ef4c1b4bd60.html` |
| 日文维基『柳田國男』 | `pages/62025d8d8518.html` |
| 英文维基 Kaii-Yōkai Denshō Database | `pages/c340bd5eced0.html` |
| NDL Search（妖怪百科书目） | `pages/7e9faa0e556c.html` |
| nccjapan 画像库资源页 | `pages/3f420715d6ee.html` |
| YOKAI.JP 妖怪図鑑 | `pages/b1832cf392dd.html` |
| 中文学术综述（长野荣俊等《国际社会科学杂志》2022 年第 4 期） | `pages/a32e01380c3a.html` |
| 妖怪学访谈（ミツカン水の文化センター） | `pages/3801e13f1017.html` |
| 付费丧神说明 | `pages/a383a8b4ad85.html` |

原 URL 与 SHA-256 见 `archive/pages/index.json`。

"""
SNAP = re.compile(r"pages/([0-9a-f]{12})\.html")
ENTRY = re.compile(r"^(?:- |\*\*)")


def split_entries(lines):
    """出处节切成条目：`- ` 或 `**` 开头算新条目，其余算续行。"""
    out = []
    for line in lines:
        if ENTRY.match(line) or not out:
            out.append([line])
        else:
            out[-1].append(line)
    return out


def drop_empty_headings(entries):
    """条目被删光后，`**小标题**` 会变成空壳，一并去掉。"""
    out = []
    for e in entries:
        if e[0].startswith("**") and len(e) == 1:
            continue
        out.append(e)
    return out


def main():
    for path in sorted(ROOT.glob("yokai_0*.md")):
        ls = path.read_text(encoding="utf-8").splitlines()
        hi = next((i for i, l in enumerate(ls) if l.startswith("## ") and "出处" in l), None)
        if hi is None:
            continue
        end = next((j for j in range(hi + 1, len(ls)) if ls[j].startswith("## ")), len(ls))
        entries = split_entries(ls[hi + 1 : end])

        first = next((x for e in entries for x in e if x.strip()), "")
        if first.startswith("通用来源见") or first.startswith("**通用来源"):
            print(f"  {path.name:34s} 已收敛，跳过")
            continue

        if path.name == HUB:
            body = [BLOCK.rstrip("\n").splitlines()] + entries
        else:
            kept = []
            for e in entries:
                snaps = {s for line in e for s in SNAP.findall(line)}
                # 子标题整块删；条目仅当快照全部通用才删，保留混合条目
                if snaps and snaps <= GENERIC:
                    continue
                if e[0].startswith("通用来源见"):
                    continue
                kept.append(e)
            body = [["通用来源见 " + f"《{HUB[:-3]}》" + " 出处清单。"]] + drop_empty_headings(kept)

        new = ls[: hi + 1] + [x for e in body for x in e] + ls[end:]
        delta = len(new) - len(ls)
        path.write_text("\n".join(new) + "\n", encoding="utf-8")
        print(f"  {path.name:34s} {len(ls):4d} → {len(new):4d} 行 ({delta:+d})")


if __name__ == "__main__":
    sys.exit(main())
