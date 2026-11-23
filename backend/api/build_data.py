"""
构建看板 JSON 数据底座
======================
职责：把原始 CSV 与 outputs/tables 下已有分析表聚合成前端直接消费的 dashboard.json。
调用：python backend/api/build_data.py
产物：backend/api/data/dashboard.json

口径
----
- 一行 = 一名运动员 x 一届 x 一个小项（团体项目每人一行）
- 运动员行口径：每条奖牌记录计 1 枚
- 小项口径：按 (Year, Event, Medal, NOC) 去重
- 1906 届间奥运会默认排除
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_CSV = ROOT / "olympics_dataset.csv"
TABLES = ROOT / "outputs" / "tables"
TASK1 = ROOT / "docs" / "Task1"
OUT_JSON = Path(__file__).resolve().parent / "data" / "dashboard.json"

EXCLUDE_YEARS = {1906}

# 2020 起数据源切换后出现的泛化 Event 取值（与 backend/src/cleaning.py 保持一致）
GENERIC_EVENTS = {
    "Men", "Women", "Men Team", "Women Team", "Mixed Team",
    "Relay Only Athlete", "Mixed", "Open",
}

MEDAL_COLORS = {"Gold": "gold", "Silver": "silver", "Bronze": "bronze"}


def load_sport_mapping() -> dict[str, str]:
    """读取任务一的 Sport 归一映射表，保证前端与清洗口径完全一致。"""
    path = TASK1 / "sport_mapping.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row["原始Sport"]: row["归一Sport"] for row in csv.DictReader(handle)}


SPORT_MAPPING = load_sport_mapping()


def sport_of(raw: str) -> str:
    """归一体育大类；映射表缺失时退化为「取逗号前首项」。"""
    return SPORT_MAPPING.get(raw) or str(raw).split(",")[0].strip()


def to_float(value):
    """把 CSV 里的空值 / nan / None 统一转成 None，其余转 float。"""
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "null"}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return None if math.isnan(number) else number


def to_int(value, default=0):
    number = to_float(value)
    return default if number is None else int(round(number))


def to_bool(value):
    return str(value).strip().lower() in {"true", "1", "yes"}


def read_table(name: str) -> list[dict]:
    """读取 outputs/tables 下的 CSV，使用 utf-8-sig 兼容 BOM。"""
    path = TABLES / name
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def new_year_bucket() -> dict:
    return {
        "rows": 0,
        "female": 0,
        "genericRows": 0,
        "nocs": set(),
        "events": set(),
        "teams": set(),
        "sports": set(),
        "goldEvent": 0,
        "silverEvent": 0,
        "bronzeEvent": 0,
        "goldAthlete": 0,
        "silverAthlete": 0,
        "bronzeAthlete": 0,
        # 女性奖牌（供性别口径弧线使用）
        "femaleGoldEvent": 0,
        "femaleSilverEvent": 0,
        "femaleBronzeEvent": 0,
        "femaleGoldAthlete": 0,
        "femaleSilverAthlete": 0,
        "femaleBronzeAthlete": 0,
    }


def new_country_bucket(year: int, noc: str, team: str) -> dict:
    return {
        "year": year,
        "noc": noc,
        "team": team,
        "records": 0,
        "female": 0,
        "goldEvent": 0,
        "silverEvent": 0,
        "bronzeEvent": 0,
        "goldAthlete": 0,
        "silverAthlete": 0,
        "bronzeAthlete": 0,
    }


def new_team_bucket(noc: str, team: str) -> dict:
    """团队粒度：Team 字段去重后的一支队伍（含 China-1、帆船船名等）。"""
    return {
        "noc": noc,
        "team": team,
        "years": set(),
        "records": 0,
        "female": 0,
        "goldEvent": 0,
        "silverEvent": 0,
        "bronzeEvent": 0,
        "goldAthlete": 0,
        "silverAthlete": 0,
        "bronzeAthlete": 0,
    }


def new_sport_bucket() -> dict:
    return {
        "years": set(),
        "records": 0,
        "female": 0,
        "goldEvent": 0,
        "silverEvent": 0,
        "bronzeEvent": 0,
        "goldAthlete": 0,
        "silverAthlete": 0,
        "bronzeAthlete": 0,
    }


def aggregate_raw() -> tuple[dict, dict, dict, dict, set]:
    """一次扫描原始 CSV，同时产出届次 / 代表团 / 团队 / 运动四套聚合。"""
    years: dict[int, dict] = {}
    countries: dict[tuple[int, str], dict] = {}
    teams: dict[tuple[str, str], dict] = {}
    sports: dict[str, dict] = {}
    sport_years: dict[tuple[int, str], dict] = {}
    all_nocs: set[str] = set()
    event_keys: set[tuple] = set()
    team_event_keys: set[tuple] = set()

    with RAW_CSV.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            year = to_int(row["Year"])
            if year in EXCLUDE_YEARS:
                continue
            noc = row["NOC"]
            team = row["Team"]
            event = row["Event"]
            medal = row["Medal"]
            sport = sport_of(row["Sport"])
            all_nocs.add(noc)

            y = years.setdefault(year, new_year_bucket())
            c = countries.setdefault((year, noc), new_country_bucket(year, noc, team))
            t = teams.setdefault((noc, team), new_team_bucket(noc, team))
            s = sports.setdefault(sport, new_sport_bucket())
            sy = sport_years.setdefault((year, sport), {"records": 0, "goldEvent": 0, "silverEvent": 0, "bronzeEvent": 0, "female": 0})

            y["rows"] += 1
            y["nocs"].add(noc)
            y["events"].add(event)
            y["teams"].add(team)
            y["sports"].add(sport)
            c["records"] += 1
            t["years"].add(year)
            t["records"] += 1
            s["years"].add(year)
            s["records"] += 1
            sy["records"] += 1

            if row["Sex"] == "F":
                y["female"] += 1
                c["female"] += 1
                t["female"] += 1
                s["female"] += 1
                sy["female"] += 1
            if event in GENERIC_EVENTS:
                y["genericRows"] += 1

            color = MEDAL_COLORS.get(medal)
            if color is None:
                continue

            # 运动员行口径：一条记录就是 1 枚
            y[f"{color}Athlete"] += 1
            c[f"{color}Athlete"] += 1
            t[f"{color}Athlete"] += 1
            s[f"{color}Athlete"] += 1
            if row["Sex"] == "F":
                y[f"female{color.capitalize()}Athlete"] += 1

            # 小项口径：同一 (届次, 小项, 奖牌色, NOC) 只计 1 枚（国家层级）
            key = (year, event, medal, noc)
            if key not in event_keys:
                event_keys.add(key)
                y[f"{color}Event"] += 1
                c[f"{color}Event"] += 1
                s[f"{color}Event"] += 1
                sy[f"{color}Event"] += 1
                if row["Sex"] == "F":
                    y[f"female{color.capitalize()}Event"] += 1

            # 团队层级的小项口径：去重键再多一维 Team
            team_key = (year, event, medal, noc, team)
            if team_key not in team_event_keys:
                team_event_keys.add(team_key)
                t[f"{color}Event"] += 1

    return years, countries, teams, sports, sport_years, all_nocs


def build_years(raw_years: dict) -> list[dict]:
    """把内部聚合转成前端可直接画图的届次序列。"""
    rows = []
    for year in sorted(raw_years):
        y = raw_years[year]
        total_event = y["goldEvent"] + y["silverEvent"] + y["bronzeEvent"]
        total_athlete = y["goldAthlete"] + y["silverAthlete"] + y["bronzeAthlete"]
        rows.append(
            {
                "year": year,
                "records": y["rows"],
                "athletes": y["rows"],
                "female": y["female"],
                "femaleRatio": round(y["female"] / y["rows"], 4) if y["rows"] else 0,
                "nocs": len(y["nocs"]),
                "teams": len(y["teams"]),
                "sports": len(y["sports"]),
                "uniqueEvents": len(y["events"]),
                "genericShare": round(y["genericRows"] / y["rows"], 4) if y["rows"] else 0,
                "goldEvent": y["goldEvent"],
                "silverEvent": y["silverEvent"],
                "bronzeEvent": y["bronzeEvent"],
                "totalEvent": total_event,
                "goldAthlete": y["goldAthlete"],
                "silverAthlete": y["silverAthlete"],
                "bronzeAthlete": y["bronzeAthlete"],
                "totalAthlete": total_athlete,
                "femaleEvent": y["femaleGoldEvent"] + y["femaleSilverEvent"] + y["femaleBronzeEvent"],
                "femaleAthlete": y["femaleGoldAthlete"] + y["femaleSilverAthlete"] + y["femaleBronzeAthlete"],
            }
        )
    return rows


def build_countries(raw_countries: dict, team_names: dict[str, str], host_map: dict[int, str]) -> list[dict]:
    """把代表团 x 届次聚合补全成前端可筛选的宽表。"""
    rows = []
    for (year, noc), c in sorted(raw_countries.items()):
        total_event = c["goldEvent"] + c["silverEvent"] + c["bronzeEvent"]
        total_athlete = c["goldAthlete"] + c["silverAthlete"] + c["bronzeAthlete"]
        rows.append(
            {
                "year": year,
                "noc": noc,
                "team": team_names.get(noc) or c["team"],
                "records": c["records"],
                "athletes": c["records"],
                "female": c["female"],
                "femaleRatio": round(c["female"] / c["records"], 4) if c["records"] else 0,
                "goldEvent": c["goldEvent"],
                "silverEvent": c["silverEvent"],
                "bronzeEvent": c["bronzeEvent"],
                "totalEvent": total_event,
                "goldAthlete": c["goldAthlete"],
                "silverAthlete": c["silverAthlete"],
                "bronzeAthlete": c["bronzeAthlete"],
                "totalAthlete": total_athlete,
                "isHost": 1 if host_map.get(year) == noc else 0,
            }
        )
    return rows


def build_sports(raw_sports: dict) -> list[dict]:
    """运动大类名录：生命周期 + 逐年分布 + 双口径奖牌。"""
    rows = []
    lifecycle = {r["Sport"]: r for r in read_table("d_sport_lifecycle.csv")}

    for name, r in lifecycle.items():
        agg = raw_sports.get(name) or new_sport_bucket()
        rows.append(
            {
                "sport": name,
                "first": to_int(r["首次"]),
                "last": to_int(r["末次"]),
                "editions": to_int(r["届数"]),
                "records": to_int(r["记录数"]),
                "span": to_int(r["跨度"]),
                "retired": to_bool(r["已消失"]),
                "years": sorted(agg["years"]),
                "goldEvent": agg["goldEvent"],
                "silverEvent": agg["silverEvent"],
                "bronzeEvent": agg["bronzeEvent"],
                "goldAthlete": agg["goldAthlete"],
                "silverAthlete": agg["silverAthlete"],
                "bronzeAthlete": agg["bronzeAthlete"],
            }
        )

    # 兜底：归一后出现但生命周期表未收录的运动，直接从原始聚合补录
    for name, agg in raw_sports.items():
        if name in lifecycle:
            continue
        years = sorted(agg["years"])
        rows.append(
            {
                "sport": name,
                "first": years[0] if years else 0,
                "last": years[-1] if years else 0,
                "editions": len(years),
                "records": agg["records"],
                "span": (years[-1] - years[0]) if years else 0,
                "retired": bool(years and years[-1] < 2024),
                "years": years,
                "goldEvent": agg["goldEvent"],
                "silverEvent": agg["silverEvent"],
                "bronzeEvent": agg["bronzeEvent"],
                "goldAthlete": agg["goldAthlete"],
                "silverAthlete": agg["silverAthlete"],
                "bronzeAthlete": agg["bronzeAthlete"],
            }
        )

    for item in rows:
        item["totalEvent"] = item["goldEvent"] + item["silverEvent"] + item["bronzeEvent"]
        item["totalAthlete"] = item["goldAthlete"] + item["silverAthlete"] + item["bronzeAthlete"]
    rows.sort(key=lambda item: (-item["records"], item["sport"]))
    return rows


def build_sport_year(raw_sport_years: dict) -> list[dict]:
    """运动 × 届次：供动态排序柱状图逐帧使用。"""
    rows = []
    for (year, sport), agg in raw_sport_years.items():
        rows.append(
            {
                "year": year,
                "sport": sport,
                "records": agg["records"],
                "female": agg["female"],
                "goldEvent": agg["goldEvent"],
                "silverEvent": agg["silverEvent"],
                "bronzeEvent": agg["bronzeEvent"],
                "totalEvent": agg["goldEvent"] + agg["silverEvent"] + agg["bronzeEvent"],
            }
        )
    rows.sort(key=lambda item: (item["year"], -item["records"], item["sport"]))
    return rows


def build_teams(raw_teams: dict) -> list[dict]:
    """团队名录：Team 字段去重后的全部队伍，含参赛年份与双口径奖牌。"""
    rows = []
    for (noc, team), agg in raw_teams.items():
        years = sorted(agg["years"])
        rows.append(
            {
                "noc": noc,
                "team": team,
                "first": years[0] if years else 0,
                "last": years[-1] if years else 0,
                "editions": len(years),
                "years": years,
                "records": agg["records"],
                "female": agg["female"],
                "femaleRatio": round(agg["female"] / agg["records"], 4) if agg["records"] else 0,
                "goldEvent": agg["goldEvent"],
                "silverEvent": agg["silverEvent"],
                "bronzeEvent": agg["bronzeEvent"],
                "goldAthlete": agg["goldAthlete"],
                "silverAthlete": agg["silverAthlete"],
                "bronzeAthlete": agg["bronzeAthlete"],
            }
        )
    for item in rows:
        item["totalEvent"] = item["goldEvent"] + item["silverEvent"] + item["bronzeEvent"]
        item["totalAthlete"] = item["goldAthlete"] + item["silverAthlete"] + item["bronzeAthlete"]
    rows.sort(key=lambda item: (-item["records"], item["team"]))
    return rows


def build_event_count() -> list[dict]:
    rows = []
    for r in read_table("d_event_count_by_year.csv"):
        rows.append(
            {
                "year": to_int(r["Year"]),
                "uniqueEvents": to_int(r["事件唯一值"]),
                "genericShare": to_float(r["泛化行占比"]) or 0,
                "combos": to_int(r["大类×性别组合数"]),
            }
        )
    rows.sort(key=lambda item: item["year"])
    return rows


def build_women_supply() -> list[dict]:
    rows = []
    for r in read_table("c_women_event_supply.csv"):
        rows.append(
            {
                "year": to_int(r["Year"]),
                "allEvents": to_int(r["all_events"]),
                "womenEvents": to_float(r["women_events"]) or 0,
                "womenShare": to_float(r["women_share"]) or 0,
            }
        )
    rows.sort(key=lambda item: item["year"])
    return rows


def build_host() -> list[dict]:
    rows = []
    for r in read_table("s1_host_effect.csv"):
        rows.append(
            {
                "year": to_int(r["Year"]),
                "noc": r["NOC"],
                "team": r["Team"],
                "hostMedals": to_int(r["主办届奖牌"]),
                "hostGold": to_int(r["主办届金牌"]),
                "prevMedals": to_float(r["上届奖牌"]),
                "prevGold": to_float(r["上届金牌"]),
                "nextMedals": to_float(r["下届奖牌"]),
                "goldRank": to_int(r["主办届金牌排名"]),
                "deltaMedals": to_float(r["较上届奖牌增幅"]),
                "deltaRatio": to_float(r["较上届增幅比例"]),
                "dropAfter": to_float(r["主办后回落"]),
            }
        )
    rows.sort(key=lambda item: item["year"])
    return rows


def sanitize(value):
    """递归把 NaN / inf 转成 None，保证输出是合法 JSON。"""
    if isinstance(value, float):
        return None if (math.isnan(value) or math.isinf(value)) else value
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return value


def load_highlights() -> dict:
    path = TABLES / "analysis_results.json"
    with path.open(encoding="utf-8") as handle:
        raw = json.loads(handle.read(), parse_constant=lambda _: None)
    raw = sanitize(raw)
    return {
        "medals": raw.get("A_奖牌格局", {}),
        "countries": raw.get("B_国家兴衰", {}),
        "gender": raw.get("C_她的奥运", {}),
        "sports": raw.get("D_项目演化", {}),
        "host": {k: v for k, v in raw.get("S1_东道主效应", {}).items() if k != "明细"},
        "caliber": raw.get("S2_口径的魔力", {}),
        "insights": raw.get("洞察", []),
        "base": raw.get("基础统计", {}),
    }


def main() -> int:
    if not RAW_CSV.exists():
        raise SystemExit(f"找不到原始数据：{RAW_CSV}")

    raw_years, raw_countries, raw_teams, raw_sports, raw_sport_years, all_nocs = aggregate_raw()

    team_names = {r["NOC"]: r["Team"] for r in read_table("a_history_medal_table.csv") if r.get("Team")}
    host_rows = build_host()
    host_map = {r["year"]: r["noc"] for r in host_rows}

    years = build_years(raw_years)
    countries = build_countries(raw_countries, team_names, host_map)
    teams = build_teams(raw_teams)
    sports = build_sports(raw_sports)
    sport_year = build_sport_year(raw_sport_years)
    event_count = build_event_count()
    women_supply = build_women_supply()
    highlights = load_highlights()

    total_event = sum(y["totalEvent"] for y in years)
    total_athlete = sum(y["totalAthlete"] for y in years)
    shrink = round((1 - total_event / total_athlete) * 100, 1) if total_athlete else 0

    meta = {
        "title": "数说奥运 1896–2024",
        "subtitle": "夏季奥运会参赛与奖牌记录 · 252,565 行 × 11 列",
        "rawRows": 252565,
        "rows": sum(y["records"] for y in years),
        "officialEditions": len(years),
        "yearStart": years[0]["year"],
        "yearEnd": years[-1]["year"],
        "excludeYears": sorted(EXCLUDE_YEARS),
        "totals": {
            "eventMedals": total_event,
            "athleteMedals": total_athlete,
            "shrinkPct": shrink,
        },
        "nocs": len(all_nocs),
        "teams": len(teams),
        "sports": len(sports),
        "activeSports": sum(1 for item in sports if not item["retired"]),
        "female2024": next((y["femaleRatio"] for y in years if y["year"] == 2024), 0),
        "calibers": {
            "event": "小项口径（同届 · 同小项 · 同奖牌色 · 同 NOC 计 1 枚）",
            "athlete": "运动员行口径（每条奖牌记录计 1 枚）",
        },
    }

    payload = {
        "meta": meta,
        "years": years,
        "countryYear": countries,
        "teams": teams,
        "sports": sports,
        "sportYear": sport_year,
        "eventCount": event_count,
        "womenSupply": women_supply,
        "host": host_rows,
        "highlights": highlights,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        encoding="utf-8",
    )

    print(f"✓ 写入 {OUT_JSON.relative_to(ROOT)}")
    print(f"  届次 {len(years)} / 代表团×届次 {len(countries)} / 团队 {len(teams)} / 运动 {len(sports)} / 东道主 {len(host_rows)}")
    print(f"  小项口径奖牌 {total_event:,} / 行口径奖牌 {total_athlete:,} / 收缩 {shrink}%")
    expected = (17901, 38360)
    if (total_event, total_athlete) != expected:
        print(f"  ! 与基线 {expected} 不一致，请检查 1906 排除与去重键")
        return 2
    print("  ✓ 与基线 17,901 / 38,360 一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
