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
- Algorithm configuration panel: delivery ordering strategy, pathfinding choice, safety toggles
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

---

## AI Log

This section documents the full AI-assisted development process, from initial research through final implementation.

### 1. Initial Prompt Curated by ChatGPT

The process began with ChatGPT (5.4 thinking model) analyzing the Cenith Innovations take-home assessment. ChatGPT was used to research the company, deconstruct the exercise requirements, identify implicit expectations, and frame the problem strategically for a defense-tech audience.

**Output:** [`docs/Cenith_Weather_Aware_Dispatcher_Strategic_Analysis.md`](docs/Cenith_Weather_Aware_Dispatcher_Strategic_Analysis.md)

This document covers company-aware framing, exercise deconstruction, what the reviewers are testing for, and five candidate solution archetypes (A through E) with tradeoff analysis for each.

### 2. Claude Cowork to Generate Various Approaches

The strategic analysis was given to Claude (via Cowork/collaborative mode) to generate and evaluate multiple solution approaches. Claude explored the five archetypes in depth:

- **Archetype A:** Greedy Nearest-Neighbor with static A*
- **Archetype B:** Time-Aware A* with exhaustive permutation search
- **Archetype C:** Simulation-Driven with Strategy Pattern
- **Archetype D:** Graph-Based state-space search
- **Archetype E:** Hybrid Domain-Driven Architecture

Each approach was evaluated on correctness, complexity, maintainability, failure modes, and strategic fit for Cenith's engineering culture.

### 3. Chose Hybrid Approach (Archetype E)

Selected Archetype E — Hybrid Domain-Driven Architecture — as the best balance of:
- Production-mindedness over academic purity
- Safety as a structural guarantee (defense-in-depth simulation validation)
- Domain modeling that mirrors real drone operations
- Independently testable layers
- Extensibility without over-engineering

This decision was based on synthesizing insights from all five archetypes. For example, the permutation optimization from Archetype B was incorporated as a bonus for small manifests, while the simulation backbone from Archetype C became the independent validator.

**Full hypothetical analysis:** [`docs/Cenith_Weather_Aware_Dispatcher_Strategic_Analysis.md`](docs/Cenith_Weather_Aware_Dispatcher_Strategic_Analysis.md) (Sections 4-5)

### 4. Claude Cowork to Create Technical Specification

The chosen approach was developed into a detailed technical specification with Claude Cowork. This spec defined every layer, every data structure, every function signature, all edge cases, reference test values, and exact implementation order.

**Output:** [`docs/WEATHER_AWARE_DISPATCHER_SPEC.md`](docs/WEATHER_AWARE_DISPATCHER_SPEC.md)

### 5. Gave Spec to Claude Code CLI — Entered Plan Mode

The full specification was given to a fresh Claude Code CLI session (Claude Opus 4.6). Claude Code entered plan mode, analyzed the spec, produced a file-by-file implementation plan with build order and test gates, and awaited approval before writing any code.

### 6. Reviewed Plan and Gave Permission to Proceed

Reviewed the plan for alignment with the spec. The plan correctly identified:
- Layer-by-layer build order with test gates after each step
- Config constants first, then models, then cost calculator, etc.
- All 7 reference cost values as gate criteria for the cost calculator step
- 55+ tests across 7 test files

Approved the plan. Claude Code began implementation.

### 7. CLI Plan Passed All Tests

Claude Code implemented each layer sequentially, running `pytest` after every step:
- **Step 1-2:** Config + Models — 14 tests pass
- **Step 3:** Cost Calculator — 17 tests pass (all 7 reference values exact)
- **Step 4:** Pathfinder — 6 tests pass
- **Step 5:** Input Loader — 6 tests pass
- **Step 6:** Delivery Planner — 4 tests pass
- **Step 7:** Simulation Engine — 4 tests pass
- **Step 8-9:** Output Formatter + Main entry — CLI runs end-to-end
- **Step 10:** Integration tests — 4 tests pass

**Final result:** 55/55 tests pass. `python main.py sample_input.json` delivers 3/3 packages, 125.10 battery consumed, optimal ordering found via permutation search.

### 8. Decided to Add Visual Simulation

Wanted the ability to visually test various permutations of scenarios — grid size, weather impacts, payload weight, obstacles, etc. Requested a browser-based 3D simulator.

Downloaded a GLTF quadcopter drone model to use as the 3D drone asset in the simulation, providing a realistic visual representation rather than placeholder geometry.

Claude Code designed and built:
- `SimulationConfig` dataclass making all physics constants injectable (backward compatible — 55 tests still pass with zero changes)
- Python stdlib HTTP server with JSON API (`/api/simulate`, `/api/defaults`)
- Three.js 3D frontend with the downloaded GLTF quadcopter model loaded via GLTFLoader (with fallback geometry if model fails to load)
- Full parameter panel, 5 preset scenarios, tick-by-tick animation with playback controls
- Live HUD with battery gauge, wind direction, phase tracking

### 9. Tests Passed

After the 3D simulator addition, all 55 original tests continued to pass. The config refactoring used optional `config=None` parameters throughout, preserving every existing call site.

### 10. Added Branding, UI Polish, Algorithm Configuration

Applied Cenith Innovations branding:
- Gold/amber accent palette from company logo
- Inter + JetBrains Mono typography
- Logo header with branded identity

Added right-side algorithm configuration panel:
- Delivery ordering strategy (Auto/Permutation/Greedy)
- Permutation threshold slider with complexity notes
- Pathfinding algorithm choice (Wind-Aware A* vs Standard A*)
- Safety toggles (simulator cross-check, strict battery)
- Movement rules reference cards and cost formula display

Production polish: parameter cards, toggle switches, phase-colored HUD, focus-visible accessibility, hover transitions.

### 11. Committed and Pushed Changes

Three commits to `main`, pushed to GitHub:

1. `28aecb3` — Initial Weather-Aware Dispatcher CLI application (55 tests, full pipeline)
2. `0dec8c7` — 3D web simulator and configurable simulation parameters
3. `435f976` — Cenith branding, UI polish, algorithm configuration panel

---

**Tools used:** ChatGPT (5.4 thinking model) for strategic analysis, Claude Cowork for approach evaluation and spec writing, Claude Code CLI (Opus 4.6) for all implementation.

**What AI got right:** The layered architecture, cost calculator math, time-aware A*, permutation optimizer, config refactoring, and 3D frontend all worked correctly on the first implementation. The layer-by-layer build order with test gates prevented regressions throughout.

**What needed human judgment:** Choosing the hybrid approach from five candidates, deciding to add the visual simulator, branding direction, and the decision to include algorithm configuration as a right-panel feature rather than buried in settings.
