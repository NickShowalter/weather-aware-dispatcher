from __future__ import annotations

import math
from typing import Optional

from weather_aware_dispatcher.config import (
    BASE_MOVE_COST,
    DEFAULT_CONFIG,
    PAYLOAD_PENALTY_INCREMENT_LBS,
    PAYLOAD_PENALTY_RATE,
    WIND_AGAINST_MULTIPLIER,
    WIND_CROSS_MULTIPLIER,
    WIND_WITH_MULTIPLIER,
    SimulationConfig,
)
from weather_aware_dispatcher.models.coordinate import Coordinate
from weather_aware_dispatcher.models.direction import DELTA_TO_DIRECTION, Direction
from weather_aware_dispatcher.models.weather import WeatherForecast


def wind_multiplier(
    move_direction: Direction,
    wind_direction: Direction,
    config: Optional[SimulationConfig] = None,
) -> float:
    cfg = config or DEFAULT_CONFIG
    if move_direction == wind_direction:
        return cfg.wind_with_multiplier
    if move_direction == wind_direction.opposite():
        return cfg.wind_against_multiplier
    return cfg.wind_cross_multiplier


def payload_multiplier(
    weight_lbs: float,
    config: Optional[SimulationConfig] = None,
) -> float:
    cfg = config or DEFAULT_CONFIG
    increments = math.floor(weight_lbs / cfg.payload_penalty_increment_lbs)
    return 1.0 + increments * cfg.payload_penalty_rate


def move_cost(
    move_direction: Direction,
    wind_direction: Direction,
    weight_lbs: float,
    config: Optional[SimulationConfig] = None,
) -> float:
    cfg = config or DEFAULT_CONFIG
    return cfg.base_move_cost * wind_multiplier(move_direction, wind_direction, cfg) * payload_multiplier(weight_lbs, cfg)


def direction_from_coords(a: Coordinate, b: Coordinate) -> Direction:
    delta = (b.x - a.x, b.y - a.y)
    direction = DELTA_TO_DIRECTION.get(delta)
    if direction is None:
        raise ValueError(f"Non-adjacent coordinates: {a} -> {b}")
    return direction


def estimate_path_cost(
    path: list[Coordinate],
    start_tick: int,
    weather: WeatherForecast,
    weight_lbs: float,
    config: Optional[SimulationConfig] = None,
) -> float:
    cfg = config or DEFAULT_CONFIG
    total = 0.0
    tick = start_tick
    for i in range(len(path) - 1):
        direction = direction_from_coords(path[i], path[i + 1])
        wind = weather.wind_at_tick(tick)
        total += move_cost(direction, wind, weight_lbs, cfg)
        tick += 1
    return total
