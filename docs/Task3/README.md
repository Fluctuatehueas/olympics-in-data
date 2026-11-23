# Task3 · S4「小代表团的大突破」· 专题 README

> 本目录是赛题任务三候选方向 S4 的完整交付：研究报告、分析代码、数据表、图表。
> 定量结果全部由项目数据集现算，可一键复现；外部资料仅用于定性解释，不参与任何计算。

---

## 一、这个专题是什么

**赛题原文**：中国香港（HKG）1996 年首金 → 2020 年「8 行奖牌」的历史最佳 → 2024；以及 TPE、SGP 等「小而精」的夺牌策略（聚焦个别优势项目 vs 全面上阵）。

**核心研究问题**：

1. 参赛规模很小的代表团，靠什么取得超出体量的突破？
2. 突破口是「集中押注少数优势项目」还是「全面铺开」？
3. 这种突破能否持续？

**一句话结论**：小团靠「必然的单一项目押注」拿牌，靠不住的是持续性；「人效更高」只在绑定小项口径时成立。

**主报告**：`S4_小代表团的大突破.md`

---

## 二、如何复现

### 2.1 前置条件

- Python 3 + `pandas` + `numpy` + `scipy`
- **必须先有 Task1 产物**：`docs/Task1/olympics_clean.csv`、`medal_event_level.csv`、`noc_year_summary.csv`、`features_noc_year.csv`
  若缺失，先跑 Task1 清洗链路（`backend/src/cleaning.py` 等）

### 2.2 三条命令

```bash
# 1) 全量运行：数据准备 → 分析 → 绘图 → 自检
python backend/src/task3_s4_run_all.py

# 2) 只跑数据准备与十项口径校验（产出 s4_base.csv / s4_verification.json）
python backend/src/task3_s4_clean.py

# 3) 只跑分析与静态图（产出 s4_results.json / tables/ / figures/）
python backend/src/task3_s4_analysis.py && python backend/src/task3_s4_visualize.py
```

补充命令：

```bash
# 只自检已有产物（34 项：4 个核心文件 + 20 张表 + 10 张图）
python backend/src/task3_s4_run_all.py --check
```

份额趋势的阈值敏感性（`task3_s4_share_trend.py`）已并入全量流程，无需单独运行；
它读取 `s4_base.csv`，产出 `outputs/task3_s4/tables/f_share_trend_by_threshold.csv` 并回写
`s4_results.json` 的 `F_trend.share_trend_by_threshold` 字段。

前端页面「小团突破」的数据由 `outputs/task3_s4/` 构建：

```bash
python backend/api/build_s4_data.py     # 生成 backend/api/data/s4.json
python backend/api/main.py              # 启动 API（/api/s4）
```

### 2.3 复现性说明

- 所有 bootstrap 固定 `seed=42`，`n_boot=2000`，percentile 法取中位数区间
- 连续两次运行 `s4_results.json` 的 MD5 一致，当前快照为 `3bcb995161c4`（见 `test_log.md` 第三节）
- 注：不同 scipy 版本可能让 p 值浮点末位产生差异，哈希随之变化；数值结论不变
- 统计检验：`scipy.stats` 的 `spearmanr` / `mannwhitneyu(two-sided)` / `linregress`

---

## 三、目录结构

```
docs/Task3/                          # 只放文档
├── README.md                        # 本文件
├── S4_小代表团的大突破.md            # 主报告（十二节）
├── 任务清单.md                       # 规划与调度（最终状态：全部已完成）
├── 外部资料采集记录.md                # 制度侧资料与链接，仅定性使用
└── test_log.md                      # 代码测试记录（运行、幂等、断言）

outputs/task3_s4/                    # 数据与图表产物
├── s4_base.csv                      # 基础表 3,201 行（代表团 × 届次）
├── s4_noc_first_medal.csv           # 各 NOC 首牌信息
├── s4_results.json                  # 全部统计结果
├── s4_verification.json             # 10 项口径守恒校验
├── tables/                          # 20 张结果表
│   ├── a_*.csv                      # 全景：规模分布与夺牌率
│   ├── b_*.csv                      # 机制：集中度与人效
│   ├── c_*.csv                      # 个案：八国汇总与逐届明细
│   ├── d_*.csv                      # 持续性：首牌后行为、一次性突破国
│   ├── e_*.csv                      # 敏感性：阈值 × 口径
│   └── f_*.csv                      # 结构：小团份额逐届
└── figures/                         # 10 张 SVG（fig01–fig10）
```

**代码位置**：`backend/src/task3_s4_clean.py` / `task3_s4_analysis.py` / `task3_s4_visualize.py` / `task3_s4_visualize_extra.py` / `task3_s4_share_trend.py` / `task3_s4_run_all.py`
**前端页面**：`frontend/datavision/src/views/SmallTeamsView.vue`（菜单「小团突破」），数据由 `backend/api/build_s4_data.py` 构建、`/api/s4` 提供。

---

## 四、口径要点（读数据前必看）

| 项目 | 设定 | 说明 |
|---|---|---|
| 数据源 | `olympics_dataset.csv`，252,565 行 × 11 列，1896–2024 夏奥 | 一行 = 一名运动员 × 一届 × 一个小项 |
| **主口径** | **小项口径 17,901 枚** | 去重键 `(Year, Event, Medal, NOC)` |
| 对照口径 | 运动员行口径 38,360 枚 | 每个奖牌行计 1；两口径收缩 53.3% |
| 届次排除 | 默认排除 1906 届 | 非官方届次 |
| 小团主阈值 | 参赛人数 **≤ 50** | 另有 ≤10 / ≤25 / ≤100 / ≤150 四档做敏感性 |
| 规模四档 | 微型 ≤10 / 小型 11–50 / 中型 51–150 / 大型 >150 | 按单届参赛人数 |
| 小团届次 | 单届属性，共 2,139 个代表团届次 | 与「小团型国家」不同 |
| 小团型国家 | 国家属性：历史峰值参赛 ≤50，共 63 个 NOC | 持续性分析用此定义 |
| 近代样本 | 1980 年及以后，n = 12 届 | 理由见报告 1.5；代价见 2.3 |
| 基础表 | 3,201 行，233 个 NOC，30 个官方届次 | 十项校验全部通过 |

**最容易踩的三个坑**：

1. **HKG 2020 = 6 枚（小项口径）≠ 8 行（行口径）**。赛题说的是行口径。
2. **「小团人效更高」只在绑定小项口径时成立**，换行口径后大团更高（见报告 8.2）。
3. **「小团在变强」只在 1980 断点后成立**，全期 OLS 斜率是负的（见报告 2.3）。

---

## 五、产物清单

### 5.1 核心文件（4，位于 `outputs/task3_s4/`）

| 文件 | 内容 | 校验 |
|---|---|---|
| `s4_base.csv` | 3,201 行，含双口径奖牌数、规模分档、集中度特征 | 行数与 Task1 对账 |
| `s4_noc_first_medal.csv` | 157 个曾夺牌 NOC 的首牌/持续性字段 | — |
| `s4_results.json` | meta / anchors / 四块分析 / 敏感性 / 趋势 | 可 MD5 比对（当前 `3bcb995161c4`，两次运行一致） |
| `s4_verification.json` | 10 项口径守恒检查 | 全部 `通过` |

### 5.2 结果表（20，位于 `outputs/task3_s4/tables/`）

`a_size_distribution` / `a_size_class_by_year` / `a_small_medal_rate_by_year` / `b_concentration_scatter` / `b_strategy_by_size` / `b_strategy_by_size_modern` / `b_efficiency_vs_size` / `c_case_countries` / `c_case_medal_by_sport` / `c_hkg_detail` / `c_sgp_detail` / `c_tpe_detail` / `d_persistence` / `d_streak_by_type` / `d_one_hit_wonders` / `e_threshold_sensitivity` / `e_caliber_sensitivity` / `f_small_rise` / `f_small_rise_all_years` / `f_share_trend_by_threshold`

### 5.3 图表（10，位于 `outputs/task3_s4/figures/`）

| 图 | 文件 | 论点 |
|---|---|---|
| 1 | `fig01_size_vs_rate.svg` | 四档规模 × 两时代夺牌率 |
| 2 | `fig02_small_trend.svg` | 小团夺牌率百年趋势，拐点 1980 |
| 3 | `fig03_concentration_scatter.svg` | 规模 vs 集中度（874 点） |
| 4 | `fig04_efficiency.svg` | 人效 U 形曲线 + bootstrap 区间 |
| 5 | `fig05_case_sports.svg` | 八国夺牌项目构成 |
| 6 | `fig06_case_trajectory.svg` | HKG / SGP / TPE 逐届轨迹 |
| 7 | `fig07_persistence.svg` | 首牌后夺牌率分布 |
| 8 | `fig08_small_share_rise.svg` | 小团奖牌份额上升 |
| 9 | `fig09_sensitivity.svg` | 阈值敏感性与口径翻转 |
| 10 | `fig10_small_noc_board.svg` | 小团型国家奖牌榜前 15 |

---

## 六、已知限制

1. **强依赖 Task1 产物**：本专题不做原始清洗。缺文件时会直接报出补救命令，不会静默产出空表。
2. **人效指标分母被条件化**：只统计有奖牌的届次，未做 hurdle 模型估计「期望产出」，因此人效表只能读作「成功者的效率」。
3. **小团份额趋势已有阈值敏感性，但外推受限**：8.4 补测了 ≤10 / 25 / 50 / 100 / 150 五个阈值，方向全部一致且 p < 0.01；但 2024 年是单届峰值，前 15 年在 6–8% 震荡，趋势外推只有 1 个观测支撑。
4. **持续性以「届次」为单位**：不区分相邻届次的实际间隔（4 年或 8 年）。
5. **团体项目只做口径对照**：未整项剔除棒球、篮球等大名单项目。
6. **制度资料为定性对照**：数据集无制度变量，第九节只提假设、不验证因果；且存在反向因果（先有成绩再进资助名单）的可能。
7. **无 pytest**：以 `run_all.py --check` + 断言脚本覆盖，对作业量级足够。
8. **统计检验未做多重比较校正**：双尾检验，B 块 4 次、E 块 5×4 次、8.4 的 5 次趋势检验；主要结论 p 值远小于 Bonferroni 阈值（α/25 ≈ 0.002），判断不变。
9. **与官方奖牌榜存在已知偏差**：去重键含 NOC，混合队/跨国组合各计一次；同口径下 2024 金牌数与 IOC 官方略有差异，属可解释偏差。

---

## 七、引用规范

- 报告中的定量结论**只依赖数据集**，不引用外部数字；
- 外部制度资料逐条给链接，采集记录见 `外部资料采集记录.md`；
- 外文来源的中文转述为作者翻译，歧义以原文为准；
- 转载或复用时请同时保留口径说明（小项口径 17,901 / 行口径 38,360）。
