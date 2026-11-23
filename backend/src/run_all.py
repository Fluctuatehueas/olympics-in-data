"""
全链路一键运行入口
==================
职责
----
按固定顺序执行整条分析链路，任一环节失败即中止并返回非零退出码：

    质量体检 → 清洗与口径 → 特征工程与分析 → 可视化 → 产物自检

调用关系
--------
- 上游调用方：`python src/run_all.py`（命令行）或 CI。
- 下游被调用方：依次 import 并调用 quality_checks / cleaning / features / visualize 的 main()。
- 并发/线程：刻意串行。四个模块之间通过磁盘文件传递中间结果（data/processed/*.csv、
  outputs/tables/*.csv），串行执行保证下游读到的一定是上游最新版本；
  若改成多进程并行会产生读写竞态，不建议。

用法
----
    python src/run_all.py            # 全量运行
    python src/run_all.py --check    # 仅自检已有产物，不重新计算
"""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# 以仓库根为 import 根，保证 `backend.src.*` 与 `backend.api.*` 都可被解析
sys.path.insert(0, str(ROOT))

from backend.src import cleaning              # noqa: E402
from backend.src import features             # noqa: E402
from backend.src import quality_checks       # noqa: E402
from backend.src import visualize            # noqa: E402

# 各阶段必须存在的关键产物，用于运行后自检
REQUIRED = {
    "质量体检": [ROOT / "outputs" / "tables" / "quality_checks.md"],
    "清洗与口径": [
        ROOT / "docs" / "Task1" / "olympics_clean.csv",
        ROOT / "docs" / "Task1" / "medal_event_level.csv",
        ROOT / "docs" / "Task1" / "noc_year_summary.csv",
        ROOT / "docs" / "Task1" / "sport_mapping.csv",
        ROOT / "docs" / "Task1" / "noc_lineage.csv",
        ROOT / "docs" / "Task1" / "cleaning_verification.md",
    ],
    "特征与分析": [
        ROOT / "docs" / "Task1" / "features_noc_year.csv",
        ROOT / "outputs" / "tables" / "analysis_results.json",
        ROOT / "outputs" / "tables" / "a_history_medal_table.csv",
        ROOT / "outputs" / "tables" / "s1_host_effect.csv",
        ROOT / "outputs" / "tables" / "s2_2024_caliber_compare.csv",
    ],
    "可视化": [ROOT / "figures", ROOT / "dashboard.html"],
}


def check_artifacts() -> list[str]:
    """自检产物是否存在且非空，返回缺失项描述列表（空列表表示全部通过）。"""
    problems: list[str] = []
    for stage, paths in REQUIRED.items():
        for p in paths:
            if not p.exists():
                problems.append(f"[{stage}] 缺失 {p.relative_to(ROOT)}")
            elif p.is_file() and p.stat().st_size == 0:
                problems.append(f"[{stage}] 空文件 {p.relative_to(ROOT)}")
    # 图表数量单独统计
    fig_dir = ROOT / "figures"
    if fig_dir.exists():
        n_svg = len(list(fig_dir.glob("*.svg")))
        if n_svg < 10:
            problems.append(f"[可视化] 仅生成 {n_svg} 张折线/条形图，少于预期的 10 张")
    return problems


def run_stage(name: str, fn) -> None:
    """执行一个阶段并打印耗时；异常直接向上抛出，由 main 统一处理退出码。"""
    t0 = time.time()
    print(f"\n{'=' * 62}\n▶ {name}\n{'=' * 62}")
    fn()
    print(f"✓ {name} 完成，用时 {time.time() - t0:.1f}s")


def main() -> int:
    ap = argparse.ArgumentParser(description="奥运数据分析全链路")
    ap.add_argument("--check", action="store_true", help="只自检已有产物，不重新计算")
    args = ap.parse_args()

    if not args.check:
        try:
            run_stage("1/4 数据质量体检", quality_checks.main)
            run_stage("2/4 清洗与口径构建", cleaning.main)
            run_stage("3/4 特征工程与分析", features.main)
            run_stage("4/4 可视化", visualize.main)
        except Exception:
            print("\n✗ 执行失败，堆栈如下：", file=sys.stderr)
            traceback.print_exc()
            return 1

    print(f"\n{'=' * 62}\n▶ 产物自检\n{'=' * 62}")
    problems = check_artifacts()
    if problems:
        for p in problems:
            print(f"  ✗ {p}")
        return 2
    print("  ✓ 全部关键产物存在且非空")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
