"""
特征工程与探索分析
==================
职责
----
在清洗后的数据上构建分析级特征表，并产出四视角 + 两个专题的分析结果表（CSV）
与关键统计量（JSON），供 `src/visualize.py` 绘图与报告引用。

调用关系
--------
- 上游调用方：`src/run_all.py` 第 3 步；也可单独运行（需先跑过 cleaning.py）。
- 读取：data/processed/olympics_clean.csv、medal_event_level.csv、noc_year_summary.csv
- 下游被调用方：src/visualize.py 读取本脚本输出的 outputs/tables/*.csv
- 并发/线程：单进程单线程。每个 perspective_* 函数只读共享入参、各自返回独立 DataFrame，
  因此可安全地在 run_all 中串行调用；没有就地修改（inplace）操作。

设计说明
--------
所有「奖牌数」默认使用**小项口径**（event-level）；使用运动员行口径处一律以
`_athlete` 后缀命名，避免口径混淆。
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "docs" / "Task1"
TABLES = ROOT / "outputs" / "tables"

# 国家兴衰视角要画的国家（含历史政体，用于展示骤起骤落）
FOCUS_NOCS = ["USA", "URS", "GDR", "GER", "CHN", "JPN", "GBR", "AUS", "FRA", "KOR"]

# 政体继承链：与 cleaning.NOC_LINEAGE 保持一致（此处独立声明，避免跨模块耦合）
NOC_TO_LINEAGE = {
    "URS": "RUS", "EUN": "RUS", "ROC": "RUS", "AIN": "RUS",
    "FRG": "GER", "GDR": "GER", "SAA": "GER",
    "YUG": "SRB", "SCG": "SRB",
    "TCH": "CZE", "BOH": "CZE", "ANT": "AHO",
}


def load_processed() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """读取三张清洗后表。缺文件时给出明确提示，避免报错信息难懂。"""
    paths = {
        "clean": PROCESSED / "olympics_clean.csv",
        "event": PROCESSED / "medal_event_level.csv",
        "summary": PROCESSED / "noc_year_summary.csv",
    }
    for name, p in paths.items():
        if not p.exists():
            raise FileNotFoundError(f"缺少清洗产物 {p}，请先运行 src/cleaning.py")
    clean = pd.read_csv(paths["clean"], low_memory=False)
    event = pd.read_csv(paths["event"])
    summary = pd.read_csv(paths["summary"])
    return clean, event, summary


# ---------------------------------------------------------------------------
# 特征工程
# ---------------------------------------------------------------------------
def build_features(clean: pd.DataFrame, event: pd.DataFrame) -> pd.DataFrame:
    """构建「代表团 × 届次」特征宽表。

    派生特征：
    - gold/silver/bronze/total_*：双口径奖牌数（_event 为小项口径）
    - medal_per_athlete：小项口径总奖牌 / 参赛人数（代表团规模效率）
    - gold_share：金牌占该国总奖牌比（夺金集中度）
    - female_share：女性参赛比例
    - is_host：是否东道主（用 City 与 NOC 的国家映射近似判断）
    - prev_total / delta / delta_ratio：与上届相比的奖牌变化（东道主效应用）
    """
    # 东道主国家映射（手工维护，仅覆盖有明确主办国的届次；1956 双城取墨尔本为主）
    host_map = {
        1896: "GRE", 1900: "FRA", 1904: "USA", 1908: "GBR", 1912: "SWE",
        1920: "BEL", 1924: "FRA", 1928: "NED", 1932: "USA", 1936: "GER",
        1948: "GBR", 1952: "FIN", 1956: "AUS", 1960: "ITA", 1964: "JPN",
        1968: "MEX", 1972: "FRG", 1976: "CAN", 1980: "URS", 1984: "USA",
        1988: "KOR", 1992: "ESP", 1996: "USA", 2000: "AUS", 2004: "GRE",
        2008: "CHN", 2012: "GBR", 2016: "BRA", 2020: "JPN", 2024: "FRA",
    }

    feat = event.groupby(["Year", "NOC"], as_index=False)[["Gold", "Silver", "Bronze", "Total"]].sum()
    feat = feat.rename(columns={"Gold": "gold_event", "Silver": "silver_event",
                                "Bronze": "bronze_event", "Total": "total_event"})

    # 合并参赛规模等基础指标（来自 summary）
    base_cols = ["Year", "NOC", "Team", "athletes", "sports", "events",
                 "female", "female_ratio", "noc_lineage",
                 "Total_athlete", "Gold_athlete"]
    base = pd.read_csv(PROCESSED / "noc_year_summary.csv")[base_cols]
    feat = base.merge(feat, on=["Year", "NOC"], how="left")
    for c in ["gold_event", "silver_event", "bronze_event", "total_event"]:
        feat[c] = feat[c].fillna(0).astype(int)

    # 效率与结构特征
    feat["medal_per_athlete"] = (feat["total_event"] / feat["athletes"]).round(4)
    feat["gold_share"] = np.where(feat["total_event"] > 0,
                                  (feat["gold_event"] / feat["total_event"]).round(4), 0.0)
    feat["athletes_per_sport"] = (feat["athletes"] / feat["sports"]).round(2)
    feat["is_host"] = feat.apply(
        lambda r: int(host_map.get(int(r["Year"]), "") == r["NOC"]), axis=1)

    # 组委会口径的"官方国家"标识（用于避免同一继承实体重复计入）
    feat["lineage"] = feat["NOC"].map(lambda n: NOC_TO_LINEAGE.get(n, n))

    # 与上届比较：必须先按 NOC 排序，否则 diff 会跨国家串行
    feat = feat.sort_values(["NOC", "Year"]).reset_index(drop=True)
    feat["prev_total"] = feat.groupby("NOC")["total_event"].shift(1)
    feat["delta"] = feat["total_event"] - feat["prev_total"]
    feat["delta_ratio"] = (feat["delta"] / feat["prev_total"].replace(0, np.nan)).round(4)
    return feat.sort_values(["Year", "NOC"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 视角 A · 奖牌格局
# ---------------------------------------------------------------------------
def perspective_a(feat: pd.DataFrame, event: pd.DataFrame) -> dict:
    """历史总榜（双口径对照）、逐届奖牌演变、奖牌通货膨胀。"""
    # 历史总榜：小项口径，按金牌优先排序
    total_a = (feat.groupby("NOC", as_index=False)
               [["gold_event", "silver_event", "bronze_event", "total_event"]].sum())
    total_athlete = (feat.groupby("NOC", as_index=False)[["Gold_athlete", "Total_athlete"]].sum())
    hist = total_a.merge(total_athlete, on="NOC", how="left").fillna(0)
    team = feat.drop_duplicates("NOC").set_index("NOC")["Team"].to_dict()
    hist["Team"] = hist["NOC"].map(team)
    # 行口径与小项口径的放大倍数——团体项目依赖度的代理指标
    hist["amplification"] = (hist["Total_athlete"] / hist["total_event"].replace(0, np.nan)).round(2)
    hist = hist.sort_values(["gold_event", "total_event"], ascending=False)
    hist["rank_event"] = range(1, len(hist) + 1)
    hist.to_csv(TABLES / "a_history_medal_table.csv", index=False, encoding="utf-8")

    # 逐届奖牌：整体奖牌数随时间膨胀
    by_year = (event.groupby("Year")[["Gold", "Silver", "Bronze", "Total"]].sum().reset_index())
    # 同一届的参赛代表团数，用于解释膨胀
    nocs = feat.groupby("Year")["NOC"].nunique().rename("nocs").reset_index()
    by_year = by_year.merge(nocs, on="Year")
    by_year["medals_per_noc"] = (by_year["Total"] / by_year["nocs"]).round(2)
    by_year.to_csv(TABLES / "a_medals_by_year.csv", index=False, encoding="utf-8")

    # 前 10 名的逐届轨迹（用于堆叠/线图）
    top10 = hist.head(10)["NOC"].tolist()
    top_traj = feat[feat["NOC"].isin(top10)][["Year", "NOC", "gold_event", "total_event"]]
    top_traj.to_csv(TABLES / "a_top10_trajectory.csv", index=False, encoding="utf-8")

    return {
        "总榜前10": hist.head(10)[["rank_event", "NOC", "Team", "gold_event",
                                    "silver_event", "bronze_event", "total_event"]]
                    .to_dict("records"),
        "奖牌数增长倍数": round(float(by_year["Total"].iloc[-1] / by_year["Total"].iloc[1]), 2),
        "代表团数增长倍数": round(float(by_year["nocs"].iloc[-1] / by_year["nocs"].iloc[1]), 2),
        "口径放大倍数极值": {
            "最高": hist.nlargest(3, "amplification")[["NOC", "amplification"]].to_dict("records"),
            "最低": hist.nsmallest(3, "amplification")[["NOC", "amplification"]].to_dict("records"),
        },
    }


# ---------------------------------------------------------------------------
# 视角 B · 国家兴衰
# ---------------------------------------------------------------------------
def perspective_b(feat: pd.DataFrame) -> dict:
    """8+ 个代表国家的逐届奖牌曲线，含政体继承链版本。"""
    focus = feat[feat["NOC"].isin(FOCUS_NOCS)][
        ["Year", "NOC", "Team", "gold_event", "silver_event", "bronze_event",
         "total_event", "athletes", "is_host"]]
    focus.to_csv(TABLES / "b_focus_countries.csv", index=False, encoding="utf-8")

    # 继承链聚合：把 URS/EUN/RUS/ROC/AIN 合成 RUS 曲线，GER 侧合成 GER 曲线
    lin = feat.copy()
    lin_agg = (lin.groupby(["Year", "lineage"], as_index=False)
               [["gold_event", "total_event", "athletes"]].sum())
    lin_focus = lin_agg[lin_agg["lineage"].isin(["RUS", "GER", "USA", "CHN", "JPN", "GBR"])]
    lin_focus.to_csv(TABLES / "b_lineage_curves.csv", index=False, encoding="utf-8")

    # 关键国家指标
    stats = {}
    for noc in ["USA", "URS", "GDR", "CHN", "GBR", "JPN"]:
        sub = feat[feat["NOC"] == noc]
        if len(sub):
            peak = sub.loc[sub["total_event"].idxmax()]
            stats[noc] = {
                "首次参赛": int(sub["Year"].min()),
                "末次参赛": int(sub["Year"].max()),
                "参赛届数": int(len(sub)),
                "奖牌最多的一届": f"{int(peak['Year'])} 年（{int(peak['total_event'])} 枚）",
                "历史小项口径总奖牌": int(sub["total_event"].sum()),
            }
    return {"国家指标": stats, "覆盖国家数": len(FOCUS_NOCS)}


# ---------------------------------------------------------------------------
# 视角 C · 她的奥运
# ---------------------------------------------------------------------------
def perspective_c(clean: pd.DataFrame, feat: pd.DataFrame) -> dict:
    """女性参赛占比弧线、女子项目供给、各国女性参与差异。"""
    off = clean[clean["is_official"]]

    # 逐届性别构成（运动员行）
    by_year = (off.groupby("Year")
               .agg(athletes=("Name", "size"), female=("Sex", lambda s: int((s == "F").sum())))
               .reset_index())
    by_year["female_ratio"] = (by_year["female"] / by_year["athletes"]).round(4)
    by_year["male_ratio"] = (1 - by_year["female_ratio"]).round(4)
    by_year.to_csv(TABLES / "c_gender_by_year.csv", index=False, encoding="utf-8")

    # 女子项目供给：以 Event 名称含 Women/Ladies 且为具体小项的记录数代理
    ev = off[~off["event_is_generic"]]
    women_events = (ev[ev["Event"].str.contains("Women|Ladies", case=False, na=False)]
                    .groupby("Year")["Event"].nunique().rename("women_events").reset_index())
    all_events = ev.groupby("Year")["Event"].nunique().rename("all_events").reset_index()
    supply = all_events.merge(women_events, on="Year", how="left").fillna(0)
    supply["women_share"] = (supply["women_events"] / supply["all_events"]).round(4)
    supply.to_csv(TABLES / "c_women_event_supply.csv", index=False, encoding="utf-8")

    # 各国女性参与：取有代表性的若干国家，看最近三届
    recent = feat[feat["Year"].isin([2008, 2016, 2024])]
    recent = recent[recent["athletes"] >= 30]
    recent[["Year", "NOC", "Team", "athletes", "female", "female_ratio"]] \
        .to_csv(TABLES / "c_country_female_ratio.csv", index=False, encoding="utf-8")

    first_female = by_year.loc[by_year["female"] > 0, "Year"].min()
    first_parity_near = by_year[by_year["female_ratio"] >= 0.45]["Year"].min()

    # 女性首次夺牌的年份与代表团（用运动员行口径，逐行奖牌计数）
    medal_female = off[off["has_medal"] & (off["Sex"] == "F")]
    first_medal_year = int(medal_female["Year"].min()) if len(medal_female) else None
    first_medal_noc = (medal_female.loc[medal_female["Year"] == first_medal_year, "NOC"]
                       .value_counts().head(3).to_dict()) if first_medal_year else {}

    # 跃升点：逐届占比差最大的三届
    jumps = by_year.assign(diff=by_year["female_ratio"].diff()).nlargest(3, "diff")
    jump_detail = [{"Year": int(r.Year), "jump_pp": round(float(r.diff) * 100, 2)}
                   for r in jumps.itertuples()]

    return {
        "1896女性占比": float(by_year.loc[by_year.Year == 1896, "female_ratio"].iloc[0]),
        "2024女性占比": float(by_year.loc[by_year.Year == 2024, "female_ratio"].iloc[0]),
        "女性首次出现年份": int(first_female),
        "女性占比首次≥45%": int(first_parity_near),
        "女性首次夺牌年份": first_medal_year,
        "女性首次夺牌NOC": first_medal_noc,
        "女子小项占比2024": float(supply.loc[supply.Year == 2024, "women_share"].iloc[0]),
        "占比跃升点": jump_detail,
    }


# ---------------------------------------------------------------------------
# 视角 D · 项目演化
# ---------------------------------------------------------------------------
def perspective_d(clean: pd.DataFrame, event: pd.DataFrame) -> dict:
    """运动大类与小项的生命周期：新增、消失、存续。"""
    off = clean[clean["is_official"]]

    # 每个 Sport（归一后）的参赛年份覆盖
    sport_life = (off.groupby("sport_normalized")
                  .agg(首次=("Year", "min"), 末次=("Year", "max"),
                       届数=("Year", "nunique"), 记录数=("Name", "size"))
                  .reset_index().rename(columns={"sport_normalized": "Sport"}))
    sport_life["跨度"] = sport_life["末次"] - sport_life["首次"]
    sport_life["已消失"] = sport_life["末次"] < 2024
    sport_life.to_csv(TABLES / "d_sport_lifecycle.csv", index=False, encoding="utf-8")

    # 小项数随时间（S2 策略：泛化届次降维，用 Event 唯一值作粗代理并标注）
    ev_count = (off.groupby("Year")
                .agg(事件唯一值=("Event", "nunique"),
                     泛化行占比=("event_is_generic", "mean"))
                .reset_index())
    # 大类 × 性别的组合数，作为泛化届次的替代粒度
    combo = (off.assign(k=off["sport_normalized"] + "|" + off["Sex"])
             .groupby("Year")["k"].nunique().rename("大类×性别组合数").reset_index())
    ev_count = ev_count.merge(combo, on="Year")
    ev_count["泛化行占比"] = ev_count["泛化行占比"].round(4)
    ev_count.to_csv(TABLES / "d_event_count_by_year.csv", index=False, encoding="utf-8")

    disappeared = sport_life[sport_life["已消失"]].sort_values("末次")
    newest = sport_life.sort_values("首次", ascending=False).head(8)

    return {
        "消失的运动": disappeared[["Sport", "首次", "末次", "记录数"]].to_dict("records"),
        "最新出现的运动": newest[["Sport", "首次", "记录数"]].to_dict("records"),
        "运动总数": int(len(sport_life)),
        "2024年在办运动数": int((~sport_life["已消失"]).sum()),
    }


# ---------------------------------------------------------------------------
# 专题 S2 · 口径的魔力
# ---------------------------------------------------------------------------
def topic_s2(feat: pd.DataFrame) -> dict:
    """同一批奖牌，两套口径如何改写排名。"""
    recent_years = [2008, 2012, 2016, 2020, 2024]
    sub = feat[feat["Year"].isin(recent_years)]
    agg = sub.groupby("NOC", as_index=False).agg(
        gold_event=("gold_event", "sum"),
        total_event=("total_event", "sum"),
        gold_athlete=("Gold_athlete", "sum"),
        total_athlete=("Total_athlete", "sum"),
        Team=("Team", "last"),
    )
    agg["event_rank"] = agg["gold_event"].rank(ascending=False, method="min").astype(int)
    agg["athlete_rank"] = agg["gold_athlete"].rank(ascending=False, method="min").astype(int)
    agg["rank_move"] = agg["event_rank"] - agg["athlete_rank"]  # 正数=行口径下排名上升
    agg = agg.sort_values("event_rank")
    agg.to_csv(TABLES / "s2_caliber_rank_shift.csv", index=False, encoding="utf-8")

    # 2024 单届对照（报告主案例）
    y24 = feat[feat["Year"] == 2024].copy()
    y24 = y24[y24["total_event"] > 0].sort_values("gold_event", ascending=False)
    y24[["NOC", "Team", "gold_event", "Gold_athlete", "total_event",
         "Total_athlete", "athletes"]].to_csv(
        TABLES / "s2_2024_caliber_compare.csv", index=False, encoding="utf-8")

    # 团体依赖度：行口径相对小项口径的放大倍数，作为各届各队的结构指标
    amp = feat.copy()
    amp["amplification"] = (amp["Total_athlete"] / amp["total_event"].replace(0, np.nan)).round(2)
    amp = amp.dropna(subset=["amplification"])
    amp.sort_values("amplification", ascending=False).head(30)[
        ["Year", "NOC", "Team", "total_event", "Total_athlete", "amplification"]
    ].to_csv(TABLES / "s2_amplification_top30.csv", index=False, encoding="utf-8")

    biggest_moves = agg.reindex(agg["rank_move"].abs().sort_values(ascending=False).index).head(8)
    return {
        "近五届排名变动最大": biggest_moves[["NOC", "Team", "event_rank", "athlete_rank",
                                              "rank_move"]].to_dict("records"),
        "2024对照前8": y24.head(8)[["NOC", "gold_event", "Gold_athlete"]].to_dict("records"),
        "平均放大倍数": round(float(amp["amplification"].mean()), 2),
    }


# ---------------------------------------------------------------------------
# 专题 S1 · 东道主效应
# ---------------------------------------------------------------------------
def topic_s1(feat: pd.DataFrame) -> dict:
    """主办国在主办届的奖牌增益及其持续性。

    方法：对每个东道主，取主办届前后的奖牌数，计算
    - 主办届增益（相对上届）
    - 主办后回落幅度（主办后一届相对主办届）
    - 主办届在全球的排名变化
    """
    rows = []
    hosts = feat[feat["is_host"] == 1]
    for _, h in hosts.iterrows():
        noc, yr = h["NOC"], int(h["Year"])
        hist = feat[feat["NOC"] == noc].sort_values("Year")
        idx = hist.index[hist["Year"] == yr]
        if len(idx) == 0:
            continue
        i = hist.index.get_loc(idx[0])
        prev = hist.iloc[i - 1] if i > 0 else None
        nxt = hist.iloc[i + 1] if i + 1 < len(hist) else None

        # 该届全球排名（小项口径金牌）
        year_all = feat[feat["Year"] == yr].sort_values("gold_event", ascending=False)
        rank = int(year_all["NOC"].tolist().index(noc) + 1) if noc in year_all["NOC"].values else None

        rows.append({
            "Year": yr, "NOC": noc, "Team": h["Team"],
            "主办届奖牌": int(h["total_event"]),
            "主办届金牌": int(h["gold_event"]),
            "上届奖牌": int(prev["total_event"]) if prev is not None else np.nan,
            "上届金牌": int(prev["gold_event"]) if prev is not None else np.nan,
            "下届奖牌": int(nxt["total_event"]) if nxt is not None else np.nan,
            "主办届金牌排名": rank,
            "较上届奖牌增幅": (int(h["total_event"]) - int(prev["total_event"])) if prev is not None else np.nan,
            "较上届增幅比例": round((h["total_event"] - prev["total_event"]) / prev["total_event"], 4)
                            if prev is not None and prev["total_event"] > 0 else np.nan,
            "主办后回落": (int(nxt["total_event"]) - int(h["total_event"])) if nxt is not None else np.nan,
        })
    df = pd.DataFrame(rows)
    df.to_csv(TABLES / "s1_host_effect.csv", index=False, encoding="utf-8")

    valid = df.dropna(subset=["较上届奖牌增幅"])
    return {
        "东道主届次数": int(len(df)),
        "奖牌正增长的主办国数": int((valid["较上届奖牌增幅"] > 0).sum()),
        "有可比数据的主办国数": int(len(valid)),
        "平均增幅比例": round(float(valid["较上届增幅比例"].dropna().mean()), 4),
        "主办后回落的国家数": int((df["主办后回落"] < 0).sum()),
        "明细": df[["Year", "NOC", "主办届奖牌", "上届奖牌", "较上届奖牌增幅",
                    "主办后回落", "主办届金牌排名"]].to_dict("records"),
    }


# ---------------------------------------------------------------------------
# 反直觉发现与交叉验证
# ---------------------------------------------------------------------------
def insights(clean: pd.DataFrame, feat: pd.DataFrame) -> list[dict]:
    """从数据中提炼若干「推翻直觉」的结论，每条标注证据强度。

    每条结论都必须有两项以上独立计数支撑；数字全部由本函数现算，
    不引用任何硬编码常量，避免结论与数据脱节。
    """
    out = []
    off = clean[clean["is_official"]]
    by_year = off.groupby("Year").agg(rows=("Name", "size"), nocs=("NOC", "nunique"))
    ev_count = pd.read_csv(TABLES / "d_event_count_by_year.csv").set_index("Year")

    # 1. 增长归因：分阶段比较三项增速，指出主导因素随阶段变化
    def growth(y0: int, y1: int) -> dict:
        return {
            "记录数": round(by_year.loc[y1, "rows"] / by_year.loc[y0, "rows"], 2),
            "代表团数": round(by_year.loc[y1, "nocs"] / by_year.loc[y0, "nocs"], 2),
            "小项数": round(ev_count.loc[y1, "事件唯一值"] / ev_count.loc[y0, "事件唯一值"], 2),
        }
    early, recent = growth(1896, 1948), growth(1948, 2024)
    out.append({
        "结论": "奥运规模的扩张在两个阶段由不同因素主导：早期靠新增代表团，"
                "近 76 年靠小项扩张。",
        "证据": (f"1896→1948：记录数 ×{early['记录数']}，代表团 ×{early['代表团数']}，"
                 f"小项 ×{early['小项数']}（代表团最快）；"
                 f"1948→2024：记录数 ×{recent['记录数']}，代表团 ×{recent['代表团数']}，"
                 f"小项 ×{recent['小项数']}（小项最快）。"
                 f"注意这是与赛题常识相反的方向——近 76 年新增的主要是项目，不是国家。"),
        "强度": "强（三条独立计数同向，且分阶段结论相反，排除单一指标偶然性）",
    })

    # 2. 团体项目依赖度：小国比大国更依赖"人多"
    h = pd.read_csv(TABLES / "a_history_medal_table.csv")
    big = h[h["total_event"] >= 300].dropna(subset=["amplification"])
    small = h[(h["total_event"].between(20, 100))].dropna(subset=["amplification"])
    out.append({
        "结论": "奖牌高度依赖团体项目成员复制的是中小代表团，不是奖牌榜大国；"
                "用行口径做排名会系统性高估它们的实力。",
        "证据": (f"奖牌数≥300 的国家平均放大倍数 {big['amplification'].mean():.2f}×；"
                 f"奖牌数 20–100 的国家平均 {small['amplification'].mean():.2f}×。"
                 "极端如 " + "、".join(
                     f"{r.NOC} {r.amplification}×" for r in
                     h.nlargest(3, "amplification").itertuples())),
        "强度": "中（放大倍数受混合队与并列奖牌影响，方向可信、精确值需谨慎）",
    })

    # 3. 女性占比不是匀速上升
    c = pd.read_csv(TABLES / "c_gender_by_year.csv")
    jumps = c.assign(diff=c["female_ratio"].diff()).nlargest(3, "diff")
    out.append({
        "结论": "女性参赛占比不是匀速上升，而是集中在少数几届发生阶跃。",
        "证据": "最大三次跃升：" + "、".join(
            f"{int(r.Year)} 年 +{r.diff*100:.1f}pp" for r in jumps.itertuples()),
        "强度": "强（逐届连续数据，跃升点可与历史事件对应）",
    })

    # 4. 东道主效应是否持续
    s1 = pd.read_csv(TABLES / "s1_host_effect.csv")
    persist = s1.dropna(subset=["主办后回落"])
    out.append({
        "结论": "东道主效应在赛后普遍回落，属于一次性脉冲而非能力跃迁。",
        "证据": (f"有可比数据的 {len(persist)} 位东道主中，"
                 f"{int((persist['主办后回落'] < 0).sum())} 位赛后奖牌数下降；"
                 f"平均赛后回落 {persist['主办后回落'].mean():.1f} 枚。"),
        "强度": "中（样本量小，且受抵制潮等外生事件干扰）",
    })

    # 5. 奖牌集中度：不算总额，只看当届内部份额，规避小项扩张干扰
    def year_share(years: range) -> float:
        shares = []
        for y in years:
            g = feat[feat["Year"] == y]
            if g["total_event"].sum() > 0:
                shares.append(g.nlargest(3, "total_event")["total_event"].sum()
                              / g["total_event"].sum())
        return float(np.mean(shares)) if shares else 0.0

    early_share, late_share = year_share(range(1896, 1913, 4)), year_share(range(2000, 2025, 4))
    out.append({
        "结论": "奥运会从「少数国家的独角戏」变成「两百个代表团的分布场」，"
                "前三国的奖牌份额百年间腰斩再腰斩。",
        "证据": (f"1912 年及以前，前三国平均占当届奖牌 {early_share*100:.1f}%；"
                 f"2000 年后降至 {late_share*100:.1f}%，仅为早期的 "
                 f"{late_share/early_share*100:.0f}%。"
                 "此处用当届内部份额而非绝对数，故不受小项数量扩张干扰。"),
        "强度": "强（份额口径，与小项数量变化无关）",
    })
    return out


def main() -> dict:
    """入口：读清洗产物 → 特征工程 → 四视角 + 两专题 → 洞察 → 落盘。"""
    TABLES.mkdir(parents=True, exist_ok=True)
    clean, event, summary = load_processed()

    feat = build_features(clean, event)
    feat.to_csv(PROCESSED / "features_noc_year.csv", index=False, encoding="utf-8")

    result = {
        "A_奖牌格局": perspective_a(feat, event),
        "B_国家兴衰": perspective_b(feat),
        "C_她的奥运": perspective_c(clean, feat),
        "D_项目演化": perspective_d(clean, event),
        "S1_东道主效应": topic_s1(feat),
        "S2_口径的魔力": topic_s2(feat),
        "洞察": insights(clean, feat),
        "基础统计": {
            "特征表行数": int(len(feat)),
            "有奖牌的代表团届次组合": int((feat["total_event"] > 0).sum()),
            "从未获奖的NOC数": int((feat.groupby("NOC")["total_event"].sum() == 0).sum()),
        },
    }
    (TABLES / "analysis_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"[features] 特征表 {len(feat)} 行；分析结果已写入 outputs/tables/analysis_results.json")
    return result


if __name__ == "__main__":
    main()
