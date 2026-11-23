"""
S4 报告第七节补充分析：小团奖牌份额趋势的阈值敏感性
====================================================
职责
----
报告第七节（结构变化）只用了 ≤50 一个主阈值，而第八节已证明人效结论
会随阈值翻转。本节补测：把「小团」阈值换成 ≤10/≤25/≤50/≤100/≤150，
小团奖牌份额的上升趋势是否依然成立。

调用关系
--------
- 上游：`outputs/task3_s4/s4_base.csv`
- 下游：写入 `outputs/task3_s4/tables/f_share_trend_by_threshold.csv`，
  并更新 `outputs/task3_s4/s4_results.json` 中的 `F_trend.share_trend_by_threshold`

口径：小项口径（Total_event），1980 年起。
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
T3 = ROOT / "outputs" / "task3_s4"

THRESHOLDS = [10, 25, 50, 100, 150]
MODERN_FROM = 1980


def share_trend(base: pd.DataFrame, th: int) -> dict:
    """计算给定阈值下，小团奖牌份额随届次的线性趋势。

    返回斜率（pp/年）、R²、p 值、首末届份额与 Spearman 系数。
    """
    rows = []
    for year, g in base[base["Year"] >= MODERN_FROM].groupby("Year"):
        small = g[g["athletes"] <= th]
        total = float(g["Total_event"].sum())
        rows.append({
            "Year": int(year),
            "small_noc": int(len(small)),
            "small_medal": float(small["Total_event"].sum()),
            "total_medal": total,
            "small_medal_share": (float(small["Total_event"].sum()) / total) if total else 0.0,
        })
    df = pd.DataFrame(rows).sort_values("Year").reset_index(drop=True)
    lr = stats.linregress(df["Year"], df["small_medal_share"])
    sp = stats.spearmanr(df["Year"], df["small_medal_share"])
    first, last = df.iloc[0], df.iloc[-1]
    return {
        "threshold": th,
        "n_editions": int(len(df)),
        "share_first_year": int(first["Year"]),
        "share_first": round(float(first["small_medal_share"]), 4),
        "share_last_year": int(last["Year"]),
        "share_last": round(float(last["small_medal_share"]), 4),
        "share_change": round(float(last["small_medal_share"]) - float(first["small_medal_share"]), 4),
        "ols_slope_pp_per_year": round(float(lr.slope) * 100, 4),
        "ols_r2": round(float(lr.rvalue ** 2), 4),
        "ols_p": float(lr.pvalue),
        "spearman_rho": round(float(sp.statistic), 4),
        "spearman_p": float(sp.pvalue),
        "direction": "上升" if lr.slope > 0 else "下降",
        "significant_05": bool(lr.pvalue < 0.05),
        "_series": df,
    }


def main() -> dict:
    """跑全部阈值，输出 CSV 与 JSON 摘要。"""
    base = pd.read_csv(T3 / "s4_base.csv")
    results = [share_trend(base, th) for th in THRESHOLDS]

    # 明细表：每阈值每届一行，便于画图与复核
    rows = []
    for r in results:
        for t in r["_series"].itertuples():
            rows.append({
                "threshold": r["threshold"],
                "Year": t.Year,
                "small_noc": t.small_noc,
                "small_medal": t.small_medal,
                "total_medal": t.total_medal,
                "small_medal_share": round(float(t.small_medal_share), 4),
            })
    detail = pd.DataFrame(rows)
    detail.to_csv(T3 / "tables" / "f_share_trend_by_threshold.csv",
                  index=False, encoding="utf-8-sig")

    # 摘要（去掉内部 _series）
    summary = [{k: v for k, v in r.items() if k != "_series"} for r in results]
    verdict = {
        "n_thresholds": len(results),
        "all_rising": all(r["direction"] == "上升" for r in results),
        "all_significant_05": all(r["significant_05"] for r in results),
        "min_slope_pp": min(r["ols_slope_pp_per_year"] for r in results),
        "max_slope_pp": max(r["ols_slope_pp_per_year"] for r in results),
        "note": "若所有阈值下方向一致且显著，则第七节结论通过稳健性检验",
    }

    out = T3 / "s4_results.json"
    payload = json.loads(out.read_text(encoding="utf-8"))
    payload.setdefault("F_trend", {})["share_trend_by_threshold"] = summary
    payload["F_trend"]["share_trend_verdict"] = verdict
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("[share_trend] 阈值敏感性结果：")
    for r in summary:
        print(f"  ≤{r['threshold']:>3}人：份额 {r['share_first']:.4f} → {r['share_last']:.4f}"
              f"（{r['direction']}，斜率 {r['ols_slope_pp_per_year']:+.4f} pp/年，"
              f"R²={r['ols_r2']:.3f}，p={r['ols_p']:.3g}，ρ={r['spearman_rho']:+.3f}）")
    print(f"[share_trend] 判定：{'全部上升' if verdict['all_rising'] else '存在下降'}；"
          f"{'全部显著' if verdict['all_significant_05'] else '存在不显著'}")
    return verdict


if __name__ == "__main__":
    main()
