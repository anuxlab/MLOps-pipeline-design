import argparse
import json

from .config import load_config
from .pipeline import run_baseline
from .ci_pipeline import run_ci
from .ct_pipeline import run_ct
from .registry import register_and_deploy
from .monitoring import run_monitoring


def main():
    parser = argparse.ArgumentParser(description="GitHub MLOps Laboratory CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    baseline = subparsers.add_parser("run-baseline", help="Run Phase 1 baseline training")
    baseline.add_argument("--config", default="configs/baseline.yaml")
    baseline.add_argument("--output-dir", default=None)

    ci = subparsers.add_parser("run-ci", help="Run Phase 2 ML continuous integration")
    ci.add_argument("--config", default="configs/ci.yaml")
    ci.add_argument("--output-dir", default=None)
    ci.add_argument(
        "--failure-mode",
        choices=["none", "invalid_schema", "nan_feature", "force_quality_gate"],
        default="none",
    )

    ct = subparsers.add_parser("run-ct", help="Run Phase 3 continuous training simulation")
    ct.add_argument("--config", default="configs/ct.yaml")
    ct.add_argument("--output-dir", default=None)
    ct.add_argument(
        "--scenario",
        choices=["stable", "covariate_shift", "concept_drift", "corrupted_data"],
        default="stable",
    )

    cd = subparsers.add_parser("run-cd", help="Register and deploy a promoted CT candidate")
    cd.add_argument("--source-dir", required=True)
    cd.add_argument("--registry-dir", default="model_registry")
    cd.add_argument("--environment", choices=["dev", "staging", "prod"], required=True)
    cd.add_argument("--model-name", default="mlops-binary-classifier")
    cd.add_argument("--expected-source-run-id", default=None)

    monitor = subparsers.add_parser("run-monitor", help="Run Phase 6 model and data monitoring")
    monitor.add_argument("--registry-dir", default="model_registry")
    monitor.add_argument("--environment", choices=["dev", "staging", "prod"], default="dev")
    monitor.add_argument("--output-dir", default="artifacts/monitoring-runs")
    monitor.add_argument("--scenario", choices=["normal", "prediction_drift", "quality_degradation", "invalid_input"], default="normal")
    monitor.add_argument("--config", default="configs/monitoring.yaml")

    args = parser.parse_args()
    if args.command == "run-baseline":
        config = load_config(args.config)
        run_dir = run_baseline(config, args.output_dir)
        print(f"Baseline run completed: {run_dir}")
        for filename in ("metrics.json", "resource_profile.json"):
            payload = json.loads((run_dir / filename).read_text(encoding="utf-8"))
            print(f"\n{filename}:")
            print(json.dumps(payload, indent=2))
    elif args.command == "run-ci":
        config = load_config(args.config)
        run_dir = run_ci(config, args.output_dir, args.failure_mode)
        print(f"ML CI pipeline passed: {run_dir}")
        report = json.loads((run_dir / "ci_report.json").read_text(encoding="utf-8"))
        print(json.dumps(report, indent=2))
    elif args.command == "run-ct":
        config = load_config(args.config)
        run_dir = run_ct(config, args.output_dir, args.scenario)
        print(f"ML CT pipeline completed: {run_dir}")
        report = json.loads((run_dir / "ct_report.json").read_text(encoding="utf-8"))
        print(json.dumps(report, indent=2))
    elif args.command == "run-monitor":
        run_dir = run_monitoring(args.registry_dir, args.environment, args.output_dir, args.scenario, args.config)
        print(f"Monitoring completed: {run_dir}")
        print((run_dir / "monitoring_report.json").read_text(encoding="utf-8"))
    elif args.command == "run-cd":
        version_dir = register_and_deploy(
            args.source_dir, args.registry_dir, args.environment, args.model_name,
            args.expected_source_run_id
        )
        print(f"Model registered and deployed: {version_dir}")
        print((version_dir / "manifest.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
