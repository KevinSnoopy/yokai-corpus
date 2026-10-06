#!/usr/bin/env python3
"""妖怪知识库自检：拆分/重组后必查的几项。

现有 verify_all.py 不覆盖以下维度，而这几项正是重组时最容易出错的地方：
  1. 《文件名》交叉引用是否指向真实存在的文件
  2. 是否残留旧式 §x.y 编号引用
  3. 是否残留容器本地路径（ima 端不可访问，对读者无意义）
  4. 是否残留研究日志体措辞（本轮/第N轮/主代理/上一轮）
  5. 是否残留上一版的过期统计（如已改的 181 张）
  6. 标题层级是否断裂（正文全在 #### 之下，profile 的「小节数」统计会失真）
  7. 是否存在空壳括号或悬空标点（批量替换后的典型残留）
  8. 相邻重复标题

用法：python3 check_yokai.py
退出码 0 = 全过。
"""
import pathlib
import re
import sys

D = pathlib.Path(__file__).resolve().parents[1]

# 已知的过期数字。
# 注意：这里只收「确定的错误」，不要把合法的不同数字当过期值。
# 反例：「抽样 181 张」与「197 个妖怪名」是两个不同口径的数字，都正确，不要列入。
STALE = []

# 研究日志体措辞：这些词只对当时的研究者有意义，对未来读者是噪声
LOGGY = ["本轮", "上一轮", "主代理", "用户未提及", "用户说"]

BAD_PATH = re.compile(r"~/workspace|~/shared|/root/")


def check_refs():
    """《文件名》交叉引用必须指向真实文件。

    正则要求书名号内不含句读——引用后面紧跟「）》或「》。」时应正确截断。
    """
    problems = []
    refs = set()
    for p in D.glob("yokai_*.md"):
        for m in re.findall(r"《(yokai_[^》\n]+?)》", p.read_text(encoding="utf-8")):
            refs.add((m, p.name))
    for ref, src in sorted(refs):
        if not (D / f"{ref}.md").exists():
            problems.append(f"交叉引用指向不存在的文件：《{ref}》（出自 {src}）")
    return problems


def check_patterns():
    problems = []
    for p in sorted(D.glob("yokai_*.md")):
        s = p.read_text(encoding="utf-8")
        for kw in LOGGY:
            n = len(re.findall(kw, s))
            if n:
                problems.append(f"{p.name}：残留研究日志体措辞「{kw}」{n} 处")
        for old, why in STALE:
            if old in s:
                problems.append(f"{p.name}：残留过期统计「{old}」——{why}")
        for m in BAD_PATH.finditer(s):
            line = s[: m.start()].count("\n") + 1
            problems.append(f"{p.name}:{line}：残留容器路径「{m.group()}」（ima 端不可访问）")
        # 旧式编号引用。§9 出现在 profile 摘要块里，是 gen_file_profiles.py
        # 的模板文字，不算残留——跳过 profile 区块再检查。
        body = re.sub(r"<!-- profile:begin -->.*?<!-- profile:end -->", "", s, flags=re.S)
        if re.search(r"§\d", body):
            problems.append(f"{p.name}：残留旧式 §编号引用")
    return problems


def check_headings():
    problems = []
    for p in sorted(D.glob("yokai_*.md")):
        lines = p.read_text(encoding="utf-8").split("\n")
        h2 = [i for i, l in enumerate(lines) if l.startswith("## ")]
        # 相邻重复标题
        for a, b in zip(h2, h2[1:]):
            if lines[a] == lines[b]:
                problems.append(f"{p.name}:{a+1}：相邻重复标题「{lines[a]}」")
        # 层级断裂：正文小节都在 #### 之下而缺 ### 承接
        if p.name.startswith("yokai_0") and p.name[7] != "0":
            body = [l for l in lines if re.match(r"^#{3,6} ", l)]
            deep = [l for l in lines if l.startswith("#### ")]
            mids = [l for l in lines if l.startswith("### ")]
            if deep and not mids:
                problems.append(f"{p.name}：标题层级断裂——{len(deep)} 个 #### 但无 ### 承接")
    return problems


def check_punctuation():
    problems = []
    pats = [
        (r"（\s*）", "空壳括号"),
        (r"（\s*）", "空壳括号"),
        (r"（[^）]*\s{3,}[^）]*）", "括号内异常多空格"),
        (r"、。", "悬空标点"),
        (r"，。", "悬空标点"),
        (r"。\s*。", "重复句号"),
        (r"^\s*[-*]\s*$", "空列表项"),
    ]
    for p in sorted(D.glob("yokai_*.md")):
        for i, line in enumerate(p.read_text(encoding="utf-8").split("\n"), 1):
            for pat, desc in pats:
                if re.search(pat, line):
                    problems.append(f"{p.name}:{i}：{desc} — {line.strip()[:50]}")
                    break
    return problems


def main():
    groups = [
        ("交叉引用", check_refs()),
        ("残留模式", check_patterns()),
        ("标题结构", check_headings()),
        ("标点残留", check_punctuation()),
    ]
    total = 0
    for name, problems in groups:
        if problems:
            print(f"── {name} ──")
            for x in problems:
                print(f"  ✗ {x}")
            total += len(problems)
        else:
            print(f"  ✓ {name}")
    print()
    if total:
        print(f"✗ 共 {total} 项问题")
        return 1
    print("✓ 妖怪知识库自检全过")
    return 0


if __name__ == "__main__":
    sys.exit(main())