"""
Task3 专题 S4「小代表团的大突破」—— 数据准备与清洗校验
==========================================================
职责
----
1. 从 Task1 已清洗产物中抽取 S4 分析所需的子集；
2. 定义「参赛规模分档」，作为「小代表团」的可操作定义；
3. 做清洗校验：与 Task1 的关键数字交叉对账、口径守恒检查。

调用关系
--------
- 上游：`docs/Task1/{olympics_clean, medal_event_level, noc_year_summary}.csv`（由 backend/src/cleaning.py 生成）
- 下游：`backend/src/task3_s4_analysis.py` 读取本脚本产出的 `outputs/task3_s4/s4_base.csv`
- 并发：单进程串行，无共享可变状态。

口径约定（与 Task1 一致，本专题不得偏离）
------------------------------------------
- 主分析口径：**小项口径**（去重键 Year, Event, Medal, NOC），奖牌总数 17,901
- 对照口径：运动员行口径，奖牌总数 38,360
- 默认排除 1906 届间奥运会（is_official=False）
- 「突破」的判断一律基于跨届连续性，不以单届峰值定性
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
T1 = ROOT / "docs" / "Task1"
OUT = ROOT / "outputs" / "task3_s4"
OUT.mkdir(parents=True, exist_ok=True)

# 参赛规模分档阈值（按参赛人数）。依据：见 docs/Task3/任务清单.md 与实际分布分位。
# 中位数 22、上四分位 82，因此以 10 / 50 / 150 切分，使各档样本量不至于悬殊。
SIZE_BINS = [0, 10, 50, 150, 10**9]
SIZE_LABELS = ["微型(≤10)", "小型(11-50)", "中型(51-150)", "大型(>150)"]

# 「近代」主样本起点：1980 年莫斯科。理由：此前参赛国少、项目少，
# 夺牌率被结构性放大，不适合做小国策略比较。该断点与 Task2 四视角的
# 「早期/近代」划分保持一致，避免同一份数据在不同文档里出现两套分期。
MODERN_FROM = 1980


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """读取 Task1 三张表，缺文件时给出明确补救提示。"""
    need = {
        "olympics_clean.csv": T1 / "olympics_clean.csv",
        "medal_event_level.csv": T1 / "medal_event_level.csv",
        "noc_year_summary.csv": T1 / "noc_year_summary.csv",
    }
    for name, p in need.items():
        if not p.exists():
            raise FileNotFoundError(
                f"缺少 Task1 产物 {p}，请先运行 backend/src/cleaning.py 生成清洗结果")
    clean = pd.read_csv(need["olympics_clean.csv"], low_memory=False)
    event = pd.read_csv(need["medal_event_level.csv"])
    summary = pd.read_csv(need["noc_year_summary.csv"])
    return clean, event, summary


def build_base(summary: pd.DataFrame) -> pd.DataFrame:
    """构建「代表团 × 届次」基础表，附参赛规模分档与小代表团标记。

    输入：noc_year_summary（Task1 产物，含双口径奖牌与参赛人数）
    输出：s4_base，在 summary 基础上新增 size_class / is_small / era 三列
    """
    base = summary.copy()
    base["size_class"] = pd.cut(base["athletes"], bins=SIZE_BINS,
                                labels=SIZE_LABELS, right=True)
    # 「小代表团」定义：参赛人数 ≤ 50（微型 + 小型）。
    # 选 50 作主阈值而非 10，是为保证每档有足够样本支持分组统计；
    # 报告中另做 10 / 150 阈值敏感性检验。
    base["is_small"] = (base["athletes"] <= 50).astype(int)
    base["era"] = np.where(base["Year"] >= MODERN_FROM, "近代(1980+)", "早期(<1980)")
    base["has_medal_event"] = (base["Total_event"] > 0).astype(int)
    base["has_medal_athlete"] = (base["Total_athlete"] > 0).astype(int)
    return base.sort_values(["Year", "NOC"]).reset_index(drop=True)


def build_concentration(event: pd.DataFrame) -> pd.DataFrame:
    """计算每个「代表团 × 届次」的夺牌集中度。

    集中度指标（仅在当届有奖牌时计算）：
    - top1_share：最大运动大类占该国当届小项口径奖牌的比重
    - n_sports_medal：夺牌的运动大类数（项目广度）
    - hhi：各运动大类份额平方和（1 为完全集中，1/n 为完全分散）

    输入：medal_event_level（小项口径奖牌表）
    输出：每行一个代表团届次的集中度指标
    """
    g = event.groupby(["Year", "NOC", "Sport"], as_index=False)["Total"].sum()
    tot = g.groupby(["Year", "NOC"])["Total"].transform("sum")
    g["share"] = g["Total"] / tot
    agg = g.groupby(["Year", "NOC"]).agg(
        n_sports_medal=("Sport", "nunique"),
        top1_share=("share", "max"),
        hhi=("share", lambda s: float((s ** 2).sum())),
        top_sport=("Total", lambda s: g.loc[s.idxmax(), "Sport"]),
    ).reset_index()
    return agg


def build_first_medal(base: pd.DataFrame) -> pd.DataFrame:
    """标记每个代表团的「首枚奖牌届次」与「首金届次」，用于持续性分析。

    注意：这里的「首」指**本数据集内**的最早届次，不代表历史真实首牌
    （早期届次可能因数据缺失而未记录），报告中已声明此限制。
    """
    rows = []
    for noc, g in base.groupby("NOC"):
        g = g.sort_values("Year")
        m = g[g["has_medal_event"] == 1]
        gold = g[g["Gold_event"] > 0]
        rows.append({
            "NOC": noc,
            "Team": g["Team"].iloc[-1],
            "n_appear": int(len(g)),
            "first_year": int(g["Year"].min()),
            "last_year": int(g["Year"].max()),
            "first_medal_year": int(m["Year"].min()) if len(m) else np.nan,
            "first_gold_year": int(gold["Year"].min()) if len(gold) else np.nan,
            "n_medal_editions": int(len(m)),
            "total_event": int(g["Total_event"].sum()),
            "total_athlete": int(g["Total_athlete"].sum()),
            "max_athletes": int(g["athletes"].max()),
            "median_athletes": float(g["athletes"].median()),
        })
    out = pd.DataFrame(rows)
    out["medal_edition_rate"] = (out["n_medal_editions"] / out["n_appear"]).round(4)
    return out.sort_values("total_event", ascending=False).reset_index(drop=True)


def verify(clean: pd.DataFrame, event: pd.DataFrame,
           summary: pd.DataFrame, base: pd.DataFrame) -> dict:
    """清洗校验：完整性 + 保真性 + 与 Task1 的数字对账。

    返回可直接打印为 Markdown 的校验结果字典。
    """
    checks = []

    def add(name: str, expect, actual, ok: bool, note: str = "") -> None:
        checks.append({"检查项": name, "期望": expect, "实测": actual,
                       "结果": "通过" if ok else "不通过", "说明": note})

    # 1 行数与 Task1 一致
    add("主表行数", 252565, len(clean), len(clean) == 252565, "与原始 CSV 一致")
    # 2 小项口径奖牌总数
    et = int(event[["Gold", "Silver", "Bronze"]].sum().sum())
    add("小项口径奖牌总数", 17901, et, et == 17901, "与 Task1 口径说明书一致")
    # 3 运动员行口径奖牌总数
    at = int(summary["Total_athlete"].sum())
    add("运动员行口径奖牌总数", 38360, at, at == 38360, "1906 已排除")
    # 4 1906 已排除
    y1906 = int((event["Year"] == 1906).sum())
    add("小项奖牌表中 1906 行数", 0, y1906, y1906 == 0, "默认口径排除 1906")
    # 5 分档无遗漏
    n_null = int(base["size_class"].isna().sum())
    add("规模分档无空值", 0, n_null, n_null == 0, "bins 覆盖 0 至极大值")
    # 6 分档样本量加总守恒
    s_sum = int(base["size_class"].value_counts().sum())
    add("分档样本量守恒", len(base), s_sum, s_sum == len(base), "")
    # 7 小项口径 ≤ 行口径（逐行）
    bad = int((summary["Total_event"] > summary["Total_athlete"]).sum())
    add("逐行 小项口径 ≤ 行口径", 0, bad, bad == 0, "小项口径必为行口径的子集去重")
    # 8 参赛国数
    n_noc = int(summary["NOC"].nunique())
    add("代表团数（NOC）", 233, n_noc, n_noc == 233, "Task2 五视角文档给出 233")
    # 9 届次数
    n_year = int(summary["Year"].nunique())
    add("官方届次数", 30, n_year, n_year == 30, "1896–2024 共 30 届，不含 1906")
    # 10 有奖牌的代表团届次比例应在合理区间
    rate = float(base["has_medal_event"].mean())
    add("有奖牌的代表团届次占比", "0.2 ~ 0.5", round(rate, 4),
        0.2 < rate < 0.5, "小项口径")

    return {"checks": checks,
            "all_pass": all(c["结果"] == "通过" for c in checks)}


def main() -> dict:
    clean, event, summary = load_inputs()
    base = build_base(summary)
    conc = build_concentration(event)
    first = build_first_medal(base)

    # 合并集中度到基础表（无奖牌者留空）
    base = base.merge(conc, on=["Year", "NOC"], how="left")

    base.to_csv(OUT / "s4_base.csv", index=False, encoding="utf-8-sig")
    first.to_csv(OUT / "s4_noc_first_medal.csv", index=False, encoding="utf-8-sig")

    ver = verify(clean, event, summary, base)
    (OUT / "s4_verification.json").write_text(
        json.dumps(ver, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[s4_clean] 基础表 {base.shape[0]} 行 × {base.shape[1]} 列")
    print(f"[s4_clean] 代表团档案 {first.shape[0]} 行")
    print(f"[s4_clean] 校验 {'全部通过' if ver['all_pass'] else '存在不通过项'}")
    for c in ver["checks"]:
        print(f"  [{c['结果']}] {c['检查项']}: 期望 {c['期望']} / 实测 {c['实测']}")
    return ver


if __name__ == "__main__":
    main()
