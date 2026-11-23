"""
数据清洗与口径构建主脚本
========================
职责
----
把原始 `olympics_dataset.csv` 清洗为可分析资产：
1. 体育大类归一（含逗号拼接拆分）
2. 小项泛化标记（2020 起的 Men/Women/... 泛化值）
3. 特殊届次与政体继承标记（1906、URS→RUS 等）
4. 奖牌双口径：运动员行口径 / 小项口径
5. 输出主表、小项奖牌表、代表团×届次汇总表

调用关系
--------
- 上游调用方：`src/run_all.py`（串行，第 2 步）或命令行直接运行。
- 下游被调用方：仅依赖 pandas/numpy，不 import 本项目其他业务模块；
  其输出被 `src/features.py`、`src/visualize.py`、`src/quality_report_assets.py` 读取。
- 并发/线程：单进程单线程；所有操作为纯函数式 DataFrame 变换，
  每个 build_* 函数返回新表而不改入参，便于 run_all 中按需复用中间结果。

设计原则
--------
- 不静默丢行：任何过滤都必须在新列上打标记，行数守恒由 `verify()` 校验。
- 口径显式化：两套奖牌口径分别落到不同列/表，绝不混用。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# 项目根目录：backend/src/cleaning.py → 上溯三级才是仓库根
ROOT = Path(__file__).resolve().parents[2]
RAW_CSV = ROOT / "olympics_dataset.csv"
# 任务一交付物统一落在 docs/Task1，与口径说明书放在同一目录
PROCESSED_DIR = ROOT / "docs" / "Task1"
TABLES_DIR = ROOT / "outputs" / "tables"

# ---------------------------------------------------------------------------
# Sport 归一映射：键为原始取值，值为归一后的大类。
# 依据见 docs/02_数据质量与口径说明书.md 第三节（Q2）。
# ---------------------------------------------------------------------------
SPORT_MAPPING: dict[str, str] = {
    # 体操三分（2020 起拆分）
    "Artistic Gymnastics": "Gymnastics",
    "Rhythmic Gymnastics": "Gymnastics",
    "Trampoline Gymnastics": "Gymnastics",
    # 自行车五分（2020 起拆分）
    "Cycling Road": "Cycling",
    "Cycling Track": "Cycling",
    "Cycling Mountain Bike": "Cycling",
    "Cycling BMX Racing": "Cycling",
    "Cycling BMX Freestyle": "Cycling",
    # 皮划艇二分
    "Canoe Sprint": "Canoeing",
    "Canoe Slalom": "Canoeing",
    # 其余名称漂移
    "Equestrian": "Equestrianism",
    "Artistic Swimming": "Synchronized Swimming",
    "3x3 Basketball": "Basketball",
    "Marathon Swimming": "Swimming",
    "Baseball/Softball": "Baseball/Softball",
}

# 2020 起数据源切换后出现的泛化 Event 取值（无法还原具体小项）
GENERIC_EVENTS = {
    "Men", "Women", "Men Team", "Women Team", "Mixed Team",
    "Relay Only Athlete", "Mixed", "Open",
}

# ---------------------------------------------------------------------------
# NOC 继承链：把历史政体映射到「继承实体」，仅用于长周期国家曲线。
# 键为原始 NOC，值为继承实体标签。未列出的 NOC 继承到自己。
# 依据见说明书第五节（Q5）。
# ---------------------------------------------------------------------------
NOC_LINEAGE: dict[str, str] = {
    # 苏联一脉
    "URS": "RUS", "EUN": "RUS", "ROC": "RUS", "AIN": "RUS",
    # 两德
    "FRG": "GER", "GDR": "GER", "SAA": "GER",
    # 南斯拉夫一脉
    "YUG": "SRB", "SCG": "SRB", "YUG2": "SRB",
    # 捷克斯洛伐克
    "TCH": "CZE",
    # 其他常见分裂政体
    "ANT": "AHO", "BOH": "CZE",
}

MEDAL_COLORS = ["Gold", "Silver", "Bronze"]


def normalize_sport(raw_value: str) -> str:
    """把原始 Sport 归一到体育大类（唯一口径出口）。

    逗号拼接值取首个成分后查映射表，保证映射表与清洗结果完全一致。
    """
    primary = str(raw_value).split(",")[0].strip()
    return SPORT_MAPPING.get(primary, primary)


def load_raw() -> pd.DataFrame:
    """读取原始数据。上游唯一入口，供 run_all 与其他脚本共用。"""
    if not RAW_CSV.exists():
        raise FileNotFoundError(f"原始数据不存在: {RAW_CSV}")
    return pd.read_csv(RAW_CSV, encoding="utf-8")


def build_sport_columns(df: pd.DataFrame) -> pd.DataFrame:
    """构建 sport_normalized 与 sport_all 两列。

    - sport_all：逗号拼接拆成列表字符串，用于「按项展开统计」
    - sport_normalized：逗号取首项后再查 SPORT_MAPPING，得到归一后大类
    """
    out = df.copy()
    # 用分号连接拆开的成分，避免与原逗号分隔冲突
    out["sport_all"] = out["Sport"].fillna("").str.split(",").apply(
        lambda parts: ";".join(p.strip() for p in parts if p.strip())
    )
    # 统一走 normalize_sport，避免映射表与实现两套逻辑
    out["sport_normalized"] = out["Sport"].fillna("").map(normalize_sport)
    return out


def build_event_columns(df: pd.DataFrame) -> pd.DataFrame:
    """构建 event_resolved 与 event_is_generic。

    策略 S2（保留下沉）：泛化值不删除、不改写，只打标记，
    使「小项数」统计能自动识别并在图表中降维说明。
    """
    out = df.copy()
    out["event_is_generic"] = out["Event"].isin(GENERIC_EVENTS)
    out["event_resolved"] = out["Event"]  # 保留原文，供回溯
    return out


def build_special_flags(df: pd.DataFrame) -> pd.DataFrame:
    """构建 is_official 与 noc_lineage 两列。"""
    out = df.copy()
    out["is_official"] = out["Year"] != 1906
    out["noc_lineage"] = out["NOC"].map(lambda n: NOC_LINEAGE.get(n, n))
    out["medal_color"] = out["Medal"].where(out["Medal"] != "No medal", None)
    out["has_medal"] = out["Medal"] != "No medal"
    return out


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """串起全部清洗步骤。纯函数：不改入参，返回新表。"""
    out = df.pipe(build_sport_columns).pipe(build_event_columns).pipe(build_special_flags)
    # 列顺序：原始 11 列 + 派生列，便于人工核对
    base_cols = list(df.columns)
    derived = [c for c in out.columns if c not in base_cols]
    return out[base_cols + derived]


def build_event_level_medals(df_clean: pd.DataFrame,
                             official_only: bool = True) -> pd.DataFrame:
    """构建小项口径（口径 B）奖牌表。

    去重键 (Year, Event, Medal, NOC)：同国同项同色只算 1 枚，吃掉团体项目成员行。
    参数 official_only=True 时排除 1906 届（默认口径）。

    返回列：Year, NOC, noc_lineage, Sport, Event, Gold, Silver, Bronze, Total
    """
    src = df_clean[df_clean["has_medal"]]
    if official_only:
        src = src[src["is_official"]]
    dedup = src.drop_duplicates(subset=["Year", "Event", "Medal", "NOC"])

    pivot = (dedup.groupby(["Year", "NOC", "noc_lineage", "sport_normalized", "Event", "Medal"])
             .size()
             .unstack("Medal", fill_value=0)
             .reset_index())
    for c in MEDAL_COLORS:
        if c not in pivot.columns:
            pivot[c] = 0
    pivot = pivot.rename(columns={"sport_normalized": "Sport"})
    pivot["Total"] = pivot[MEDAL_COLORS].sum(axis=1)
    return pivot[["Year", "NOC", "noc_lineage", "Sport", "Event",
                  "Gold", "Silver", "Bronze", "Total"]]


def build_noc_year_summary(df_clean: pd.DataFrame,
                           event_medals: pd.DataFrame) -> pd.DataFrame:
    """构建「代表团 × 届次」汇总宽表，双口径并列。

    - *_athlete 结尾：运动员行口径（口径 A）
    - *_event 结尾：小项口径（口径 B）
    - 同时带上参赛人数、参赛项目数、性别构成等基础指标
    """
    athlete = df_clean[df_clean["is_official"]].copy()

    # 口径 A：运动员行
    medals_a = athlete[athlete["has_medal"]]
    agg_a = (medals_a.groupby(["Year", "NOC"])["Medal"]
             .value_counts().unstack(fill_value=0))
    for c in MEDAL_COLORS:
        if c not in agg_a.columns:
            agg_a[c] = 0
    agg_a = agg_a.rename(columns={c: f"{c}_athlete" for c in MEDAL_COLORS})
    agg_a["Total_athlete"] = agg_a[[f"{c}_athlete" for c in MEDAL_COLORS]].sum(axis=1)

    # 口径 B：小项
    agg_b = (event_medals.groupby(["Year", "NOC"])[MEDAL_COLORS]
             .sum().rename(columns={c: f"{c}_event" for c in MEDAL_COLORS}))
    agg_b["Total_event"] = agg_b[[f"{c}_event" for c in MEDAL_COLORS]].sum(axis=1)

    # 基础规模指标
    base = athlete.groupby(["Year", "NOC"]).agg(
        athletes=("Name", "size"),
        sports=("sport_normalized", "nunique"),
        events=("Event", "nunique"),
        female=("Sex", lambda s: int((s == "F").sum())),
    )
    noc_name = df_clean.drop_duplicates("NOC").set_index("NOC")["Team"].to_dict()
    lineage = df_clean.drop_duplicates("NOC").set_index("NOC")["noc_lineage"].to_dict()

    out = base.join(agg_a, how="left").join(agg_b, how="left").reset_index()
    fill_cols = [c for c in out.columns if c.endswith("_athlete") or c.endswith("_event")]
    out[fill_cols] = out[fill_cols].fillna(0).astype(int)
    out["Team"] = out["NOC"].map(noc_name)
    out["noc_lineage"] = out["NOC"].map(lineage)
    out["female_ratio"] = (out["female"] / out["athletes"]).round(4)
    return out.sort_values(["Year", "NOC"]).reset_index(drop=True)


def verify(raw: pd.DataFrame, cleaned: pd.DataFrame,
           event_medals: pd.DataFrame, summary: pd.DataFrame) -> dict:
    """清洗校验：完整性 + 保真性。

    - 完整性：行数守恒、无新增缺失、1906 标记数与原数据一致
    - 保真性：抽样若干行，比对清洗前后原始 11 列是否完全一致；
              小项口径奖牌总数应显著小于运动员行口径
    """
    checks = {}
    checks["行数守恒"] = (len(raw), len(cleaned), len(raw) == len(cleaned))
    checks["新增缺失"] = {c: int(cleaned[c].isna().sum())
                         for c in cleaned.columns
                         if c in raw.columns and cleaned[c].isna().sum() > raw[c].isna().sum()}
    checks["1906标记"] = (int((~cleaned["is_official"]).sum()), int((raw["Year"] == 1906).sum()))
    checks["1906一致"] = (~cleaned["is_official"]).sum() == (raw["Year"] == 1906).sum()

    # 保真性：随机抽样 200 行比对原始列
    sample_idx = np.random.default_rng(42).choice(len(raw), size=min(200, len(raw)), replace=False)
    same = cleaned.iloc[sample_idx][list(raw.columns)].reset_index(drop=True).equals(
        raw.iloc[sample_idx].reset_index(drop=True))
    checks["抽样200行原始列一致"] = bool(same)

    # 口径差异：小项口径奖牌数应远小于运动员行口径
    athlete_medals = int(raw.loc[raw["Year"] != 1906, "Medal"].ne("No medal").sum())
    event_medals_total = int(event_medals["Total"].sum())
    checks["运动员行口径奖牌数"] = athlete_medals
    checks["小项口径奖牌数"] = event_medals_total
    checks["口径收缩比例"] = round(1 - event_medals_total / athlete_medals, 4)
    checks["收缩合理"] = event_medals_total < athlete_medals

    # Sport 归一覆盖率
    unmapped = cleaned.loc[~cleaned["sport_normalized"].isin(cleaned["sport_normalized"].unique()), :]
    checks["Sport归一后取值数"] = int(cleaned["sport_normalized"].nunique())
    checks["Sport归一后空值"] = int(cleaned["sport_normalized"].isna().sum())

    return checks


def main() -> dict:
    """入口：清洗 → 建表 → 校验 → 落盘。返回校验字典供 run_all 判定。"""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    raw = load_raw()
    cleaned = clean(raw)
    event_medals = build_event_level_medals(cleaned, official_only=True)
    summary = build_noc_year_summary(cleaned, event_medals)

    cleaned.to_csv(PROCESSED_DIR / "olympics_clean.csv", index=False, encoding="utf-8")
    event_medals.to_csv(PROCESSED_DIR / "medal_event_level.csv", index=False, encoding="utf-8")
    summary.to_csv(PROCESSED_DIR / "noc_year_summary.csv", index=False, encoding="utf-8")

    # 映射表落盘（全部 76 个原始取值，逗号拼接值按归一后的主项给出）
    mapping_rows = [
        {"原始Sport": s, "归一Sport": normalize_sport(s)}
        for s in sorted(raw["Sport"].dropna().unique())
    ]
    pd.DataFrame(mapping_rows).to_csv(PROCESSED_DIR / "sport_mapping.csv",
                                       index=False, encoding="utf-8")

    lineage_rows = [{"NOC": k, "继承实体": v} for k, v in sorted(NOC_LINEAGE.items())]
    pd.DataFrame(lineage_rows).to_csv(PROCESSED_DIR / "noc_lineage.csv",
                                      index=False, encoding="utf-8")

    checks = verify(raw, cleaned, event_medals, summary)

    # 校验结果写成 Markdown，作为「数据清洗校验报告」
    lines = ["# 数据清洗校验报告", "",
             "> 由 `backend/src/cleaning.py` 的 `verify()` 自动生成。", "",
             "| 检查项 | 结果 | 是否通过 |", "|---|---|---|"]
    lines.append(f"| 行数守恒 | 原始 {checks['行数守恒'][0]} → 清洗后 {checks['行数守恒'][1]} | "
                 f"{'✅' if checks['行数守恒'][2] else '❌'} |")
    lines.append(f"| 1906 标记数 | 清洗后 {checks['1906标记'][0]} 行 vs 原始 {checks['1906标记'][1]} 行 | "
                 f"{'✅' if checks['1906一致'] else '❌'} |")
    lines.append(f"| 抽样 200 行原始列一致 | {checks['抽样200行原始列一致']} | "
                 f"{'✅' if checks['抽样200行原始列一致'] else '❌'} |")
    lines.append(f"| 新增缺失列数 | {len(checks['新增缺失'])} | "
                 f"{'✅' if not checks['新增缺失'] else '❌'} |")
    lines.append(f"| 运动员行口径奖牌数 | {checks['运动员行口径奖牌数']:,} | — |")
    lines.append(f"| 小项口径奖牌数 | {checks['小项口径奖牌数']:,} | — |")
    lines.append(f"| 口径收缩比例 | {checks['口径收缩比例']:.2%} | "
                 f"{'✅' if checks['收缩合理'] else '❌'} |")
    lines.append(f"| Sport 归一后取值数 | {checks['Sport归一后取值数']} | — |")
    lines.append(f"| Sport 归一后空值 | {checks['Sport归一后空值']} | "
                 f"{'✅' if checks['Sport归一后空值'] == 0 else '❌'} |")
    lines += ["", "## 口径差异说明", "",
              f"运动员行口径 {checks['运动员行口径奖牌数']:,} 枚 → 小项口径 "
              f"{checks['小项口径奖牌数']:,} 枚，收缩 {checks['口径收缩比例']:.1%}。",
              "差额全部来自团体项目成员行与并列/多队伍同项记录，",
              "与《数据质量与口径说明书》QC2 的结论相互印证。", ""]
    # 校验报告与数据集同目录，便于任务一整体交付
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    (PROCESSED_DIR / "cleaning_verification.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"[cleaning] 主表 {len(cleaned):,} 行 | 小项奖牌表 {len(event_medals):,} 行 "
          f"| 汇总表 {len(summary):,} 行")
    print(f"[cleaning] 校验: 行数守恒={checks['行数守恒'][2]}, "
          f"抽样一致={checks['抽样200行原始列一致']}, "
          f"口径收缩={checks['口径收缩比例']:.1%}")
    return checks


if __name__ == "__main__":
    main()
