from weather_aware_dispatcher.core.cost_calculator import (
    wind_multiplier,
    payload_multiplier,
    move_cost,
    estimate_path_cost,
)
from weather_aware_dispatcher.models.coordinate import Coordinate
from weather_aware_dispatcher.models.direction import Direction
from weather_aware_dispatcher.models.weather import WeatherSegment, WeatherForecast


# --- wind_multiplier ---

def test_wind_multiplier_with_wind():
    assert wind_multiplier(Direction.EAST, Direction.EAST) == 0.5


def test_wind_multiplier_against_wind():
    assert wind_multiplier(Direction.WEST, Direction.EAST) == 2.0


def test_wind_multiplier_cross_wind():
    assert wind_multiplier(Direction.NORTH, Direction.EAST) == 1.0
    assert wind_multiplier(Direction.SOUTH, Direction.EAST) == 1.0


# --- payload_multiplier ---

def test_payload_multiplier_zero_weight():
    assert payload_multiplier(0) == 1.0


def test_payload_multiplier_under_5_lbs():
    assert payload_multiplier(2) == 1.0
    assert payload_multiplier(3) == 1.0
    assert payload_multiplier(4.99) == 1.0


def test_payload_multiplier_exact_5_lbs():
    assert payload_multiplier(5) == 1.1


def test_payload_multiplier_between_increments():
    assert payload_multiplier(7) == 1.1


def test_payload_multiplier_10_lbs():
    assert payload_multiplier(10) == 1.2


def test_payload_multiplier_12_lbs():
    # floor(12/5) = 2 increments → 1.2 (floor, not ceil)
    assert payload_multiplier(12) == 1.2


# --- move_cost (reference values from spec) ---

def test_move_cost_east_wind_east_0lbs():
    assert move_cost(Direction.EAST, Direction.EAST, 0) == 0.5


def test_move_cost_west_wind_east_0lbs():
    assert move_cost(Direction.WEST, Direction.EAST, 0) == 2.0


def test_move_cost_north_wind_east_0lbs():
    assert move_cost(Direction.NORTH, Direction.EAST, 0) == 1.0


def test_move_cost_east_wind_east_5lbs():
    assert move_cost(Direction.EAST, Direction.EAST, 5) == 0.55


def test_move_cost_east_wind_east_10lbs():
    assert move_cost(Direction.EAST, Direction.EAST, 10) == 0.60


def test_move_cost_west_wind_east_10lbs():
    assert move_cost(Direction.WEST, Direction.EAST, 10) == 2.4


def test_move_cost_north_wind_east_5lbs():
    assert move_cost(Direction.NORTH, Direction.EAST, 5) == 1.1


# --- estimate_path_cost ---

def test_estimate_path_cost_with_wind_change():
    """Verify tick boundary correctly uses new wind direction."""
    forecast = WeatherForecast([
        WeatherSegment(Direction.EAST, 0, 1),
        WeatherSegment(Direction.WEST, 2, None),
    ])
    # Path: 3 coords = 2 moves, all eastward
    path = [Coordinate(0, 0), Coordinate(1, 0), Coordinate(2, 0)]

    # Tick 0: move east, wind east → 0.5
    # Tick 1: move east, wind east → 0.5
    cost_start_0 = estimate_path_cost(path, start_tick=0, weather=forecast, weight_lbs=0)
    assert cost_start_0 == 1.0

    # Tick 1: move east, wind east → 0.5
    # Tick 2: move east, wind west → 2.0
    cost_start_1 = estimate_path_cost(path, start_tick=1, weather=forecast, weight_lbs=0)
    assert cost_start_1 == 2.5
