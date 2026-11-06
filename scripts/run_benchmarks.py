#!/usr/bin/env python3
"""Run repeatable Phase 7 experiments over CI, CT and monitoring scenarios."""
from __future__ import annotations
import argparse
import json
import os
import platform
import resource
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def execute(name, command, env, expected_success=True):
    started = time.perf_counter()
    before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    proc = subprocess.run(command, env=env, text=True, capture_output=True)
    elapsed = time.perf_counter() - started
    after = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    success = proc.returncode == 0
    return {
        "name": name, "command": command, "return_code": proc.returncode,
        "success": success, "expected_success": expected_success,
        "expectation_met": success == expected_success,
        "wall_time_seconds": round(elapsed, 6),
        "child_peak_rss_delta_platform_units": max(0, after - before),
        "stdout_tail": proc.stdout[-3000:], "stderr_tail": proc.stderr[-3000:],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry-dir", default="model_registry")
    parser.add_argument("--environment", choices=["dev", "staging", "prod"], default="dev")
    parser.add_argument("--output-dir", default="artifacts/benchmark-runs")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--include-negative-tests", action="store_true")
    args = parser.parse_args()
    if args.repeats < 1 or args.repeats > 5:
        parser.error("--repeats must be between 1 and 5")

    root = Path(args.output_dir)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = root / run_id
    out.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path("src").resolve()) + os.pathsep + env.get("PYTHONPATH", "")
    py = sys.executable
    results = []
    expected_failure_scenarios = {"corrupted_data", "invalid_input"}
    for repeat in range(args.repeats):
        results.append(execute(
            f"ci_repeat_{repeat+1}",
            [py, "-m", "mlops_lab.cli", "run-ci", "--config", "configs/ci.yaml",
             "--output-dir", str(out / f"ci-{repeat+1}")], env
        ))
        for scenario in ["stable", "covariate_shift", "concept_drift"]:
            results.append(execute(
                f"ct_{scenario}_repeat_{repeat+1}",
                [py, "-m", "mlops_lab.cli", "run-ct", "--config", "configs/ct.yaml",
                 "--output-dir", str(out / f"ct-{scenario}-{repeat+1}"),
                 "--scenario", scenario], env
            ))
        if args.include_negative_tests:
            results.append(execute(
                f"ct_corrupted_data_repeat_{repeat+1}",
                [py, "-m", "mlops_lab.cli", "run-ct", "--config", "configs/ct.yaml",
                 "--output-dir", str(out / f"ct-corrupted-{repeat+1}"),
                 "--scenario", "corrupted_data"], env, expected_success=False
            ))
        results.append(execute(
            f"monitor_normal_repeat_{repeat+1}",
            [py, "-m", "mlops_lab.cli", "run-monitor", "--registry-dir", args.registry_dir,
             "--environment", args.environment, "--output-dir", str(out / f"monitor-normal-{repeat+1}"),
             "--scenario", "normal"], env
        ))
        results.append(execute(
            f"monitor_prediction_drift_repeat_{repeat+1}",
            [py, "-m", "mlops_lab.cli", "run-monitor", "--registry-dir", args.registry_dir,
             "--environment", args.environment, "--output-dir", str(out / f"monitor-drift-{repeat+1}"),
             "--scenario", "prediction_drift"], env
        ))
        results.append(execute(
            f"monitor_quality_degradation_repeat_{repeat+1}",
            [py, "-m", "mlops_lab.cli", "run-monitor", "--registry-dir", args.registry_dir,
             "--environment", args.environment, "--output-dir", str(out / f"monitor-quality-{repeat+1}"),
             "--scenario", "quality_degradation"], env
        ))
        if args.include_negative_tests:
            results.append(execute(
                f"monitor_invalid_input_repeat_{repeat+1}",
                [py, "-m", "mlops_lab.cli", "run-monitor", "--registry-dir", args.registry_dir,
                 "--environment", args.environment, "--output-dir", str(out / f"monitor-invalid-{repeat+1}"),
                 "--scenario", "invalid_input"], env, expected_success=False
            ))

    passed = sum(r["expectation_met"] for r in results)
    summary = {
        "schema_version": 1, "pipeline": "PHASE7_BENCHMARK",
        "run_id": run_id, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(), "platform": platform.platform(),
        "environment": args.environment, "repeats": args.repeats,
        "include_negative_tests": args.include_negative_tests,
        "total_experiments": len(results), "expectations_met": passed,
        "expectations_failed": len(results) - passed,
        "overall_status": "passed" if passed == len(results) else "failed",
        "results": results,
    }
    (out / "benchmark_report.json").write_text(json.dumps(summary, indent=2) + "\n")
    # CSV is deliberately dependency-free and easy to import into R/Excel.
    import csv
    with (out / "benchmark_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "name", "return_code", "success", "expected_success", "expectation_met",
            "wall_time_seconds", "child_peak_rss_delta_platform_units"])
        writer.writeheader()
        for row in results:
            writer.writerow({k: row[k] for k in writer.fieldnames})
    print(json.dumps({k: summary[k] for k in (
        "total_experiments", "expectations_met", "expectations_failed", "overall_status")}, indent=2))
    if summary["overall_status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
