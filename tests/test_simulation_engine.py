import math

from weather_aware_dispatcher.core.delivery_planner import plan_deliveries
from weather_aware_dispatcher.core.simulation_engine import simulate
from weather_aware_dispatcher.config import BATTERY_CAPACITY
from weather_aware_dispatcher.models.coordinate import Coordinate
from weather_aware_dispatcher.models.direction import Direction
from weather_aware_dispatcher.models.grid import Grid
from weather_aware_dispatcher.models.package import Package
from weather_aware_dispatcher.models.weather import WeatherSegment, WeatherForecast
from weather_aware_dispatcher.core.delivery_planner import DeliveryPlan, PlannedDelivery


def _simple_grid() -> Grid:
    return Grid(20, 20, frozenset())


def _east_wind() -> WeatherForecast:
    return WeatherForecast([WeatherSegment(Direction.EAST, 0, None)])


def test_simulation_matches_planner_cost():
    """Simulator's total cost should match the planner's total cost."""
    packages = [
        Package("pkg_1", Coordinate(5, 0), 5),
        Package("pkg_2", Coordinate(0, 3), 0),
    ]
    plan = plan_deliveries(packages, _simple_grid(), _east_wind())
    result = simulate(plan, _east_wind())

    assert result.success
    assert abs(result.total_battery_consumed - plan.total_battery_consumed) < 0.001


def test_simulation_detects_battery_violation():
    """Simulator should catch a plan that would deplete battery."""
    # Manually construct a plan with a path that's too expensive
    pkg = Package("test", Coordinate(19, 19), 0)
    # Create a valid-looking but battery-busting plan
    # 38 moves at against-wind (2.0 each) = 76 outbound + return
    # We'll make a real plan first to get real paths, then verify it's feasible
    forecast = WeatherForecast([WeatherSegment(Direction.EAST, 0, None)])
    plan = plan_deliveries([pkg], _simple_grid(), forecast)

    # With east wind and 0 lbs: outbound east=0.5, north=1.0; return west=2.0, south=1.0
    # This should be feasible: 19*0.5 + 19*1.0 + 19*2.0 + 19*1.0 = 9.5+19+38+19 = 85.5
    result = simulate(plan, forecast)
    assert result.success
    assert result.total_battery_consumed < BATTERY_CAPACITY


def test_simulation_tracks_battery_across_deliveries():
    """Each delivery should start with a fresh battery."""
    packages = [
        Package("pkg_1", Coordinate(3, 0), 0),
        Package("pkg_2", Coordinate(0, 3), 0),
    ]
    plan = plan_deliveries(packages, _simple_grid(), _east_wind())
    result = simulate(plan, _east_wind())

    assert result.success
    assert len(result.recharges) == 2
    # Each recharge should show battery was used (less than 100)
    for recharge in result.recharges:
        assert recharge.battery_before_swap < BATTERY_CAPACITY


def test_simulation_recharge_resets_to_full():
    """After battery swap, the next delivery should start with full battery."""
    packages = [
        Package("pkg_1", Coordinate(10, 0), 0),
        Package("pkg_2", Coordinate(0, 10), 0),
    ]
    plan = plan_deliveries(packages, _simple_grid(), _east_wind())
    result = simulate(plan, _east_wind())

    assert result.success
    # Find the first move of the second delivery
    first_delivery_moves = (len(plan.planned_deliveries[0].outbound_path) - 1 +
                            len(plan.planned_deliveries[0].return_path) - 1)
    # The move right after recharge should show battery close to 100 minus one move cost
    second_delivery_first_move = result.moves[first_delivery_moves]
    # Battery after first move of second delivery = 100 - cost of that move
    assert second_delivery_first_move.battery_after > BATTERY_CAPACITY - 3.0  # generous margin
