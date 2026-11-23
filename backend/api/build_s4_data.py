"""
构建 S4 专题看板数据
====================
职责：读取 `outputs/task3_s4/` 下的分析产物，聚合成前端直接消费的 `s4.json`。
调用：python backend/api/build_s4_data.py
产物：backend/api/data/s4.json

口径
----
- 主口径：小项口径（17,901 枚）
- 对照口径：运动员行口径（38,360 枚）
- 小团主阈值：参赛人数 ≤ 50；近代样本：1980 年及以后
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
S4 = ROOT / "outputs" / "task3_s4"
TABLES = S4 / "tables"
OUT_JSON = Path(__file__).resolve().parent / "data" / "s4.json"

SMALL_THRESHOLD = 50
MODERN_FROM = 1980


def to_float(value) -> float | None:
    """空值 / nan / None 统一转 None，其余转 float。"""
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "null"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def to_int(value, default=None):
    number = to_float(value)
    return default if number is None else int(round(number))


def to_bool(value) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def read_table(name: str) -> list[dict]:
    path = TABLES / name
    if not path.exists():
        print(f"  ! 缺少表 {path.relative_to(ROOT)}，跳过")
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path) -> dict:
    if not path.exists():
        print(f"  ! 缺少文件 {path.relative_to(ROOT)}，跳过")
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_size_distribution() -> list[dict]:
    rows = []
    for r in read_table("a_size_distribution.csv"):
        rows.append({
            "sizeClass": r["size_class"],
            "era": r["era"],
            "editions": to_int(r["n_noc_editions"], 0),
            "withMedal": to_int(r["n_with_medal"], 0),
            "medalRate": to_float(r["medal_rate"]),
            "gold": to_int(r["gold"], 0),
            "silver": to_int(r["silver"], 0),
            "bronze": to_int(r["bronze"], 0),
            "totalMedal": to_int(r["total_medal"], 0),
            "medalShare": to_float(r["medal_share_of_total"]),
            "medianAthletes": to_float(r["median_athletes"])
        })
    return rows


def build_size_class_by_year() -> list[dict]:
    rows = []
    for r in read_table("a_size_class_by_year.csv"):
        rows.append({
            "year": to_int(r["Year"]),
            "sizeClass": r["size_class"],
            "editions": to_int(r["n"], 0),
            "withMedal": to_int(r["n_with_medal"], 0),
            "totalMedal": to_int(r["total_medal"], 0),
            "medalRate": to_float(r["medal_rate"])
        })
    return rows


def build_small_rate_by_year() -> list[dict]:
    rows = []
    for r in read_table("a_small_medal_rate_by_year.csv"):
        rows.append({
            "year": to_int(r["Year"]),
            "smallN": to_int(r["small_n"], 0),
            "smallMedalN": to_int(r["small_medal_n"], 0),
            "smallMedal": to_int(r["small_medal"], 0),
            "smallAthletes": to_int(r["small_athletes"], 0),
            "bigN": to_int(r["big_n"], 0),
            "bigMedalN": to_int(r["big_medal_n"], 0),
            "smallMedalRate": to_float(r["small_medal_rate"]),
            "bigMedalRate": to_float(r["big_medal_rate"]),
            "rateGap": to_float(r["rate_gap_small_minus_big"]),
            "totalNoc": to_int(r["total_noc"], 0),
            "smallShareOfNoc": to_float(r["small_share_of_noc"]),
            "smallMedalShare": to_float(r["small_medal_share"])
        })
    return rows


def build_efficiency() -> list[dict]:
    rows = []
    for r in read_table("b_efficiency_vs_size.csv"):
        rows.append({
            "bin": r["size_bin"],
            "editions": to_int(r["n_noc_editions_in_bin"], 0),
            "withMedal": to_int(r["n_with_medal"], 0),
            "mpaMedian": to_float(r["mpa_median"]),
            "mpaMean": to_float(r["mpa_mean"]),
            "ciLow": to_float(r["ci95_low"]),
            "ciHigh": to_float(r["ci95_high"])
        })
    return rows


def build_strategy(name: str) -> list[dict]:
    rows = []
    for r in read_table(name):
        rows.append({
            "sizeClass": r["size_class"],
            "withMedal": to_int(r["n_editions_with_medal"], 0),
            "mpaMedian": to_float(r["mpa_median"]),
            "mpaMean": to_float(r["mpa_mean"]),
            "top1ShareMedian": to_float(r["top1_share_median"]),
            "nSportsMedian": to_float(r["n_sports_medal_median"]),
            "hhiMedian": to_float(r["hhi_median"]),
            "totalMedalMedian": to_float(r["total_event_median"]),
            "athletesMedian": to_float(r["athletes_median"])
        })
    return rows


def build_scatter() -> list[dict]:
    rows = []
    for r in read_table("b_concentration_scatter.csv"):
        rows.append({
            "year": to_int(r["Year"]),
            "noc": r["NOC"],
            "team": r["Team"],
            "athletes": to_int(r["athletes"], 0),
            "total": to_int(r["Total_event"], 0),
            "mpa": to_float(r["medal_per_athlete"]),
            "top1Share": to_float(r["top1_share"]),
            "nSports": to_float(r["n_sports_medal"]),
            "hhi": to_float(r["hhi"]),
            "topSport": r["top_sport"],
            "sizeClass": r["size_class"],
            "named": to_bool(r["is_named_case"]),
            "extra": to_bool(r["is_extra_case"]),
            "bigReference": to_bool(r["is_big_reference"])
        })
    return rows


def build_case_countries() -> list[dict]:
    rows = []
    for r in read_table("c_case_countries.csv"):
        rows.append({
            "noc": r["NOC"],
            "team": r["Team"],
            "firstOlympicYear": to_int(r["first_olympic_year"]),
            "firstMedalYear": to_int(r["first_medal_year"]),
            "firstGoldYear": to_int(r["first_gold_year"]),
            "appearances": to_int(r["n_appearances"], 0),
            "medalEditions": to_int(r["n_medal_editions"], 0),
            "medalEditionRate": to_float(r["medal_edition_rate"]),
            "totalMedal": to_int(r["total_medal_event"], 0),
            "totalGold": to_int(r["total_gold_event"], 0),
            "maxMedalSingleEdition": to_int(r["max_medal_single_edition"], 0),
            "maxAthletes": to_int(r["max_athletes_single_edition"], 0),
            "medianAthletes": to_float(r["median_athletes"]),
            "topSports": r["top3_sports_with_medals"],
            "nMedalSports": to_int(r["n_medal_sports_total"], 0)
        })
    return rows


def build_case_sports() -> list[dict]:
    rows = []
    for r in read_table("c_case_medal_by_sport.csv"):
        rows.append({
            "noc": r["NOC"],
            "sport": r["Sport"],
            "total": to_int(r["Total"], 0),
            "team": r["Team"],
            "rank": to_float(r["rank_in_noc"])
        })
    return rows


def build_case_detail(name: str) -> list[dict]:
    rows = []
    for r in read_table(name):
        rows.append({
            "year": to_int(r["Year"]),
            "noc": r["NOC"],
            "athletes": to_int(r["athletes"], 0),
            "sports": to_int(r["sports"], 0),
            "events": to_int(r["events"], 0),
            "gold": to_int(r["Gold_event"], 0),
            "silver": to_int(r["Silver_event"], 0),
            "bronze": to_int(r["Bronze_event"], 0),
            "total": to_int(r["Total_event"], 0),
            "nSportsMedal": to_float(r["n_sports_medal"]),
            "topSport": r["top_sport"],
            "top1Share": to_float(r["top1_share"]),
            "medalSports": r["medal_sport_list"],
            "hasMedal": to_bool(r["has_medal_event"])
        })
    return rows


def build_persistence() -> list[dict]:
    rows = []
    for r in read_table("d_persistence.csv"):
        rows.append({
            "noc": r["NOC"],
            "team": r["Team"],
            "firstMedalYear": to_int(r["first_medal_year"]),
            "secondMedalYear": to_int(r["second_medal_year"]),
            "appearances": to_int(r["n_appear"], 0),
            "medalEditions": to_int(r["n_medal_editions"], 0),
            "postRate": to_float(r["post_first_medal_rate"]),
            "maxStreak": to_int(r["max_streak"], 0),
            "totalMedal": to_int(r["total_medal_event"], 0),
            "maxAthletes": to_int(r["max_athletes"], 0),
            "medianAthletes": to_float(r["median_athletes"]),
            "teamType": r["team_type"]
        })
    return rows


def build_streak_by_type() -> list[dict]:
    rows = []
    for r in read_table("d_streak_by_type.csv"):
        rows.append({
            "teamType": r["team_type"],
            "nNoc": to_int(r["n_noc"], 0),
            "postRateMedian": to_float(r["post_rate_median"]),
            "postRateMean": to_float(r["post_rate_mean"]),
            "postRateP25": to_float(r["post_rate_p25"]),
            "postRateP75": to_float(r["post_rate_p75"]),
            "maxStreakMedian": to_float(r["max_streak_median"]),
            "medalEditionsMedian": to_float(r["n_medal_editions_median"]),
            "totalMedalMedian": to_float(r["total_medal_median"])
        })
    return rows


def build_one_hit() -> list[dict]:
    rows = []
    for r in read_table("d_one_hit_wonders.csv"):
        rows.append({
            "noc": r["NOC"],
            "team": r["Team"],
            "firstMedalYear": to_int(r["first_medal_year"]),
            "appearances": to_int(r["n_appear"], 0),
            "maxAthletes": to_int(r["max_athletes"], 0),
            "medianAthletes": to_float(r["median_athletes"]),
            "totalMedal": to_int(r["total_medal_event"], 0),
            "teamType": r["team_type"]
        })
    return rows


def build_threshold_sensitivity() -> list[dict]:
    rows = []
    for r in read_table("e_threshold_sensitivity.csv"):
        rows.append({
            "threshold": to_int(r["threshold"]),
            "smallEditions": to_int(r["n_small_editions"], 0),
            "bigEditions": to_int(r["n_big_editions"], 0),
            "smallMedalRate": to_float(r["small_medal_rate"]),
            "bigMedalRate": to_float(r["big_medal_rate"]),
            "rateGap": to_float(r["rate_gap"]),
            "smallMpaMedian": to_float(r["small_mpa_median"]),
            "bigMpaMedian": to_float(r["big_mpa_median"]),
            "mpaP": to_float(r["mpa_mwu_p"]),
            "mpaEffectR": to_float(r["mpa_effect_r"]),
            "smallTop1Median": to_float(r["small_top1_share_median"]),
            "bigTop1Median": to_float(r["big_top1_share_median"]),
            "top1EffectR": to_float(r["top1_share_effect_r"]),
            "smallNSportsMedian": to_float(r["small_n_sports_median"]),
            "bigNSportsMedian": to_float(r["big_n_sports_median"]),
            "nSportsEffectR": to_float(r["n_sports_effect_r"])
        })
    return rows


def build_caliber_sensitivity() -> list[dict]:
    rows = []
    for r in read_table("e_caliber_sensitivity.csv"):
        rows.append({
            "sample": r["sample"],
            "caliber": r["caliber"],
            "nSmall": to_int(r["n_small_le50"], 0),
            "nBig": to_int(r["n_big_gt150"], 0),
            "smallMpaMedian": to_float(r["small_mpa_median"]),
            "bigMpaMedian": to_float(r["big_mpa_median"]),
            "p": to_float(r["mwu_p"]),
            "effectR": to_float(r["effect_r"]),
            "direction": r["direction"],
            "totalMedal": to_int(r["total_medal_sum_in_sample"], 0)
        })
    return rows


def build_small_rise() -> list[dict]:
    rows = []
    for r in read_table("f_small_rise.csv"):
        rows.append({
            "year": to_int(r["Year"]),
            "nocCount": to_int(r["n_noc"], 0),
            "smallCount": to_int(r["n_small"], 0),
            "smallShareOfNoc": to_float(r["small_share_of_noc"]),
            "smallMedal": to_int(r["small_medal"], 0),
            "totalMedal": to_int(r["total_medal"], 0),
            "smallMedalShare": to_float(r["small_medal_share"]),
            "medalNocCount": to_int(r["n_medal_noc"], 0),
            "smallMedalNocCount": to_int(r["n_medal_noc_small"], 0),
            "smallMedalNocShare": to_float(r["small_medal_noc_share"]),
            "smallAthletes": to_int(r["small_athletes"], 0),
            "smallAthleteShare": to_float(r["small_athlete_share"])
        })
    return rows


def build_share_trend_by_threshold() -> list[dict]:
    rows = []
    for r in read_table("f_share_trend_by_threshold.csv"):
        rows.append({
            "threshold": to_int(r["threshold"]),
            "year": to_int(r["Year"]),
            "smallNoc": to_int(r["small_noc"], 0),
            "smallMedal": to_int(r["small_medal"], 0),
            "totalMedal": to_int(r["total_medal"], 0),
            "share": to_float(r["small_medal_share"])
        })
    return rows


def build_small_noc_board() -> list[dict]:
    """从基础表计算小团型国家（历史峰值参赛 ≤50）的历史奖牌榜前 15。"""
    path = S4 / "s4_base.csv"
    if not path.exists():
        return []
    peak: dict[str, int] = {}
    team: dict[str, str] = {}
    total: dict[str, int] = {}
    gold: dict[str, int] = {}
    editions: dict[str, set] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            noc = row["NOC"]
            athletes = to_int(row["athletes"], 0)
            peak[noc] = max(peak.get(noc, 0), athletes)
            team.setdefault(noc, row["Team"])
            total[noc] = total.get(noc, 0) + to_int(row["Total_event"], 0)
            gold[noc] = gold.get(noc, 0) + to_int(row["Gold_event"], 0)
            editions.setdefault(noc, set()).add(row["Year"])
    rows = [
        {
            "noc": noc,
            "team": team.get(noc, noc),
            "total": total.get(noc, 0),
            "gold": gold.get(noc, 0),
            "peakAthletes": peak[noc],
            "editions": len(editions.get(noc, set()))
        }
        for noc in peak
        if peak[noc] <= SMALL_THRESHOLD and total.get(noc, 0) > 0
    ]
    rows.sort(key=lambda item: (-item["total"], -item["gold"], item["team"]))
    return rows[:15]


def build_kpi(analysis: dict) -> dict:
    panorama = analysis.get("A_panorama", {})
    tiny = panorama.get("tiny_teams_with_medal", {})
    strategy = analysis.get("B_strategy", {})
    persistence = analysis.get("D_persistence", {})
    trend = analysis.get("F_trend", {}).get("trend_verdict", {})
    single = strategy.get("single_sport_dependence", {})
    overview = persistence.get("persistence_overview", {})
    by_type = {row["teamType"]: row for row in build_streak_by_type()}
    micro = next(
        (row for row in build_size_distribution()
         if row["sizeClass"] == "微型(≤10)" and row["era"] == "近代(1980+)"),
        {}
    )
    return {
        "microModernRate": micro.get("medalRate"),
        "microModernEditions": micro.get("editions"),
        "microModernWithMedal": micro.get("withMedal"),
        "tinyCases": tiny.get("n_cases"),
        "tinyRate": tiny.get("rate"),
        "tinyEditions": tiny.get("n_editions_athletes_le5"),
        "singleSportShare": single.get("small_le50_share_top1_eq_1"),
        "singleSportBigShare": single.get("big_gt150_share_top1_eq_1"),
        "smallPostMedian": by_type.get("小团型(峰值≤50)", {}).get("postRateMedian"),
        "bigPostMedian": by_type.get("大团型(峰值>50)", {}).get("postRateMedian"),
        "smallShare1980": trend.get("small_medal_share_1980"),
        "smallShare2024": trend.get("small_medal_share_2024"),
        "oneHitShare": overview.get("share_never_medal_again"),
        "oneHitCount": overview.get("n_never_medal_again"),
        "medalNations": overview.get("n_noc_ever_medal")
    }


def main() -> int:
    if not S4.exists():
        raise SystemExit(f"找不到 Task3 S4 产物目录：{S4}")

    analysis = load_json(S4 / "s4_results.json")
    verification = load_json(S4 / "s4_verification.json")

    payload = {
        "meta": {
            "title": "小代表团的大突破",
            "subtitle": "规模约束下的夺牌机制、可持续性与口径边界",
            "source": "olympics_dataset.csv · 1896–2024 夏季奥运会",
            "primaryCaliber": "小项口径（17,901 枚）",
            "referenceCaliber": "运动员行口径（38,360 枚）",
            "smallThreshold": SMALL_THRESHOLD,
            "modernFrom": MODERN_FROM,
            "thresholds": [10, 25, 50, 100, 150],
            "excludedYears": analysis.get("meta", {}).get("excluded_years", [1906]),
            "bootstrap": analysis.get("meta", {}).get("bootstrap", {}),
            "tests": analysis.get("meta", {}).get("tests", "")
        },
        "kpi": build_kpi(analysis),
        "sizeDistribution": build_size_distribution(),
        "sizeClassByYear": build_size_class_by_year(),
        "smallRateByYear": build_small_rate_by_year(),
        "efficiency": build_efficiency(),
        "strategyBySize": build_strategy("b_strategy_by_size.csv"),
        "strategyBySizeModern": build_strategy("b_strategy_by_size_modern.csv"),
        "scatter": build_scatter(),
        "caseCountries": build_case_countries(),
        "caseSports": build_case_sports(),
        "caseDetail": {
            "HKG": build_case_detail("c_hkg_detail.csv"),
            "SGP": build_case_detail("c_sgp_detail.csv"),
            "TPE": build_case_detail("c_tpe_detail.csv")
        },
        "persistence": {
            "detail": build_persistence(),
            "byType": build_streak_by_type(),
            "oneHit": build_one_hit()
        },
        "smallNocBoard": build_small_noc_board(),
        "structure": {
            "series": build_small_rise(),
            "trend": analysis.get("F_trend", {})
        },
        "sensitivity": {
            "threshold": build_threshold_sensitivity(),
            "caliber": build_caliber_sensitivity(),
            "shareTrendByThreshold": build_share_trend_by_threshold(),
            "verdict": analysis.get("E_sensitivity", {}).get("threshold_robustness_verdict", {}),
            "caliberVerdict": analysis.get("E_sensitivity", {}).get("caliber_verdict", {})
        },
        "analysis": analysis,
        "verification": verification.get("checks", [])
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        encoding="utf-8"
    )

    size_kb = OUT_JSON.stat().st_size / 1024
    print(f"✓ 写入 {OUT_JSON.relative_to(ROOT)}（{size_kb:.1f} KB）")
    print(f"  规模分布 {len(payload['sizeDistribution'])} 行 / 散点 {len(payload['scatter'])} 点 / "
          f"个案 {len(payload['caseCountries'])} 国 / 持续性 {len(payload['persistence']['detail'])} 国")
    print(f"  阈值敏感性 {len(payload['sensitivity']['threshold'])} 档 / "
          f"口径敏感性 {len(payload['sensitivity']['caliber'])} 组 / 校验 {len(payload['verification'])} 项")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
