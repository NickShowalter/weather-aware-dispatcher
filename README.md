# Weather-Aware Dispatcher

## Overview
A Python application that optimally routes a delivery drone across a 20x20 grid under dynamic wind conditions, battery constraints, payload penalties, and obstacles. Includes a browser-based 3D simulator for interactive scenario modeling.

## Quick Start

### CLI Mode
```bash
# Run the dispatcher
python main.py sample_input.json

# Run as module
python -m weather_aware_dispatcher sample_input.json

# Run tests
pytest tests/ -v
```

### 3D Simulator
```bash
# Start the web server
python main.py --serve

# Custom port
python main.py --serve --port 9000
```
Then open http://localhost:8080 in your browser.

## Requirements
- Python 3.10+
- pytest (for tests only)
- Modern browser with WebGL support (for 3D simulator)

```bash
pip install -r requirements.txt
```

## 3D Simulator

The web-based simulator lets you configure every parameter, build scenarios visually, and watch the drone execute the mission in real time.

**Features:**
- Full parameter panel: battery capacity, wind multipliers, payload penalties, grid size
- Interactive obstacle editor (click grid cells to toggle)
- Package and weather segment management
- 5 preset scenarios (default, low battery, heavy wind, small grid, no wind penalty)
- GLTF quadcopter drone model with Three.js rendering
- Smooth tick-by-tick animation with interpolation
- Playback controls: play/pause, step forward/back, reset, speed adjustment
- Live HUD: battery gauge, tick counter, wind direction, active package, phase
- Mission summary with delivery stats

**Architecture:** Python stdlib HTTP server serves static files and exposes two JSON API endpoints (`POST /api/simulate`, `GET /api/defaults`). The frontend uses Three.js (loaded from CDN) with no build step required.

## Configurable Parameters

All simulation parameters can be overridden via the input JSON `config` section or the web UI:

```json
{
  "grid_width": 20,
  "grid_height": 20,
  "config": {
    "battery_capacity": 50,
    "wind_against_multiplier": 4.0
  },
  "manifest": [...],
  "weather_forecast": [...],
  "obstacles": [...]
}
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `battery_capacity` | 100 | Max battery units per round trip |
| `base_move_cost` | 1.0 | Base cost per grid move |
| `wind_with_multiplier` | 0.5 | Cost multiplier when moving with wind |
| `wind_against_multiplier` | 2.0 | Cost multiplier when moving against wind |
| `wind_cross_multiplier` | 1.0 | Cost multiplier for perpendicular wind |
| `payload_penalty_rate` | 0.10 | Penalty per weight increment (10%) |
| `payload_penalty_increment_lbs` | 5.0 | Weight threshold for each penalty step |

## Architecture

The system is built in 8 layers, each with a single responsibility and independently testable:

**Cost Calculator** (`core/cost_calculator.py`) — Pure stateless functions that compute movement costs given wind direction, move direction, and payload weight. This is the mathematical foundation: `final_cost = base_cost x wind_multiplier x payload_multiplier`. All 7 reference values from the spec are verified in tests.

**Pathfinder** (`core/pathfinder.py`) — Two pathfinding algorithms. `find_path` is standard A* with Manhattan heuristic. `find_path_cost_aware` is a time-aware A* where edge costs incorporate wind direction at each tick — the same coordinate at different ticks is a different state because wind shifts affect cost. This means a physically longer path may consume less battery if it aligns with favorable wind.

**Delivery Planner** (`core/delivery_planner.py`) — Since the drone carries one package at a time, each delivery is a round trip from base. The optimization problem is: *in what order should we deliver?* For manifests of 8 or fewer packages, the planner tries all permutations (8! = 40,320) and picks the ordering with minimum total battery. For larger manifests, it falls back to a wind-aware greedy heuristic.

**Simulation Engine** (`core/simulation_engine.py`) — An independent tick-by-tick executor that validates the plan. It recomputes all costs from scratch using the Cost Calculator — it never trusts the planner's pre-computed values. If the planner has a bug, the simulator catches the discrepancy. This is defense-in-depth: the same pattern used in flight-critical software where independent channels verify each other.

**Web Server** (`server.py`) — Python stdlib HTTP server that serves the 3D frontend and exposes a JSON API for running simulations from the browser.

The remaining layers handle domain models (`models/`), configuration (`config.py` with `SimulationConfig` dataclass), input parsing/validation (`io/input_loader.py`), and output formatting (`io/output_formatter.py`).

## Key Design Decisions

- **Floor division for payload penalty:** `floor(weight / 5)` increments. A 12-lb package gets `floor(12/5) = 2` increments = 1.2x multiplier.
- **Wind-aware greedy heuristic** for delivery ordering — good enough for small manifests, clearly improvable with branch-and-bound for larger ones. Exhaustive permutation search for <= 8 packages.
- **Time-aware A* pathfinding:** Node state is `(coordinate, tick)` because wind changes over time. Heuristic is `manhattan * 0.5` (admissible — minimum possible cost per move).
- **Simulation engine as independent validator:** Defense-in-depth. The simulator recomputes costs from first principles and logs warnings on any discrepancy with the planner.
- **SimulationConfig dataclass:** All parameters injectable via frozen dataclass. Functions accept optional `config=None` for full backward compatibility — existing call sites and tests required zero changes.
- **Stdlib-only web server:** No Flask/Django dependency. Python's built-in `http.server` with custom handler keeps the project dependency-free.
- **Input validation collects all errors:** Doesn't fail on the first error — reports everything at once.

## Assumptions

1. Payload penalty uses **floor division**: `floor(weight / 5)` increments.
2. Battery tracked as **float** — no per-move rounding.
3. Arriving at (0,0) with exactly 0.0 battery is **not a crash**.
4. Tick advances by 1 per movement. Battery swap, pickup, drop-off are **instant (0 ticks)**.
5. Coordinates are **[x, y]**: x = column (East/West), y = row (North/South). (0,0) = southwest corner.
6. Infeasible deliveries are **reported, not skipped silently**.
7. **No external Python dependencies** beyond Python stdlib + pytest.

## AI Log

This project was built with Claude Code (Claude Opus 4.6). The AI was given a detailed specification and produced the implementation layer-by-layer, running tests after each step.

**What went well:**
- The layered architecture translated cleanly from spec to code. Each layer was implemented and tested independently before moving on.
- All 7 reference cost values matched on the first implementation — the cost calculator formulas were straightforward.
- The time-aware A* pathfinder worked correctly on the first pass, including proper tick-state tracking.
- The permutation optimizer found the optimal delivery ordering (125.10 battery for the sample input).
- The config refactoring (adding `SimulationConfig` with optional `config=None` params) preserved all 55 existing tests with zero changes — clean backward compatibility.
- The 3D web frontend was built with vanilla JS modules and Three.js from CDN, requiring no build tools or bundler setup.

**What needed attention:**
- Setting up the Python environment (venv, pytest installation) required a few iterations to get the right Python path on macOS.
- The coordinate convention (NORTH = +y, EAST = +x, origin at southwest) needed careful consistency across Direction.to_delta(), pathfinder, cost calculator, and the 3D scene (where Z maps to the grid Y axis).

**What I'd improve with more time:**
- Add branch-and-bound pruning for the permutation search to handle larger manifests efficiently.
- Add property-based testing (Hypothesis) for the cost calculator to catch edge cases.
- Add wind direction visualization in the 3D scene (particle effects or animated arrows).
- Path trail rendering showing the drone's trajectory on the grid.
- The greedy fallback could be improved with a look-ahead heuristic that considers wind forecasts.
