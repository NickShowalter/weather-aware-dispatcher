from __future__ import annotations

import heapq
from typing import Optional

from weather_aware_dispatcher.models.coordinate import Coordinate
from weather_aware_dispatcher.models.direction import DELTA_TO_DIRECTION
from weather_aware_dispatcher.models.grid import Grid
from weather_aware_dispatcher.models.weather import WeatherForecast
from weather_aware_dispatcher.core.cost_calculator import move_cost


def find_path(
    start: Coordinate, end: Coordinate, grid: Grid
) -> Optional[list[Coordinate]]:
    """A* pathfinding with Manhattan distance heuristic. Returns path inclusive of both endpoints, or None."""
    if start == end:
        return [start]
    if not grid.is_valid(start) or not grid.is_valid(end):
        return None

    counter = 0
    # (f_cost, counter, coord, parent)
    open_set: list[tuple[int, int, Coordinate, Optional[Coordinate]]] = []
    heapq.heappush(open_set, (start.manhattan_distance(end), counter, start, None))
    counter += 1

    came_from: dict[Coordinate, Optional[Coordinate]] = {}
    g_cost: dict[Coordinate, int] = {start: 0}

    while open_set:
        _, _, current, parent = heapq.heappop(open_set)

        if current in came_from:
            continue
        came_from[current] = parent

        if current == end:
            return _reconstruct(came_from, end)

        for neighbor in grid.passable_neighbors(current):
            new_g = g_cost[current] + 1
            if new_g < g_cost.get(neighbor, float("inf")):
                g_cost[neighbor] = new_g
                f = new_g + neighbor.manhattan_distance(end)
                heapq.heappush(open_set, (f, counter, neighbor, current))
                counter += 1

    return None


def find_path_cost_aware(
    start: Coordinate,
    end: Coordinate,
    grid: Grid,
    start_tick: int,
    weather: WeatherForecast,
    weight_lbs: float,
) -> Optional[tuple[list[Coordinate], float]]:
    """Time-aware A* where edge costs account for wind at each tick.

    Node state is (coordinate, tick) since the same coordinate at different
    ticks has different wind costs.

    Returns (path, total_cost) or None.
    """
    if start == end:
        return ([start], 0.0)
    if not grid.is_valid(start) or not grid.is_valid(end):
        return None

    counter = 0
    # Admissible heuristic: manhattan * 0.5 (minimum possible cost per move)
    h = start.manhattan_distance(end) * 0.5

    # (f_cost, counter, coord, tick, g_cost, parent_coord, parent_tick)
    open_set: list[tuple[float, int, Coordinate, int, float, Optional[Coordinate], Optional[int]]] = []
    heapq.heappush(open_set, (h, counter, start, start_tick, 0.0, None, None))
    counter += 1

    # Best known g-cost for (coord, tick)
    best: dict[tuple[Coordinate, int], float] = {(start, start_tick): 0.0}
    came_from: dict[tuple[Coordinate, int], Optional[tuple[Coordinate, int]]] = {}

    while open_set:
        _, _, current, tick, g, parent_coord, parent_tick = heapq.heappop(open_set)

        state = (current, tick)
        if state in came_from:
            continue
        came_from[state] = (parent_coord, parent_tick) if parent_coord is not None else None

        if current == end:
            return (_reconstruct_timed(came_from, state), g)

        wind = weather.wind_at_tick(tick)
        for neighbor in grid.passable_neighbors(current):
            delta = (neighbor.x - current.x, neighbor.y - current.y)
            direction = DELTA_TO_DIRECTION[delta]
            edge_cost = move_cost(direction, wind, weight_lbs)
            new_g = g + edge_cost
            new_tick = tick + 1
            neighbor_state = (neighbor, new_tick)

            if new_g < best.get(neighbor_state, float("inf")):
                best[neighbor_state] = new_g
                h = neighbor.manhattan_distance(end) * 0.5
                heapq.heappush(
                    open_set,
                    (new_g + h, counter, neighbor, new_tick, new_g, current, tick),
                )
                counter += 1

    return None


def _reconstruct(
    came_from: dict[Coordinate, Optional[Coordinate]], end: Coordinate
) -> list[Coordinate]:
    path = [end]
    current = end
    while came_from[current] is not None:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def _reconstruct_timed(
    came_from: dict[tuple[Coordinate, int], Optional[tuple[Coordinate, int]]],
    end_state: tuple[Coordinate, int],
) -> list[Coordinate]:
    path = [end_state[0]]
    current = end_state
    while came_from[current] is not None:
        current = came_from[current]
        path.append(current[0])
    path.reverse()
    return path
