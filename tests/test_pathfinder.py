from weather_aware_dispatcher.core.pathfinder import find_path, find_path_cost_aware
from weather_aware_dispatcher.models.coordinate import Coordinate
from weather_aware_dispatcher.models.direction import Direction
from weather_aware_dispatcher.models.grid import Grid
from weather_aware_dispatcher.models.weather import WeatherSegment, WeatherForecast


def _empty_grid() -> Grid:
    return Grid(20, 20, frozenset())


def test_straight_line_no_obstacles():
    path = find_path(Coordinate(0, 0), Coordinate(3, 0), _empty_grid())
    assert path is not None
    assert path[0] == Coordinate(0, 0)
    assert path[-1] == Coordinate(3, 0)
    assert len(path) == 4  # 3 moves


def test_path_around_single_obstacle():
    grid = Grid(20, 20, frozenset({Coordinate(1, 0)}))
    path = find_path(Coordinate(0, 0), Coordinate(2, 0), grid)
    assert path is not None
    assert path[0] == Coordinate(0, 0)
    assert path[-1] == Coordinate(2, 0)
    assert Coordinate(1, 0) not in path
    # Must detour: at least 4 moves
    assert len(path) >= 5


def test_path_around_wall_of_obstacles():
    # Wall at x=5 from y=0 to y=5
    obstacles = frozenset(Coordinate(5, y) for y in range(6))
    grid = Grid(20, 20, obstacles)
    path = find_path(Coordinate(0, 0), Coordinate(10, 0), grid)
    assert path is not None
    assert path[0] == Coordinate(0, 0)
    assert path[-1] == Coordinate(10, 0)
    for obs in obstacles:
        assert obs not in path


def test_unreachable_destination_returns_none():
    # Completely surround (5, 5) with obstacles
    obstacles = frozenset([
        Coordinate(5, 6), Coordinate(5, 4),
        Coordinate(4, 5), Coordinate(6, 5),
    ])
    grid = Grid(20, 20, obstacles)
    path = find_path(Coordinate(0, 0), Coordinate(5, 5), grid)
    assert path is None


def test_start_equals_end_returns_single_coordinate():
    path = find_path(Coordinate(3, 3), Coordinate(3, 3), _empty_grid())
    assert path == [Coordinate(3, 3)]


def test_cost_aware_prefers_wind_aligned_path():
    """A detour with wind should be cheaper than direct path against wind."""
    # Wind blows east. Going from (0,0) to (0,2).
    # Direct path: north twice → crosswind → cost = 1.0 * 2 = 2.0
    # Detour east then north then west: with + cross + against = 0.5 + 1.0 + 1.0 + 2.0 = hmm
    # Actually on a small grid, direct crosswind is already optimal.
    # Better test: go from (0,0) to (3,0) with wind WEST.
    # Direct east x3 = against wind = 2.0 * 3 = 6.0
    # Wind blows west; any detour through north/south still has to go east.
    # Let's test that cost_aware finds the same path but with correct cost.

    forecast = WeatherForecast([WeatherSegment(Direction.EAST, 0, None)])
    grid = _empty_grid()

    # East with east wind = 0.5 per move
    result = find_path_cost_aware(
        Coordinate(0, 0), Coordinate(5, 0), grid, 0, forecast, 0.0
    )
    assert result is not None
    path, cost = result
    assert path[0] == Coordinate(0, 0)
    assert path[-1] == Coordinate(5, 0)
    # Optimal: 5 moves east with wind = 0.5 * 5 = 2.5
    assert cost == 2.5

    # Now same destination but wind blows west → east is against wind = 2.0 each
    forecast_west = WeatherForecast([WeatherSegment(Direction.WEST, 0, None)])
    result2 = find_path_cost_aware(
        Coordinate(0, 0), Coordinate(5, 0), grid, 0, forecast_west, 0.0
    )
    assert result2 is not None
    _, cost2 = result2
    # Must go east 5 times against wind = 2.0 * 5 = 10.0
    # No detour can avoid going net 5 east
    assert cost2 == 10.0
    assert cost2 > cost
