# 日本妖怪文化研究语料库

一部长篇小说所需的日本妖怪文化背景调查。**自足仓库**——结论与证据同处一地，
不依赖任何外部站点继续在线。

## 怎么用

| 你要做的事 | 查这里 |
|---|---|
| 判断某条结论能不能写进正文 | 《yokai_00_读法与判据》第一节「可引用的数字」 |
| 查某个说法为什么被禁用 | 《yokai_00_读法与判据》「禁用清单」 |
| 查还剩什么没核实 | 《yokai_00_读法与判据》第三节「待核实项」 |
| 查妖怪分几类、异名、日语俗语 | `yokai_02_分类与异名.md` |
| 查同一种妖怪各地怎么不同 | `yokai_03_跨地域实检.md` |
| 查某妖怪形象是谁画的 | `yokai_04_形象源流.md` |
| 查学界怎么解释、争论在哪 | `yokai_05_学理与争鸣.md` |
| 查今天日本怎么拿妖怪做产业 | `yokai_06_妖怪产业化.md` |
| **看图**（181 张妖怪画＋介绍） | `archive/card/index.html` |

## 资料构成

| 目录 | 内容 | 规模 |
|---|---|---|
| `yokai_00` … `yokai_07` | 研究文档 8 份，按「写作时想查什么」组织 | 约 2,800 行 |
| `archive/card/` | 妖怪画图鉴条目 181 份＋索引页 | 0.2 MB |
| `archive/record/` | 传承库记录页 3,210 份（六组检索实抓） | 64 MB |
| `archive/image/` | **妖怪画图像 181 张**（画像数据库） | 21.1 MB |
| `archive/pages/` | 本库引用的外部页面快照 78 份 ＋ 索引 | 11.6 MB |
| `archive/iiif/` | IIIF manifest 36 份（全分辨率取图通道） | 327 KB |
| `data/` | 抓取所得的结构化元数据 | 314 KB |
| `scripts/` | 抓取、生成与校验脚本，可复现 | 45 KB |

## 文档

| 文件 | 回答什么问题 |
|---|---|
| `yokai_00_读法与判据.md` | 置信度分级、**可引用的数字**、判据、待核实项、**禁用清单**、核心结论速览 |
| `yokai_01_数据源与核验.md` | 两大数据库的规模与用法、字段、**引文陷阱**、检索式、本地快照说明 |
| `yokai_02_分类与异名.md` | 分类框架、异名地图、日语俗语 |
| `yokai_03_跨地域实检.md` | 河童・天狗・雪女・猿・座敷童子・鬼・土蜘蛛的跨地域差异 |
| `yokai_04_形象源流.md` | 画家、绘卷、出典的实测对应 |
| `yokai_05_学理与争鸣.md` | 柳田国男、小松和彦、学界争鸣 |
| `yokai_06_妖怪产业化.md` | 各自治体与国立机构的妖怪观光、文化产业化 |
| `yokai_07_图像清单.md` | 181 张妖怪画的清单与画廊（自动生成） |

## 置信度标记

- `【A】` 原始页面可查（快照存于 `archive/`）
- `【B】` 单一可靠来源，未回溯原页
- `【存】` 未能核实，**正文不得引用**

`【快照 pages/xxx.html】` 指向本地证据（12 位前缀，完整文件名见 `archive/pages/`）；
`【无快照｜…】` 说明该来源已下线或本机不可达。

## 关于网址

**正文不载任何网址。** 原始 URL 只保留在 `archive/pages/index.json`
（原 URL → 本地文件、HTTP 状态、SHA-256、抓取时间），机器可读，供溯源。

## 生成与校验

全部脚本均可重复运行，产物幂等。

```bash
# 生成（快照已在库内时无需联网）
python3 scripts/build_image_index.py    # 由 data/image_index.json 生成 yokai_07 清单
python3 scripts/build_image_gallery.py  # 向 yokai_07 注入 181 张图片画廊
python3 scripts/build_card_index.py     # 生成 archive/card/index.html 图鉴索引
python3 scripts/slim_card_pages.py      # 卡片页瘦身为图鉴条目（图＋介绍）
python3 scripts/fix_card_images.py      # 修正卡片页图片路径

# 校验
python3 scripts/check_yokai.py          # 交叉引用、残留措辞、标题层级、标点
python3 scripts/check_entry_names.py    # 图鉴条目名是否有卡片依据
```

抓取（需联网，会覆盖 `archive/`，**不建议在没有必要时运行**）：

```bash
python3 scripts/grab_archive.py         # 卡片页 + 图像 + IIIF manifest
python3 scripts/grab_pages.py           # 本库引用的外部页面
python3 scripts/fetch_authors.py        # 逐件补齐「著作者」等字段
```

图像完整性：181 张 JPEG 头尾魔数校验，**零损坏**。

## 数据来源

主源为日本国立国语研究所（国際日本文化研究センター）的
「怪異・妖怪伝承データベース」与「怪異・妖怪画像データベース」，
以及各自治体・文教机构的公开页面。完整出处见 `archive/pages/index.json`
与各文档末尾的出处节。

图像版权归原权利人所有，此处仅作研究引用——**详见 [NOTICE.md](NOTICE.md)**。
本仓库正文与脚本采用 MIT（`LICENSE`），但 `archive/` 下的图像与页面快照不在此授权范围内。
