"""
Run 日频回测 pipeline step by step (readme 步骤 2–7).
Each script runs in project root; one finishes then the next runs.
Step 1 (更新 daily_stockpool.xlsx) is manual — do that before running this.
"""
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# Order of scripts (relative to project root)
STEPS = [
    ("5a. 中证500指增_LGBM_weekly_to_daily.py", "data_collection/wind_choice/中证500指增_LGBM_weekly_to_daily.py"),
    ("5b. 中证500指增_LGBM_excel_upperlimit.py (Wind+Choice 涨跌停/停牌)", "data_collection/wind_choice/中证500指增_LGBM_excel_upperlimit.py"),
    ("6. main.py — 回测", "main.py"),
]


def main():
    print("Pipeline run from:", PROJECT_ROOT)
    print("Backtest\n")
    for label, rel_path in STEPS:
        script = PROJECT_ROOT / rel_path
        if not script.exists():
            print(f"[SKIP] {label}: file not found — {script}")
            continue
        print(f"[RUN] {label}")
        print(f"      {script}\n")
        ret = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(PROJECT_ROOT),
        )
        if ret.returncode != 0:
            print(f"\n[FAIL] {label} exited with code {ret.returncode}. Stopping.")
            sys.exit(ret.returncode)
    print("\n[DONE] All steps finished.")


if __name__ == "__main__":
    main()
