from __future__ import annotations

import argparse
import logging
import sys

from weather_aware_dispatcher.core.delivery_planner import plan_deliveries
from weather_aware_dispatcher.core.simulation_engine import simulate
from weather_aware_dispatcher.io.input_loader import load_input
from weather_aware_dispatcher.io.output_formatter import format_result


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Weather-Aware Dispatcher — drone delivery route planner",
    )
    parser.add_argument("input_file", help="Path to input JSON file")
    args = parser.parse_args(argv)

    # Load and validate input
    load_result = load_input(args.input_file)
    if not load_result.ok:
        print("Input validation failed:", file=sys.stderr)
        for error in load_result.errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    data = load_result.data

    # Plan deliveries
    plan = plan_deliveries(data.packages, data.grid, data.weather)

    # Simulate plan
    result = simulate(plan, data.weather)

    # Output
    print(format_result(plan, result))

    if not result.success:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
