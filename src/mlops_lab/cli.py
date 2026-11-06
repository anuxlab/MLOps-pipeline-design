import argparse
from pathlib import Path
import json

from .config import load_config
from .pipeline import run_baseline


def main():
    parser = argparse.ArgumentParser(description="GitHub MLOps Laboratory CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    baseline = subparsers.add_parser("run-baseline", help="Run Phase 1 baseline training")
    baseline.add_argument("--config", default="configs/baseline.yaml")
    baseline.add_argument("--output-dir", default=None)

    args = parser.parse_args()
    if args.command == "run-baseline":
        config = load_config(args.config)
        run_dir = run_baseline(config, args.output_dir)
        print(f"Baseline run completed: {run_dir}")
        for filename in ("metrics.json", "resource_profile.json"):
            payload = json.loads((run_dir / filename).read_text(encoding="utf-8"))
            print(f"\n{filename}:")
            print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
