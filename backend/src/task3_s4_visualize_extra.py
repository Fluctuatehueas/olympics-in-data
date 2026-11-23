"""图 10 · 小团型国家的历史奖牌榜（横向条形）。"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import task3_s4_visualize as V  # 复用绘图原语


def f10():
    """按峰值参赛人数 ≤50 定义的小团型国家，历史小项口径奖牌前 15。"""
    base = pd.read_csv(V.T3 / "s4_base.csv")
    peak = base.groupby("NOC")["athletes"].max()
    small = peak[peak <= 50].index
    tot = (base[base["NOC"].isin(small)]
           .groupby(["NOC", "Team"])
           .agg(Total=("Total_event", "sum"), Gold=("Gold_event", "sum"),
                peak=("athletes", "max"), eds=("Year", "nunique"))
           .reset_index())
    tot = tot[tot["Total"] > 0].sort_values("Total", ascending=False).head(15)

    h = 110 + len(tot) * 28
    p = V.op(V.W, h)
    V.ti(p, "图 10 · 小团型国家的历史奖牌榜（前 15）",
         "小团型 = 该国历史峰值参赛人数 ≤ 50；小项口径；括号内为峰值人数与参赛届数")
    x0, x1 = 130, V.W - 120
    xmax = float(tot["Total"].max()) * 1.12
    y = 76
    for r in tot.itertuples():
        w = V.sc(float(r.Total), 0, xmax, 0, x1 - x0)
        p.append(f'<text x="24" y="{y + 15}" font-size="12" '
                 f'fill="{V.C["ink"]}">{r.Team}（{r.NOC}）</text>')
        p.append(f'<rect x="{x0}" y="{y}" width="{w:.1f}" height="20" '
                 f'fill="{V.C["accent"]}" rx="2"/>')
        # 金牌部分用金色覆盖前段
        wg = V.sc(float(r.Gold), 0, xmax, 0, x1 - x0)
        p.append(f'<rect x="{x0}" y="{y}" width="{wg:.1f}" height="20" '
                 f'fill="{V.C["gold"]}" rx="2"/>')
        p.append(f'<text x="{x0 + w + 8:.1f}" y="{y + 15}" font-size="11" '
                 f'fill="{V.C["muted"]}">{int(r.Total)}（金 {int(r.Gold)}）'
                 f' · 峰值 {int(r.peak)} 人 · {int(r.eds)} 届</text>')
        y += 28
    V.lg(p, [("金牌", V.C["gold"]), ("银+铜", V.C["accent"])])
    V.nt(p, "埃塞俄比亚以 48 人峰值拿下 61 枚奖牌，是小团型国家里的绝对第一；"
            "63 个小团型国家的奖牌合计只占总量 1.97%。", h)
    return V.save(p, "fig10_small_noc_board.svg")


if __name__ == "__main__":
    path = f10()
    print(f"[s4_fig] {path.name} ({path.stat().st_size} bytes)")
