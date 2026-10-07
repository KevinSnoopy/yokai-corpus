#!/usr/bin/env python3
"""把卡片页瘦身成图鉴条目：只留妖名、图、介绍与出处。

原页是日文研究中心的整页快照，裹着三层布局表格、失效的检索表单、
指向原站 script/ 的死脚本、IIIF 按钮与页脚导航——离线打开全是死的。
本脚本抽出有价值的字段，重新吐一页干净的 HTML。

字段取自原页的 dataTable，并逐条校验；抽不全就整页跳过，绝不写出半成品。
已瘦身的页（没有 dataTable）会被跳过，所以重复运行安全。
"""
import html
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CARD_DIR = ROOT / "archive" / "card"

MARK = "dataTable"
IMG = re.compile(r'<img\b[^>]*?\bsrc="([^"]+)"')
COPYRIGHT = re.compile(r"Copyright \(c\)[^<]*")

FIELDS = ("タイトル", "著作者", "主題", "内容記述", "日付", "情報源", "資源識別子")


def plain(html_fragment):
    text = re.sub(r"<[^>]+>", "", html_fragment)
    return re.sub(r"\s+", " ", text).strip()


def field(text, label):
    m = re.search(
        r"<th><p>" + label + r"</p></th>\s*<td[^>]*>(.*?)</td>", text, re.S
    )
    return plain(m.group(1)) if m else ""


def extract(text):
    """抽齐必备字段才算成功。内容記述和图缺一不可。"""
    img = IMG.search(text)
    data = {label: field(text, label) for label in FIELDS}
    # 标题回退链：有 29 页的 タイトル 字段与 h2 都是空的，只有 <title> 里有名字。
    title = data["タイトル"]
    for pattern in (r"<title>(.*?)</title>", r"<h2>(.*?)</h2>"):
        if not title:
            m = re.search(pattern, text, re.S)
            title = plain(m.group(1)) if m else ""
    data["タイトル"] = title or data["資源識別子"]
    data["image"] = img.group(1) if img else ""
    data["copyright"] = plain(COPYRIGHT.search(text).group(0)) if COPYRIGHT.search(text) else ""
    return data


def render(d):
    e = html.escape
    out = [
        "<!DOCTYPE html>",
        '<html lang="ja">',
        "<head>",
        '<meta charset="UTF-8">',
        f"<title>{e(d['タイトル'])}</title>",
        "</head>",
        "<body>",
        "",
        f"<h1>{e(d['タイトル'])}</h1>",
    ]
    if d["主題"] and d["主題"] != d["タイトル"]:
        out.append(f"<p>{e(d['主題'])}</p>")
    out += [
        "",
        f'<img src="{e(d["image"])}" alt="{e(d["タイトル"])}">',
        "",
        f"<p>{e(d['内容記述'])}</p>",
        "",
    ]
    prov = []
    if d["著作者"]:
        prov.append(f"著作者：{d['著作者']}")
    if d["情報源"]:
        prov.append(f"出典：{d['情報源']}")
    if d["日付"]:
        prov.append(f"日付：{d['日付']}")
    if d["資源識別子"]:
        prov.append(f"資源識別子：{d['資源識別子']}")
    if prov:
        out.append(f"<p>{e('／'.join(prov))}</p>")
    if d["copyright"]:
        out += ["", f"<p>{e(d['copyright'])}</p>"]
    out += ["", "</body>", "</html>", ""]
    return "\n".join(out)


def main():
    if not CARD_DIR.is_dir():
        print(f"✗ 找不到 {CARD_DIR}")
        return 1
    files = sorted(CARD_DIR.glob("*.html"))
    if not files:
        print(f"✗ {CARD_DIR} 下没有 html")
        return 1

    written = skipped = already = failed = 0
    problems = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        if MARK not in text:
            already += 1
            continue
        d = extract(text)
        if not d["タイトル"] or not d["内容記述"] or not d["image"]:
            failed += 1
            problems.append(f"{path.name}: 标题/介绍/图 缺 "
                            f"{[k for k in ('タイトル', '内容記述', 'image') if not d[k]]}")
            continue
        if not (path.parent / d["image"]).resolve().exists():
            failed += 1
            problems.append(f"{path.name}: 图片不存在 {d['image']}")
            continue
        path.write_text(render(d), encoding="utf-8")
        written += 1

    print(f"✓ 瘦身 {written} 页，已是图鉴跳过 {already} 页")
    if problems:
        print(f"✗ {failed} 页抽取不全，原样保留")
        for p in problems[:10]:
            print(f"    {p}")
        return 1
    print("✓ 无失败页")
    return 0


if __name__ == "__main__":
    sys.exit(main())
