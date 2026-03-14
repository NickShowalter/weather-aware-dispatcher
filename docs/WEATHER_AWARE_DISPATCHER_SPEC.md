# Technical Specification & Implementation Prompt: The Weather-Aware Dispatcher

## ROLE & CONTEXT

You are a Senior Software Engineer implementing a take-home assessment for Cenith Innovations, a defense-tech company that builds autonomous drone systems (route optimization, swarm UAS, battlefield planning AI). This is not a toy exercise — the reviewers build real drone software. They care far more about **how you structure your code, handle edge cases, and solve problems** than getting a perfectly optimized routing algorithm. Treat the submission as if you were submitting a large PR at your job.

**Deadline:** Thursday, March 19, 2026
**Time budget intent:** 3–4 hours (but the architecture should look like it came from someone who thinks in systems, not scripts)
**Delivery format:** GitHub repository

---

## THE PROBLEM

Build a Python application that routes a single delivery drone on a grid to deliver a manifest of packages. The drone starts at the Launch Pad (0,0) with a full battery, must deliver all packages, and return to (0,0) while minimizing total battery consumed. Wind conditions change over time and affect battery cost directionally. Packages have weight that adds a penalty. The grid contains impassable obstacles.

---

## EXACT RULES & CONSTRAINTS (from the assessment — follow these precisely)

### 1. Movement & Distance
- Grid is 20×20 (coordinates 0,0 to 19,19).
- Drone can only move North, South, East, West. NO diagonal movement.
- 1 movement = 1 "tick" of time.

### 2. Battery & Base Cost
- Maximum battery capacity: **100 units**.
- Base cost to move 1 grid space: **1 battery unit**.
- If the drone runs out of battery before returning to (0,0), **it crashes** (this is a failure condition).
- The drone can return to (0,0) at **any time** to instantly swap to a fresh battery (reset to 100 units).

### 3. The Wind Factor
Wind affects battery drain. Wind direction changes based on the current "tick" (time step).
- Moving **with** the wind: cost becomes **0.5 units**.
- Moving **against** the wind: cost becomes **2.0 units**.
- Moving **cross-wind** (perpendicular): cost remains **1.0 unit**.
- Example: If wind is blowing EAST → moving East costs 0.5, moving West costs 2.0, moving North or South costs 1.0.

### 4. Payload Penalty
- Every **5 lbs** of payload adds a flat **10% penalty** to the final battery consumption of a move (calculated **after** wind is applied).
- The drone can only carry **one package at a time**.
- It drops the package at the destination, **immediately shedding the weight penalty**.
- A 0 lb or <5 lb package contributes 0 penalty increments (we use floor division: `floor(weight / 5)`).

### 5. Obstacles
- Certain grid coordinates are impassable. The drone cannot enter these cells.

### 6. Weather Forecast
- Time-segmented wind directions provided in input.
- The last segment may have `end_tick: null`, meaning it lasts indefinitely.
- Wind direction is one of: `"NORTH"`, `"SOUTH"`, `"EAST"`, `"WEST"`.

---

## SAMPLE INPUT FORMAT

The application reads a JSON file specified as a command-line argument.

```json
{
  "grid_width": 20,
  "grid_height": 20,
  "manifest": [
    {"id": "pkg_1", "destination": [18, 18], "weight_lbs": 5},
    {"id": "pkg_2", "destination": [2, 15], "weight_lbs": 10},
    {"id": "pkg_3", "destination": [15, 2], "weight_lbs": 2}
  ],
  "weather_forecast": [
    {"direction": "EAST", "start_tick": 0, "end_tick": 49},
    {"direction": "NORTH", "start_tick": 50, "end_tick": 99},
    {"direction": "WEST", "start_tick": 100, "end_tick": null}
  ],
  "obstacles": [
    [5, 5],
    [5, 6],
    [5, 7],
    [12, 15],
    [12, 16]
  ]
}
```

---

## REQUIRED DELIVERABLES

1. **The Code:** A well-structured, object-oriented Python application that outputs the sequence of deliveries, the step-by-step path, and the total battery consumed.
2. **Unit Tests:** At least 2–3 tests proving cost-calculation math (wind + weight) works correctly.
3. **README & AI Log:** A brief markdown file with instructions on how to run the code, plus an AI Log section.

---

## ARCHITECTURE: HYBRID DOMAIN-DRIVEN DESIGN (Archetype E)

You MUST implement the following layered architecture. This is a deliberate design choice — each layer has a single responsibility, is independently testable, and mirrors how real autonomous systems are built.

### Layer 1: Domain Models (value objects and entities)

```
Coordinate (value object — immutable)
├── x: int
├── y: int
├── manhattan_distance(other: Coordinate) → int
├── __eq__, __hash__ (for use in sets and dicts)
└── neighbors() → List[Coordinate]  (N/S/E/W only)

Direction (enum)
├── NORTH, SOUTH, EAST, WEST
├── opposite() → Direction
├── is_perpendicular(other: Direction) → bool
└── to_delta() → Tuple[int, int]  (e.g., EAST → (1, 0), NORTH → (0, 1))

Package (entity)
├── id: str
├── destination: Coordinate
├── weight_lbs: float
└── weight_penalty_multiplier → float  (computed property: 1.0 + floor(weight_lbs / 5) * 0.10)

Grid (value object)
├── width: int
├── height: int
├── obstacles: FrozenSet[Coordinate]
├── is_valid(coord: Coordinate) → bool  (in bounds AND not an obstacle)
├── passable_neighbors(coord: Coordinate) → List[Coordinate]
└── is_reachable(start: Coordinate, end: Coordinate) → bool  (BFS connectivity check)

WeatherSegment (value object)
├── direction: Direction
├── start_tick: int
├── end_tick: Optional[int]  (None = indefinite)
└── contains_tick(tick: int) → bool

WeatherForecast (value object)
├── segments: List[WeatherSegment]
└── wind_at_tick(tick: int) → Direction
    (must handle: null end_tick, tick beyond all segments, tick exactly on boundaries)

DroneState (immutable value object — a snapshot of drone state at a point in time)
├── position: Coordinate
├── battery: float
├── tick: int
├── carrying: Optional[Package]
├── delivered: FrozenSet[str]  (package IDs)
└── is_at_base → bool
```

**IMPORTANT COORDINATE CONVENTION:** Use `[x, y]` where x = column (East/West axis) and y = row (North/South axis). EAST increases x. NORTH increases y. This must be consistent everywhere.

**IMPORTANT DIRECTION MAPPING:**
- NORTH → (0, +1) — y increases
- SOUTH → (0, -1) — y decreases
- EAST  → (+1, 0) — x increases
- WEST  → (-1, 0) — x decreases

### Layer 2: Cost Calculator (pure, stateless functions)

```
CostCalculator (stateless — all methods are pure functions)

├── wind_multiplier(move_direction: Direction, wind_direction: Direction) → float
│   Rules:
│   - move_direction == wind_direction → 0.5  (with wind)
│   - move_direction == wind_direction.opposite() → 2.0  (against wind)
│   - otherwise → 1.0  (cross-wind / perpendicular)
│
├── payload_multiplier(weight_lbs: float) → float
│   Formula: 1.0 + floor(weight_lbs / 5) * 0.10
│   Examples:
│   - 0 lbs → 1.0 (no penalty)
│   - 2 lbs → 1.0 (floor(2/5)=0, no penalty)
│   - 5 lbs → 1.1 (floor(5/5)=1, 10% penalty)
│   - 10 lbs → 1.2 (floor(10/5)=2, 20% penalty)
│   - 12 lbs → 1.2 (floor(12/5)=2, 20% penalty — NOT ceil)
│   - 25 lbs → 1.5 (floor(25/5)=5, 50% penalty)
│
├── move_cost(move_direction: Direction, wind_direction: Direction, weight_lbs: float) → float
│   Formula: BASE_COST × wind_multiplier × payload_multiplier
│   Where BASE_COST = 1.0
│   This is THE core formula. Everything flows through here.
│   Examples:
│   - East with East wind, 0 lbs: 1.0 × 0.5 × 1.0 = 0.5
│   - West with East wind, 0 lbs: 1.0 × 2.0 × 1.0 = 2.0
│   - East with East wind, 5 lbs: 1.0 × 0.5 × 1.1 = 0.55
│   - West with East wind, 10 lbs: 1.0 × 2.0 × 1.2 = 2.4
│   - North with East wind, 5 lbs: 1.0 × 1.0 × 1.1 = 1.1
│
└── estimate_path_cost(path: List[Coordinate], start_tick: int, weather: WeatherForecast, weight_lbs: float) → float
    Walks the path step-by-step, incrementing tick, looking up wind_at_tick for each move,
    and summing move_cost for each step. This is the tick-aware cost estimator.
```

**CRITICAL:** The `move_cost` function is the single source of truth for battery consumption. Every other part of the system calls this. It must be correct. Test it exhaustively.

### Layer 3: Pathfinder (obstacle-aware routing)

```
Pathfinder (depends on Grid)

├── find_path(start: Coordinate, end: Coordinate, grid: Grid) → Optional[List[Coordinate]]
│   Uses A* (or BFS since grid is small) to find the shortest physical path around obstacles.
│   Returns the sequence of coordinates from start to end (inclusive of both).
│   Returns None if the destination is unreachable.
│   Heuristic for A*: Manhattan distance.
│
└── find_path_cost_aware(
│       start: Coordinate,
│       end: Coordinate,
│       grid: Grid,
│       start_tick: int,
│       weather: WeatherForecast,
│       weight_lbs: float
│   ) → Optional[Tuple[List[Coordinate], float]]
│
│   Time-aware A* variant where edge costs use move_cost() with the wind at the
│   current tick. This finds the CHEAPEST path (not necessarily shortest) accounting
│   for wind conditions at the time of traversal.
│
│   The g-cost for each node is actual battery consumed (using move_cost with tick-aware wind).
│   The h-cost heuristic: Manhattan distance × minimum possible move cost (0.5) — admissible.
│   Each node in the open set tracks: (coordinate, tick, g_cost).
│
│   Returns (path, total_battery_cost) or None if unreachable.
```

**DESIGN NOTE:** The cost-aware pathfinder is what makes this solution senior-level. A naive approach uses physical shortest path then applies cost afterward, but that ignores the fact that wind changes during traversal and that a physically longer path may be cheaper if it aligns with wind direction.

### Layer 4: Delivery Planner (scheduling/ordering logic)

```
DeliveryPlanner

├── plan_deliveries(
│       manifest: List[Package],
│       grid: Grid,
│       weather: WeatherForecast,
│       battery_capacity: float = 100.0,
│       safety_margin: float = 0.0
│   ) → DeliveryPlan
│
│   This is the brain. It decides:
│   (a) What ORDER to deliver packages
│   (b) WHEN to return to base for battery swap
│
│   ALGORITHM — Wind-Aware Nearest-Neighbor with Safe Recharge Insertion:
│
│   1. Start at (0,0) with full battery at tick=0.
│   2. For each undelivered package, estimate the cost of:
│      - Flying from current position to pickup (always base, since we carry one at a time)
│        Actually — since the drone carries one package at a time and picks up from base,
│        the sequence is always: base → destination → base → destination → base → ...
│        So the delivery order IS the key decision.
│   3. For each candidate next delivery:
│      a. Compute cost to fly from (0,0) to destination with that package's weight, using
│         cost-aware pathfinder starting at the current tick.
│      b. Compute cost to fly from destination back to (0,0) with 0 weight (empty return),
│         using cost-aware pathfinder starting at tick after arriving.
│      c. Total round-trip cost = outbound + return.
│      d. Check: is round-trip cost ≤ battery_capacity - safety_margin? If not, the delivery
│         is INFEASIBLE and should be flagged.
│   4. Among feasible candidates, pick the one with lowest round-trip cost
│      (greedy nearest-neighbor by cost, not distance).
│   5. Add this delivery to the plan. Update tick. Battery swaps to 100 at base.
│   6. Repeat until all packages are delivered or remaining packages are infeasible.
│   7. The final action is always: return to (0,0) (which is already the case since
│      every delivery ends with a return to base).
│
│   IMPORTANT REALIZATION: Because the drone carries ONE package at a time, every delivery
│   is a round trip from base: (0,0) → destination → (0,0). The drone always gets a fresh
│   battery between deliveries. The optimization problem reduces to:
│   "What ORDER should we do these round trips in, given that wind changes with tick count?"
│
│   This is a key insight. The ordering matters because wind conditions change — delivering
│   an eastern package during eastward wind is cheaper than during westward wind. The greedy
│   heuristic approximates this by choosing the cheapest round trip at each step, but the
│   globally optimal order may differ.
│
│   For BONUS SOPHISTICATION (if time allows): try all permutations for small manifests
│   (≤ 8 packages → 8! = 40,320 permutations is tractable) and pick the one with lowest
│   total battery across all round trips. Fall back to greedy for larger manifests.
│
│   EDGE CASE — infeasible deliveries:
│   If a round trip exceeds 100 battery units under any wind condition, it cannot be
│   delivered. The planner must report these clearly, deliver everything else, and NOT crash.
│
└── Returns: DeliveryPlan
        ├── planned_deliveries: List[PlannedDelivery]
        │   Each contains: package, outbound_path, return_path, outbound_cost, return_cost,
        │   start_tick, wind_conditions_during_leg
        ├── infeasible_packages: List[Tuple[Package, str]]  (package + reason)
        ├── total_battery_consumed: float
        └── total_ticks: int
```

### Layer 5: Simulation Engine (validation + execution + output)

```
SimulationEngine

├── execute(plan: DeliveryPlan, grid: Grid, weather: WeatherForecast) → SimulationResult
│
│   Tick-by-tick executor. Takes the plan from the DeliveryPlanner and simulates it
│   step by step to:
│   (a) VALIDATE that the plan is safe (battery never hits 0 away from base)
│   (b) Produce the detailed execution log (the required output)
│   (c) Compute the authoritative total battery consumed
│
│   For each planned delivery:
│   1. Assert drone is at (0,0) with full battery.
│   2. Walk the outbound path step by step:
│      - For each move, compute move_cost using current tick's wind + package weight.
│      - Deduct from battery. Log the move.
│      - Advance tick.
│      - SAFETY CHECK: if battery would go to 0 or below, ABORT and report error.
│   3. At destination: drop package. Log delivery. Weight penalty stops.
│   4. Walk the return path step by step:
│      - For each move, compute move_cost using current tick's wind + 0 weight (empty).
│      - Deduct from battery. Log the move.
│      - Advance tick.
│      - SAFETY CHECK: same as above.
│   5. At (0,0): battery swap. Log recharge event.
│   6. Repeat for next delivery.
│
│   The simulation engine is INDEPENDENT from the planner. It re-computes all costs from
│   scratch using the same CostCalculator. This is defense-in-depth: if the planner has a
│   bug in cost estimation, the simulator will catch the discrepancy.
│
└── Returns: SimulationResult
        ├── success: bool
        ├── moves: List[MoveRecord]  (tick, from, to, direction, wind, cost, battery_after)
        ├── deliveries: List[DeliveryRecord]  (package_id, tick_delivered, leg_cost)
        ├── recharges: List[RechargeRecord]  (tick, battery_before)
        ├── total_battery_consumed: float
        ├── total_ticks: int
        ├── packages_delivered: int
        └── error: Optional[str]  (if simulation failed, why)
```

### Layer 6: Input Loader & Validator

```
InputLoader

├── load(filepath: str) → Result[MissionData, List[str]]
│
│   Reads JSON, parses into domain objects, and validates EVERYTHING:
│
│   Structural validation:
│   - File exists and is valid JSON.
│   - All required top-level keys present: grid_width, grid_height, manifest, weather_forecast, obstacles.
│   - Manifest entries have: id, destination, weight_lbs.
│   - Weather entries have: direction, start_tick, end_tick.
│
│   Semantic validation:
│   - Grid dimensions are positive integers.
│   - All destination coordinates are within grid bounds.
│   - All obstacle coordinates are within grid bounds.
│   - No destination is on an obstacle.
│   - (0,0) is not an obstacle.
│   - Package weights are non-negative numbers.
│   - Package IDs are unique.
│   - Weather segments don't have gaps (each start_tick = previous end_tick + 1, or 0 for first).
│   - Weather directions are valid enum values.
│   - Weather covers tick 0.
│   - All destinations are reachable from (0,0) via BFS (considering obstacles).
│
│   Returns either a validated MissionData object or a list of all validation errors found.
│   Do NOT fail on first error — collect all errors and report them together.
│
└── MissionData (validated container)
        ├── grid: Grid
        ├── manifest: List[Package]
        ├── weather: WeatherForecast
        └── battery_capacity: float (default 100.0)
```

### Layer 7: Output Formatter

```
OutputFormatter

├── format_result(result: SimulationResult, mission: MissionData) → str
│
│   Produces clean, readable output. Required sections:
│
│   === DELIVERY SEQUENCE ===
│   1. pkg_2 → (2, 15) [weight: 10 lbs]
│   2. pkg_3 → (15, 2) [weight: 2 lbs]
│   3. pkg_1 → (18, 18) [weight: 5 lbs]
│
│   === DELIVERY DETAILS ===
│   --- Delivery 1: pkg_2 ---
│   Outbound: (0,0) → (2,15) | 17 moves | Cost: 18.7 | Wind: EAST
│   Path: (0,0)→(1,0)→(2,0)→(2,1)→...→(2,15)
│   Return:  (2,15) → (0,0) | 17 moves | Cost: 15.0 | Wind: EAST
│   Path: (2,15)→(2,14)→...→(0,0)
│   Round trip cost: 33.7 | Battery swap at tick 34
│
│   [repeat for each delivery]
│
│   === SUMMARY ===
│   Packages delivered: 3/3
│   Total battery consumed: 94.2 units
│   Total ticks: 102
│   Battery swaps: 3
│   Infeasible packages: 0
│
│   Keep output readable but informative. Think "flight plan" not "debug log."
```

### Layer 8: Main Entry Point

```
main.py (CLI entry point)

├── Parse command-line argument for JSON file path (use argparse).
├── Load and validate input via InputLoader.
│   - If validation fails → print all errors, exit with non-zero code.
├── Create CostCalculator, Pathfinder, DeliveryPlanner.
├── Generate delivery plan via DeliveryPlanner.
├── Execute plan via SimulationEngine.
├── Format and print result via OutputFormatter.
├── Exit with 0 on success.
│
│   Usage: python main.py input.json
│   Or:    python -m weather_aware_dispatcher input.json
```

---

## PROJECT STRUCTURE

```
weather-aware-dispatcher/
├── README.md
├── requirements.txt                  (if any deps beyond stdlib — prefer none)
├── sample_input.json                 (the sample from the assessment)
├── weather_aware_dispatcher/
│   ├── __init__.py
│   ├── __main__.py                   (allows `python -m weather_aware_dispatcher`)
│   ├── main.py                       (CLI entry point)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── coordinate.py
│   │   ├── direction.py
│   │   ├── package.py
│   │   ├── grid.py
│   │   ├── weather.py
│   │   └── drone_state.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── cost_calculator.py
│   │   ├── pathfinder.py
│   │   ├── delivery_planner.py
│   │   └── simulation_engine.py
│   ├── io/
│   │   ├── __init__.py
│   │   ├── input_loader.py
│   │   └── output_formatter.py
│   └── config.py                     (constants: BATTERY_CAPACITY, BASE_MOVE_COST, etc.)
└── tests/
    ├── __init__.py
    ├── test_cost_calculator.py        (REQUIRED — the 2-3 tests they asked for, plus more)
    ├── test_pathfinder.py
    ├── test_delivery_planner.py
    ├── test_simulation_engine.py
    ├── test_input_loader.py
    ├── test_models.py
    └── test_integration.py            (end-to-end with sample input)
```

---

## CONFIGURATION CONSTANTS (config.py)

```python
BATTERY_CAPACITY = 100.0
BASE_MOVE_COST = 1.0
WIND_WITH_MULTIPLIER = 0.5
WIND_AGAINST_MULTIPLIER = 2.0
WIND_CROSS_MULTIPLIER = 1.0
PAYLOAD_PENALTY_RATE = 0.10       # 10% per increment
PAYLOAD_PENALTY_INCREMENT = 5.0   # every 5 lbs
LAUNCH_PAD = Coordinate(0, 0)
```

All magic numbers live here. Nothing is hardcoded in business logic.

---

## UNIT TEST REQUIREMENTS (MINIMUM)

### Required tests (cost calculator — what the assessment explicitly asks for):

```
test_move_with_wind_no_payload:
    move East, wind East, 0 lbs → 0.5

test_move_against_wind_no_payload:
    move West, wind East, 0 lbs → 2.0

test_move_crosswind_no_payload:
    move North, wind East, 0 lbs → 1.0

test_move_with_wind_and_payload:
    move East, wind East, 5 lbs → 0.55
    move East, wind East, 10 lbs → 0.60

test_move_against_wind_and_payload:
    move West, wind East, 10 lbs → 2.4

test_payload_penalty_floor_division:
    2 lbs → multiplier 1.0  (floor(2/5) = 0)
    5 lbs → multiplier 1.1  (floor(5/5) = 1)
    7 lbs → multiplier 1.1  (floor(7/5) = 1)
    12 lbs → multiplier 1.2 (floor(12/5) = 2)

test_zero_weight:
    0 lbs → multiplier 1.0
```

### Additional tests (demonstrate thoroughness):

```
test_pathfinder_straight_line:
    (0,0) to (3,0) with no obstacles → [(0,0),(1,0),(2,0),(3,0)]

test_pathfinder_around_obstacle:
    obstacle at (1,0), (0,0) to (2,0) → path goes around via (0,1),(1,1),(2,1),(2,0)

test_pathfinder_unreachable:
    destination fully walled off → returns None

test_wind_at_tick_boundary:
    tick 49 → EAST, tick 50 → NORTH (from sample data)

test_wind_at_null_end_tick:
    tick 100, 200, 10000 → all return WEST (from sample data)

test_simulation_matches_planner:
    run planner → run simulator on the plan → costs match

test_full_sample_input:
    load sample_input.json → plan → simulate → all 3 packages delivered, drone at base, no crash
```

Use `pytest` as the test runner. No external test dependencies beyond pytest.

---

## EXPLICIT ASSUMPTIONS (document these in the README)

1. **Payload penalty uses floor division:** `floor(weight_lbs / 5)` determines the number of 5-lb increments. A 3-lb package has 0 penalty increments (multiplier = 1.0). This interpretation follows the "every 5 lbs" language literally.
2. **Battery is tracked as a float.** No rounding per move. The running total accumulates fractional values.
3. **Arriving at (0,0) with exactly 0.0 battery is NOT a crash.** The drone is home.
4. **The tick counter advances by 1 for each movement.** Battery swap, package pickup, and package drop-off are instant (0 ticks).
5. **Coordinates are [x, y]:** x is the column (East/West), y is the row (North/South). (0,0) is the bottom-left / southwest corner of the grid.
6. **If a delivery's round-trip cost exceeds battery capacity under current wind conditions, it is reported as infeasible** rather than silently skipped or causing a crash.
7. **No external dependencies beyond Python standard library and pytest.** The solution should be self-contained.

---

## EDGE CASES TO HANDLE

1. **Empty manifest** → output success with 0 deliveries, 0 battery consumed.
2. **Package destination at (0,0)** → deliver instantly with 0 cost (already there).
3. **Package destination is an obstacle** → report as infeasible during input validation.
4. **Destination unreachable due to obstacles** → report as infeasible during input validation.
5. **Weight is 0** → penalty multiplier = 1.0, no crash.
6. **Negative weight in input** → validation error.
7. **Weather gaps between segments** → validation error.
8. **Tick exactly on a weather boundary** → must use the new segment's wind (the segment whose start_tick matches).
9. **Fractional battery remaining** → no rounding, track as float.
10. **Obstacles forming a wall** → A* routes around; if fully enclosed, mark unreachable.
11. **Single package manifest** → straightforward single round trip.
12. **All packages at the same destination** → should work, each is a separate round trip.
13. **Very heavy package (e.g., 50 lbs)** → 100% penalty, outbound cost doubled. May be infeasible for far destinations.

---

## WHAT NOT TO DO

- **Do NOT over-optimize.** The assessment explicitly says they care more about structure, edge cases, and problem-solving than mathematical perfection. A clean greedy heuristic that is well-tested beats a complex optimizer that is fragile.
- **Do NOT use external optimization libraries** (PuLP, scipy.optimize, OR-Tools). This should be pure Python logic.
- **Do NOT add features not requested** (multiple drones, priority levels, GUI). But DO structure code so these would be easy to add.
- **Do NOT ignore the AI Log deliverable.** Write a genuine, specific section about what AI tools were used and where they got things wrong. This is evaluated.
- **Do NOT hardcode the sample input.** The solution must work with any valid JSON input matching the schema.
- **Do NOT print debug output by default.** Clean output only. Use Python's `logging` module for debug-level information that can be enabled with a flag.

---

## QUALITY SIGNALS TO HIT

These are the things that will make the reviewers think "this person is senior":

1. **The cost calculator is a pure function with zero side effects.** It takes values in, returns a number. No state, no mutation, no god-objects.
2. **The simulation engine re-derives costs independently from the planner.** This is defense-in-depth. If there's a bug in cost estimation during planning, the simulator catches the discrepancy.
3. **Every class has a single, obvious responsibility.** Someone should be able to read the class name and know what it does without reading the implementation.
4. **The output reads like a flight plan.** Delivery sequence, per-leg breakdown, total summary. Operational, not academic.
5. **Input validation is thorough and reports ALL errors at once** — not just the first one found.
6. **Config values are constants, not magic numbers scattered through business logic.**
7. **The README explains WHY, not just HOW.** Two paragraphs of design rationale are worth more than a page of API docs.
8. **Tests go beyond the minimum.** The 2–3 required cost-calculator tests are there, PLUS pathfinder tests, integration tests, and edge case tests. Total test count should be 15–25.

---

## README STRUCTURE

```markdown
# Weather-Aware Dispatcher

## Overview
[1–2 sentences about what this does]

## Quick Start
[Exact commands to run]

## Architecture
[2–3 paragraphs on the layered design and why it's structured this way.
Mention: cost calculator → pathfinder → delivery planner → simulation engine.
Explain that the simulation engine independently validates the plan as defense-in-depth.]

## Key Design Decisions
[Bullet points on the important tradeoffs:
- Floor division for payload penalty
- Greedy heuristic vs exhaustive search and why
- Time-aware pathfinding
- Battery safety approach]

## Running Tests
[Exact pytest command]

## AI Log
[Which tools were used. What they got wrong. How you fixed it. Be specific.]
```

---

## IMPLEMENTATION ORDER (for the coding agent)

Follow this order to build incrementally with testability at each step:

1. **config.py** — constants only. 30 seconds.
2. **models/** — all domain objects. Test with test_models.py.
3. **cost_calculator.py** — pure functions. Test with test_cost_calculator.py. **This is the foundation — get it right.**
4. **pathfinder.py** — A* on grid. Test with test_pathfinder.py.
5. **input_loader.py** — JSON parsing + validation. Test with test_input_loader.py.
6. **delivery_planner.py** — greedy ordering with cost-aware pathfinding. Test with test_delivery_planner.py.
7. **simulation_engine.py** — tick-by-tick executor. Test with test_simulation_engine.py.
8. **output_formatter.py** — clean output rendering.
9. **main.py + __main__.py** — CLI wiring.
10. **test_integration.py** — end-to-end with sample input.
11. **sample_input.json** — the sample from the assessment.
12. **README.md** — last, after you know the full design.

---

## FINAL CHECKLIST BEFORE SUBMISSION

- [ ] `python main.py sample_input.json` runs cleanly and produces correct output
- [ ] `pytest` passes all tests with 0 failures
- [ ] All 3 sample packages are delivered successfully
- [ ] Drone returns to (0,0) at the end
- [ ] Total battery consumed is reported
- [ ] Step-by-step path is shown for each delivery
- [ ] No external dependencies beyond pytest
- [ ] README has run instructions + AI Log
- [ ] Code is well-structured, object-oriented, and uses type hints
- [ ] No hardcoded sample data in business logic
- [ ] Edge cases handled: empty manifest, unreachable destination, heavy package
- [ ] Config values are centralized constants
- [ ] Logging is available but not noisy by default
