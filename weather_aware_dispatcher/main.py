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
    parser.add_argument("input_file", nargs="?", help="Path to input JSON file")
    parser.add_argument("--serve", action="store_true", help="Start web server for 3D visualization")
    parser.add_argument("--port", type=int, default=8080, help="Server port (default: 8080)")
    args = parser.parse_args(argv)

    if args.serve:
        from weather_aware_dispatcher.server import run_server
        run_server(port=args.port)
        return 0

    if not args.input_file:
        parser.error("input_file is required when not using --serve")

    # Load and validate input
    load_result = load_input(args.input_file)
    if not load_result.ok:
        print("Input validation failed:", file=sys.stderr)
        for error in load_result.errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    data = load_result.data

    # Plan deliveries
    plan = plan_deliveries(data.packages, data.grid, data.weather, data.config)

    # Simulate plan
    result = simulate(plan, data.weather, data.config)

    # Output
    print(format_result(plan, result))

    if not result.success:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
