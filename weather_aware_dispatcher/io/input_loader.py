from __future__ import annotations

import json
import logging
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional

from weather_aware_dispatcher.config import DEFAULT_CONFIG, SimulationConfig
from weather_aware_dispatcher.models.coordinate import Coordinate
from weather_aware_dispatcher.models.direction import Direction
from weather_aware_dispatcher.models.grid import Grid
from weather_aware_dispatcher.models.package import Package
from weather_aware_dispatcher.models.weather import WeatherSegment, WeatherForecast

logger = logging.getLogger(__name__)


@dataclass
class InputData:
    grid: Grid
    packages: list[Package]
    weather: WeatherForecast
    config: SimulationConfig = DEFAULT_CONFIG


@dataclass
class LoadResult:
    data: Optional[InputData]
    errors: list[str]

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0 and self.data is not None


def parse_config(raw_config: dict) -> tuple[SimulationConfig, list[str]]:
    """Parse a config dict and overlay on defaults. Returns (config, errors)."""
    errors: list[str] = []
    overrides: dict = {}

    float_fields = {
        "battery_capacity": (0.1, 10000),
        "base_move_cost": (0.01, 100),
        "wind_with_multiplier": (0.01, 10),
        "wind_against_multiplier": (0.01, 10),
        "wind_cross_multiplier": (0.01, 10),
        "payload_penalty_rate": (0.0, 1.0),
        "payload_penalty_increment_lbs": (0.1, 1000),
    }

    for field_name, (lo, hi) in float_fields.items():
        if field_name in raw_config:
            val = raw_config[field_name]
            if not isinstance(val, (int, float)):
                errors.append(f"config.{field_name} must be a number, got: {val}")
            elif val < lo or val > hi:
                errors.append(f"config.{field_name} must be between {lo} and {hi}, got: {val}")
            else:
                overrides[field_name] = float(val)

    if "launch_pad" in raw_config:
        lp = raw_config["launch_pad"]
        if isinstance(lp, list) and len(lp) == 2:
            overrides["launch_pad"] = Coordinate(lp[0], lp[1])
        else:
            errors.append(f"config.launch_pad must be [x, y], got: {lp}")

    config = replace(DEFAULT_CONFIG, **overrides) if overrides else DEFAULT_CONFIG
    return config, errors


def load_input(file_path: str) -> LoadResult:
    """Load and validate input JSON. Collects all errors before returning."""
    errors: list[str] = []

    path = Path(file_path)
    if not path.exists():
        return LoadResult(None, [f"File not found: {file_path}"])

    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return LoadResult(None, [f"Invalid JSON: {e}"])

    return load_from_dict(raw)


def load_from_dict(raw: dict) -> LoadResult:
    """Load and validate from a parsed dict. Used by both file loader and API."""
    errors: list[str] = []

    # --- Config (optional) ---
    config = DEFAULT_CONFIG
    if "config" in raw:
        config, config_errors = parse_config(raw["config"])
        errors.extend(config_errors)

    # --- Structural checks ---
    required_keys = ["grid_width", "grid_height", "manifest", "weather_forecast", "obstacles"]
    for key in required_keys:
        if key not in raw:
            errors.append(f"Missing required key: '{key}'")
    if any(f"Missing required key" in e for e in errors):
        return LoadResult(None, errors)

    # --- Grid ---
    grid_width = raw["grid_width"]
    grid_height = raw["grid_height"]

    if not isinstance(grid_width, int) or grid_width <= 0:
        errors.append(f"grid_width must be a positive integer, got: {grid_width}")
    if not isinstance(grid_height, int) or grid_height <= 0:
        errors.append(f"grid_height must be a positive integer, got: {grid_height}")

    obstacle_set: set[Coordinate] = set()
    for obs in raw["obstacles"]:
        if not isinstance(obs, list) or len(obs) != 2:
            errors.append(f"Obstacle must be [x, y], got: {obs}")
            continue
        coord = Coordinate(obs[0], obs[1])
        if isinstance(grid_width, int) and isinstance(grid_height, int):
            if not (0 <= coord.x < grid_width and 0 <= coord.y < grid_height):
                errors.append(f"Obstacle {coord} is out of grid bounds")
        obstacle_set.add(coord)

    launch = config.launch_pad
    if launch in obstacle_set:
        errors.append(f"Launch pad {launch} cannot be an obstacle")

    grid = None
    if not any("grid_width" in e or "grid_height" in e for e in errors):
        grid = Grid(grid_width, grid_height, frozenset(obstacle_set))

    # --- Packages ---
    packages: list[Package] = []
    seen_ids: set[str] = set()

    for item in raw["manifest"]:
        pkg_id = item.get("id")
        dest = item.get("destination")
        weight = item.get("weight_lbs")

        if pkg_id is None:
            errors.append("Package missing 'id' field")
            continue

        if pkg_id in seen_ids:
            errors.append(f"Duplicate package id: '{pkg_id}'")
        seen_ids.add(pkg_id)

        if dest is None or not isinstance(dest, list) or len(dest) != 2:
            errors.append(f"Package '{pkg_id}': invalid destination: {dest}")
            continue

        if weight is None or not isinstance(weight, (int, float)):
            errors.append(f"Package '{pkg_id}': invalid weight: {weight}")
            continue

        if weight < 0:
            errors.append(f"Package '{pkg_id}': weight cannot be negative ({weight})")
            continue

        coord = Coordinate(dest[0], dest[1])

        if grid is not None:
            if not (0 <= coord.x < grid_width and 0 <= coord.y < grid_height):
                errors.append(f"Package '{pkg_id}': destination {coord} is out of grid bounds")
            elif coord in obstacle_set:
                errors.append(f"Package '{pkg_id}': destination {coord} is on an obstacle")
            elif not grid.is_reachable(launch, coord):
                errors.append(f"Package '{pkg_id}': destination {coord} is unreachable from {launch}")

        packages.append(Package(id=pkg_id, destination=coord, weight_lbs=weight))

    # --- Weather ---
    segments: list[WeatherSegment] = []
    valid_directions = {d.value for d in Direction}

    for seg in raw["weather_forecast"]:
        direction_str = seg.get("direction")
        start_tick = seg.get("start_tick")
        end_tick = seg.get("end_tick")

        if direction_str not in valid_directions:
            errors.append(f"Invalid wind direction: '{direction_str}'")
            continue

        if not isinstance(start_tick, int) or start_tick < 0:
            errors.append(f"Invalid start_tick: {start_tick}")
            continue

        if end_tick is not None and (not isinstance(end_tick, int) or end_tick < start_tick):
            errors.append(f"Invalid end_tick: {end_tick} (must be >= start_tick {start_tick} or null)")
            continue

        segments.append(WeatherSegment(
            direction=Direction(direction_str),
            start_tick=start_tick,
            end_tick=end_tick,
        ))

    if segments:
        min_start = min(s.start_tick for s in segments)
        if min_start > 0:
            errors.append(f"Weather forecast must cover tick 0 (earliest segment starts at {min_start})")

    weather = WeatherForecast(segments) if segments else None

    if errors:
        return LoadResult(None, errors)

    return LoadResult(InputData(grid=grid, packages=packages, weather=weather, config=config), [])
