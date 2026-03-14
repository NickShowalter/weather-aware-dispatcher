# Weather-Aware Dispatcher

## Overview
A Python application that optimally routes a delivery drone across a 20x20 grid under dynamic wind conditions, battery constraints, payload penalties, and obstacles.

## Quick Start
```bash
# Run the dispatcher
python main.py sample_input.json

# Run as module
python -m weather_aware_dispatcher sample_input.json

# Run tests
pytest tests/ -v
```

## Requirements
- Python 3.10+
- pytest (for tests only)

```bash
pip install -r requirements.txt
```

## Architecture

The system is built in 8 layers, each with a single responsibility and independently testable:

**Cost Calculator** (`core/cost_calculator.py`) — Pure stateless functions that compute movement costs given wind direction, move direction, and payload weight. This is the mathematical foundation: `final_cost = base_cost x wind_multiplier x payload_multiplier`. All 7 reference values from the spec are verified in tests.

**Pathfinder** (`core/pathfinder.py`) — Two pathfinding algorithms. `find_path` is standard A* with Manhattan heuristic. `find_path_cost_aware` is a time-aware A* where edge costs incorporate wind direction at each tick — the same coordinate at different ticks is a different state because wind shifts affect cost. This means a physically longer path may consume less battery if it aligns with favorable wind.

**Delivery Planner** (`core/delivery_planner.py`) — Since the drone carries one package at a time, each delivery is a round trip from base. The optimization problem is: *in what order should we deliver?* For manifests of 8 or fewer packages, the planner tries all permutations (8! = 40,320) and picks the ordering with minimum total battery. For larger manifests, it falls back to a wind-aware greedy heuristic.

**Simulation Engine** (`core/simulation_engine.py`) — An independent tick-by-tick executor that validates the plan. It recomputes all costs from scratch using the Cost Calculator — it never trusts the planner's pre-computed values. If the planner has a bug, the simulator catches the discrepancy. This is defense-in-depth: the same pattern used in flight-critical software where independent channels verify each other.

The remaining layers handle domain models (`models/`), configuration constants (`config.py`), input parsing/validation (`io/input_loader.py`), and output formatting (`io/output_formatter.py`).

## Key Design Decisions

- **Floor division for payload penalty:** `floor(weight / 5)` increments. A 12-lb package gets `floor(12/5) = 2` increments = 1.2x multiplier.
- **Wind-aware greedy heuristic** for delivery ordering — good enough for small manifests, clearly improvable with branch-and-bound for larger ones. Exhaustive permutation search for <= 8 packages.
- **Time-aware A* pathfinding:** Node state is `(coordinate, tick)` because wind changes over time. Heuristic is `manhattan * 0.5` (admissible — minimum possible cost per move).
- **Simulation engine as independent validator:** Defense-in-depth. The simulator recomputes costs from first principles and logs warnings on any discrepancy with the planner.
- **All constants in `config.py`:** No magic numbers in business logic.
- **Input validation collects all errors:** Doesn't fail on the first error — reports everything at once.

## Assumptions

1. Payload penalty uses **floor division**: `floor(weight / 5)` increments.
2. Battery tracked as **float** — no per-move rounding.
3. Arriving at (0,0) with exactly 0.0 battery is **not a crash**.
4. Tick advances by 1 per movement. Battery swap, pickup, drop-off are **instant (0 ticks)**.
5. Coordinates are **[x, y]**: x = column (East/West), y = row (North/South). (0,0) = southwest corner.
6. Infeasible deliveries are **reported, not skipped silently**.
7. **No external dependencies** beyond Python stdlib + pytest.

## AI Log

This project was built with Claude Code (Claude Opus 4.6). The AI was given a detailed specification and produced the implementation layer-by-layer, running tests after each step.

**What went well:**
- The layered architecture translated cleanly from spec to code. Each layer was implemented and tested independently before moving on.
- All 7 reference cost values matched on the first implementation — the cost calculator formulas were straightforward.
- The time-aware A* pathfinder worked correctly on the first pass, including proper tick-state tracking.
- The permutation optimizer found the optimal delivery ordering (125.10 battery for the sample input).

**What needed attention:**
- Setting up the Python environment (venv, pytest installation) required a few iterations to get the right Python path on macOS.
- The coordinate convention (NORTH = +y, EAST = +x, origin at southwest) needed careful consistency across Direction.to_delta(), pathfinder, and cost calculator — this is the kind of thing that's easy to get wrong silently.

**What I'd improve with more time:**
- Add branch-and-bound pruning for the permutation search to handle larger manifests efficiently.
- Add property-based testing (Hypothesis) for the cost calculator to catch edge cases.
- Add a `--verbose` flag for move-by-move output.
- The greedy fallback could be improved with a look-ahead heuristic that considers wind forecasts.
