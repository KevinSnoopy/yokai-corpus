#!/usr/bin/env python3
"""知识库结构重组的机械部分：删 profile 块、修模板 bug、改名与引用跟改。

语义性的工作（合并判据文件、精简出处节）不在这里做，那些要逐份判断。
本脚本只做可以一次性验证的替换，因此可用 check_yokai.py 复核。

    python3 scripts/restructure.py --dry-run   # 只报告
    python3 scripts/restructure.py             # 执行
"""
import argparse
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

RENAME = {
    "yokai_00_读法与禁用清单.md": "yokai_00_读法与判据.md",
    "yokai_01_数据源与核验方法.md": "yokai_01_数据源与核验.md",
    "yokai_02_妖怪图谱_分类异名与俗语.md": "yokai_02_分类与异名.md",
    "yokai_03_跨地域实检_七个妖怪.md": "yokai_03_跨地域实检.md",
    "yokai_04_形象源流_画家绘卷与出典.md": "yokai_04_形象源流.md",
    "yokai_05_学理_理论谱系与争鸣.md": "yokai_05_学理与争鸣.md",
    "yokai_06_当代日本_妖怪的产业化.md": "yokai_06_妖怪产业化.md",
}
PROFILE = re.compile(r"\n?<!-- profile:begin -->.*?<!-- profile:end -->\n?", re.S)
SKIP = {"CONCLUSIONS_已确认结论.md", "PENDING_待验证与禁用清单.md"}
DOCS = sorted({p for p in ROOT.glob("*.md")})


def strip_profile(text):
    return PROFILE.sub("\n", text)


def fix_template(text):
    """生成器把当前文档名错替换成了「本文件」，留下「本文件 本文件」与自引。"""
    text = re.sub(r"本文件\s*本文件\s*、", "本文件与", text)
    return re.sub(r"本文件\s*本文件", "本文件", text)


def rewrite_refs(text, mapping):
    for old, new in mapping.items():
        text = text.replace(f"《{old[:-3]}》", f"《{new[:-3]}》")
        text = text.replace(old, new)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    changed = []
    for path in DOCS:
        if path.name in SKIP:
            continue
        old = path.read_text(encoding="utf-8")
        new = rewrite_refs(fix_template(strip_profile(old)), RENAME)
        # 判据文件并入 yokai_00 后，指向旧独立文件的引用改指 yokai_00
        new = new.replace("`CONCLUSIONS_已确认结论.md`", "《yokai_00_读法与判据.md》")
        new = new.replace("`PENDING_待验证与禁用清单.md`", "《yokai_00_读法与判据.md》")
        if new != old:
            changed.append((path.name, len(old.splitlines()), len(new.splitlines())))

    for name, a, b in changed:
        print(f"  {name:44s} {a:4d} → {b:4d} 行  ({b - a:+d})")
    print(f"\n共 {len(changed)} 份文档内容有改动")
    print(f"将改名 {len([k for k in RENAME if (ROOT / k).exists()])} 份")

    if args.dry_run:
        print("\n--dry-run：未写入")
        return 0

    for path in DOCS:
        if path.name in SKIP:
            continue
        old = path.read_text(encoding="utf-8")
        new = rewrite_refs(fix_template(strip_profile(old)), RENAME)
        new = new.replace("`CONCLUSIONS_已确认结论.md`", "《yokai_00_读法与判据.md》")
        new = new.replace("`PENDING_待验证与禁用清单.md`", "《yokai_00_读法与判据.md》")
        if new != old:
            path.write_text(new, encoding="utf-8")

    for old, new in RENAME.items():
        src = ROOT / old
        if src.exists():
            src.rename(ROOT / new)
            print(f"  改名 {old} → {new}")

    out = subprocess.run(
        [sys.executable, "scripts/check_yokai.py"], cwd=ROOT, capture_output=True, text=True
    )
    print("\n=== check_yokai.py ===")
    print(out.stdout.strip())
    return out.returncode


if __name__ == "__main__":
    sys.exit(main())
