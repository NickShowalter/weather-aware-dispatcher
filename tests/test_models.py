from weather_aware_dispatcher.models.coordinate import Coordinate
from weather_aware_dispatcher.models.direction import Direction
from weather_aware_dispatcher.models.grid import Grid
from weather_aware_dispatcher.models.package import Package
from weather_aware_dispatcher.models.weather import WeatherSegment, WeatherForecast


# --- Coordinate ---

def test_coordinate_equality_and_hashing():
    a = Coordinate(3, 4)
    b = Coordinate(3, 4)
    assert a == b
    assert hash(a) == hash(b)
    assert a != Coordinate(3, 5)
    # Usable in sets/dicts
    s = {a, b}
    assert len(s) == 1


def test_coordinate_manhattan_distance():
    assert Coordinate(0, 0).manhattan_distance(Coordinate(3, 4)) == 7
    assert Coordinate(5, 5).manhattan_distance(Coordinate(5, 5)) == 0
    assert Coordinate(0, 0).manhattan_distance(Coordinate(19, 19)) == 38


def test_coordinate_neighbors():
    c = Coordinate(5, 5)
    neighbors = c.neighbors()
    assert len(neighbors) == 4
    assert Coordinate(5, 6) in neighbors  # North
    assert Coordinate(5, 4) in neighbors  # South
    assert Coordinate(6, 5) in neighbors  # East
    assert Coordinate(4, 5) in neighbors  # West


# --- Direction ---

def test_direction_opposite():
    assert Direction.NORTH.opposite() == Direction.SOUTH
    assert Direction.SOUTH.opposite() == Direction.NORTH
    assert Direction.EAST.opposite() == Direction.WEST
    assert Direction.WEST.opposite() == Direction.EAST


def test_direction_is_perpendicular():
    assert Direction.NORTH.is_perpendicular(Direction.EAST)
    assert Direction.NORTH.is_perpendicular(Direction.WEST)
    assert not Direction.NORTH.is_perpendicular(Direction.SOUTH)
    assert not Direction.NORTH.is_perpendicular(Direction.NORTH)
    assert Direction.EAST.is_perpendicular(Direction.NORTH)
    assert Direction.EAST.is_perpendicular(Direction.SOUTH)
    assert not Direction.EAST.is_perpendicular(Direction.WEST)


def test_direction_to_delta():
    assert Direction.NORTH.to_delta() == (0, 1)
    assert Direction.SOUTH.to_delta() == (0, -1)
    assert Direction.EAST.to_delta() == (1, 0)
    assert Direction.WEST.to_delta() == (-1, 0)


# --- Grid ---

def test_grid_is_valid_in_bounds():
    grid = Grid(20, 20, frozenset())
    assert grid.is_valid(Coordinate(0, 0))
    assert grid.is_valid(Coordinate(19, 19))
    assert not grid.is_valid(Coordinate(-1, 0))
    assert not grid.is_valid(Coordinate(0, 20))
    assert not grid.is_valid(Coordinate(20, 0))


def test_grid_is_valid_on_obstacle():
    grid = Grid(20, 20, frozenset({Coordinate(5, 5)}))
    assert not grid.is_valid(Coordinate(5, 5))
    assert grid.is_valid(Coordinate(5, 4))


def test_grid_passable_neighbors():
    grid = Grid(20, 20, frozenset({Coordinate(5, 6)}))
    neighbors = grid.passable_neighbors(Coordinate(5, 5))
    assert Coordinate(5, 6) not in neighbors  # blocked by obstacle
    assert Coordinate(5, 4) in neighbors
    assert Coordinate(4, 5) in neighbors
    assert Coordinate(6, 5) in neighbors


def test_grid_passable_neighbors_corner():
    grid = Grid(20, 20, frozenset())
    neighbors = grid.passable_neighbors(Coordinate(0, 0))
    assert len(neighbors) == 2
    assert Coordinate(0, 1) in neighbors
    assert Coordinate(1, 0) in neighbors


# --- Weather ---

def test_weather_forecast_wind_at_tick_first_segment():
    forecast = WeatherForecast([
        WeatherSegment(Direction.EAST, 0, 49),
        WeatherSegment(Direction.NORTH, 50, 99),
    ])
    assert forecast.wind_at_tick(0) == Direction.EAST
    assert forecast.wind_at_tick(25) == Direction.EAST
    assert forecast.wind_at_tick(49) == Direction.EAST


def test_weather_forecast_wind_at_tick_boundary():
    forecast = WeatherForecast([
        WeatherSegment(Direction.EAST, 0, 49),
        WeatherSegment(Direction.NORTH, 50, 99),
    ])
    assert forecast.wind_at_tick(49) == Direction.EAST
    assert forecast.wind_at_tick(50) == Direction.NORTH


def test_weather_forecast_wind_at_null_end_tick():
    forecast = WeatherForecast([
        WeatherSegment(Direction.EAST, 0, 49),
        WeatherSegment(Direction.WEST, 50, None),
    ])
    assert forecast.wind_at_tick(50) == Direction.WEST
    assert forecast.wind_at_tick(1000) == Direction.WEST


# --- Package ---

def test_package_weight_penalty_multiplier():
    assert Package("a", Coordinate(0, 0), 0).weight_penalty_multiplier == 1.0
    assert Package("b", Coordinate(0, 0), 3).weight_penalty_multiplier == 1.0
    assert Package("c", Coordinate(0, 0), 5).weight_penalty_multiplier == 1.1
    assert Package("d", Coordinate(0, 0), 7).weight_penalty_multiplier == 1.1
    assert Package("e", Coordinate(0, 0), 10).weight_penalty_multiplier == 1.2
    assert Package("f", Coordinate(0, 0), 12).weight_penalty_multiplier == 1.2
