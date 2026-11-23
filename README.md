# 数说奥运 1896–2024

> 夏季奥运会数据可视分析 · 数据可视分析课程作业
> 数据：`olympics_dataset.csv`（26 MB，252,565 行 × 11 列，1896–2024）
> 许可：CC BY-NC-SA 4.0 · 仅依赖 pandas / numpy · 静态图手写 SVG，交互看板单文件 HTML

---

## 一、项目简介

本项目对 1896–2024 年夏季奥运会的全部参赛与奖牌记录做一次完整的数据分析链路：**数据质量体检 → 清洗与口径定义 → 特征工程与四视角探索 → 静态图与交互看板 → 分析报告**。它要解决的核心问题不是"谁第一"，而是**"这份数据的奖牌数到底该怎么数"**：原始数据的行为粒度是"一名运动员 × 一届 × 一个小项"，团体项目每位成员各占一行，于是同一批记录既能得出 38,360 枚奖牌，也能得出 17,901 枚奖牌，相差 53.3%。项目把两套口径并列贯穿全篇，并以此解释奖牌榜、国家兴衰、女性入场、项目演化与东道主效应中的反直觉现象。

全部图表与结论均可由 `python backend/src/run_all.py` 从原始 CSV 一键复现，无需外部数据、无需联网（交互看板加载 ECharts 除外）。

---

## 二、选题与背景

赛题要求在一份真实、脏、口径不清的奥运数据集上完成四个任务。完成情况如下：

| 赛题任务 | 要求 | 本仓库对应交付 | 状态 |
|---|---|---|---|
| 任务一（必做） | 数据质量体检与口径说明书 | `backend/src/quality_checks.py`（QC1–QC6）+ `docs/Task1/数据质量与口径说明书.md` + `docs/Task1/*.csv` 数据集 | 已完成 |
| 任务二 | 四个视角的探索分析 | 视角 A 格局 / B 国家兴衰 / C 女性奥运 / D 项目演化，共 10 张静态图 | 已完成 |
| 任务三 | 两个专题深挖 | 专题 S2「口径的魔力」、专题 S1「东道主效应」 | 已完成 |
| 任务四（加分项） | 交互式呈现 | `dashboard.html` 单文件看板（7 个图表容器） | 已完成 |

设计取向上的两个取舍：

- **不用 matplotlib**。静态图由手写 SVG 输出，零字体依赖、矢量清晰、可被 XML 解析器直接校验，不依赖绘图库版本。
- **看板单文件自包含**。`dashboard.html` 内嵌数据与样式，只有 ECharts 走 CDN，双击即可打开。

---

## 三、快速开始

### 3.1 环境准备

需要 Python 3.10+ 与 pandas、numpy（本项目已在 `.venv` 中验证，Python 3.12 + pandas 3.1.1）：

```bash
# 已有 .venv 时跳过创建，直接装依赖
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

### 3.2 全量运行（从原始 CSV 到全部图表）

```bash
.venv\Scripts\python backend/src/run_all.py
```

依次执行质量体检 → 清洗与口径构建 → 特征工程与分析 → 可视化，并在结束时自检关键产物。清洗/归一数据集落到 `docs/Task1/`，分析表落到 `outputs/tables/`，图表落到 `figures/`。

### 3.3 仅自检已有产物

```bash
.venv\Scripts\python backend/src/run_all.py --check
```

不重算，只检查关键产物是否存在且非空（覆盖 14 个关键文件 + 图表数量下限 ≥10 张）。

### 3.4 分步运行

```bash
.venv\Scripts\python backend/src/quality_checks.py    # 1. 六项质量体检 → outputs/tables/quality_checks.md
.venv\Scripts\python backend/src/cleaning.py          # 2. 清洗 + 双口径 + 校验 → docs/Task1/、docs/Task1/cleaning_verification.md
.venv\Scripts\python backend/src/features.py          # 3. 特征工程 + 四视角 + 两专题 → outputs/tables/analysis_results.json
.venv\Scripts\python backend/src/visualize.py         # 4. 静态图 + 看板 → figures/、dashboard.html
```

---

## 四、目录结构

```
课设/
├── olympics_dataset.csv          # 原始数据（26 MB）
├── 赛题介绍.md                    # 赛题原文
├── dashboard.html                # 交互式看板（单文件自包含，ECharts 走 CDN）
├── README.md                     # 本文件
├── requirements.txt              # Python 依赖
├── backend/
│   ├── src/
│   │   ├── run_all.py            # 全链路一键入口
│   │   ├── quality_checks.py     # 六项数据质量体检 QC1–QC6
│   │   ├── cleaning.py           # 清洗、双口径构建、NOC 继承链
│   │   ├── features.py           # 特征工程 + 四视角 + 两专题 + 洞察
│   │   └── visualize.py          # 10 张静态 SVG + 交互看板
│   └── api/                      # FastAPI 看板接口 + dashboard.json
├── docs/
│   ├── Task1/                    # 任务一交付物（说明书 + 清洗/归一并集）
│   │   ├── 数据质量与口径说明书.md
│   │   ├── olympics_clean.csv        # 主表 252,565 × 19
│   │   ├── medal_event_level.csv     # 小项口径奖牌表 16,071 行
│   │   ├── noc_year_summary.csv      # 代表团×届次汇总 3,201 行
│   │   ├── features_noc_year.csv     # 特征宽表 3,201 行
│   │   ├── sport_mapping.csv         # Sport 归一映射表（76 → 57）
│   │   ├── noc_lineage.csv           # NOC 继承链映射表
│   │   └── cleaning_verification.md  # 清洗校验报告（脚本生成）
│   ├── 01_任务清单.md             # 需求拆解与状态
│   ├── 03_分析报告.md             # 主报告
│   ├── data_profile.md           # 数据概况核验
│   └── test_log.md               # 代码测试记录
├── outputs/
│   └── tables/                   # 分析结果表与统计 JSON（脚本自动生成，共 17 个文件）
└── figures/                      # 10 张静态图 fig01–fig10（SVG）
```

---

## 五、数据与口径

这一节是全项目的核心。报告里的每个数字都依赖下面六条约定。

### 5.1 数据粒度

**一行 = 一名运动员 × 一届奥运会 × 一个小项。** 团体项目每位成员各占一行。这是唯一的真实粒度，也是所有口径分歧的根源。

### 5.2 两套奖牌口径（必须并存）

| 口径 | 定义 | 总数 | 适用场景 |
|---|---|---|---|
| A · 运动员行口径 | 每一行奖牌记录计 1 枚 | **38,360** | 人次、参与度、女性占比 |
| B · 小项口径 | 去重键 `(Year, Event, Medal, NOC)` | **17,901** | 奖牌榜、跨国比较 |

收缩 **53.3%**，差额全部来自团体项目的成员复制。**报告中所有奖牌数默认用小项口径**，凡使用行口径处均显式标注。小项口径分色为金 5,816 / 银 5,783 / 铜 6,302。

### 5.3 1906 届默认排除

1906 届间奥运会打标 `is_official=False`，官方届次统计默认排除。该届含 458 枚行口径奖牌，故全量为 38,818 = 38,360 + 458。

### 5.4 2020/2024 的 Event 泛化

两届共 30,013 行中，**6,488 行（21.62%）** 的 `Event` 只有 `Men` / `Women` / `Men Team` / `Mixed Team` 这类泛化值，无法还原具体小项。处理策略为 S2「保留下沉」：保留行、打 `event_is_generic` 标记，凡涉及这两届「小项数量」的统计一律降维到「大类 × 性别」并加脚注。

### 5.5 Sport 归一：76 → 57

原始 76 个取值（含 89 行逗号拼接的跨项写法），归并为 57 个大类：

| 原始取值 | 归一为 |
|---|---|
| Artistic / Rhythmic / Trampoline Gymnastics | Gymnastics |
| Cycling Road / Track / Mountain Bike / BMX Racing / BMX Freestyle | Cycling |
| Canoe Sprint / Canoe Slalom | Canoeing |
| Equestrian | Equestrianism |
| Artistic Swimming | Synchronized Swimming |
| 3x3 Basketball | Basketball |
| Marathon Swimming | Swimming |

映射表见 `docs/Task1/sport_mapping.csv`，归一后零空值。

### 5.6 姓名与 player_id 不可靠

`player_id` 平均频次仅 **1.07**（同一人多 ID），另有 **498 个姓名跨度超过 50 年**（多人一 Name）。本项目**不做实体识别**，所有个体层面结论一律不下，主结论全部落在「代表团 × 届次」层级。

### 5.7 其他特殊记录

| 记录 | 处置 |
|---|---|
| 1956 双城（墨尔本 + 斯德哥尔摩马术） | `City` 保留原值，不合并 |
| 政体变迁（URS→EUN→RUS→ROC→AIN、FRG/GDR→GER） | 建 `noc_lineage` 字段，只在长周期曲线使用；国家排名一律用原始 NOC |
| EOR 难民代表团 | 保留独立标识，不并入任何继承链 |

---

## 六、分析视角与产物索引

### 6.1 视角 / 专题 → 图与表

| 章节 | 视角 / 专题 | 对应图 | 对应数据表 |
|---|---|---|---|
| 二 | A · 奖牌格局 | fig01、fig02 | `a_history_medal_table.csv`、`a_medals_by_year.csv`、`a_top10_trajectory.csv` |
| 三 | B · 国家兴衰 | fig03 | `b_focus_countries.csv`、`b_lineage_curves.csv` |
| 四 | C · 她的奥运 | fig04、fig10 | `c_gender_by_year.csv`、`c_women_event_supply.csv`、`c_country_female_ratio.csv` |
| 五 | D · 项目演化 | fig05 | `d_sport_lifecycle.csv`、`d_event_count_by_year.csv` |
| 六 | S2 · 口径的魔力 | fig06、fig07 | `s2_2024_caliber_compare.csv`、`s2_caliber_rank_shift.csv`、`s2_amplification_top30.csv` |
| 七 | S1 · 东道主效应 | fig08 | `s1_host_effect.csv` |
| 八 | 洞察 5 · 集中度 | fig09 | 由 `features_noc_year.csv` 现算 |

### 6.2 十张静态图

| 图号 | 文件 | 图名 | 口径 |
|---|---|---|---|
| 图 1 | `figures/fig01_medal_inflation.svg` | 奖牌膨胀：奖牌总数与代表团数 | 小项口径，排除 1906 |
| 图 2 | `figures/fig02_history_ranking.svg` | 历史总奖牌榜前 12（金/银/铜堆叠横条） | 小项口径，排除 1906 |
| 图 3 | `figures/fig03_country_curves.svg` | 十个代表国家的逐届奖牌曲线 | 小项口径；URS 不并入 RUS |
| 图 4 | `figures/fig04_female_arc.svg` | 女性参赛占比弧线与三次阶跃 | 运动员行口径 |
| 图 5 | `figures/fig05_sport_lifecycle.svg` | 消失的运动：存续区间与记录规模 | 首次–末次年份 + 原始记录数 |
| 图 6 | `figures/fig06_caliber_compare.svg` | 2024 年金牌双口径对照 | 双口径并列 |
| 图 7 | `figures/fig07_rank_shift.svg` | 近五届双口径排名位移 | 双口径并列 |
| 图 8 | `figures/fig08_host_effect.svg` | 东道主效应：主办届增益与赛后回落 | 小项口径 |
| 图 9 | `figures/fig09_concentration.svg` | 前三名国家奖牌份额的百年变化 | 当届内部份额 |
| 图 10 | `figures/fig10_supply_vs_demand.svg` | 女子小项供给与女性参赛占比 | 泛化届次末端不可比 |

### 6.3 数据产物

| 文件 | 内容 |
|---|---|
| `docs/Task1/olympics_clean.csv` | 主表：原始 11 列 + 8 个派生列（`sport_normalized`、`sport_all`、`event_resolved`、`event_is_generic`、`is_official`、`noc_lineage`、`medal_color`、`has_medal`），252,565 × 19 |
| `docs/Task1/medal_event_level.csv` | 小项口径奖牌表（16,071 行） |
| `docs/Task1/noc_year_summary.csv` | 代表团 × 届次汇总，双口径并列（3,201 行） |
| `docs/Task1/features_noc_year.csv` | 派生特征宽表（3,201 行，含 `medal_per_athlete`、`gold_share`、`is_host`、`delta` 等） |
| `docs/Task1/sport_mapping.csv` | Sport 归一映射表（76 个原始取值 → 57 个大类，逗号拼接值按首项归一） |
| `docs/Task1/noc_lineage.csv` | NOC 继承链映射表 |
| `outputs/tables/` | 17 个文件：分析结果表（a/b/c/d/s1/s2 前缀）+ `analysis_results.json` + 质量检查结果（`.md`/`.json`） |

---

## 七、主要发现

| # | 发现 | 证据强度 |
|---|---|---|
| 1 | 历史总榜（小项口径）：USA 2,748、URS 1,005（仅 9 届）、GBR 995、CHN 715 | 强 |
| 2 | 女性参赛占比 0%（1896）→ 49.1%（2024），集中三次阶跃：1952 +8.3pp、1976 +3.9pp、1996 +4.6pp | 强 |
| 3 | 57 个运动大类中 21 项已退场，艺术竞赛 1912–1948 累积 3,578 条记录，是体量最大的消失项目 | 强 |
| 4 | 2024 年同一批数据，换口径后 USA 金牌 37 → 131、NED 14 → 67（平均放大 2.22 倍） | 强 |
| 5 | 29 位有可比数据的东道主中 26 位赛后奖牌下滑，平均 −29.2 枚；两个例外（1996 USA、2016 BRA） | 中 |
| 6 | 奥运扩张的驱动因素换过挡：早期靠代表团入场（×4.92），近 76 年靠小项扩张（×1.89 > ×3.49 中的小项一项最快） | 强 |

细节、机制解释与反例讨论见 [`docs/03_分析报告.md`](docs/03_分析报告.md)。

---

## 八、复现与验证

### 8.1 测试结果

| 检查项 | 结果 |
|---|---|
| 全链路耗时 | 约 **5.5 秒**，退出码 **0**（质量体检 0.9s / 清洗 2.6s / 分析 1.9s / 可视化 0.1s） |
| 幂等性 | 连续两次运行，`analysis_results.json` 哈希一致 |
| 数据完整性断言 | **8 项全部通过** |
| 图表 | 10 张 SVG 全部为合法 XML，无 `nan` / `None` 字符串污染 |
| 看板 | `dashboard.html` 含 7 个图表容器，仅 **1 个** CDN 外链，无本地 js/css/图片依赖 |
| 错误提示 | 缺清洗产物、缺原始数据两类错误均给出可执行的补救命令 |

8 项断言覆盖的关键数字：主表行数守恒 252,565、原始 11 列无缺失、小项口径奖牌总数 17,901、榜首 NOC 为 USA、2024 女性占比 0.491、2024 USA 行口径金牌 131、洞察 1 证据强度为"强"、逐届 totals 在两张表间交叉一致。

### 8.2 如何自检

```bash
.venv\Scripts\python backend/src/run_all.py --check      # 只查产物存在性与数量
.venv\Scripts\python backend/src/run_all.py              # 完整重跑并自动执行同样的自检
```

若只改动了某一环节，可分步重跑对应脚本；下游脚本会读取上游产物，顺序见 3.4。

### 8.3 幂等性说明

流程中唯一的随机操作是清洗校验中的抽样，已固定 `seed=42`，因此重复运行结果完全一致，可直接用于结果对账。

---

## 九、已知限制

| # | 限制 | 表现与处置 |
|---|---|---|
| L1 | **无外部数据交叉验证** | 未引入人口、GDP、参赛人数基数与 IOC 官方榜单，"人均""效率"类指标无法计算；涉及制度差异的结论只标为待验证 |
| L2 | **姓名与 ID 不可靠** | `player_id` 平均频次 1.07，498 个姓名跨度超 50 年；不做个体粒度分析 |
| L3 | **Event 泛化** | 2020/2024 共 21.62% 的 Event 为泛化值，小项数相关统计降维到"大类 × 性别"，曲线在 2020 处不连续 |
| L4 | **看板需联网** | `dashboard.html` 的 ECharts 走 CDN，离线打开时图表区空白；静态 SVG 不受影响 |
| L5 | **未使用 pytest** | 当前以断言脚本覆盖关键数字，对课程作业量级足够；长期维护建议补单元测试 |
| L6 | **与官方榜单存在已知偏差** | 去重键含 `NOC`，混合队与并列奖牌各计一次（2024 年本口径 CHN 38 金、USA 37 金，官方均为 40）；结论只依赖同口径内部比较 |
| L7 | **小项奖牌并非严格等量** | 163 个小项未发满三色，故金 / 银 / 铜为 5,816 / 5,783 / 6,302，"金牌占比"类指标存在系统性小偏差 |

此外，2024 年巴黎的赛后数据缺失，东道主回落无法计算，项目不做 2028 预测。

---

## 十、数据来源与许可

### 10.1 来源

| 项 | 内容 |
|---|---|
| 主数据集 | Kaggle — *Summer Olympics Medals (1896-2024)*，作者 Stefany De Oliveira |
| 2020 及以前 | Kaggle — *Olympics 124 years Dataset (till 2020)*，作者 Nitish Sharma |
| 2024 巴黎 | Kaggle — *Paris 2024 Olympic Summer Games*，作者 Petro Ivaniuk |
| 交叉验证参考 | Olympedia（https://www.olympedia.org/）、IOC 官方奖牌榜 |

原始 CSV 不随包提交（评审方持有相同副本）。

### 10.2 许可要求（CC BY-NC-SA 4.0）

1. **署名**：作品与报告注明上述数据来源及两个上游数据集；
2. **非商业**：本项目及衍生作品不得用于商业用途；
3. **相同方式共享**：对数据集的衍生或清洗版本须以同等许可开放。

凡与 IOC 官方奖牌榜对比处，均已注明本项目所采用的统计口径，不作误导性呈现。
