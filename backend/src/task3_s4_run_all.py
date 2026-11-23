"""
Task3 S4 全链路一键运行 + 自检
==============================
职责
----
按顺序执行：数据准备 → 分析 → 静态图 → 产物自检。
任一步失败即中止并返回非零退出码。

调用关系
--------
- 上游依赖：`docs/Task1/*.csv`（Task1 清洗产物）
- 下游：`outputs/task3_s4/` 下的 json/csv/figures

用法
----
    python backend/src/task3_s4_run_all.py           # 全量运行
    python backend/src/task3_s4_run_all.py --check   # 只自检已有产物
"""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))

import task3_s4_clean            # noqa: E402
import task3_s4_analysis         # noqa: E402
import task3_s4_share_trend      # noqa: E402
import task3_s4_visualize        # noqa: E402
import task3_s4_visualize_extra  # noqa: E402

T3 = ROOT / "outputs" / "task3_s4"

# 关键产物清单：用于运行后自检
REQUIRED = [
    T3 / "s4_base.csv",
    T3 / "s4_noc_first_medal.csv",
    T3 / "s4_results.json",
    T3 / "s4_verification.json",
]

# 必须存在的 19 张结果表
REQUIRED_TABLES = [
    "a_size_distribution.csv", "a_size_class_by_year.csv",
    "a_small_medal_rate_by_year.csv",
    "b_strategy_by_size.csv", "b_strategy_by_size_modern.csv",
    "b_efficiency_vs_size.csv", "b_concentration_scatter.csv",
    "c_case_countries.csv", "c_case_medal_by_sport.csv",
    "c_hkg_detail.csv", "c_sgp_detail.csv", "c_tpe_detail.csv",
    "d_persistence.csv", "d_streak_by_type.csv", "d_one_hit_wonders.csv",
    "e_threshold_sensitivity.csv", "e_caliber_sensitivity.csv",
    "f_small_rise.csv", "f_small_rise_all_years.csv",
    "f_share_trend_by_threshold.csv",
]

# 必须存在的 10 张图
REQUIRED_FIGS = [
    "fig01_size_vs_rate.svg", "fig02_small_trend.svg",
    "fig03_concentration_scatter.svg", "fig04_efficiency.svg",
    "fig05_case_sports.svg", "fig06_case_trajectory.svg",
    "fig07_persistence.svg", "fig08_small_share_rise.svg",
    "fig09_sensitivity.svg", "fig10_small_noc_board.svg",
]


def check_artifacts() -> list[str]:
    """检查关键产物是否存在且非空，返回问题列表（空表示全部通过）。"""
    problems: list[str] = []
    for p in REQUIRED:
        if not p.exists():
            problems.append(f"缺失 {p.relative_to(ROOT)}")
        elif p.stat().st_size == 0:
            problems.append(f"空文件 {p.relative_to(ROOT)}")
    for name in REQUIRED_TABLES:
        p = T3 / "tables" / name
        if not p.exists() or p.stat().st_size == 0:
            problems.append(f"缺失或空 表 {name}")
    for name in REQUIRED_FIGS:
        p = T3 / "figures" / name
        if not p.exists() or p.stat().st_size == 0:
            problems.append(f"缺失或空 图 {name}")
    return problems


def run_stage(name: str, fn) -> None:
    """执行一个阶段并打印耗时。异常向上抛，由 main 统一处理退出码。"""
    t0 = time.time()
    print(f"\n{'=' * 62}\n▶ {name}\n{'=' * 62}")
    fn()
    print(f"✓ {name} 完成，用时 {time.time() - t0:.1f}s")


def main() -> int:
    ap = argparse.ArgumentParser(description="Task3 S4 全链路")
    ap.add_argument("--check", action="store_true", help="只自检产物，不重算")
    args = ap.parse_args()

    if not args.check:
        try:
            run_stage("1/3 数据准备与清洗校验", task3_s4_clean.main)
            run_stage("2/3 特征工程与分析", task3_s4_analysis.main)
            run_stage("2.5/3 份额趋势阈值敏感性", task3_s4_share_trend.main)
            run_stage("3/3 可视化", lambda: (task3_s4_visualize.main(),
                                            task3_s4_visualize_extra.f10()))
        except Exception:
            print("\n✗ 执行失败：", file=sys.stderr)
            traceback.print_exc()
            return 1

    print(f"\n{'=' * 62}\n▶ 产物自检\n{'=' * 62}")
    problems = check_artifacts()
    if problems:
        for p in problems:
            print(f"  ✗ {p}")
        return 2
    print(f"  ✓ 关键产物齐全：4 个核心文件 + {len(REQUIRED_TABLES)} 张表 "
          f"+ {len(REQUIRED_FIGS)} 张图")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
