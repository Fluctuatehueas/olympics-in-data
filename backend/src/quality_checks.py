"""
奥运数据集质量检查脚本（QC1–QC6）
=====================================
职责
----
只做「体检」，不改数据：对原始 olympics_dataset.csv 执行 6 项可复现检查，
把结果写成 Markdown 表格，供《数据质量与口径说明书》引用。

调用关系
--------
- 上游调用方：本脚本由 `src/run_all.py` 在清洗之前调用（`python src/quality_checks.py` 可单独跑）。
- 下游被调用方：只依赖 pandas，不 import 本项目其他模块；输出文件被
  `docs/02_数据质量与口径说明书.md` 与 `docs/03_分析报告.md` 引用。
- 并发/线程：单进程单线程，纯 pandas 向量化操作，无共享状态，可在 run_all 中串行执行。

输出
----
outputs/tables/quality_checks.md
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# 路径常量：以项目根为基准，保证从任意工作目录调用都能定位文件。
# 调用方（run_all.py）无需传参，直接调用 main()。
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
RAW_CSV = ROOT / "olympics_dataset.csv"
OUT_DIR = ROOT / "outputs" / "tables"

# 2020 起数据源切换后 Event 字段出现的泛化取值集合（见口径说明书第四节 Q3）
GENERIC_EVENTS = {
    "Men", "Women", "Men Team", "Women Team", "Mixed Team",
    "Relay Only Athlete", "Mixed", "Open",
}


def load_raw() -> pd.DataFrame:
    """读取原始 CSV。编码固定 UTF-8（已核验无 BOM），不做任何类型转换以免失真。"""
    if not RAW_CSV.exists():
        raise FileNotFoundError(f"原始数据不存在: {RAW_CSV}")
    return pd.read_csv(RAW_CSV, encoding="utf-8")


def qc1_medal_imbalance(df: pd.DataFrame) -> dict:
    """QC1：金/银/铜数量是否相等。

    天真假设是三者相等；实际因早期无铜牌、并列奖牌、走跑夺冠而不等。
    返回各颜色计数与差额，供报告解释。
    """
    medals = df[df["Medal"] != "No medal"]
    counts = medals["Medal"].value_counts()
    return {
        "检查项": "QC1 奖牌颜色不均衡",
        "方法": "统计 Gold/Silver/Bronze 行数并比较差额",
        "Gold": int(counts.get("Gold", 0)),
        "Silver": int(counts.get("Silver", 0)),
        "Bronze": int(counts.get("Bronze", 0)),
        "结论": (
            f"金-银差 {int(counts.get('Gold',0)) - int(counts.get('Silver',0))}，"
            f"银-铜差 {int(counts.get('Silver',0)) - int(counts.get('Bronze',0))}；"
            "并非相等，需用『早期无铜牌 / 并列奖牌 / 走跑夺冠』解释"
        ),
    }


def qc2_team_medal_inflation(df: pd.DataFrame) -> dict:
    """QC2：团体项目导致同一小项奖牌出现多行。

    按 (Year, Event, Medal) 分组计数，统计组内行数 > 1 的规模，
    这是奖牌双口径差异的直接来源。
    """
    medals = df[df["Medal"] != "No medal"]
    grouped = medals.groupby(["Year", "Event", "Medal"], dropna=False).size()
    multi = grouped[grouped > 1]
    return {
        "检查项": "QC2 团体项目奖牌膨胀",
        "方法": "按 (Year, Event, Medal) 分组计数，统计组内行数 >1 的组",
        "多行组数": int(multi.shape[0]),
        "涉及行数": int(multi.sum()),
        "单组最大行数": int(multi.max()) if len(multi) else 0,
        "结论": (
            f"{int(multi.shape[0])} 组出现同届同项同色多行，覆盖 {int(multi.sum())} 行，"
            "单组最多 " + str(int(multi.max()) if len(multi) else 0) +
            " 行；不做去重会把团体项目奖牌放大数倍"
        ),
    }


def qc3_single_medal_events(df: pd.DataFrame) -> dict:
    """QC3：只颁发了一种奖牌的小项。

    正常小项应有金/银/铜三种；少于三种说明存在走跑夺冠、取消银铜牌等历史特例。
    """
    medals = df[df["Medal"] != "No medal"]
    colors_per_event = medals.groupby(["Year", "Event"], dropna=False)["Medal"].nunique()
    single = colors_per_event[colors_per_event < 3]
    return {
        "检查项": "QC3 只发一种奖牌的小项",
        "方法": "按 (Year, Event) 统计奖牌颜色种类数，筛 <3 的组",
        "小项数": int(single.shape[0]),
        "结论": (
            f"{int(single.shape[0])} 个小项未发满三色奖牌，"
            "典型如 1908 男子 400 米走跑夺冠（仅金牌）"
        ),
    }


def qc4_sport_drift(df: pd.DataFrame) -> dict:
    """QC4：Sport 大类名称在 2020 年前后漂移。

    检查同一运动是否出现「旧名只在前段、新名只在后段」的共存现象。
    """
    pairs = [
        ("Gymnastics", ["Artistic Gymnastics", "Rhythmic Gymnastics", "Trampoline Gymnastics"]),
        ("Cycling", ["Cycling Road", "Cycling Track", "Cycling Mountain Bike",
                     "Cycling BMX Racing", "Cycling BMX Freestyle"]),
        ("Canoeing", ["Canoe Sprint", "Canoe Slalom"]),
        ("Equestrianism", ["Equestrian"]),
        ("Synchronized Swimming", ["Artistic Swimming"]),
        ("Basketball", ["3x3 Basketball"]),
        ("Swimming", ["Marathon Swimming"]),
    ]
    details = []
    for old, news in pairs:
        old_years = df.loc[df["Sport"] == old, "Year"]
        row = {"旧名": old,
               "旧名年份区间": f"{int(old_years.min())}-{int(old_years.max())}" if len(old_years) else "无"}
        for n in news:
            sub = df[df["Sport"] == n]
            row[n] = f"{int(sub['Year'].min())}-{int(sub['Year'].max())} ({len(sub)}行)" if len(sub) else "无"
        details.append(row)
    comma_rows = int(df["Sport"].fillna("").str.contains(",").sum())
    return {
        "检查项": "QC4 Sport 名称漂移",
        "方法": "对比新旧名称各自的年份覆盖区间，并统计逗号拼接行",
        "逗号拼接行数": comma_rows,
        "明细": details,
        "结论": (
            f"{len(pairs)} 组运动存在新旧名并存，另有 {comma_rows} 行 Sport 为逗号拼接跨项写法；"
            "做按运动统计前必须归一"
        ),
    }


def qc5_event_generic(df: pd.DataFrame) -> dict:
    """QC5：2020 起 Event 泛化比例。

    统计近两届中 Event 落在泛化集合内的行数占比，是口径降维的直接依据。
    """
    recent = df[df["Year"].isin([2020, 2024])]
    generic = recent[recent["Event"].isin(GENERIC_EVENTS)]
    ratio = len(generic) / len(recent) if len(recent) else 0.0
    top = generic["Event"].value_counts().head(5).to_dict()
    return {
        "检查项": "QC5 Event 泛化比例",
        "方法": "统计 2020/2024 两届中 Event ∈ 泛化集合的行数占比",
        "近两届行数": int(len(recent)),
        "泛化行数": int(len(generic)),
        "占比": f"{ratio:.2%}",
        "Top泛化值": ", ".join(f"{k}={v}" for k, v in top.items()),
        "结论": f"近两届 {ratio:.2%} 的行无法还原具体小项，小项统计需降维并加注",
    }


def qc6_name_ambiguity(df: pd.DataFrame) -> dict:
    """QC6：姓名歧义（同名跨年份跨度过大）。"""
    span = df.groupby("Name")["Year"].agg(["min", "max", "size"])
    span["span"] = span["max"] - span["min"]
    suspicious = span[span["span"] > 50].sort_values("span", ascending=False)
    pid_per_name = df.groupby("Name")["player_id"].nunique()
    single_id_ratio = float((pid_per_name == 1).mean())
    return {
        "检查项": "QC6 姓名歧义",
        "方法": "统计同名记录的最早/最晚年份跨度，筛 >50 年者；并算 player_id 平均频次",
        "player_id平均频次": f"{len(df) / df['player_id'].nunique():.2f}",
        "同名跨度>50年的人数": int(suspicious.shape[0]),
        "Top示例": ", ".join(
            f"{name}({int(r['min'])}-{int(r['max'])}, {int(r['size'])}行)"
            for name, r in suspicious.head(5).iterrows()
        ) or "无",
        "结论": (
            f"{int(suspicious.shape[0])} 个姓名跨越 50 年以上，显然是多个人被并到同一字符串；"
            "个体粒度分析不可靠，本项目主结论落在代表团层级"
        ),
    }


def to_markdown(checks: list[dict]) -> str:
    """把 6 项检查结果渲染成 Markdown。明细型结果（QC4）单独成表。"""
    lines = ["# 数据质量检查结果（QC1–QC6）", "",
             "> 由 `backend/src/quality_checks.py` 自动生成，可复现。", ""]
    for c in checks:
        lines.append(f"## {c['检查项']}")
        lines.append("")
        lines.append(f"- **方法**：{c['方法']}")
        for k, v in c.items():
            if k in ("检查项", "方法", "结论", "明细"):
                continue
            lines.append(f"- **{k}**：{v}")
        lines.append(f"- **结论**：{c['结论']}")
        lines.append("")
        if "明细" in c:
            # 各组新名数量不一致（体操 3 个、自行车 5 个），用列表渲染避免表格列错位
            lines.append("**明细**：")
            lines.append("")
            for row in c["明细"]:
                old_name = row["旧名"]
                old_span = row["旧名年份区间"]
                new_items = [f"`{k}` {v}" for k, v in row.items()
                             if k not in ("旧名", "旧名年份区间")]
                lines.append(f"- **{old_name}**（{old_span}）→ " + "；".join(new_items))
            lines.append("")
    return "\n".join(lines)


def main() -> Path:
    """入口：读取原始数据 → 跑 6 项检查 → 落盘 Markdown。返回输出路径供调用方校验。"""
    df = load_raw()
    checks = [
        qc1_medal_imbalance(df),
        qc2_team_medal_inflation(df),
        qc3_single_medal_events(df),
        qc4_sport_drift(df),
        qc5_event_generic(df),
        qc6_name_ambiguity(df),
    ]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "quality_checks.md"
    out.write_text(to_markdown(checks), encoding="utf-8")
    print(f"[quality_checks] 已写出 {out}")

    # 同时落一份机器可读的 JSON，便于 run_all 汇总时不用再解析 Markdown
    import json
    (OUT_DIR / "quality_checks.json").write_text(
        json.dumps(checks, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    return out


if __name__ == "__main__":
    main()
