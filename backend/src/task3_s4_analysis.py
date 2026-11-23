"""
Task3 专题 S4「小代表团的大突破」—— 分析计算脚本
================================================================

职责
----
在 `backend/src/task3_s4_clean.py` 已产出的两张底表之上，完成 S4 的 6 块分析
（A 全景 / B 小而精 vs 全面上阵 / C 个案深挖 / D 可持续性 / E 敏感性 / F 时间趋势），
输出 `outputs/task3_s4/tables/*.csv` 与 `outputs/task3_s4/s4_results.json`。

调用关系
--------
- 上游：`docs/Task1/medal_event_level.csv`
        `outputs/task3_s4/s4_base.csv`（代表团×届次，已含 size_class / is_small / era /
        has_medal_event / top1_share / n_sports_medal / hhi / top_sport）
        `outputs/task3_s4/s4_noc_first_medal.csv`（代表团档案，已含首牌/首金/参赛届数）
  本脚本**不重复实现**清洗脚本已有的分档、集中度、首牌逻辑，只做读取与增量计算。
- 下游：写报告的同事 / 前端图表。单进程串行，无共享可变状态。

口径铁律（与 task3_s4_clean.py 完全一致，不得自创）
--------------------------------------------------
- 主口径 = **小项口径**：`Total_event` / `Gold_event` / `Silver_event` / `Bronze_event`，
  全表奖牌合计 17,901。
- 对照口径 = **运动员行口径**：`Total_athlete` / `Gold_athlete` / …，合计 38,360。
  行口径把「一队 12 人的接力银牌」计为 12 枚，仅作口径敏感性对照，不作主结论依据。
- 已排除 1906 届间奥运会。
- 「小代表团」= 参赛人数 ≤ 50（`is_small`），敏感性检验用 10 / 25 / 50 / 100 / 150。
- 「近代」= Year ≥ 1980（`era`）。
- 所有比例的分母都显式写出，不做隐式 dropna。

统计学约定
----------
- 相关系数：Spearman 秩相关（不假设正态；对重尾分布稳健），双侧检验。
- 两组差异：Mann-Whitney U（双侧，method='auto'：无并列且样本小时用精确法，
  否则正态近似 + 并列校正），并报秩二列效应量 r = 2U/(n1*n2) - 1。
- 置信区间：bootstrap 百分位法，固定 seed=42，默认 B=2000（中位数）。
- 不做多重比较校正（探索性分析），p 值原样输出，结论同时看效应量方向。
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

# --------------------------------------------------------------------------- #
# 路径与常量
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parents[2]
T1 = ROOT / "docs" / "Task1"
T3 = ROOT / "outputs" / "task3_s4"
TAB = T3 / "tables"
TAB.mkdir(parents=True, exist_ok=True)

SEED = 42                     # bootstrap 随机种子（固定，保证可复现）
N_BOOT = 2000                 # bootstrap 重采样次数
MODERN_FROM = 1980            # 近代样本起点，与 clean 脚本一致
SMALL_MAIN = 50               # 主阈值：参赛人数 ≤ 50
BIG_CMP = 150                 # B/D 块分组对比用「大团」阈值：> 150
THRESHOLDS = [10, 25, 50, 100, 150]   # E 块敏感性阈值

# B 块效率检验的人数分箱（左闭右开）
EFF_BINS = [1, 6, 11, 26, 51, 101, 201, 10**9]
EFF_LABELS = ["1-5", "6-10", "11-25", "26-50", "51-100", "101-200", "201+"]

NAMED = ["HKG", "SGP", "TPE"]     # C 块点名案例
EXTRA_POOL = ["FIJ", "BAH", "PUR", "MGL", "GEO", "KOS", "BRN", "GRN", "TTO",
              "QAT", "ARM", "ERI", "VIE", "DOM", "MAS"]   # 自选案例候选池
BIG_REF = ["USA", "CHN", "GBR", "GER", "AUS", "JPN", "FRA", "URS", "RUS", "ITA"]


# --------------------------------------------------------------------------- #
# 通用工具
# --------------------------------------------------------------------------- #
def boot_ci(x, stat_fn=np.median, n_boot: int = N_BOOT, alpha: float = 0.05,
            seed: int = SEED) -> tuple[float, float]:
    """Bootstrap 百分位法置信区间（固定 seed=42，可复现）。

    输入：x 一维样本；stat_fn 统计量函数（默认中位数）；n_boot 重采样次数。
    输出：(lower, upper)；样本量 < 2 时返回 (nan, nan)。
    口径：有放回重采样，取 alpha/2 与 1-alpha/2 分位点。
    """
    arr = np.asarray(x, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size < 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, arr.size, size=(n_boot, arr.size))
    boots = stat_fn(arr[idx], axis=1)
    lo, hi = np.percentile(boots, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return (float(lo), float(hi))


def effect_r(u: float, n1: int, n2: int) -> float:
    """Mann-Whitney U → 秩二列效应量 r = 2U/(n1*n2) - 1，范围 [-1, 1]。

    r > 0 表示第一组（本脚本约定为小团组）取值整体更大。
    """
    if n1 == 0 or n2 == 0:
        return float("nan")
    return float(2.0 * u / (n1 * n2) - 1.0)


def mwu_test(a, b) -> dict:
    """Mann-Whitney U 双侧检验 + 效应量，返回可 JSON 化的字典。

    输入：a = 小团组取值（第一组），b = 大团组取值（第二组）；NaN 自动剔除。
    输出：n1/n2/U/p/effect_r/两组中位数/方向文字 + 检验名称。
    """
    a = pd.Series(a).dropna().to_numpy(dtype=float)
    b = pd.Series(b).dropna().to_numpy(dtype=float)
    rec = {"test": "Mann-Whitney U (two-sided, method=auto)",
           "n1": int(a.size), "n2": int(b.size)}
    if a.size < 3 or b.size < 3:
        rec.update({"U": None, "p": None, "effect_r": None,
                    "median1": None, "median2": None, "direction": "样本不足"})
        return rec
    res = stats.mannwhitneyu(a, b, alternative="two-sided", method="auto")
    m1, m2 = float(np.median(a)), float(np.median(b))
    rec.update({
        "U": float(res.statistic), "p": float(res.pvalue),
        "effect_r": effect_r(float(res.statistic), a.size, b.size),
        "median1": m1, "median2": m2,
        "direction": ("小团更高" if m1 > m2 else "大团更高" if m1 < m2 else "相同"),
    })
    return rec


def spearman_test(x, y, label: str = "") -> dict:
    """Spearman 秩相关双侧检验，返回 rho / p / n / 结论文字。"""
    df = pd.DataFrame({"x": pd.Series(x).reset_index(drop=True),
                       "y": pd.Series(y).reset_index(drop=True)}).dropna()
    if len(df) < 5:
        return {"label": label, "test": "Spearman rank correlation",
                "n": int(len(df)), "rho": None, "p": None, "note": "样本不足"}
    rho, p = stats.spearmanr(df["x"], df["y"])
    strength = "强" if abs(rho) >= 0.6 else ("中" if abs(rho) >= 0.3 else "弱")
    note = (f"{strength}{'正' if rho > 0 else '负'}相关，"
            f"{'显著' if p < 0.05 else '不显著'}(α=0.05)")
    return {"label": label, "test": "Spearman rank correlation", "n": int(len(df)),
            "rho": float(rho), "p": float(p), "note": note}


def ols_trend(x, y) -> dict:
    """一元 OLS 线性趋势：斜率 / 截距 / R² / p / n。

    输入：x 自变量（年份），y 因变量（比例或计数）。
    输出：slope 即「每过一年 y 的绝对变化量」。
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 3:
        return {"slope": None, "intercept": None, "r2": None, "p": None,
                "n": int(len(x))}
    lr = stats.linregress(x, y)
    return {"slope": float(lr.slope), "intercept": float(lr.intercept),
            "r2": float(lr.rvalue ** 2), "p": float(lr.pvalue), "n": int(len(x))}


def save_csv(df: pd.DataFrame, name: str) -> None:
    """落盘 CSV（utf-8-sig），并打印行数以验证。"""
    df.to_csv(TAB / name, index=False, encoding="utf-8-sig")
    print(f"  [写出] {name}: {len(df)} 行 x {df.shape[1]} 列")


def load_data():
    """读取底表，并派生效率指标（不覆盖已有列）。"""
    need = {"base": T3 / "s4_base.csv",
            "first": T3 / "s4_noc_first_medal.csv",
            "event": T1 / "medal_event_level.csv"}
    for name, p in need.items():
        if not p.exists():
            raise FileNotFoundError(f"缺少 {p}，请先运行 backend/src/task3_s4_clean.py")
    base = pd.read_csv(need["base"])
    first = pd.read_csv(need["first"])
    event = pd.read_csv(need["event"])
    # 效率指标：小项口径奖牌 / 参赛人数（人效）
    base["medal_per_athlete"] = np.where(base["athletes"] > 0,
                                         base["Total_event"] / base["athletes"], np.nan)
    # 行口径对应指标，供 E 块口径敏感性使用
    base["medal_per_athlete_row"] = np.where(
        base["athletes"] > 0, base["Total_athlete"] / base["athletes"], np.nan)
    return base, first, event


# --------------------------------------------------------------------------- #
# A 块：小代表团全景
# --------------------------------------------------------------------------- #
def block_a(base: pd.DataFrame) -> dict:
    """A 块：小团全景 + 「多小的团还能拿牌」。

    输入：s4_base（代表团×届次）
    输出：
      a_size_distribution.csv        size_class × era 的样本量/夺牌数/夺牌率/金牌/奖牌
      a_small_medal_rate_by_year.csv 逐届 小团(≤50) vs 大团(>50) 夺牌率 + 样本量
      a_size_class_by_year.csv       逐届 × 规模档 夺牌率
    口径：夺牌率分母 = 该组代表团届次样本量；奖牌均为小项口径。
    """
    out: dict = {}

    # ---- A1 规模档 × 时代 ----
    g = (base.groupby(["size_class", "era"], observed=True)
         .agg(n_noc_editions=("NOC", "size"),
              n_with_medal=("has_medal_event", "sum"),
              gold=("Gold_event", "sum"), silver=("Silver_event", "sum"),
              bronze=("Bronze_event", "sum"), total_medal=("Total_event", "sum"),
              athlete_sum=("athletes", "sum"),
              median_athletes=("athletes", "median")).reset_index())
    g["medal_rate"] = (g["n_with_medal"] / g["n_noc_editions"]).round(4)
    g["medal_share_of_total"] = (g["total_medal"] / base["Total_event"].sum()).round(4)
    g = g[["size_class", "era", "n_noc_editions", "n_with_medal", "medal_rate",
           "gold", "silver", "bronze", "total_medal", "medal_share_of_total",
           "athlete_sum", "median_athletes"]]
    save_csv(g, "a_size_distribution.csv")
    out["size_distribution"] = g.to_dict(orient="records")

    # ---- A2 逐届 小团 vs 大团 ----
    small = base[base["athletes"] <= SMALL_MAIN]
    big = base[base["athletes"] > SMALL_MAIN]
    s = (small.groupby("Year").agg(small_n=("NOC", "size"),
                                   small_medal_n=("has_medal_event", "sum"),
                                   small_medal=("Total_event", "sum"),
                                   small_athletes=("athletes", "sum")).reset_index())
    b = (big.groupby("Year").agg(big_n=("NOC", "size"),
                                 big_medal_n=("has_medal_event", "sum"),
                                 big_medal=("Total_event", "sum")).reset_index())
    yr = s.merge(b, on="Year", how="outer").sort_values("Year").reset_index(drop=True)
    yr["small_medal_rate"] = (yr["small_medal_n"] / yr["small_n"]).round(4)
    yr["big_medal_rate"] = (yr["big_medal_n"] / yr["big_n"]).round(4)
    yr["rate_gap_small_minus_big"] = (yr["small_medal_rate"] - yr["big_medal_rate"]).round(4)
    yr["total_noc"] = yr["small_n"] + yr["big_n"]
    yr["small_share_of_noc"] = (yr["small_n"] / yr["total_noc"]).round(4)
    yr["small_medal_share"] = (yr["small_medal"] /
                               (yr["small_medal"] + yr["big_medal"])).round(4)
    save_csv(yr, "a_small_medal_rate_by_year.csv")
    out["small_vs_big_by_year"] = yr.to_dict(orient="records")

    # ---- A3 逐届 × 规模档 ----
    yx = (base.groupby(["Year", "size_class"], observed=True)
          .agg(n=("NOC", "size"), n_with_medal=("has_medal_event", "sum"),
               total_medal=("Total_event", "sum")).reset_index())
    yx["medal_rate"] = (yx["n_with_medal"] / yx["n"]).round(4)
    save_csv(yx, "a_size_class_by_year.csv")

    # ---- 「多小的团还能拿牌」：各档夺牌率（全期 + 近代）----
    by_class = (base.groupby("size_class", observed=True)
                .agg(n=("NOC", "size"), n_with_medal=("has_medal_event", "sum"),
                     total_medal=("Total_event", "sum")).reset_index())
    by_class["medal_rate"] = (by_class["n_with_medal"] / by_class["n"]).round(4)
    mod = base[base["Year"] >= MODERN_FROM]
    modc = (mod.groupby("size_class", observed=True)
            .agg(n_modern=("NOC", "size"),
                 n_with_medal_modern=("has_medal_event", "sum"),
                 total_medal_modern=("Total_event", "sum")).reset_index())
    modc["medal_rate_modern"] = (modc["n_with_medal_modern"] / modc["n_modern"]).round(4)
    by_class = by_class.merge(modc, on="size_class", how="left")
    out["medal_rate_by_size_class"] = by_class.to_dict(orient="records")

    # 极小团（≤5 人）拿牌证据：直接回答「多小的团还能拿牌」
    tiny = base[(base["athletes"] <= 5) & (base["has_medal_event"] == 1)]
    out["tiny_teams_with_medal"] = {
        "definition": "参赛人数 ≤ 5 且当届有小项口径奖牌",
        "n_cases": int(len(tiny)), "n_noc": int(tiny["NOC"].nunique()),
        "n_editions_athletes_le5": int((base["athletes"] <= 5).sum()),
        "rate": round(float(len(tiny) / max(1, (base["athletes"] <= 5).sum())), 4),
        "top_examples": (tiny.sort_values("Total_event", ascending=False)
                         .head(10)[["Year", "NOC", "Team", "athletes", "Total_event",
                                    "Gold_event", "top_sport"]]
                         .to_dict(orient="records")),
    }

    # 单兵作战（1-2 人）拿牌
    solo = base[(base["athletes"] <= 2) & (base["has_medal_event"] == 1)]
    n_solo = int((base["athletes"] <= 2).sum())
    out["solo_teams_le2_athletes"] = {
        "n_cases": int(len(solo)), "n_editions": n_solo,
        "rate": round(float(len(solo) / max(1, n_solo)), 4),
        "examples": (solo.sort_values("Total_event", ascending=False)
                     .head(8)[["Year", "NOC", "Team", "athletes", "Total_event"]]
                     .to_dict(orient="records")),
    }

    # ---- 趋势：1980+ 小团夺牌率完整序列 + 线性趋势 ----
    m = yr[yr["Year"] >= MODERN_FROM].reset_index(drop=True)
    tr = ols_trend(m["Year"], m["small_medal_rate"])
    tr_all = ols_trend(yr["Year"], yr["small_medal_rate"])
    y1980 = float(m.loc[m["Year"] == 1980, "small_medal_rate"].iloc[0])
    y2024 = float(m.loc[m["Year"] == 2024, "small_medal_rate"].iloc[0])
    out["small_medal_rate_trend"] = {
        "series_1980_2024": {str(int(r.Year)): float(r.small_medal_rate)
                              for r in m.itertuples()},
        "n_years": int(len(m)),
        "value_1980": y1980, "value_2024": y2024,
        "change_1980_2024_pct_points": round((y2024 - y1980) * 100, 2),
        "modern_ols": tr,
        "modern_slope_pct_points_per_year": round(tr["slope"] * 100, 4),
        "all_years_ols": tr_all,
        "all_years_slope_pct_points_per_year": round(tr_all["slope"] * 100, 4),
        "min_year_in_series": int(m.loc[m["small_medal_rate"].idxmin(), "Year"]),
        "min_value": float(m["small_medal_rate"].min()),
        "max_year_in_series": int(m.loc[m["small_medal_rate"].idxmax(), "Year"]),
        "max_value": float(m["small_medal_rate"].max()),
    }
    return out


# --------------------------------------------------------------------------- #
# B 块：小而精 vs 全面上阵
# --------------------------------------------------------------------------- #
def _strategy_table(df: pd.DataFrame) -> pd.DataFrame:
    """按 size_class 汇总策略指标（中位数 + 均值 + 90 分位）。

    输入：有奖牌的代表团届次子表。
    输出：每档一行；medal_per_athlete 为小项口径奖牌/参赛人数。
    """
    t = (df.groupby("size_class", observed=True)
         .agg(n_editions_with_medal=("NOC", "size"),
              mpa_median=("medal_per_athlete", "median"),
              mpa_mean=("medal_per_athlete", "mean"),
              mpa_p90=("medal_per_athlete", lambda s: float(np.nanpercentile(s, 90))),
              top1_share_median=("top1_share", "median"),
              n_sports_medal_median=("n_sports_medal", "median"),
              hhi_median=("hhi", "median"),
              total_event_median=("Total_event", "median"),
              athletes_median=("athletes", "median")).reset_index())
    for c in ["mpa_median", "mpa_mean", "mpa_p90", "top1_share_median",
              "hhi_median", "athletes_median"]:
        t[c] = t[c].round(4)
    return t


def block_b(base: pd.DataFrame) -> dict:
    """B 块核心检验：参赛规模 ↔ 夺牌效率 / 项目集中度。

    输入：s4_base；样本 = 有奖牌的代表团届次（has_medal_event==1），
          统计检验再限定 Year>=1980。
    输出：
      b_strategy_by_size.csv        规模档策略指标（全期）
      b_strategy_by_size_modern.csv 同上，限定 1980+
      b_efficiency_vs_size.csv      人数分箱的 medal_per_athlete 中位数 + bootstrap 95%CI
      b_concentration_scatter.csv   每个有奖牌的代表团届次一行（散点图底表）
    口径：medal_per_athlete = 小项口径奖牌数 / 参赛人数（人效）。
    """
    out: dict = {}
    med = base[base["has_medal_event"] == 1].copy()
    mod = med[med["Year"] >= MODERN_FROM].copy()

    sa = _strategy_table(med)
    save_csv(sa, "b_strategy_by_size.csv")
    out["strategy_by_size_all_years"] = sa.to_dict(orient="records")
    smt = _strategy_table(mod)
    save_csv(smt, "b_strategy_by_size_modern.csv")
    out["strategy_by_size_1980plus"] = smt.to_dict(orient="records")

    # ---- B2 人数分箱效率（bootstrap 95% CI，seed=42）----
    med["size_bin"] = pd.cut(med["athletes"], bins=EFF_BINS, labels=EFF_LABELS,
                             right=False)
    rows = []
    for lab in EFF_LABELS:
        sub = med.loc[med["size_bin"] == lab, "medal_per_athlete"].dropna()
        lo, hi = boot_ci(sub, np.median)
        rows.append({"size_bin": lab,
                     "n_noc_editions_in_bin": int((med["size_bin"] == lab).sum()),
                     "n_with_medal": int(sub.size),
                     "mpa_median": round(float(sub.median()), 4) if sub.size else np.nan,
                     "mpa_mean": round(float(sub.mean()), 4) if sub.size else np.nan,
                     "ci95_low": round(lo, 4), "ci95_high": round(hi, 4),
                     "ci_method": f"bootstrap percentile on median, B={N_BOOT}, seed={SEED}"})
    eff = pd.DataFrame(rows)
    save_csv(eff, "b_efficiency_vs_size.csv")
    out["efficiency_vs_size"] = eff.to_dict(orient="records")

    # ---- B3 散点底表（每行 = 一个有奖牌的代表团届次）----
    sc = med[["Year", "NOC", "Team", "athletes", "Total_event", "medal_per_athlete",
              "top1_share", "n_sports_medal", "hhi", "top_sport", "size_class",
              "Gold_event", "Silver_event", "Bronze_event"]].copy()
    sc["is_named_case"] = sc["NOC"].isin(NAMED).astype(int)
    sc["is_extra_case"] = sc["NOC"].isin(EXTRA_POOL).astype(int)
    sc["is_big_reference"] = sc["NOC"].isin(BIG_REF).astype(int)
    sc = sc.sort_values(["Year", "NOC"]).reset_index(drop=True)
    save_csv(sc, "b_concentration_scatter.csv")
    out["scatter_coverage_check"] = {
        "n_rows": int(len(sc)),
        "named_cases_missing": [n for n in NAMED if n not in set(sc["NOC"])],
        "named_case_rows": int(sc["NOC"].isin(NAMED).sum()),
        "big_reference_present": sorted(set(sc["NOC"]) & set(BIG_REF)),
    }

    # ---- B4 Spearman 相关（1980+ 有奖牌为主样本）----
    out["spearman"] = {
        "athletes_vs_top1_share_1980plus": spearman_test(
            mod["athletes"], mod["top1_share"], "1980+ 有奖牌：参赛人数 vs top1_share"),
        "athletes_vs_n_sports_medal_1980plus": spearman_test(
            mod["athletes"], mod["n_sports_medal"], "1980+ 有奖牌：参赛人数 vs 夺牌大类数"),
        "athletes_vs_hhi_1980plus": spearman_test(
            mod["athletes"], mod["hhi"], "1980+ 有奖牌：参赛人数 vs HHI"),
        "athletes_vs_medal_per_athlete_1980plus": spearman_test(
            mod["athletes"], mod["medal_per_athlete"],
            "1980+ 有奖牌：参赛人数 vs medal_per_athlete"),
        "athletes_vs_total_event_1980plus": spearman_test(
            mod["athletes"], mod["Total_event"], "1980+ 有奖牌：参赛人数 vs 奖牌数"),
        "athletes_vs_top1_share_all_years": spearman_test(
            med["athletes"], med["top1_share"], "全期有奖牌：参赛人数 vs top1_share"),
        "athletes_vs_n_sports_medal_all_years": spearman_test(
            med["athletes"], med["n_sports_medal"], "全期有奖牌：参赛人数 vs 夺牌大类数"),
    }

    # ---- B5 分组对比 小团(≤50) vs 大团(>150)，1980+ 有奖牌 ----
    a = mod[mod["athletes"] <= SMALL_MAIN]
    b = mod[mod["athletes"] > BIG_CMP]
    grp = {col: mwu_test(a[col], b[col])
           for col in ["top1_share", "n_sports_medal", "medal_per_athlete",
                       "hhi", "Total_event"]}
    out["group_compare_small50_vs_big150"] = {
        "sample": "Year>=1980 且 has_medal_event==1",
        "n_small_le50": int(len(a)), "n_big_gt150": int(len(b)),
        "note": "第一组=小团(≤50)，第二组=大团(>150)；effect_r>0 表示小团取值更大",
        "results": grp,
    }
    out["single_sport_dependence"] = {
        "n_small": int(len(a)), "n_big": int(len(b)),
        "small_le50_share_top1_eq_1": round(float((a["top1_share"] >= 0.9999).mean()), 4),
        "big_gt150_share_top1_eq_1": round(float((b["top1_share"] >= 0.9999).mean()), 4),
        "all_modern_share_top1_eq_1": round(float((mod["top1_share"] >= 0.9999).mean()), 4),
    }
    return out


# --------------------------------------------------------------------------- #
# C 块：个案深挖
# --------------------------------------------------------------------------- #
def pick_extra_cases(event: pd.DataFrame, base: pd.DataFrame,
                     exclude: list[str], k: int = 5) -> list[str]:
    """从候选池挑「参赛人数少但奖牌多」的 k 个成功案例（规则可复现）。

    规则：候选池内须有奖牌；按 生涯人效 = 历史小项口径奖牌总数 / 峰值参赛人数 降序，
          平手时奖牌总数多者优先。与 B 块 medal_per_athlete 同源但跨届聚合。
    """
    ev = event.groupby("NOC")["Total"].sum()
    peak = base.groupby("NOC")["athletes"].max()
    rows = []
    for noc in EXTRA_POOL:
        if noc in exclude or noc not in ev.index:
            continue
        tot, pk = float(ev.get(noc, 0)), float(peak.get(noc, np.nan))
        if tot <= 0 or not np.isfinite(pk) or pk <= 0:
            continue
        rows.append({"NOC": noc, "total_medal": tot, "peak_athletes": pk,
                     "life_efficiency": tot / pk})
    if not rows:
        return []
    df = pd.DataFrame(rows).sort_values(["life_efficiency", "total_medal"],
                                       ascending=False)
    return df.head(k)["NOC"].tolist()


def block_c(base: pd.DataFrame, first: pd.DataFrame, event: pd.DataFrame) -> dict:
    """C 块：HKG / SGP / TPE + 5 个自选小团成功案例的个案档案。

    输入：s4_base、s4_noc_first_medal、medal_event_level
    输出：
      c_case_countries.csv       案例国档案（首参赛/首牌/首金/届数/奖牌/项目 Top3）
      c_case_medal_by_sport.csv  案例国 × 运动大类 × 奖牌数（堆叠条形图底表）
      c_hkg_detail.csv / c_sgp_detail.csv / c_tpe_detail.csv 逐届明细
    口径：奖牌一律小项口径；「首牌届」= 本数据集内最早有奖牌届次（早期可能缺记）。
    """
    out: dict = {}
    extra = pick_extra_cases(event, base, exclude=NAMED, k=5)
    cases = NAMED + extra
    out["selected_cases"] = {"named": NAMED, "extra": extra,
                             "rule": "候选池内 历史小项口径奖牌/峰值参赛人数 降序取5"}

    # 当届夺牌项目列表（小项口径，去重后按字母序拼接）
    ev_ys = (event.groupby(["Year", "NOC"])["Sport"]
             .agg(lambda s: "; ".join(sorted(set(s))))
             .rename("medal_sport_list").reset_index())

    # 项目 × 奖牌数明细
    sp = (event[event["NOC"].isin(cases)]
          .groupby(["NOC", "Sport"], as_index=False)["Total"].sum()
          .sort_values(["NOC", "Total"], ascending=[True, False]))
    sp = sp.merge(first[["NOC", "Team"]], on="NOC", how="left")
    sp["rank_in_noc"] = sp.groupby("NOC")["Total"].rank(ascending=False, method="min")
    save_csv(sp, "c_case_medal_by_sport.csv")

    # 国家档案
    rows = []
    for noc in cases:
        g = base[base["NOC"] == noc].sort_values("Year")
        f = first[first["NOC"] == noc].iloc[0]
        s3 = sp[(sp["NOC"] == noc) & (sp["rank_in_noc"] <= 3)]
        rows.append({
            "NOC": noc, "Team": f["Team"],
            "first_olympic_year": int(f["first_year"]),
            "first_medal_year": None if pd.isna(f["first_medal_year"])
            else int(f["first_medal_year"]),
            "first_gold_year": None if pd.isna(f["first_gold_year"])
            else int(f["first_gold_year"]),
            "n_appearances": int(f["n_appear"]),
            "n_medal_editions": int(f["n_medal_editions"]),
            "medal_edition_rate": round(float(f["n_medal_editions"] / f["n_appear"]), 4),
            "total_medal_event": int(g["Total_event"].sum()),
            "total_gold_event": int(g["Gold_event"].sum()),
            "max_medal_single_edition": int(g["Total_event"].max()),
            "max_athletes_single_edition": int(g["athletes"].max()),
            "median_athletes": float(g["athletes"].median()),
            "top3_sports_with_medals": "; ".join(
                f"{r.Sport}:{int(r.Total)}" for r in s3.itertuples()),
            "n_medal_sports_total": int(sp.loc[sp["NOC"] == noc, "Sport"].nunique()),
            "has_ever_been_small_le50": int((g["athletes"] <= 50).any()),
        })
    cc = pd.DataFrame(rows)
    save_csv(cc, "c_case_countries.csv")
    out["case_countries"] = cc.to_dict(orient="records")

    # 逐届明细（点名三国）
    for noc in NAMED:
        g = base[base["NOC"] == noc].sort_values("Year")
        d = g[["Year", "NOC", "Team", "athletes", "sports", "events",
               "Gold_event", "Silver_event", "Bronze_event", "Total_event",
               "Total_athlete", "n_sports_medal", "top_sport", "top1_share"]].copy()
        d = d.merge(ev_ys[ev_ys["NOC"] == noc], on=["Year", "NOC"], how="left")
        d["medal_sport_list"] = d["medal_sport_list"].fillna("")
        d["has_medal_event"] = (d["Total_event"] > 0).astype(int)
        save_csv(d, f"c_{noc.lower()}_detail.csv")
        out[f"{noc.lower()}_detail_summary"] = {
            "n_appearances": int(len(d)),
            "n_medal_editions": int(d["has_medal_event"].sum()),
            "total_medal_event": int(d["Total_event"].sum()),
            "total_gold_event": int(d["Gold_event"].sum()),
            "max_athletes": int(d["athletes"].max()),
            "median_athletes": float(d["athletes"].median()),
            "editions_with_medal": d.loc[d["has_medal_event"] == 1,
                                         ["Year", "athletes", "Total_event",
                                          "Gold_event", "medal_sport_list"]]
            .to_dict(orient="records"),
        }
    return out


# --------------------------------------------------------------------------- #
# D 块：突破的可持续性
# --------------------------------------------------------------------------- #
def consecutive_streak(flags: list[int]) -> int:
    """求 0/1 序列中最长连续 1 的长度（= 连续夺牌届数）。

    输入：按年份升序排列的夺牌标记列表。
    输出：最长连续 1 的个数；无 1 时返回 0。
    """
    best = cur = 0
    for f in flags:
        cur = cur + 1 if f == 1 else 0
        best = max(best, cur)
    return int(best)


def build_persistence(base: pd.DataFrame, first: pd.DataFrame) -> pd.DataFrame:
    """逐代表团计算「首牌之后的持续性」。

    输入：s4_base（逐届）、s4_noc_first_medal（首牌届等档案）
    输出：每代表团一行，含
      first_medal_year / n_appear / n_medal_editions
      post_n        首牌之后（不含首牌届）的参赛届数
      post_medal_n  首牌之后有奖牌的届数
      post_first_medal_rate = post_medal_n / post_n（post_n=0 时为 NaN）
      max_streak    全期「连续夺牌」的最长连续届数
      gap_first_to_second 首牌→第二次夺牌 的年份间隔
    口径：奖牌 = 小项口径（Total_event>0）；只统计本数据集记录的届次，
          「连续」按参赛届次序号计，不按年份差计（跳一届即中断）。
    """
    rows = []
    for noc, g in base.groupby("NOC", observed=True):
        g = g.sort_values("Year")
        years = g["Year"].to_numpy()
        flags = (g["has_medal_event"] == 1).to_numpy().astype(int)
        if flags.sum() == 0:
            continue
        first_idx = int(np.argmax(flags))          # 首次夺牌在序列中的位置
        after = flags[first_idx + 1:]
        medal_years = years[flags == 1]
        f0 = first[first["NOC"] == noc].iloc[0]
        rows.append({
            "NOC": noc, "Team": f0["Team"],
            "first_medal_year": int(medal_years[0]),
            "second_medal_year": int(medal_years[1]) if len(medal_years) > 1 else None,
            "gap_first_to_second": (int(medal_years[1] - medal_years[0])
                                    if len(medal_years) > 1 else None),
            "n_appear": int(len(flags)),
            "n_medal_editions": int(flags.sum()),
            "post_n": int(after.size),
            "post_medal_n": int(after.sum()),
            "post_first_medal_rate": (round(float(after.mean()), 4)
                                      if after.size else np.nan),
            "max_streak": consecutive_streak(flags.tolist()),
            "total_medal_event": int(g["Total_event"].sum()),
            "max_athletes": int(g["athletes"].max()),
            "median_athletes": float(g["athletes"].median()),
        })
    return pd.DataFrame(rows)


def block_d(base: pd.DataFrame, first: pd.DataFrame) -> dict:
    """D 块第二核心检验：突破之后能不能守住。

    输入：s4_base、s4_noc_first_medal
    输出：
      d_persistence.csv        每个曾夺牌代表团一行（首牌届/后续夺牌率/最长连冠）
      d_one_hit_wonders.csv    仅在一届夺过奖牌的代表团明细
      d_streak_by_type.csv     小团型 / 大团型 的持续性分布对照
    分组定义：按代表团「历史峰值参赛人数」分型 —— 小团型 = max_athletes ≤ 50，
              大团型 = max_athletes > 50。这是「该国是否有能力凑出大团」的代理变量。
    """
    out: dict = {}
    pers = build_persistence(base, first)
    if pers.empty:
        raise RuntimeError("持续性表为空，数据异常")
    pers["team_type"] = np.where(pers["max_athletes"] <= SMALL_MAIN, "小团型(峰值≤50)",
                                 "大团型(峰值>50)")
    pers = pers.sort_values("total_medal_event", ascending=False).reset_index(drop=True)
    save_csv(pers, "d_persistence.csv")
    out["persistence_overview"] = {
        "n_noc_ever_medal": int(len(pers)),
        "median_post_first_medal_rate": round(
            float(pers["post_first_medal_rate"].median()), 4),
        "mean_post_first_medal_rate": round(
            float(pers["post_first_medal_rate"].mean()), 4),
        "median_max_streak": float(pers["max_streak"].median()),
        "share_never_medal_again": round(float((pers["post_medal_n"] == 0).mean()), 4),
        "n_never_medal_again": int((pers["post_medal_n"] == 0).sum()),
        "share_post_rate_ge_0_5": round(
            float((pers["post_first_medal_rate"] >= 0.5).mean()), 4),
        "median_gap_first_to_second": (None if pers["gap_first_to_second"].isna().all()
                                       else float(pers["gap_first_to_second"].median())),
    }

    # ---- 分组对比：小团型 vs 大团型 ----
    a = pers[pers["team_type"] == "小团型(峰值≤50)"]
    b = pers[pers["team_type"] == "大团型(峰值>50)"]
    cmp_ = {}
    for col in ["post_first_medal_rate", "max_streak", "n_medal_editions",
                "n_appear", "total_medal_event"]:
        cmp_[col] = mwu_test(a[col], b[col])
    streak_tbl = (pers.groupby("team_type")
                  .agg(n_noc=("NOC", "size"),
                       post_rate_median=("post_first_medal_rate", "median"),
                       post_rate_mean=("post_first_medal_rate", "mean"),
                       post_rate_p25=("post_first_medal_rate",
                                      lambda s: float(s.quantile(0.25))),
                       post_rate_p75=("post_first_medal_rate",
                                      lambda s: float(s.quantile(0.75))),
                       max_streak_median=("max_streak", "median"),
                       n_medal_editions_median=("n_medal_editions", "median"),
                       total_medal_median=("total_medal_event", "median"))
                  .reset_index())
    save_csv(streak_tbl.round(4), "d_streak_by_type.csv")
    out["persistence_by_team_type"] = streak_tbl.round(4).to_dict(orient="records")
    out["mwu_small_type_vs_big_type"] = {
        "group_def": "小团型=max_athletes<=50；大团型=max_athletes>50",
        "n_small_type": int(len(a)), "n_big_type": int(len(b)),
        "note": "第一组=小团型，第二组=大团型；effect_r>0 表示小团型更大",
        "results": cmp_,
    }

    # ---- 单届爆发识别（one-hit wonders）----
    ohw = pers[pers["n_medal_editions"] == 1].copy()
    ohw = ohw[["NOC", "Team", "first_medal_year", "n_appear", "max_athletes",
               "median_athletes", "total_medal_event", "team_type"]]
    ohw = ohw.sort_values(["total_medal_event", "max_athletes"],
                          ascending=[False, True]).reset_index(drop=True)
    save_csv(ohw, "d_one_hit_wonders.csv")
    multi = pers[pers["n_medal_editions"] > 1]
    out["one_hit_wonders"] = {
        "definition": "n_medal_editions == 1（仅在一届拿到小项口径奖牌）",
        "n_one_hit": int(len(ohw)),
        "n_noc_ever_medal": int(len(pers)),
        "share_of_medal_nations": round(float(len(ohw) / len(pers)), 4),
        "mean_max_athletes": round(float(ohw["max_athletes"].mean()), 2),
        "median_max_athletes": float(ohw["max_athletes"].median()),
        "mean_total_medal_event": round(float(ohw["total_medal_event"].mean()), 2),
        "median_total_medal_event": float(ohw["total_medal_event"].median()),
        "share_max_athletes_le50": round(float((ohw["max_athletes"] <= 50).mean()), 4),
        "multi_mean_max_athletes": round(float(multi["max_athletes"].mean()), 2),
        "multi_mean_total_medal": round(float(multi["total_medal_event"].mean()), 2),
        "share_noc_le50_among_all_medal": round(
            float((pers["max_athletes"] <= 50).mean()), 4),
        "examples_top8": ohw.head(8).to_dict(orient="records"),
    }
    # One-hit 与否 的规模差异检验（回答「偶然还是能力」）
    out["one_hit_vs_multi_scale_test"] = mwu_test(ohw["max_athletes"],
                                                  multi["max_athletes"])
    # 近代口径：1980 后首牌的国家里 one-hit 比例
    modern_first = pers[pers["first_medal_year"] >= MODERN_FROM]
    m1 = modern_first[modern_first["n_medal_editions"] == 1]
    out["one_hit_modern_cohort"] = {
        "n_noc_first_medal_1980plus": int(len(modern_first)),
        "n_one_hit_among_them": int(len(m1)),
        "share": round(float(len(m1) / len(modern_first)), 4)
        if len(modern_first) else None,
        "median_max_athletes_one_hit": (float(m1["max_athletes"].median())
                                        if len(m1) else None),
    }
    return out


# --------------------------------------------------------------------------- #
# E 块：敏感性检验
# --------------------------------------------------------------------------- #
def block_e(base: pd.DataFrame) -> dict:
    """E 块：结论稳健性。

    输入：s4_base
    输出：
      e_threshold_sensitivity.csv  阈值 10/25/50/100/150 下的小团夺牌率、效率中位数、
                                   top1_share 中位数、与「其余团」差异的 MWU p 值
      e_caliber_sensitivity.csv    小项口径 vs 运动员行口径 的 medal_per_athlete 对照
    口径：每个阈值下「对照组」= 参赛人数 > 该阈值；率用全部届次，效率用 1980+ 有奖牌。
    """
    out: dict = {}
    rows = []
    for th in THRESHOLDS:
        s_all = base[base["athletes"] <= th]
        b_all = base[base["athletes"] > th]
        rate_s = float((s_all["has_medal_event"] == 1).mean())
        rate_b = float((b_all["has_medal_event"] == 1).mean())
        s = s_all[(s_all["Year"] >= MODERN_FROM) & (s_all["has_medal_event"] == 1)]
        b = b_all[(b_all["Year"] >= MODERN_FROM) & (b_all["has_medal_event"] == 1)]
        t_top = mwu_test(s["top1_share"], b["top1_share"])
        t_nsp = mwu_test(s["n_sports_medal"], b["n_sports_medal"])
        t_mpa = mwu_test(s["medal_per_athlete"], b["medal_per_athlete"])
        t_rate = mwu_test(s_all["has_medal_event"], b_all["has_medal_event"])
        rows.append({
            "threshold": th,
            "n_small_editions": int(len(s_all)), "n_big_editions": int(len(b_all)),
            "small_medal_rate": round(rate_s, 4), "big_medal_rate": round(rate_b, 4),
            "rate_gap": round(rate_s - rate_b, 4),
            "rate_mwu_p": None if t_rate["p"] is None else round(t_rate["p"], 6),
            "n_small_with_medal_1980plus": int(len(s)),
            "n_big_with_medal_1980plus": int(len(b)),
            "small_mpa_median": round(float(s["medal_per_athlete"].median()), 4),
            "big_mpa_median": round(float(b["medal_per_athlete"].median()), 4),
            "mpa_mwu_p": None if t_mpa["p"] is None else round(t_mpa["p"], 6),
            "mpa_effect_r": None if t_mpa["effect_r"] is None
            else round(t_mpa["effect_r"], 4),
            "small_top1_share_median": round(float(s["top1_share"].median()), 4),
            "big_top1_share_median": round(float(b["top1_share"].median()), 4),
            "top1_share_mwu_p": None if t_top["p"] is None else round(t_top["p"], 6),
            "top1_share_effect_r": None if t_top["effect_r"] is None
            else round(t_top["effect_r"], 4),
            "small_n_sports_median": float(s["n_sports_medal"].median()),
            "big_n_sports_median": float(b["n_sports_medal"].median()),
            "n_sports_mwu_p": None if t_nsp["p"] is None else round(t_nsp["p"], 6),
            "n_sports_effect_r": None if t_nsp["effect_r"] is None
            else round(t_nsp["effect_r"], 4),
        })
    th_tbl = pd.DataFrame(rows)
    save_csv(th_tbl, "e_threshold_sensitivity.csv")
    out["threshold_sensitivity"] = th_tbl.to_dict(orient="records")

    # 结论是否翻转：看符号一致性 + 显著性个数
    sign_mpa = set(np.sign(th_tbl["small_mpa_median"] - th_tbl["big_mpa_median"]))
    sign_top = set(np.sign(th_tbl["small_top1_share_median"]
                           - th_tbl["big_top1_share_median"]))
    sign_nsp = set(np.sign(th_tbl["small_n_sports_median"]
                           - th_tbl["big_n_sports_median"]))
    sig_top = (th_tbl["top1_share_mwu_p"] < 0.05)
    sig_mpa = (th_tbl["mpa_mwu_p"] < 0.05)
    out["threshold_robustness_verdict"] = {
        "n_thresholds": len(THRESHOLDS),
        "mpa_sign_consistent": bool(len(sign_mpa) == 1),
        "mpa_sign": ("小团更高" if sign_mpa == {1.0}
                     else "大团更高" if sign_mpa == {-1.0} else "方向随阈值翻转"),
        "mpa_n_significant": int(sig_mpa.sum()),
        "top1_share_sign_consistent": bool(len(sign_top) == 1),
        "top1_share_sign": ("小团更高" if sign_top == {1.0}
                            else "大团更高" if sign_top == {-1.0} else "方向随阈值翻转"),
        "top1_share_n_significant": int(sig_top.sum()),
        "n_sports_sign_consistent": bool(len(sign_nsp) == 1),
        "n_sports_n_significant": int((th_tbl["n_sports_mwu_p"] < 0.05).sum()),
    }

    # ---- 口径敏感性：小项口径 vs 运动员行口径 ----
    cal_rows = []
    for label, df in [("全期有奖牌", base[base["has_medal_event"] == 1]),
                      ("1980+有奖牌", base[(base["has_medal_event"] == 1)
                                           & (base["Year"] >= MODERN_FROM)])]:
        sm = df[df["athletes"] <= SMALL_MAIN]
        bg = df[df["athletes"] > BIG_CMP]
        for cal, mpa_col, tot_col in [("event（小项·主口径）", "medal_per_athlete",
                                       "Total_event"),
                                      ("athlete（运动员行·对照）", "medal_per_athlete_row",
                                       "Total_athlete")]:
            t = mwu_test(sm[mpa_col], bg[mpa_col])
            cal_rows.append({
                "sample": label, "caliber": cal,
                "n_small_le50": int(len(sm)), "n_big_gt150": int(len(bg)),
                "small_mpa_median": round(float(sm[mpa_col].median()), 4),
                "big_mpa_median": round(float(bg[mpa_col].median()), 4),
                "mwu_p": None if t["p"] is None else round(t["p"], 6),
                "effect_r": None if t["effect_r"] is None else round(t["effect_r"], 4),
                "direction": t["direction"],
                "total_medal_sum_in_sample": int(df[tot_col].sum()),
            })
    cal = pd.DataFrame(cal_rows)
    save_csv(cal, "e_caliber_sensitivity.csv")
    out["caliber_sensitivity"] = {
        "rows": cal.to_dict(orient="records"),
        "anchors": {
            "event_caliber_total_medals": int(base["Total_event"].sum()),
            "athlete_caliber_total_medals": int(base["Total_athlete"].sum()),
            "ratio_athlete_to_event": round(
                float(base["Total_athlete"].sum() / base["Total_event"].sum()), 4),
        },
        "note": "top1_share / n_sports_medal 按运动大类聚合，与奖牌口径无关，只在 A/B 块列出",
    }
    dirs: dict = {}
    for r in cal_rows:
        dirs.setdefault(r["sample"], []).append(r["direction"])
    out["caliber_verdict"] = {
        "same_direction_within_sample": all(len(set(v)) == 1 for v in dirs.values()),
        "detail": dirs,
    }
    return out


# --------------------------------------------------------------------------- #
# F 块：时间趋势（近代小团崛起）
# --------------------------------------------------------------------------- #
def build_rise_table(base: pd.DataFrame) -> pd.DataFrame:
    """逐届计算「小团份额」相关指标。

    输入：s4_base
    输出：每届一行 —— 参赛代表团数、小团数、小团夺牌数份额、
          小团夺牌代表团数份额、小团运动员数份额、大团奖牌份额
    口径：分母均为当届总量；小团 = athletes ≤ 50；奖牌 = 小项口径。
    """
    rows = []
    for y, g in base.groupby("Year", observed=True):
        sm = g[g["athletes"] <= SMALL_MAIN]
        bg = g[g["athletes"] > SMALL_MAIN]
        tot_medal = int(g["Total_event"].sum())
        tot_medal_noc = int((g["has_medal_event"] == 1).sum())
        rows.append({
            "Year": int(y),
            "n_noc": int(len(g)),
            "n_small": int(len(sm)),
            "small_share_of_noc": round(len(sm) / len(g), 4),
            "small_medal": int(sm["Total_event"].sum()),
            "total_medal": tot_medal,
            "small_medal_share": (round(int(sm["Total_event"].sum()) / tot_medal, 4)
                                  if tot_medal else np.nan),
            "n_medal_noc": tot_medal_noc,
            "n_medal_noc_small": int((sm["has_medal_event"] == 1).sum()),
            "small_medal_noc_share": (round(
                int((sm["has_medal_event"] == 1).sum()) / tot_medal_noc, 4)
                if tot_medal_noc else np.nan),
            "small_athletes": int(sm["athletes"].sum()),
            "small_athlete_share": round(int(sm["athletes"].sum())
                                         / int(g["athletes"].sum()), 4),
            "big_medal_share": (round(int(bg["Total_event"].sum()) / tot_medal, 4)
                                if tot_medal else np.nan),
        })
    return pd.DataFrame(rows).sort_values("Year").reset_index(drop=True)


def block_f(base: pd.DataFrame) -> dict:
    """F 块：1980–2024 小团份额是否真的上升。

    输入：s4_base
    输出：
      f_small_rise.csv           1980–2024 逐届份额表（作图用）
      f_small_rise_all_years.csv 全期版本（自查用）
    趋势检验：年份 vs 份额 的 OLS（斜率 + R² + p），并用 Spearman 作稳健性对照。
    """
    out: dict = {}
    f_all = build_rise_table(base)
    save_csv(f_all, "f_small_rise_all_years.csv")
    f = f_all[f_all["Year"] >= MODERN_FROM].reset_index(drop=True)
    save_csv(f, "f_small_rise.csv")

    metrics = ["small_medal_share", "small_medal_noc_share", "small_share_of_noc",
               "small_athlete_share", "n_small"]
    tr = {m: ols_trend(f["Year"], f[m]) for m in metrics}
    sp = {m: spearman_test(f["Year"], f[m], f"1980-2024 {m} 随年份") for m in metrics}
    out["f_series_1980_2024"] = f.to_dict(orient="records")
    out["trend_1980_2024_ols"] = tr
    out["trend_1980_2024_spearman"] = sp
    out["trend_verdict"] = {
        "small_medal_share_1980": float(
            f.loc[f["Year"] == 1980, "small_medal_share"].iloc[0]),
        "small_medal_share_2024": float(
            f.loc[f["Year"] == 2024, "small_medal_share"].iloc[0]),
        "small_medal_share_min": float(f["small_medal_share"].min()),
        "small_medal_share_min_year": int(f.loc[f["small_medal_share"].idxmin(), "Year"]),
        "small_medal_share_max": float(f["small_medal_share"].max()),
        "small_medal_share_max_year": int(f.loc[f["small_medal_share"].idxmax(), "Year"]),
        "ols_slope_per_year_pct_points": round(
            tr["small_medal_share"]["slope"] * 100, 4),
        "ols_r2": tr["small_medal_share"]["r2"],
        "ols_p": tr["small_medal_share"]["p"],
        "spearman_rho": sp["small_medal_share"]["rho"],
        "spearman_p": sp["small_medal_share"]["p"],
        "n_small_1980": int(f.loc[f["Year"] == 1980, "n_small"].iloc[0]),
        "n_small_2024": int(f.loc[f["Year"] == 2024, "n_small"].iloc[0]),
        "n_noc_1980": int(f.loc[f["Year"] == 1980, "n_noc"].iloc[0]),
        "n_noc_2024": int(f.loc[f["Year"] == 2024, "n_noc"].iloc[0]),
    }
    return out


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def verify_anchors(base: pd.DataFrame, event: pd.DataFrame) -> dict:
    """口径锚点自检：确保读到的数字与任务书一致，防止跑错文件版本。"""
    checks = [
        ("小项口径奖牌总数(medal_event_level)", 17901,
         int(event[["Gold", "Silver", "Bronze"]].sum().sum())),
        ("小项口径奖牌总数(s4_base.Total_event)", 17901,
         int(base["Total_event"].sum())),
        ("运动员行口径奖牌总数", 38360, int(base["Total_athlete"].sum())),
        ("代表团届次样本量", 3201, int(len(base))),
        ("代表团数", 233, int(base["NOC"].nunique())),
        ("官方届次数", 30, int(base["Year"].nunique())),
        ("1906 应为 0 行", 0, int((base["Year"] == 1906).sum())),
    ]
    res = [{"check": n, "expect": e, "actual": a, "ok": e == a} for n, e, a in checks]
    for r in res:
        print(f"  [{'OK' if r['ok'] else 'FAIL'}] {r['check']}: "
              f"期望 {r['expect']} / 实测 {r['actual']}")
    if not all(r["ok"] for r in res):
        raise RuntimeError("口径锚点校验失败，请检查输入文件版本")
    return {"checks": res, "all_pass": True}


def print_summary(res: dict) -> None:
    """把六块的核心数字打印到控制台（便于人工核对与写报告取数）。"""
    ra, rb = res["A_panorama"], res["B_strategy"]
    rc, rd = res["C_cases"], res["D_persistence"]
    re_, rf = res["E_sensitivity"], res["F_trend"]

    print("  A: 各规模档夺牌率")
    for r in ra["medal_rate_by_size_class"]:
        print(f"     {r['size_class']:<12} 全期 {r['medal_rate']:.2%} (n={r['n']})"
              f" | 近代 {r['medal_rate_modern']:.2%} (n={r['n_modern']})"
              f" | 奖牌 {int(r['total_medal'])}")
    tt = ra["small_medal_rate_trend"]
    print(f"  A: 小团夺牌率 1980={tt['value_1980']:.2%} -> 2024={tt['value_2024']:.2%}, "
          f"差 {tt['change_1980_2024_pct_points']:+.2f}pp, "
          f"slope={tt['modern_slope_pct_points_per_year']:+.3f}pp/年, "
          f"R2={tt['modern_ols']['r2']:.4f}, p={tt['modern_ols']['p']:.4g}")
    t5 = ra["tiny_teams_with_medal"]
    print(f"  A: ≤5 人代表团 {t5['n_cases']}/{t5['n_editions_athletes_le5']} 夺过牌 "
          f"({t5['rate']:.2%})，涉及 {t5['n_noc']} 个 NOC")

    print("  B: Spearman（1980+ 有奖牌）")
    for k, v in rb["spearman"].items():
        print(f"     {k:<42} rho={v['rho']:+.4f} p={v['p']:.4g} n={v['n']} {v['note']}")
    gc = rb["group_compare_small50_vs_big150"]
    print(f"  B: MWU 小团(≤50,n={gc['n_small_le50']}) vs 大团(>150,n={gc['n_big_gt150']})")
    for k, v in gc["results"].items():
        print(f"     {k:<18} {v['median1']:.4f} vs {v['median2']:.4f} | U={v['U']:.1f} "
              f"p={v['p']:.4g} r={v['effect_r']:+.4f} ({v['direction']})")
    print("  B: 人数分箱 medal_per_athlete 中位数 [bootstrap 95%CI, B=2000, seed=42]")
    for r in rb["efficiency_vs_size"]:
        print(f"     {r['size_bin']:<8} n={r['n_with_medal']:<4} "
              f"{r['mpa_median']:.4f} [{r['ci95_low']:.4f}, {r['ci95_high']:.4f}]")

    print(f"  C: 自选案例 {rc['selected_cases']['extra']}；"
          f"点名案例 {rc['selected_cases']['named']}")
    for c in rc["case_countries"]:
        print(f"     {c['NOC']:<4} 首牌 {c['first_medal_year']} 首金 {c['first_gold_year']} "
              f"夺牌届次 {c['n_medal_editions']}/{c['n_appearances']} "
              f"奖牌 {c['total_medal_event']} (金 {c['total_gold_event']}) "
              f"峰值人数 {c['max_athletes_single_edition']} | {c['top3_sports_with_medals']}")

    ov = rd["persistence_overview"]
    print(f"  D: 曾夺牌 NOC {ov['n_noc_ever_medal']}，首牌后夺牌率中位 "
          f"{ov['median_post_first_medal_rate']:.2%}，最长连冠中位 "
          f"{ov['median_max_streak']}，首牌后再无牌占比 "
          f"{ov['share_never_medal_again']:.2%}")
    mt = rd["mwu_small_type_vs_big_type"]
    print(f"  D: MWU 小团型(n={mt['n_small_type']}) vs 大团型(n={mt['n_big_type']})")
    for k, v in mt["results"].items():
        print(f"     {k:<24} {v['median1']} vs {v['median2']} | U={v['U']:.1f} "
              f"p={v['p']:.4g} r={v['effect_r']:+.4f}")
    oh = rd["one_hit_wonders"]
    print(f"  D: 单届爆发 {oh['n_one_hit']}/{oh['n_noc_ever_medal']}="
          f"{oh['share_of_medal_nations']:.2%}，平均峰值人数 {oh['mean_max_athletes']}"
          f" vs 多届 {oh['multi_mean_max_athletes']}")
    st = rd["one_hit_vs_multi_scale_test"]
    print(f"     规模差异 MWU: U={st['U']:.1f} p={st['p']:.4g} r={st['effect_r']:+.4f} "
          f"(n1={st['n1']}, n2={st['n2']})")
    mc = rd["one_hit_modern_cohort"]
    print(f"  D: 1980 后首牌国家 {mc['n_noc_first_medal_1980plus']} 个，其中单届爆发 "
          f"{mc['n_one_hit_among_them']} ({mc['share']})")

    print("  E: 阈值敏感性")
    for r in re_["threshold_sensitivity"]:
        print(f"     th={r['threshold']:<4} 率 {r['small_medal_rate']:.2%} vs "
              f"{r['big_medal_rate']:.2%} | mpa {r['small_mpa_median']} vs "
              f"{r['big_mpa_median']} p={r['mpa_mwu_p']} | top1 "
              f"{r['small_top1_share_median']} vs {r['big_top1_share_median']} "
              f"p={r['top1_share_mwu_p']} | n_sports {r['small_n_sports_median']} vs "
              f"{r['big_n_sports_median']}")
    print(f"  E: 稳健性判定 {re_['threshold_robustness_verdict']}")
    print(f"  E: 口径判定 {re_['caliber_verdict']} 锚点 "
          f"{re_['caliber_sensitivity']['anchors']}")
    print("  E: 口径敏感性明细")
    for r in re_["caliber_sensitivity"]["rows"]:
        print(f"     {r['sample']:<12} {r['caliber']:<24} mpa "
              f"{r['small_mpa_median']} vs {r['big_mpa_median']} "
              f"p={r['mwu_p']} r={r['effect_r']} ({r['direction']})")

    fv = rf["trend_verdict"]
    print(f"  F: 小团奖牌份额 1980={fv['small_medal_share_1980']:.2%} -> "
          f"2024={fv['small_medal_share_2024']:.2%}，min={fv['small_medal_share_min']:.2%}"
          f"({fv['small_medal_share_min_year']}) max={fv['small_medal_share_max']:.2%}"
          f"({fv['small_medal_share_max_year']})")
    print(f"     OLS slope={fv['ols_slope_per_year_pct_points']:+.4f}pp/年 "
          f"R2={fv['ols_r2']:.4f} p={fv['ols_p']:.4g} | Spearman rho="
          f"{fv['spearman_rho']:+.4f} p={fv['spearman_p']:.4g}")
    print(f"     小团数 {fv['n_small_1980']} -> {fv['n_small_2024']}，"
          f"当届代表团 {fv['n_noc_1980']} -> {fv['n_noc_2024']}")
    print("  F: 逐届份额（Year | 小团数 | 小团奖牌份额 | 小团夺牌国份额 | 参赛国）")
    for r in rf["f_series_1980_2024"]:
        print(f"     {r['Year']} | {r['n_small']:>3} | {r['small_medal_share']:.2%} | "
              f"{r['small_medal_noc_share']:.2%} | {r['n_noc']}")


def main() -> dict:
    """跑通 A–F 六块分析，落盘 CSV + s4_results.json，并打印核心结论。"""
    print("=" * 78)
    print("Task3 S4「小代表团的大突破」分析脚本")
    print("=" * 78)
    base, first, event = load_data()
    print(f"\n[载入] s4_base {base.shape} | s4_noc_first_medal {first.shape} | "
          f"medal_event_level {event.shape}")
    print("\n[口径锚点自检]")
    anchors = verify_anchors(base, event)

    print("\n[A 块] 小代表团全景")
    ra = block_a(base)
    print("\n[B 块] 小而精 vs 全面上阵")
    rb = block_b(base)
    print("\n[C 块] 个案深挖")
    rc = block_c(base, first, event)
    print("\n[D 块] 突破口可持续性")
    rd = block_d(base, first)
    print("\n[E 块] 敏感性检验")
    re_ = block_e(base)
    print("\n[F 块] 时间趋势")
    rf = block_f(base)

    results = {
        "meta": {
            "script": "backend/src/task3_s4_analysis.py",
            "upstream": ["outputs/task3_s4/s4_base.csv",
                         "outputs/task3_s4/s4_noc_first_medal.csv",
                         "docs/Task1/medal_event_level.csv"],
            "primary_caliber": "小项口径 Total_event（合计 17,901）",
            "reference_caliber": "运动员行口径 Total_athlete（合计 38,360）",
            "small_threshold": SMALL_MAIN,
            "small_threshold_sensitivity": THRESHOLDS,
            "modern_from": MODERN_FROM,
            "big_group_for_compare": f"athletes > {BIG_CMP}",
            "bootstrap": {"n_boot": N_BOOT, "seed": SEED,
                          "method": "percentile on median"},
            "tests": "scipy.stats spearmanr / mannwhitneyu(two-sided) / linregress",
            "excluded_years": [1906],
        },
        "anchors": anchors,
        "A_panorama": ra,
        "B_strategy": rb,
        "C_cases": rc,
        "D_persistence": rd,
        "E_sensitivity": re_,
        "F_trend": rf,
    }
    outp = T3 / "s4_results.json"
    outp.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str),
                    encoding="utf-8")
    print(f"\n[写出] s4_results.json: {outp.stat().st_size} 字节")

    print("\n" + "=" * 78)
    print("核心结论（全部本脚本现算）")
    print("=" * 78)
    print_summary(results)

    n_csv = len(sorted(TAB.glob("*.csv")))
    print(f"\n[完成] outputs/task3_s4/tables 下共 {n_csv} 个 CSV；"
          f"另生成 outputs/task3_s4/s4_results.json")
    return results


if __name__ == "__main__":
    main()
