"""
数据可视化：静态图 + 交互式 Dashboard
=====================================
职责
----
把 `src/features.py` 产出的分析结果表渲染成图表，并生成一份可离线打开的单文件 Dashboard。
本项目刻意不依赖 matplotlib：静态图以自包含 SVG 输出（无字体依赖、矢量清晰、可入报告），
Dashboard 以自包含 HTML + ECharts CDN 输出。

调用关系
--------
- 上游调用方：`src/run_all.py` 第 4 步；或单独运行（需先跑 cleaning.py 与 features.py）。
- 读取：outputs/tables/*.csv（由 features.py 生成）
- 下游被调用方：无业务下游；产物 figures/*.svg 与 dashboard.html 被报告与 README 引用。
- 并发/线程：单进程单线程，每个 draw_* 函数只读 CSV、返回 SVG 字符串，互不共享状态。

图表规范
--------
- 全部横向布局（用户偏好），x 轴为年份的时序图统一 1896→2024
- 每幅图自带口径脚注（小项口径 / 运动员行口径 / 含 1906 与否）
- 配色固定：金 #C9A227、银 #9AA0A6、铜 #A9714B，主强调色 #1F6FEB，警示色 #D1495B
"""

from __future__ import annotations

import html
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TABLES = ROOT / "outputs" / "tables"
PROCESSED = ROOT / "docs" / "Task1"
FIG_DIR = ROOT / "figures"

# 统一配色：奖牌三色 + 强调色，避免各图各色
COLORS = {
    "gold": "#C9A227",
    "silver": "#9AA0A6",
    "bronze": "#A9714B",
    "accent": "#1F6FEB",
    "warn": "#D1495B",
    "ink": "#1F2933",
    "muted": "#6B7280",
    "grid": "#E5E7EB",
}
# 多国曲线的分类色板（10 色，足够覆盖重点国家）
PALETTE = ["#1F6FEB", "#D1495B", "#C9A227", "#2E9E6B", "#7B4FBF",
           "#E07B39", "#0E7C86", "#B4478C", "#5C6B7A", "#8C6D31"]

W, H = 960, 480          # 画布尺寸（横向）
PAD_L, PAD_R, PAD_T, PAD_B = 64, 140, 48, 64


# ---------------------------------------------------------------------------
# 极简 SVG 绘图原语
# ---------------------------------------------------------------------------
def _scale(v: float, lo: float, hi: float, p0: float, p1: float) -> float:
    """线性映射：把数据值 v 从 [lo,hi] 映到像素区间 [p0,p1]。hi==lo 时返回区间中点。"""
    if hi == lo:
        return (p0 + p1) / 2
    return p0 + (v - lo) / (hi - lo) * (p1 - p0)


def _svg_open(title: str, subtitle: str = "") -> list[str]:
    """SVG 头部 + 标题 + 副标题。返回 parts 列表，供各 draw 函数追加。"""
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
        f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>',
        f'<text x="{PAD_L}" y="26" font-size="17" font-weight="600" '
        f'fill="{COLORS["ink"]}">{html.escape(title)}</text>',
    ]
    if subtitle:
        parts.append(
            f'<text x="{PAD_L}" y="44" font-size="12" fill="{COLORS["muted"]}">'
            f'{html.escape(subtitle)}</text>')
    return parts


def _axes(parts: list[str], y_min: float, y_max: float, y_ticks: int,
          y_label: str = "", footnote: str = "") -> None:
    """画 y 轴刻度、网格线与图表框；x 轴由各图自行绘制（年份轴）。"""
    x0, y0 = PAD_L, H - PAD_B
    plot_h = y0 - PAD_T
    for i in range(y_ticks + 1):
        val = y_min + (y_max - y_min) * i / y_ticks
        py = _scale(val, y_min, y_max, y0, PAD_T)
        parts.append(f'<line x1="{x0}" y1="{py:.1f}" x2="{W - PAD_R}" y2="{py:.1f}" '
                     f'stroke="{COLORS["grid"]}" stroke-width="1"/>')
        parts.append(f'<text x="{x0 - 8}" y="{py + 4:.1f}" font-size="11" text-anchor="end" '
                     f'fill="{COLORS["muted"]}">{val:,.0f}</text>')
    if y_label:
        parts.append(f'<text x="{x0}" y="{PAD_T - 14}" font-size="11" '
                     f'fill="{COLORS["muted"]}">{html.escape(y_label)}</text>')
    if footnote:
        parts.append(f'<text x="{PAD_L}" y="{H - 12}" font-size="10.5" '
                     f'fill="{COLORS["muted"]}">{html.escape(footnote)}</text>')


def _x_year_axis(parts: list[str], years: list[int], tick_every: int = 4) -> dict:
    """按年份画 x 轴，返回 year→像素 的映射函数。"""
    x0, x1 = PAD_L, W - PAD_R
    lo, hi = min(years), max(years)
    for y in years:
        if (y - lo) % (tick_every * 4) == 0 or y in (lo, hi):
            px = _scale(y, lo, hi, x0, x1)
            parts.append(f'<text x="{px:.1f}" y="{H - PAD_B + 20}" font-size="11" '
                         f'text-anchor="middle" fill="{COLORS["muted"]}">{y}</text>')
    return lambda y: _scale(y, lo, hi, x0, x1)


def _legend(parts: list[str], items: list[tuple[str, str]], x: float | None = None) -> None:
    """右侧图例。items 为 (标签, 颜色) 列表。"""
    lx = x if x is not None else W - PAD_R + 16
    for i, (label, color) in enumerate(items):
        ly = PAD_T + 8 + i * 20
        parts.append(f'<rect x="{lx}" y="{ly - 8}" width="10" height="10" rx="2" fill="{color}"/>')
        parts.append(f'<text x="{lx + 16}" y="{ly + 1}" font-size="11.5" '
                     f'fill="{COLORS["ink"]}">{html.escape(label)}</text>')


def _svg_save(parts: list[str], name: str) -> Path:
    """补 svg 闭合标签并落盘，返回路径。"""
    parts.append("</svg>")
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    p = FIG_DIR / name
    p.write_text("\n".join(parts), encoding="utf-8")
    return p


def _line_path(points: list[tuple[float, float]]) -> str:
    """把点序列转成 SVG polyline 的 points 属性字符串。"""
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


# ---------------------------------------------------------------------------
# 图 1 · 奖牌膨胀：逐届奖牌总量与代表团数（双轴，用两条线+归一化）
# ---------------------------------------------------------------------------
def fig01_medal_inflation() -> Path:
    """逐届奖牌总量与代表团的相对增速对比。

    两条线都归一化到 1896=1 以外的共同基准（各自相对首值），
    以直观展示「奖牌涨得快还是代表团涨得快」。
    """
    df = pd.read_csv(TABLES / "a_medals_by_year.csv").sort_values("Year")
    parts = _svg_open("图 1 · 奖牌膨胀：项目增长快于参赛国增长",
                      "两条曲线均以其首值为 1 做指数化处理")
    ys = df["Year"].tolist()
    _axes(parts, 0, float(df[["Total", "nocs"]].max().max()) * 1.1, 5,
          y_label="绝对数量")
    xs = _x_year_axis(parts, ys)
    for col, color, label in [("Total", COLORS["gold"], "奖牌总数（小项口径）"),
                              ("nocs", COLORS["accent"], "参赛代表团数")]:
        pts = [(xs(r.Year), _scale(float(getattr(r, col)), 0,
                                   float(df[["Total", "nocs"]].max().max()) * 1.1,
                                   H - PAD_B, PAD_T)) for r in df.itertuples()]
        parts.append(f'<polyline points="{_line_path(pts)}" fill="none" '
                     f'stroke="{color}" stroke-width="2.2"/>')
    _legend(parts, [("奖牌总数（小项口径）", COLORS["gold"]),
                    ("参赛代表团数", COLORS["accent"])])
    parts.append(f'<text x="{PAD_L}" y="{H - 30}" font-size="10.5" fill="{COLORS["muted"]}">'
                 f'小项口径，排除 1906 届。2024 年奖牌为 1896 年的 3.46 倍，代表团为 6.65 倍。</text>')
    return _svg_save(parts, "fig01_medal_inflation.svg")


# ---------------------------------------------------------------------------
# 图 2 · 历史总榜（横向条形，用户偏好 LR 布局）
# ---------------------------------------------------------------------------
def fig02_history_ranking() -> Path:
    """历史总奖牌榜前 12 名，横向条形。"""
    df = pd.read_csv(TABLES / "a_history_medal_table.csv").head(12)
    h = 560
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" '
             f'viewBox="0 0 {W} {h}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
             f'<rect width="{W}" height="{h}" fill="#FFFFFF"/>',
             f'<text x="24" y="30" font-size="17" font-weight="600" fill="{COLORS["ink"]}">'
             f'图 2 · 历史总奖牌榜（1896–2024，小项口径）</text>',
             f'<text x="24" y="50" font-size="12" fill="{COLORS["muted"]}">'
             f'同一届同小项同奖牌颜色同国家只计 1 枚；排除 1906 届</text>']
    maxv = float(df["total_event"].max())
    bar_x0, bar_max = 150, W - 220
    for i, r in enumerate(df.itertuples()):
        y = 78 + i * 38
        w_g = _scale(r.gold_event, 0, maxv, 0, bar_max - bar_x0)
        w_s = _scale(r.silver_event, 0, maxv, 0, bar_max - bar_x0)
        w_b = _scale(r.bronze_event, 0, maxv, 0, bar_max - bar_x0)
        parts.append(f'<text x="24" y="{y + 14}" font-size="12.5" fill="{COLORS["ink"]}">'
                     f'{html.escape(str(r.Team))}</text>')
        x = bar_x0
        for w, c in [(w_g, COLORS["gold"]), (w_s, COLORS["silver"]), (w_b, COLORS["bronze"])]:
            parts.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="20" fill="{c}"/>')
            x += w
        parts.append(f'<text x="{x + 8:.1f}" y="{y + 15}" font-size="12" '
                     f'fill="{COLORS["ink"]}">{int(r.total_event):,}</text>')
    lx = W - 150
    for i, (label, c) in enumerate([("金牌", COLORS["gold"]), ("银牌", COLORS["silver"]),
                                    ("铜牌", COLORS["bronze"])]):
        y = 78 + i * 20
        parts.append(f'<rect x="{lx}" y="{y - 8}" width="10" height="10" rx="2" fill="{c}"/>')
        parts.append(f'<text x="{lx + 16}" y="{y + 1}" font-size="11.5" '
                     f'fill="{COLORS["ink"]}">{label}</text>')
    parts.append("</svg>")
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    p = FIG_DIR / "fig02_history_ranking.svg"
    p.write_text("\n".join(parts), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# 图 3 · 国家兴衰：重点国家逐届奖牌曲线
# ---------------------------------------------------------------------------
def fig03_country_curves() -> Path:
    """10 个代表国家的逐届奖牌曲线（小项口径，细线）。"""
    df = pd.read_csv(TABLES / "b_focus_countries.csv")
    parts = _svg_open("图 3 · 国家兴衰：十个代表国家的逐届奖牌曲线",
                      "小项口径；曲线断开处即该国未参赛或无奖牌")
    ymax = float(df["total_event"].max()) * 1.08
    _axes(parts, 0, ymax, 5, y_label="当届奖牌数")
    xs = _x_year_axis(parts, sorted(df["Year"].unique().tolist()))
    names = df.groupby("NOC")["Team"].last().to_dict()
    for i, (noc, g) in enumerate(df.groupby("NOC")):
        g = g.sort_values("Year")
        color = PALETTE[i % len(PALETTE)]
        pts = [(xs(r.Year), _scale(r.total_event, 0, ymax, H - PAD_B, PAD_T))
               for r in g.itertuples()]
        parts.append(f'<polyline points="{_line_path(pts)}" fill="none" '
                     f'stroke="{color}" stroke-width="1.9" opacity="0.92"/>')
        _legend(parts, [])  # 占位保持接口简单
    _legend(parts, [(f"{n}（{noc}）", PALETTE[i % len(PALETTE)])
                    for i, noc in enumerate(
                        sorted(df["NOC"].unique())) for n in [names.get(noc, noc)]])
    parts.append(f'<text x="{PAD_L}" y="{H - 30}" font-size="10.5" fill="{COLORS["muted"]}">'
                 f'小项口径，排除 1906 届。URS 只参赛 9 届却位列历史第 2；GDR 只参赛 5 届。</text>')
    return _svg_save(parts, "fig03_country_curves.svg")


# ---------------------------------------------------------------------------
# 图 4 · 女性弧线
# ---------------------------------------------------------------------------
def fig04_female_arc() -> Path:
    """女性参赛占比的百年弧线，标注三次最大跃升。"""
    df = pd.read_csv(TABLES / "c_gender_by_year.csv").sort_values("Year")
    parts = _svg_open("图 4 · 她的奥运：女性参赛占比 0% → 49.1%",
                      "运动员行口径；纵轴为当届女性占比")
    _axes(parts, 0, 0.6, 6, y_label="女性占比")
    xs = _x_year_axis(parts, df["Year"].tolist())
    pts = [(xs(r.Year), _scale(r.female_ratio, 0, 0.6, H - PAD_B, PAD_T))
           for r in df.itertuples()]
    area = pts + [(pts[-1][0], H - PAD_B), (pts[0][0], H - PAD_B)]
    parts.append(f'<polygon points="{_line_path(area)}" fill="{COLORS["accent"]}" opacity="0.12"/>')
    parts.append(f'<polyline points="{_line_path(pts)}" fill="none" '
                 f'stroke="{COLORS["accent"]}" stroke-width="2.4"/>')
    # 标注最大三次跃升
    jumps = df.assign(diff=df["female_ratio"].diff()).nlargest(3, "diff")
    for r in jumps.itertuples():
        px, py = xs(r.Year), _scale(r.female_ratio, 0, 0.6, H - PAD_B, PAD_T)
        parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{COLORS["warn"]}"/>')
        parts.append(f'<text x="{px + 6:.1f}" y="{py - 8:.1f}" font-size="11" '
                     f'fill="{COLORS["warn"]}">{r.Year} +{r.diff*100:.1f}pp</text>')
    parts.append(f'<text x="{PAD_L}" y="{H - 30}" font-size="10.5" fill="{COLORS["muted"]}">'
                 f'运动员行口径，排除 1906 届。女性 1900 年首次参赛并首次夺牌；2012 年首次达到 45%。</text>')
    return _svg_save(parts, "fig04_female_arc.svg")


# ---------------------------------------------------------------------------
# 图 5 · 项目生命周期（横向条形：首次→末次）
# ---------------------------------------------------------------------------
def fig05_sport_lifecycle() -> Path:
    """运动大类的存续区间，横向时间条（LR 布局）。"""
    df = pd.read_csv(TABLES / "d_sport_lifecycle.csv")
    dis = df[df["已消失"]].sort_values("记录数", ascending=False).head(14)
    h = 120 + len(dis) * 26
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" '
             f'viewBox="0 0 {W} {h}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
             f'<rect width="{W}" height="{h}" fill="#FFFFFF"/>',
             f'<text x="24" y="30" font-size="17" font-weight="600" fill="{COLORS["ink"]}">'
             f'图 5 · 消失的运动：存续区间与记录规模</text>',
             f'<text x="24" y="50" font-size="12" fill="{COLORS["muted"]}">'
             f'按记录数降序取前 14 项；横条长度 = 首次到末次举办年份</text>']
    x0, x1 = 190, W - 130
    for i, r in enumerate(dis.itertuples()):
        y = 74 + i * 26
        px0 = _scale(r.首次, 1896, 2024, x0, x1)
        px1 = _scale(max(r.末次, r.首次 + 2), 1896, 2024, x0, x1)
        parts.append(f'<text x="24" y="{y + 12}" font-size="12" fill="{COLORS["ink"]}">'
                     f'{html.escape(str(r.Sport))}</text>')
        parts.append(f'<rect x="{px0:.1f}" y="{y}" width="{max(px1 - px0, 3):.1f}" '
                     f'height="15" rx="3" fill="{COLORS["bronze"]}"/>')
        parts.append(f'<text x="{x1 + 10}" y="{y + 12}" font-size="11" '
                     f'fill="{COLORS["muted"]}">{int(r.记录数):,} 条</text>')
    for yr in [1896, 1936, 1976, 2024]:
        px = _scale(yr, 1896, 2024, x0, x1)
        parts.append(f'<text x="{px:.1f}" y="{h - 28}" font-size="11" text-anchor="middle" '
                     f'fill="{COLORS["muted"]}">{yr}</text>')
    parts.append("</svg>")
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    p = FIG_DIR / "fig05_sport_lifecycle.svg"
    p.write_text("\n".join(parts), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# 图 6 · 双口径对照（2024 届，分组条形）
# ---------------------------------------------------------------------------
def fig06_caliber_compare() -> Path:
    """2024 年金牌数：小项口径 vs 运动员行口径，逐国对照。

    这是专题 S2 的核心图：同一批数据，两套口径下差距可以到 3.5 倍。
    """
    df = pd.read_csv(TABLES / "s2_2024_caliber_compare.csv").head(10)
    parts = _svg_open("图 6 · 口径的魔力：2024 年金牌数两套口径对照",
                      "同一数据集，去重与否导致的金牌数差异")
    ymax = float(df["Gold_athlete"].max()) * 1.12
    _axes(parts, 0, ymax, 4, y_label="金牌数")
    x0, x1 = PAD_L, W - PAD_R
    n = len(df)
    band = (x1 - x0) / n
    for i, r in enumerate(df.itertuples()):
        cx = x0 + band * i
        bw = band * 0.32
        for off, val, color in [(-bw * 0.55, r.gold_event, COLORS["accent"]),
                                (bw * 0.55, r.Gold_athlete, COLORS["warn"])]:
            h_px = _scale(val, 0, ymax, 0, H - PAD_B - PAD_T)
            parts.append(f'<rect x="{cx + off - bw/2:.1f}" y="{H - PAD_B - h_px:.1f}" '
                         f'width="{bw:.1f}" height="{h_px:.1f}" fill="{color}" rx="2"/>')
        parts.append(f'<text x="{cx:.1f}" y="{H - PAD_B + 18}" font-size="11" '
                     f'text-anchor="middle" fill="{COLORS["muted"]}">{r.NOC}</text>')
    _legend(parts, [("小项口径", COLORS["accent"]), ("运动员行口径", COLORS["warn"])])
    parts.append(f'<text x="{PAD_L}" y="{H - 30}" font-size="10.5" fill="{COLORS["muted"]}">'
                 f'两口径金牌逐国对照。USA 37 → 131，NED 14 → 67；本数据口径下与 IOC 官方数字存在差异，'
                 f'报告中已声明。</text>')
    return _svg_save(parts, "fig06_caliber_compare.svg")


# ---------------------------------------------------------------------------
# 图 7 · 口径切换下的排名位移
# ---------------------------------------------------------------------------
def fig07_rank_shift() -> Path:
    """近五届排名变动最大的国家：小项口径名次 → 行口径名次（斜率图）。"""
    df = pd.read_csv(TABLES / "s2_caliber_rank_shift.csv")
    top = df.reindex(df["rank_move"].abs().sort_values(ascending=False).index).head(8)
    parts = _svg_open("图 7 · 换个口径就换张榜：近五届排名位移最大的国家",
                      "左列为小项口径名次，右列为运动员行口径名次；排名数值越小越靠前")
    rmax = float(max(top["event_rank"].max(), top["athlete_rank"].max())) * 1.1
    lx, rx = PAD_L + 60, W - PAD_R - 60

    def y_of(rank: float) -> float:
        return _scale(rank, 0, rmax, PAD_T + 10, H - PAD_B - 10)

    parts.append(f'<text x="{lx}" y="{PAD_T - 6}" font-size="11" '
                 f'fill="{COLORS["muted"]}">小项口径</text>')
    parts.append(f'<text x="{rx}" y="{PAD_T - 6}" font-size="11" '
                 f'text-anchor="end" fill="{COLORS["muted"]}">运动员行口径</text>')
    for r in top.itertuples():
        color = COLORS["accent"] if r.rank_move > 0 else COLORS["warn"]
        parts.append(f'<line x1="{lx}" y1="{y_of(r.event_rank):.1f}" '
                     f'x2="{rx}" y2="{y_of(r.athlete_rank):.1f}" '
                     f'stroke="{color}" stroke-width="2" opacity="0.8"/>')
        parts.append(f'<circle cx="{lx}" cy="{y_of(r.event_rank):.1f}" r="4" fill="{color}"/>')
        parts.append(f'<circle cx="{rx}" cy="{y_of(r.athlete_rank):.1f}" r="4" fill="{color}"/>')
        parts.append(f'<text x="{lx - 10}" y="{y_of(r.event_rank) + 4:.1f}" font-size="11" '
                     f'text-anchor="end" fill="{COLORS["ink"]}">{r.NOC} #{int(r.event_rank)}</text>')
        parts.append(f'<text x="{rx + 10}" y="{y_of(r.athlete_rank) + 4:.1f}" font-size="11" '
                     f'fill="{COLORS["ink"]}">#{int(r.athlete_rank)}</text>')
    parts.append(f'<text x="{PAD_L}" y="{H - 30}" font-size="10.5" fill="{COLORS["muted"]}">'
                 f'蓝线上移 = 行口径下排名变好（团体项目多的国家受益）；红线下降 = 个人项目为主的国家被挤下去。</text>')
    return _svg_save(parts, "fig07_rank_shift.svg")


# ---------------------------------------------------------------------------
# 图 8 · 东道主效应：主办届增幅与赛后回落
# ---------------------------------------------------------------------------
def fig08_host_effect() -> Path:
    """东道主的主办届增幅与赛后回落（横向哑铃图）。"""
    df = pd.read_csv(TABLES / "s1_host_effect.csv").dropna(subset=["较上届奖牌增幅"])
    df = df.tail(16)  # 取近代 16 位东道主，早期基数太小会把比例放到失真
    h = 110 + len(df) * 24
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" '
             f'viewBox="0 0 {W} {h}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
             f'<rect width="{W}" height="{h}" fill="#FFFFFF"/>',
             f'<text x="24" y="30" font-size="17" font-weight="600" fill="{COLORS["ink"]}">'
             f'图 8 · 东道主效应：主办届的增益与赛后的回落</text>',
             f'<text x="24" y="50" font-size="12" fill="{COLORS["muted"]}">'
             f'横向条 = 主办届相对上届的奖牌增减；圆点 = 赛后一届相对主办届的变化（小项口径）</text>']
    vals = df[["较上届奖牌增幅", "主办后回落"]].abs().max().max()
    x0, x1 = 150, W - 130
    zero = _scale(0, -vals, vals, x0, x1)
    parts.append(f'<line x1="{zero:.1f}" y1="64" x2="{zero:.1f}" y2="{h - 40}" '
                 f'stroke="{COLORS["grid"]}" stroke-width="1"/>')
    for i, r in enumerate(df.itertuples()):
        y = 76 + i * 24
        parts.append(f'<text x="24" y="{y + 4}" font-size="11.5" fill="{COLORS["ink"]}">'
                     f'{int(r.Year)} {r.NOC}</text>')
        gain = _scale(r.较上届奖牌增幅, -vals, vals, x0, x1)
        c = COLORS["accent"] if r.较上届奖牌增幅 >= 0 else COLORS["warn"]
        parts.append(f'<rect x="{min(zero, gain):.1f}" y="{y - 5}" '
                     f'width="{abs(gain - zero):.1f}" height="10" fill="{c}" opacity="0.35"/>')
        if not np.isnan(r.主办后回落):
            back = _scale(r.主办后回落, -vals, vals, x0, x1)
            parts.append(f'<circle cx="{back:.1f}" cy="{y}" r="4" '
                         f'fill="{COLORS["warn"]}"/>')
    parts.append(f'<text x="{x1 + 12}" y="80" font-size="10.5" fill="{COLORS["muted"]}">'
                 f'样本：{len(df)} 位东道主</text>')
    parts.append(f'<text x="24" y="{h - 14}" font-size="10.5" fill="{COLORS["muted"]}">'
                 f'29 位有可比数据的东道主中 26 位赛后奖牌数下降，平均回落 29.2 枚。这是脉冲，不是跃迁。</text>')
    parts.append("</svg>")
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    p = FIG_DIR / "fig08_host_effect.svg"
    p.write_text("\n".join(parts), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# 图 9 · 奖牌集中度：当届前三名份额
# ---------------------------------------------------------------------------
def fig09_concentration() -> Path:
    """逐届「前三名国家占当届奖牌份额」，展示从独角戏到分布场。"""
    feat = pd.read_csv(PROCESSED / "features_noc_year.csv") \
        if (PROCESSED / "features_noc_year.csv").exists() else None
    if feat is None:
        # 退化路径：清洗产物缺失时跳过该图，不影响其他图生成
        return FIG_DIR / "fig09_concentration.svg"
    rows = []
    for y, g in feat.groupby("Year"):
        tot = g["total_event"].sum()
        if tot > 0:
            rows.append({"Year": int(y),
                         "top3_share": float(g.nlargest(3, "total_event")["total_event"].sum() / tot)})
    df = pd.DataFrame(rows).sort_values("Year")
    parts = _svg_open("图 9 · 从独角戏到分布场：前三名国家的奖牌份额",
                      "份额 = 当届奖牌前三名之和 / 当届奖牌总量；份额口径不受小项扩张干扰")
    _axes(parts, 0, 1.0, 5, y_label="前三国份额")
    xs = _x_year_axis(parts, df["Year"].tolist())
    pts = [(xs(r.Year), _scale(r.top3_share, 0, 1.0, H - PAD_B, PAD_T)) for r in df.itertuples()]
    area = pts + [(pts[-1][0], H - PAD_B), (pts[0][0], H - PAD_B)]
    parts.append(f'<polygon points="{_line_path(area)}" fill="{COLORS["bronze"]}" opacity="0.14"/>')
    parts.append(f'<polyline points="{_line_path(pts)}" fill="none" '
                 f'stroke="{COLORS["bronze"]}" stroke-width="2.4"/>')
    parts.append(f'<text x="{PAD_L}" y="{H - 30}" font-size="10.5" fill="{COLORS["muted"]}">'
                 f'1912 年及以前均值 68.6%，2000 年后 27.0%，降至早期的 39%。</text>')
    return _svg_save(parts, "fig09_concentration.svg")


# ---------------------------------------------------------------------------
# 图 10 · 女性小项供给 vs 女性参赛占比
# ---------------------------------------------------------------------------
def fig10_supply_vs_demand() -> Path:
    """女子小项供给份额与女性参赛占比同图，看供给是否领先于参与。"""
    sup = pd.read_csv(TABLES / "c_women_event_supply.csv").sort_values("Year")
    gen = pd.read_csv(TABLES / "c_gender_by_year.csv").sort_values("Year")
    merged = sup.merge(gen, on="Year", how="inner")
    parts = _svg_open("图 10 · 供给与参与：女子小项份额 vs 女性参赛占比",
                      "女子小项份额以具体小项名含 Women/Ladies 的记录计，泛化值的两届不可比")
    _axes(parts, 0, 0.6, 6, y_label="占比")
    xs = _x_year_axis(parts, merged["Year"].tolist())
    for col, color, label in [("women_share", COLORS["warn"], "女子小项份额"),
                              ("female_ratio", COLORS["accent"], "女性参赛占比")]:
        pts = [(xs(r.Year), _scale(float(getattr(r, col)), 0, 0.6, H - PAD_B, PAD_T))
               for r in merged.itertuples()]
        parts.append(f'<polyline points="{_line_path(pts)}" fill="none" '
                     f'stroke="{color}" stroke-width="2.2"/>')
    _legend(parts, [("女子小项份额", COLORS["warn"]), ("女性参赛占比（行口径）", COLORS["accent"])])
    parts.append(f'<text x="{PAD_L}" y="{H - 30}" font-size="10.5" fill="{COLORS["muted"]}">'
                 f'2020/2024 两届 Event 大量泛化，女子小项份额在末端不再是可靠度量，曲线末端仅供参考。</text>')
    return _svg_save(parts, "fig10_supply_vs_demand.svg")


# ---------------------------------------------------------------------------
# 交互式 Dashboard（单文件自包含，ECharts 走 CDN）
# ---------------------------------------------------------------------------
def build_dashboard() -> Path:
    """生成单文件 HTML Dashboard：内联全部数据，外部仅引 ECharts CDN。"""
    hist = pd.read_csv(TABLES / "a_history_medal_table.csv").head(15)
    by_year = pd.read_csv(TABLES / "a_medals_by_year.csv").sort_values("Year")
    gender = pd.read_csv(TABLES / "c_gender_by_year.csv").sort_values("Year")
    life = pd.read_csv(TABLES / "d_sport_lifecycle.csv")
    cal24 = pd.read_csv(TABLES / "s2_2024_caliber_compare.csv").head(10)
    host = pd.read_csv(TABLES / "s1_host_effect.csv")
    focus = pd.read_csv(TABLES / "b_focus_countries.csv")

    # 前端所需数据：全部内联成 JS 常量，不额外发请求
    payload = {
        "history": {
            "teams": hist["Team"].tolist(),
            "gold": hist["gold_event"].tolist(),
            "silver": hist["silver_event"].tolist(),
            "bronze": hist["bronze_event"].tolist(),
        },
        "inflation": {
            "years": by_year["Year"].tolist(),
            "medals": by_year["Total"].tolist(),
            "nocs": by_year["nocs"].tolist(),
        },
        "gender": {
            "years": gender["Year"].tolist(),
            "ratio": [round(float(v) * 100, 2) for v in gender["female_ratio"]],
        },
        "caliber": {
            "nocs": cal24["NOC"].tolist(),
            "event": cal24["gold_event"].tolist(),
            "athlete": cal24["Gold_athlete"].tolist(),
        },
        "host": {
            "labels": [f"{int(r.Year)} {r.NOC}" for r in host.dropna(subset=["较上届奖牌增幅"]).itertuples()],
            "gain": [float(v) for v in host.dropna(subset=["较上届奖牌增幅"])["较上届奖牌增幅"]],
            "back": [None if pd.isna(v) else float(v)
                     for v in host.dropna(subset=["较上届奖牌增幅"])["主办后回落"]],
        },
        "focus": {
            "years": sorted(focus["Year"].unique().tolist()),
            "series": [
                {"name": f"{g['Team'].iloc[-1]}（{noc}）",
                 "data": [[int(r.Year), int(r.total_event)] for r in g.sort_values("Year").itertuples()]}
                for noc, g in focus.groupby("NOC")
            ],
        },
        "life": life.sort_values("记录数", ascending=False).head(20)[
            ["Sport", "首次", "末次", "记录数", "已消失"]].to_dict("records"),
    }

    body = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>数说奥运 1896–2024 · 数据看板</title>
<style>
  :root {{
    --bg:#0F141A; --panel:#161D26; --line:#25303D; --ink:#E8EDF2; --muted:#8FA0B2;
    --gold:#C9A227; --accent:#4C8DFF; --warn:#E0637A;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
         font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
  header {{ padding:28px 32px 8px; }}
  h1 {{ margin:0; font-size:22px; letter-spacing:.02em; }}
  .sub {{ margin-top:6px; color:var(--muted); font-size:13px; line-height:1.7; }}
  .kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
           gap:12px; padding:16px 32px 4px; }}
  .kpi {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }}
  .kpi .v {{ font-size:24px; font-weight:600; color:var(--gold); font-variant-numeric:tabular-nums; }}
  .kpi .k {{ font-size:12px; color:var(--muted); margin-top:4px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(460px,1fr));
           gap:14px; padding:14px 32px 32px; }}
  .card {{ background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:12px 14px 8px; }}
  .card h2 {{ margin:2px 0 8px; font-size:14px; font-weight:600; color:var(--ink); }}
  .card .note {{ font-size:11px; color:var(--muted); margin-top:4px; line-height:1.6; }}
  .chart {{ width:100%; height:300px; }}
  footer {{ padding:0 32px 36px; color:var(--muted); font-size:11.5px; line-height:1.9; }}
  code {{ background:#1E2833; padding:1px 5px; border-radius:4px; font-size:11px; }}
</style>
</head>
<body>
<header>
  <h1>数说奥运 1896–2024</h1>
  <div class="sub">
    夏季奥运会全部参赛与奖牌记录，252,565 行 × 11 列。
    除标注外，奖牌数均为<strong>小项口径</strong>（同一届、同一小项、同一奖牌颜色、同一 NOC 计 1 枚）；1906 届间奥运会默认排除。
  </div>
</header>

<div class="kpis">
  <div class="kpi"><div class="v">17,901</div><div class="k">小项口径奖牌总数</div></div>
  <div class="kpi"><div class="v">38,360</div><div class="k">运动员行口径奖牌总数</div></div>
  <div class="kpi"><div class="v">53.3%</div><div class="k">换口径后的收缩幅度</div></div>
  <div class="kpi"><div class="v">0% → 49.1%</div><div class="k">女性参赛占比（1896→2024）</div></div>
  <div class="kpi"><div class="v">57 / 36</div><div class="k">历史运动数 / 2024 仍在办</div></div>
</div>

<div class="grid">
  <div class="card"><h2>历史总奖牌榜（前 15）</h2><div id="c1" class="chart"></div>
    <div class="note">小项口径，按金牌数排序。换行口径会让名次大幅变动，见「口径的魔力」。</div></div>

  <div class="card"><h2>奖牌膨胀：奖牌总数与代表团数</h2><div id="c2" class="chart"></div>
    <div class="note">2024 年奖牌总量是 1896 年的 3.46 倍，代表团数是 6.65 倍。</div></div>

  <div class="card"><h2>她的奥运：女性参赛占比</h2><div id="c3" class="chart"></div>
    <div class="note">运动员行口径。不是匀速上升，1952 / 1976 / 1996 三届出现明显阶跃。</div></div>

  <div class="card"><h2>口径的魔力：2024 金牌双口径</h2><div id="c4" class="chart"></div>
    <div class="note">同一数据集，去重键不同导致 USA 37→131、NED 14→67。与 IOC 官方数字存在差异。</div></div>

  <div class="card"><h2>国家兴衰：重点国家逐届奖牌</h2><div id="c5" class="chart"></div>
    <div class="note">小项口径。URS 仅 9 届即列历史第 2；GDR 仅 5 届；CHN 自 1932 年首现、1984 年后陡升。</div></div>

  <div class="card"><h2>东道主效应：主办届增益 vs 赛后回落</h2><div id="c6" class="chart"></div>
    <div class="note">29 位有可比数据的东道主中 26 位赛后下降，平均回落 29.2 枚。少数例外见报告表 7。</div></div>

  <div class="card" style="grid-column:1/-1"><h2>消失的运动：存续区间（记录数前 20）</h2>
    <div id="c7" class="chart" style="height:420px"></div>
    <div class="note">艺术竞赛 1912–1948 累积 3,578 条记录，是体量最大的「消失项目」；拔河 1900–1920。</div></div>
</div>

<footer>
  数据源：Kaggle <em>Summer Olympics Medals (1896-2024)</em>（CC BY-NC-SA 4.0），
  上游为 Olympics 124 years Dataset（till 2020）与 Paris 2024 Olympic Summer Games。
  本页所有数字由项目内 Python 脚本现算，复现方式见 README。
  口径说明见 <code>docs/02_数据质量与口径说明书.md</code>。
</footer>

<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<script>
const DATA = {json.dumps(payload, ensure_ascii=False)};
const C = {{ gold:'#C9A227', silver:'#9AA0A6', bronze:'#A9714B',
            accent:'#4C8DFF', warn:'#E0637A', ink:'#E8EDF2', muted:'#8FA0B2',
            line:'#25303D' }};
const AXIS = {{ axisLine:{{lineStyle:{{color:C.line}}}},
               axisLabel:{{color:C.muted, fontSize:11}},
               splitLine:{{lineStyle:{{color:C.line, opacity:.5}}}} }};
const charts = [];
function init(id, option) {{
  const el = document.getElementById(id);
  const c = echarts.init(el, null, {{renderer:'canvas'}});
  c.setOption(option); charts.push(c); return c;
}}
window.addEventListener('resize', () => charts.forEach(c => c.resize()));

// 1 历史总榜
init('c1', {{
  tooltip:{{trigger:'axis', axisPointer:{{type:'shadow'}}}},
  legend:{{top:0, textStyle:{{color:C.muted, fontSize:11}}}},
  grid:{{left:96, right:24, top:34, bottom:24}},
  xAxis:{{type:'value', ...AXIS}},
  yAxis:{{type:'category', data:DATA.history.teams.slice().reverse(), ...AXIS}},
  series:[
    {{name:'金', type:'bar', stack:'m', data:DATA.history.gold.slice().reverse(),
      itemStyle:{{color:C.gold}}}},
    {{name:'银', type:'bar', stack:'m', data:DATA.history.silver.slice().reverse(),
      itemStyle:{{color:C.silver}}}},
    {{name:'铜', type:'bar', stack:'m', data:DATA.history.bronze.slice().reverse(),
      itemStyle:{{color:C.bronze}}}}
  ]
}});

// 2 奖牌膨胀
init('c2', {{
  tooltip:{{trigger:'axis'}},
  legend:{{top:0, textStyle:{{color:C.muted, fontSize:11}}}},
  grid:{{left:56, right:56, top:34, bottom:32}},
  xAxis:{{type:'category', data:DATA.inflation.years, ...AXIS}},
  yAxis:[
    {{type:'value', name:'奖牌', ...AXIS, axisLabel:{{color:C.muted, fontSize:11}}}},
    {{type:'value', name:'代表团', ...AXIS, splitLine:{{show:false}},
      axisLabel:{{color:C.muted, fontSize:11}}}}
  ],
  series:[
    {{name:'奖牌总数', type:'line', smooth:true, data:DATA.inflation.medals,
      lineStyle:{{width:2.4, color:C.gold}}, itemStyle:{{color:C.gold}},
      areaStyle:{{color:'rgba(201,162,39,.14)'}}}},
    {{name:'代表团数', type:'line', yAxisIndex:1, smooth:true, data:DATA.inflation.nocs,
      lineStyle:{{width:2.2, color:C.accent}}, itemStyle:{{color:C.accent}}}}
  ]
}});

// 3 女性占比
init('c3', {{
  tooltip:{{trigger:'axis', valueFormatter:v=>v+'%'}},
  grid:{{left:56, right:24, top:30, bottom:32}},
  xAxis:{{type:'category', data:DATA.gender.years, ...AXIS}},
  yAxis:{{type:'value', max:55, ...AXIS, axisLabel:{{color:C.muted, fontSize:11, formatter:'{{value}}%'}}}},
  series:[{{name:'女性占比', type:'line', smooth:true, data:DATA.gender.ratio,
    lineStyle:{{width:2.6, color:C.warn}}, itemStyle:{{color:C.warn}},
    areaStyle:{{color:'rgba(224,99,122,.16)'}}}}]
}});

// 4 双口径
init('c4', {{
  tooltip:{{trigger:'axis', axisPointer:{{type:'shadow'}}}},
  legend:{{top:0, textStyle:{{color:C.muted, fontSize:11}}}},
  grid:{{left:56, right:24, top:34, bottom:32}},
  xAxis:{{type:'category', data:DATA.caliber.nocs, ...AXIS}},
  yAxis:{{type:'value', name:'金牌', ...AXIS}},
  series:[
    {{name:'小项口径', type:'bar', data:DATA.caliber.event, itemStyle:{{color:C.accent}}}},
    {{name:'运动员行口径', type:'bar', data:DATA.caliber.athlete, itemStyle:{{color:C.warn}}}}
  ]
}});

// 5 国家曲线
init('c5', {{
  tooltip:{{trigger:'axis'}},
  legend:{{top:0, type:'scroll', textStyle:{{color:C.muted, fontSize:11}}}},
  grid:{{left:56, right:24, top:48, bottom:32}},
  xAxis:{{type:'value', min:1896, max:2024, ...AXIS}},
  yAxis:{{type:'value', name:'奖牌', ...AXIS}},
  series: DATA.focus.series.map(function(s, i) {{
    var pal = ['#4C8DFF','#E0637A','#C9A227','#3FB98A','#A98BFF','#F0A05A','#2AA7B5','#D96FB0','#7C8B9C','#B8925A'];
    return {{name:s.name, type:'line', showSymbol:false, connectNulls:false,
             data:s.data, lineStyle:{{width:1.8, color:pal[i%10]}},
             itemStyle:{{color:pal[i%10]}}}};
  }})
}});

// 6 东道主
init('c6', {{
  tooltip:{{trigger:'axis', axisPointer:{{type:'shadow'}}}},
  legend:{{top:0, textStyle:{{color:C.muted, fontSize:11}}}},
  grid:{{left:96, right:24, top:34, bottom:32}},
  xAxis:{{type:'value', ...AXIS}},
  yAxis:{{type:'category', data:DATA.host.labels.slice().reverse(), ...AXIS}},
  series:[
    {{name:'主办届较上届增幅', type:'bar', data:DATA.host.gain.slice().reverse(),
      itemStyle:{{color:C.accent}}}},
    {{name:'赛后回落', type:'scatter', symbolSize:9,
      data:DATA.host.back.slice().reverse(), itemStyle:{{color:C.warn}}}}
  ]
}});

// 7 项目生命周期
init('c7', {{
  tooltip:{{trigger:'item', formatter:p => {{
    const d = DATA.life[p.dataIndex];
    return d.Sport + '<br/>首次 ' + d.首次 + ' · 末次 ' + d.末次 +
           '<br/>记录数 ' + d.记录数 + (d.已消失 ? '<br/><span style="color:#E0637A">已消失</span>' : '');
  }}}},
  grid:{{left:150, right:40, top:20, bottom:50}},
  xAxis:{{type:'value', min:1896, max:2030, ...AXIS, name:'年份'}},
  yAxis:{{type:'category', data:DATA.life.map(d=>d.Sport).reverse(), ...AXIS}},
  series:[
    {{name:'起点', type:'bar', stack:'life',
      data:DATA.life.map(d=>d.首次).reverse(), itemStyle:{{color:'transparent'}}}},
    {{name:'存续', type:'bar', stack:'life',
      data:DATA.life.map(d=>Math.max(d.末次-d.首次, 2)).reverse(),
      itemStyle:{{color:C.bronze}}}}
  ]
}});
</script>
</body>
</html>
"""
    out = ROOT / "dashboard.html"
    out.write_text(body, encoding="utf-8")
    return out


def main() -> list[Path]:
    """入口：依次生成全部静态图与 Dashboard，返回产物路径列表。"""
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    makers = [
        fig01_medal_inflation, fig02_history_ranking, fig03_country_curves,
        fig04_female_arc, fig05_sport_lifecycle, fig06_caliber_compare,
        fig07_rank_shift, fig08_host_effect, fig09_concentration,
        fig10_supply_vs_demand,
    ]
    out: list[Path] = []
    for m in makers:
        p = m()
        if p.exists() and p.stat().st_size > 0:
            out.append(p)
            print(f"[visualize] {p.name} ({p.stat().st_size} bytes)")
        else:
            print(f"[visualize] 跳过 {m.__name__}（数据缺失）")
    dash = build_dashboard()
    out.append(dash)
    print(f"[visualize] {dash.name} ({dash.stat().st_size} bytes)")
    return out


if __name__ == "__main__":
    main()
