"""
Task3 专题 S4「小代表团的大突破」—— 静态图
==========================================
职责
----
读取 `outputs/task3_s4/tables/*.csv`，生成 9 张专题图（手写 SVG，零字体依赖）。
风格与 Task1/Task2 的 fig01–fig10 一致。

调用关系
--------
- 上游：`backend/src/task3_s4_analysis.py` 的产物
- 下游：报告 `docs/Task3/S4_小代表团的大突破.md` 引用图号
- 串行执行，无共享可变状态。

口径约定
--------
所有奖牌数为**小项口径**（17,901）。行口径对照处图注显式标注。
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
T3 = ROOT / "outputs" / "task3_s4"
TAB = T3 / "tables"
FIG = T3 / "figures"
FIG.mkdir(parents=True, exist_ok=True)

W, H = 960, 480
PL, PR, PT, PB = 64, 140, 48, 64

C = {
    "ink": "#1F2933", "muted": "#6B7280", "grid": "#E5E7EB",
    "accent": "#1F6FEB", "warn": "#D1495B", "gold": "#C9A227",
    "green": "#2E9E6B", "purple": "#7B4FBF", "orange": "#E07B39",
    "teal": "#0E7C86", "pink": "#B4478C", "brown": "#8C6D31",
}


def sc(v, lo, hi, p0, p1):
    """线性映射 v∈[lo,hi] → 像素 [p0,p1]。"""
    if hi == lo:
        return p0
    return p0 + (v - lo) / (hi - lo) * (p1 - p0)


def fx(v, nd=2):
    """格式化刻度，去掉末尾 0。"""
    return f"{v:.{nd}f}".rstrip("0").rstrip(".")


def op(w=W, h=H):
    """SVG 画布头。"""
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" '
        f'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
        f'<rect width="{w}" height="{h}" fill="#FFFFFF"/>',
    ]


def ti(p, title, sub=""):
    """标题 + 副标题。"""
    p.append(f'<text x="24" y="28" font-size="17" font-weight="600" '
             f'fill="{C["ink"]}">{title}</text>')
    if sub:
        p.append(f'<text x="24" y="47" font-size="12" '
                 f'fill="{C["muted"]}">{sub}</text>')


def nt(p, text, h=H):
    """底部注解。"""
    p.append(f'<text x="24" y="{h - 20}" font-size="10.5" '
             f'fill="{C["muted"]}">{text}</text>')


def ya(p, lo, hi, ticks, label="", x0=PL):
    """Y 轴网格 + 刻度 + 轴标题。"""
    x1 = W - PR
    for i in range(ticks + 1):
        v = lo + (hi - lo) * i / ticks
        y = sc(v, lo, hi, H - PB, PT + 8)
        p.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" '
                 f'stroke="{C["grid"]}" stroke-width="1"/>')
        p.append(f'<text x="{x0 - 8}" y="{y + 4:.1f}" font-size="11" '
                 f'text-anchor="end" fill="{C["muted"]}">{fx(v)}</text>')
    if label:
        p.append(f'<text x="24" y="{PT}" font-size="11" '
                 f'fill="{C["muted"]}">{label}</text>')


def lg(p, items, x=None, y=None):
    """右侧图例，items = [(标签, 颜色)]。"""
    x = (W - PR + 12) if x is None else x
    y = (PT + 16) if y is None else y
    for i, (label, color) in enumerate(items):
        p.append(f'<rect x="{x}" y="{y + i * 20}" width="10" height="10" '
                 f'rx="2" fill="{color}"/>')
        p.append(f'<text x="{x + 16}" y="{y + i * 20 + 9}" font-size="11.5" '
                 f'fill="{C["ink"]}">{label}</text>')


def save(p, name):
    """落盘。"""
    p.append("</svg>")
    path = FIG / name
    path.write_text("\n".join(p), encoding="utf-8")
    return path


def f01():
    """图 1 · 参赛规模与夺牌率（分组条形）。"""
    df = pd.read_csv(TAB / "a_size_distribution.csv")
    order = ["微型(≤10)", "小型(11-50)", "中型(51-150)", "大型(>150)"]
    eras = ["早期(<1980)", "近代(1980+)"]
    p = op()
    ti(p, "图 1 · 参赛规模与夺牌率：多小的团还能站上领奖台",
       "夺牌率 = 当届有小项口径奖牌的代表团 / 该档全部代表团届次；柱内为样本量")
    ya(p, 0, 1.0, 5, "夺牌率")
    x0, x1 = PL + 20, W - PR - 10
    band = (x1 - x0) / 4
    for i, cls in enumerate(order):
        cx = x0 + band * i
        for j, era in enumerate(eras):
            row = df[(df["size_class"] == cls) & (df["era"] == era)]
            v = float(row["medal_rate"].iloc[0]) if len(row) else 0.0
            nn = int(row["n_noc_editions"].iloc[0]) if len(row) else 0
            bw = band * 0.3
            x = cx + (j - 0.5) * bw * 1.15 - bw / 2
            hp = v * (H - PB - PT - 16)
            col = C["muted"] if era.startswith("早期") else C["accent"]
            p.append(f'<rect x="{x:.1f}" y="{H - PB - hp:.1f}" width="{bw:.1f}" '
                     f'height="{hp:.1f}" fill="{col}" rx="2"/>')
            p.append(f'<text x="{x + bw / 2:.1f}" y="{H - PB - hp - 5:.1f}" '
                     f'font-size="10.5" text-anchor="middle" '
                     f'fill="{C["ink"]}">{v * 100:.1f}%</text>')
            if hp > 18:
                p.append(f'<text x="{x + bw / 2:.1f}" y="{H - PB - hp + 14:.1f}" '
                         f'font-size="9.5" text-anchor="middle" '
                         f'fill="#FFFFFF">n={nn}</text>')
        p.append(f'<text x="{cx:.1f}" y="{H - PB + 20}" font-size="11.5" '
                 f'text-anchor="middle" fill="{C["ink"]}">{cls}</text>')
    lg(p, [("早期 1896–1976", C["muted"]), ("近代 1980–2024", C["accent"])])
    nt(p, "规模越小夺牌越难是硬约束：微型团近代夺牌率仅 5.2%，但仍有 48 个代表团届次做到了。")
    return save(p, "fig01_size_vs_rate.svg")


def f02():
    """图 2 · 小团夺牌率百年趋势。"""
    df = pd.read_csv(TAB / "a_small_medal_rate_by_year.csv")
    p = op()
    ti(p, "图 2 · 小团夺牌率的百年趋势",
       "小团 = 参赛人数 ≤ 50；大团 = 参赛人数 > 50；小项口径")
    ya(p, 0, 1.0, 5, "夺牌率")
    years = df["Year"].tolist()
    xm = {y: sc(y, min(years), max(years), PL, W - PR) for y in years}
    for col, color in [("big_medal_rate", C["muted"]),
                       ("small_medal_rate", C["accent"])]:
        pts = [(xm[r.Year], sc(float(getattr(r, col)), 0, 1.0, H - PB, PT + 8))
               for r in df.itertuples()]
        p.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" '
                 f'fill="none" stroke="{color}" stroke-width="2.2"/>')
        lx, ly = pts[-1]
        p.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="3.5" fill="{color}"/>')
    if 1980 in xm:
        p.append(f'<line x1="{xm[1980]:.1f}" y1="{PT + 8}" x2="{xm[1980]:.1f}" '
                 f'y2="{H - PB}" stroke="{C["warn"]}" stroke-width="1" '
                 f'stroke-dasharray="4 3"/>')
        p.append(f'<text x="{xm[1980] + 5:.1f}" y="{PT + 20}" font-size="10.5" '
                 f'fill="{C["warn"]}">1980 近代起点</text>')
    for yv in [1896, 1920, 1948, 1980, 2000, 2024]:
        if yv in xm:
            p.append(f'<text x="{xm[yv]:.1f}" y="{H - PB + 18}" font-size="10.5" '
                     f'text-anchor="middle" fill="{C["muted"]}">{yv}</text>')
    lg(p, [("大团(>50)", C["muted"]), ("小团(≤50)", C["accent"])])
    nt(p, "小团夺牌率 1980 年 16.7% → 2024 年 25.3%，近代 OLS 斜率 +0.19pp/年"
         "（R²=0.60，p=0.003）；但全期是 −0.41pp/年，拐点在 1980。")
    return save(p, "fig02_small_trend.svg")


def f03():
    """图 3 · 规模与集中度散点。"""
    df = pd.read_csv(TAB / "b_concentration_scatter.csv")
    df = df[df["Year"] >= 1980].dropna(subset=["top1_share"])
    p = op()
    ti(p, "图 3 · 参赛规模与夺牌集中度：小团几乎必然押注单一项目",
       "每点 = 一个代表团的一个有奖牌届次（1980 年后）；横轴为参赛人数（对数刻度）")
    ya(p, 0, 1.0, 5, "最大单项份额 top1_share")
    x0, x1 = PL, W - PR
    lo, hi = math.log10(1), math.log10(max(float(df["athletes"].max()), 2))
    xf = lambda v: sc(math.log10(max(float(v), 1)), lo, hi, x0, x1)
    yf = lambda v: sc(float(v), 0, 1.0, H - PB, PT + 8)
    for r in df.itertuples():
        p.append(f'<circle cx="{xf(r.athletes):.1f}" cy="{yf(r.top1_share):.1f}" '
                 f'r="2.1" fill="{C["accent"]}" opacity="0.25"/>')
    for noc, color in [("HKG", C["warn"]), ("SGP", C["gold"]),
                       ("TPE", C["green"])]:
        for r in df[df["NOC"] == noc].itertuples():
            p.append(f'<circle cx="{xf(r.athletes):.1f}" '
                     f'cy="{yf(r.top1_share):.1f}" r="5" fill="none" '
                     f'stroke="{color}" stroke-width="2"/>')
    for v in [1, 5, 10, 50, 200, 600]:
        if v <= df["athletes"].max():
            p.append(f'<text x="{xf(v):.1f}" y="{H - PB + 18}" font-size="10.5" '
                     f'text-anchor="middle" fill="{C["muted"]}">{v}</text>')
    p.append(f'<text x="{(x0 + x1) / 2:.1f}" y="{H - PB + 36}" font-size="11" '
             f'text-anchor="middle" fill="{C["muted"]}">参赛人数（对数刻度）</text>')
    lg(p, [("香港 HKG", C["warn"]), ("新加坡 SGP", C["gold"]),
           ("中华台北 TPE", C["green"])])
    nt(p, "Spearman：人数 vs 最大单项份额 ρ = −0.79（p &lt; 1e-186, n=874）；"
         "小团 72.4% 的届次只靠一个项目，大团只有 0.7%。")
    return save(p, "fig03_concentration_scatter.svg")


def f04():
    """图 4 · 人效随规模衰减。"""
    df = pd.read_csv(TAB / "b_efficiency_vs_size.csv")
    p = op()
    ti(p, "图 4 · 单位人力产出随规模衰减",
       "纵轴 = 小项口径奖牌 / 参赛人数 的中位数；误差棒为 2000 次 bootstrap 的 95% 区间")
    ymax = float(df["ci95_high"].max()) * 1.15
    ya(p, 0, ymax, 5, "奖牌 / 运动员（中位数）")
    x0, x1 = PL + 30, W - PR - 10
    band = (x1 - x0) / max(len(df), 1)
    pts = []
    for i, r in enumerate(df.itertuples()):
        cx = x0 + band * (i + 0.5)
        y = sc(float(r.mpa_median), 0, ymax, H - PB, PT + 8)
        lo = sc(float(r.ci95_low), 0, ymax, H - PB, PT + 8)
        hi = sc(float(r.ci95_high), 0, ymax, H - PB, PT + 8)
        pts.append((cx, y))
        p.append(f'<line x1="{cx:.1f}" y1="{lo:.1f}" x2="{cx:.1f}" y2="{hi:.1f}" '
                 f'stroke="{C["grid"]}" stroke-width="2.5"/>')
        p.append(f'<circle cx="{cx:.1f}" cy="{y:.1f}" r="5" fill="{C["accent"]}"/>')
        p.append(f'<text x="{cx:.1f}" y="{hi - 6:.1f}" font-size="9.5" '
                 f'text-anchor="middle" fill="{C["muted"]}">n={int(r.n_with_medal)}</text>')
        p.append(f'<text x="{cx:.1f}" y="{H - PB + 18}" font-size="10.5" '
                 f'text-anchor="middle" fill="{C["ink"]}">{r.size_bin}</text>')
    p.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" '
             f'fill="none" stroke="{C["accent"]}" stroke-width="1.6" opacity="0.45"/>')
    nt(p, "按小项口径，1–5 人团的人效中位数是 201+ 人团的 4.1 倍；"
         "但这是幸存者效应——极小队本身是从大量参赛记录里筛出来的赢家。")
    return save(p, "fig04_efficiency.svg")


def f05():
    """图 5 · 八个案例的项目构成。"""
    df = pd.read_csv(TAB / "c_case_medal_by_sport.csv")
    order = ["HKG", "SGP", "TPE", "GEO", "ARM", "MGL", "GRN", "KOS"]
    names = {"HKG": "香港", "SGP": "新加坡", "TPE": "中华台北", "GEO": "格鲁吉亚",
             "ARM": "亚美尼亚", "MGL": "蒙古", "GRN": "格林纳达", "KOS": "科索沃"}
    h = 500
    p = op(W, h)
    ti(p, "图 5 · 八个小代表团靠什么项目夺牌",
       "横向堆叠 = 各运动大类的小项口径奖牌累计；条形末端数字为该国历史总奖牌")
    pal = [C["accent"], C["warn"], C["gold"], C["green"], C["purple"],
           C["orange"], C["teal"], C["pink"]]
    x0, x1 = 152, W - 216
    xmax = float(df.groupby("NOC")["Total"].sum().max()) * 1.02
    sports = []
    for s in df.sort_values("Total", ascending=False)["Sport"]:
        if s not in sports:
            sports.append(s)
    bh, gap = 26, 16
    y = 76
    for noc in order:
        sub = df[df["NOC"] == noc].sort_values("Total", ascending=False).head(7)
        p.append(f'<text x="24" y="{y + 17}" font-size="12" '
                 f'fill="{C["ink"]}">{names[noc]}（{noc}）</text>')
        xc = x0
        for r in sub.itertuples():
            w = sc(float(r.Total), 0, xmax, 0, x1 - x0)
            color = pal[sports.index(r.Sport) % len(pal)]
            p.append(f'<rect x="{xc:.1f}" y="{y}" width="{w:.1f}" height="{bh}" '
                     f'fill="{color}" rx="2"/>')
            if w > 24:
                p.append(f'<text x="{xc + w / 2:.1f}" y="{y + 17}" font-size="10" '
                         f'text-anchor="middle" fill="#FFFFFF">{int(r.Total)}</text>')
            xc += w
        p.append(f'<text x="{xc + 8:.1f}" y="{y + 17}" font-size="11" '
                 f'fill="{C["muted"]}">{int(df[df["NOC"] == noc]["Total"].sum())}</text>')
        y += bh + gap
    lx, ly = W - 206, 76
    for i, s in enumerate(sports[:19]):
        p.append(f'<rect x="{lx}" y="{ly + i * 17}" width="9" height="9" rx="2" '
                 f'fill="{pal[i % len(pal)]}"/>')
        p.append(f'<text x="{lx + 14}" y="{ly + i * 17 + 8}" font-size="10.5" '
                 f'fill="{C["ink"]}">{s}</text>')
    nt(p, "共同结构：前两项项目吃掉大部分奖牌。格鲁吉亚摔跤+柔道占 78.7%，"
         "格林纳达 100% 来自田径，科索沃 100% 来自柔道。", h)
    return save(p, "fig05_case_sports.svg")


def f06():
    """图 6 · 三个点名案例的逐届轨迹。"""
    base = pd.read_csv(T3 / "s4_base.csv")
    cases = ["HKG", "SGP", "TPE"]
    names = {"HKG": "香港", "SGP": "新加坡", "TPE": "中华台北"}
    colors = {"HKG": C["warn"], "SGP": C["gold"], "TPE": C["green"]}
    p = op()
    ti(p, "图 6 · 三个点名案例：奖牌与参赛规模的逐届轨迹",
       "柱 = 小项口径奖牌数；虚线 = 参赛人数（仅示意规模，不共享纵轴）")
    ymax = max(14.0, float(base[base["NOC"].isin(cases)]["Total_event"].max()) * 1.2)
    ya(p, 0, ymax, 7, "小项口径奖牌")
    years = sorted(base[base["NOC"].isin(cases)]["Year"].unique())
    x0, x1 = PL + 10, W - PR - 70
    xf = lambda yv: sc(yv, min(years), max(years), x0, x1)
    band = (x1 - x0) / max(len(years) - 1, 1)
    amax = float(base[base["NOC"].isin(cases)]["athletes"].max()) * 1.1
    for noc in cases:
        sub = base[base["NOC"] == noc].set_index("Year")
        for yv in years:
            if yv in sub.index:
                v = float(sub.loc[yv, "Total_event"])
                if v > 0:
                    hp = sc(v, 0, ymax, 0, H - PB - PT - 16)
                    off = (cases.index(noc) - 1) * band * 0.24
                    p.append(f'<rect x="{xf(yv) + off - band * 0.1:.1f}" '
                             f'y="{H - PB - hp:.1f}" width="{band * 0.2:.1f}" '
                             f'height="{hp:.1f}" fill="{colors[noc]}" rx="1.5"/>')
        pts = [(xf(yv), sc(float(sub.loc[yv, "athletes"]), 0, amax,
                           H - PB, PT + 8))
               for yv in years if yv in sub.index]
        p.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" '
                 f'fill="none" stroke="{colors[noc]}" stroke-width="1.2" '
                 f'opacity="0.5" stroke-dasharray="3 3"/>')
    for i, yv in enumerate(years):
        if i % 2 == 0:
            p.append(f'<text x="{xf(yv):.1f}" y="{H - PB + 18}" font-size="10" '
                     f'text-anchor="middle" fill="{C["muted"]}">{yv}</text>')
    lg(p, [(f"{names[n]}（{n}）", colors[n]) for n in cases])
    nt(p, "香港 1996 首金 → 2020 单届 6 牌；新加坡 2016 首金后 2020 归零、2024 再得 1 牌；"
         "中华台北 2000 年起进入稳定夺牌期。")
    return save(p, "fig06_case_trajectory.svg")


def f07():
    """图 7 · 首牌后夺牌率分布。"""
    df = pd.read_csv(TAB / "d_persistence.csv")
    p = op()
    ti(p, "图 7 · 突破之后：首牌后的夺牌率分布",
       "指标 = 首次夺牌之后的所有参赛届次里，有奖牌的占比；越靠右越稳定")
    x0, x1 = PL + 150, W - PR - 10
    xf = lambda v: sc(float(v), 0, 1.0, x0, x1)
    for i in range(6):
        v = i / 5
        y = sc(v, 0, 1.0, H - PB, PT + 8)
        p.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{W - PR}" y2="{y:.1f}" '
                 f'stroke="{C["grid"]}"/>')
        p.append(f'<text x="{x0 - 8}" y="{y + 4:.1f}" font-size="11" '
                 f'text-anchor="end" fill="{C["muted"]}">{v:.1f}</text>')
    groups = [("小团型(峰值≤50)", df[df["max_athletes"] <= 50], C["warn"]),
              ("大团型(峰值>50)", df[df["max_athletes"] > 50], C["accent"])]
    for i, (label, g, color) in enumerate(groups):
        y = 150 + i * 110
        vals = g["post_first_medal_rate"].dropna().astype(float)
        q1, q2, q3 = (float(vals.quantile(q)) for q in (0.25, 0.5, 0.75))
        lo, hi = float(vals.min()), float(vals.max())
        p.append(f'<line x1="{xf(lo):.1f}" y1="{y}" x2="{xf(hi):.1f}" y2="{y}" '
                 f'stroke="{color}" stroke-width="1.5" opacity="0.55"/>')
        p.append(f'<rect x="{xf(q1):.1f}" y="{y - 17}" '
                 f'width="{max(xf(q3) - xf(q1), 1):.1f}" height="34" '
                 f'fill="{color}" opacity="0.25" stroke="{color}"/>')
        p.append(f'<line x1="{xf(q2):.1f}" y1="{y - 17}" x2="{xf(q2):.1f}" '
                 f'y2="{y + 17}" stroke="{color}" stroke-width="2.5"/>')
        p.append(f'<text x="{xf(q2):.1f}" y="{y - 26}" font-size="11" '
                 f'text-anchor="middle" fill="{C["ink"]}">中位 {q2:.2f}</text>')
        p.append(f'<text x="{x0 - 16}" y="{y + 4}" font-size="12" '
                 f'text-anchor="end" fill="{C["ink"]}">{label}</text>')
        p.append(f'<text x="{x0 - 16}" y="{y + 20}" font-size="10" '
                 f'text-anchor="end" fill="{C["muted"]}">n={len(vals)}</text>')
    nt(p, "Mann-Whitney U：小团型中位 0.155 vs 大团型 0.926，p = 6.1e-13，"
         "效应量 r = −0.70。小团的突破大多是「一次性」的。")
    return save(p, "fig07_persistence.svg")


def f08():
    """图 8 · 小团奖牌份额上升。"""
    df = pd.read_csv(TAB / "f_small_rise.csv")
    p = op()
    ti(p, "图 8 · 小团在奖牌桌上的份额正在变大",
       "份额 = 小团(≤50)奖牌占当届总奖牌比 / 小团夺牌代表团占当届夺牌代表团比")
    ya(p, 0, 0.5, 5, "份额")
    years = df["Year"].tolist()
    xm = {y: sc(y, min(years), max(years), PL + 10, W - PR - 60) for y in years}
    series = [("small_medal_share", C["warn"], "小团奖牌份额", 2.4),
              ("small_medal_noc_share", C["accent"], "小团夺牌国份额", 2.0)]
    for col, color, label, wd in series:
        pts = [(xm[r.Year], sc(float(getattr(r, col)), 0, 0.5, H - PB, PT + 8))
               for r in df.itertuples()]
        p.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" '
                 f'fill="none" stroke="{color}" stroke-width="{wd}"/>')
        for x, y in pts:
            p.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="{color}"/>')
    lg(p, [(lb, co) for _, co, lb, _ in series], y=PT + 40)
    for yv in years:
        p.append(f'<text x="{xm[yv]:.1f}" y="{H - PB + 18}" font-size="9.5" '
                 f'text-anchor="middle" fill="{C["muted"]}">{yv}</text>')
    a = float(df.iloc[0]["small_medal_share"])
    b = float(df.iloc[-1]["small_medal_share"])
    c0 = float(df.iloc[0]["small_medal_noc_share"])
    c1 = float(df.iloc[-1]["small_medal_noc_share"])
    nt(p, f"小团奖牌份额 {a * 100:.1f}% → {b * 100:.1f}%，OLS 斜率 +0.148pp/年"
         f"（R²=0.79，p=1.1e-4）；夺牌国份额 {c0 * 100:.1f}% → {c1 * 100:.1f}%。")
    return save(p, "fig08_small_share_rise.svg")


def f09():
    """图 9 · 阈值敏感性与口径翻转（上下两栏）。"""
    th = pd.read_csv(TAB / "e_threshold_sensitivity.csv")
    h = 470
    p = op(W, h)
    ti(p, "图 9 · 一个诚实的警告：换个定义，「小而精」的优势就消失了",
       "上：人效中位数随「小团」阈值变化；下：同一批数据换口径后结论方向翻转")
    # 上栏：阈值
    ytop0, ytop1 = 70, 215
    ymax = float(max(th["small_mpa_median"].max(), th["big_mpa_median"].max())) * 1.4
    for i in range(4):
        v = ymax * i / 3
        y = sc(v, 0, ymax, ytop1, ytop0)
        p.append(f'<line x1="{PL}" y1="{y:.1f}" x2="{W - PR - 40}" y2="{y:.1f}" '
                 f'stroke="{C["grid"]}"/>')
        p.append(f'<text x="{PL - 8}" y="{y + 4:.1f}" font-size="10" '
                 f'text-anchor="end" fill="{C["muted"]}">{v:.2f}</text>')
    p.append(f'<text x="24" y="{ytop0 - 14}" font-size="11" fill="{C["muted"]}">人效中位数</text>')
    xs = lambda i: sc(i, 0, max(len(th) - 1, 1), PL + 40, W - PR - 60)
    for col, color, label in [("small_mpa_median", C["warn"], "小团"),
                              ("big_mpa_median", C["accent"], "大团")]:
        pts = [(xs(i), sc(float(r[col]), 0, ymax, ytop1, ytop0))
               for i, (_, r) in enumerate(th.iterrows())]
        p.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" '
                 f'fill="none" stroke="{color}" stroke-width="2.2"/>')
        for x, y in pts:
            p.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}"/>')
    for i, r in enumerate(th.itertuples()):
        p.append(f'<text x="{xs(i):.1f}" y="{ytop1 + 16}" font-size="10.5" '
                 f'text-anchor="middle" fill="{C["muted"]}">≤{int(r.threshold)}人</text>')
    lg(p, [("小团人效", C["warn"]), ("大团人效", C["accent"])], y=ytop0)
    p.append(f'<line x1="{PL}" y1="{ytop1 + 30}" x2="{W - PL}" y2="{ytop1 + 30}" '
             f'stroke="{C["grid"]}"/>')
    # 下栏：口径翻转
    yb0, yb1 = 290, 400
    p.append(f'<text x="24" y="{yb0 - 14}" font-size="11" fill="{C["muted"]}">'
             f'小项口径 → 运动员行口径（1980+ 有奖牌届次）</text>')
    bars = [("小项·小团", 0.0732, C["warn"]), ("小项·大团", 0.0658, C["accent"]),
            ("行口径·小团", 0.0938, C["warn"]), ("行口径·大团", 0.1455, C["accent"])]
    bmax = 0.18
    bw = 90
    for i, (label, v, color) in enumerate(bars):
        x = PL + 60 + i * (bw + 60)
        hp = sc(v, 0, bmax, 0, yb1 - yb0)
        p.append(f'<rect x="{x}" y="{yb1 - hp:.1f}" width="{bw}" '
                 f'height="{hp:.1f}" fill="{color}" rx="2"/>')
        p.append(f'<text x="{x + bw / 2:.1f}" y="{yb1 - hp - 6:.1f}" font-size="11" '
                 f'text-anchor="middle" fill="{C["ink"]}">{v:.4f}</text>')
        p.append(f'<text x="{x + bw / 2:.1f}" y="{yb1 + 18}" font-size="10.5" '
                 f'text-anchor="middle" fill="{C["muted"]}">{label}</text>')
    p.append(f'<text x="24" y="{h - 44}" font-size="11" fill="{C["warn"]}">'
             f'小项口径下小团更高（0.0732 &gt; 0.0658）；换行口径后大团更高'
             f'（0.1455 &gt; 0.0938）——方向相反。</text>')
    nt(p, "这个翻转不是测量误差：团体项目在行口径下给大团额外加成，而小团的奖牌多来自个人项目。"
         "结论必须绑定口径才有意义。", h)
    return save(p, "fig09_sensitivity.svg")


def main():
    """依次生成 9 张图，返回产物路径。"""
    makers = [f01, f02, f03, f04, f05, f06, f07, f08, f09]
    out = []
    for m in makers:
        try:
            path = m()
            out.append(path)
            print(f"[s4_fig] {path.name} ({path.stat().st_size} bytes)")
        except Exception as exc:  # 单图失败不阻断其余图
            print(f"[s4_fig] 跳过 {m.__name__}: {type(exc).__name__}: {exc}")
    return out


if __name__ == "__main__":
    main()
