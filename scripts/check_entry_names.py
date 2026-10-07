#!/usr/bin/env python3
"""校验 image_index.json 的条目名是否真有卡片依据，可选就地修复。

条目名是「读音＋汉字」，而卡片的题材写在 title 与 subject 里。名字若在
title 与 subject 中都查不到（含汉字形与读音两种写法），就是流水线凭空
造的，必须改回卡片自己的 title。

    python3 scripts/check_entry_names.py          # 只报告
    python3 scripts/check_entry_names.py --fix    # 就地改回 title
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
IDX = ROOT / "data" / "image_index.json"
SAMP = ROOT / "data" / "yokai_sample.json"

LEAD_KANA = re.compile(r"^([\u30a1-\u30f6ー]+)(.*)$")


def split_name(name):
    """'シシ獅子' → ('シシ', '獅子')；纯假名则汉字侧为空。"""
    m = LEAD_KANA.match(name)
    return (m.group(1), m.group(2)) if m else ("", name)


def terms(text):
    """把 '鬼；オニ，猫；ネコ' 拆成 {('鬼','オニ'), ('猫','ネコ')}。

    只认术语级匹配：子串匹配会把 'シシ獅子' 的读音 シシ 判成出现在
    'イノシシ'（野猪）里，那是假的。
    """
    out = set()
    for chunk in re.split(r"[，,、]", text):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = [p.strip() for p in re.split(r"[；：:]", chunk) if p.strip()]
        if len(parts) == 1:
            out.add((parts[0], ""))
        else:
            out.add((parts[0], parts[1]))
    return out


def supported(name, pairs):
    kana, kanji = split_name(name)
    for tk, tr in pairs:
        if kanji and tk == kanji:
            return True
        if kana and tr == kana:
            return True
        if not kanji and (tk == name or tr == name):
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--fix",
        metavar="CARD_ID",
        action="append",
        default=[],
        help="改回该卡片自称的名字，可重复。必须显式指定——本脚本只做字符串匹配，"
        "分不清「シシ」出现在「イノシシ」里是野猪还是狮子，改哪些要人来定。",
    )
    args = ap.parse_args()

    rows = json.loads(IDX.read_text(encoding="utf-8"))
    by_card = {s["card"]: s for s in json.loads(SAMP.read_text(encoding="utf-8"))}

    flagged = {}
    for r in rows:
        s = by_card.get(r["card"])
        if not s:
            continue
        pairs = terms(s["title"]) | terms(s["subject"])
        if not supported(r["yokai"], pairs):
            flagged[r["card"]] = (r["yokai"], s["title"], s["subject"])

    print(f"条目 {len(rows)}  需人工判定的 {len(flagged)}")
    for card, (name, title, subject) in flagged.items():
        mark = " ← 待改" if card in args.fix else ""
        print(f"  {name:22s} card={card}{mark}")
        print(f"      title=「{title}」 subject=「{subject}」→ 卡片自称「{title.split('；')[0]}」")

    if not args.fix:
        return 1 if flagged else 0

    unknown = [c for c in args.fix if c not in by_card]
    if unknown:
        print(f"✗ 未知卡片：{unknown}")
        return 1

    want = {}
    for card in args.fix:
        want[card] = by_card[card]["title"].split("；")[0].strip()
    for r in rows:
        if r["card"] in want:
            print(f"  {r['yokai']} → {want[r['card']]}  ({r['card']})")
            r["yokai"] = want[r["card"]]
    IDX.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n✓ 已修正 {len(want)} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
