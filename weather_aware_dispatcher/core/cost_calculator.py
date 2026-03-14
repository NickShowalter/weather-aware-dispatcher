import math

from weather_aware_dispatcher.config import (
    BASE_MOVE_COST,
    PAYLOAD_PENALTY_INCREMENT_LBS,
    PAYLOAD_PENALTY_RATE,
    WIND_AGAINST_MULTIPLIER,
    WIND_CROSS_MULTIPLIER,
    WIND_WITH_MULTIPLIER,
)
from weather_aware_dispatcher.models.coordinate import Coordinate
from weather_aware_dispatcher.models.direction import DELTA_TO_DIRECTION, Direction
from weather_aware_dispatcher.models.weather import WeatherForecast


def wind_multiplier(move_direction: Direction, wind_direction: Direction) -> float:
    if move_direction == wind_direction:
        return WIND_WITH_MULTIPLIER
    if move_direction == wind_direction.opposite():
        return WIND_AGAINST_MULTIPLIER
    return WIND_CROSS_MULTIPLIER


def payload_multiplier(weight_lbs: float) -> float:
    increments = math.floor(weight_lbs / PAYLOAD_PENALTY_INCREMENT_LBS)
    return 1.0 + increments * PAYLOAD_PENALTY_RATE


def move_cost(move_direction: Direction, wind_direction: Direction, weight_lbs: float) -> float:
    return BASE_MOVE_COST * wind_multiplier(move_direction, wind_direction) * payload_multiplier(weight_lbs)


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
) -> float:
    total = 0.0
    tick = start_tick
    for i in range(len(path) - 1):
        direction = direction_from_coords(path[i], path[i + 1])
        wind = weather.wind_at_tick(tick)
        total += move_cost(direction, wind, weight_lbs)
        tick += 1
    return total
