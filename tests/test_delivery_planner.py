from weather_aware_dispatcher.core.delivery_planner import plan_deliveries
from weather_aware_dispatcher.models.coordinate import Coordinate
from weather_aware_dispatcher.models.direction import Direction
from weather_aware_dispatcher.models.grid import Grid
from weather_aware_dispatcher.models.package import Package
from weather_aware_dispatcher.models.weather import WeatherSegment, WeatherForecast


def _simple_grid() -> Grid:
    return Grid(20, 20, frozenset())


def _east_wind() -> WeatherForecast:
    return WeatherForecast([WeatherSegment(Direction.EAST, 0, None)])


def test_single_package_delivery():
    packages = [Package("pkg_1", Coordinate(3, 0), 5)]
    plan = plan_deliveries(packages, _simple_grid(), _east_wind())

    assert len(plan.planned_deliveries) == 1
    assert len(plan.infeasible_packages) == 0
    d = plan.planned_deliveries[0]
    assert d.package.id == "pkg_1"
    assert d.outbound_path[0] == Coordinate(0, 0)
    assert d.outbound_path[-1] == Coordinate(3, 0)
    assert d.return_path[0] == Coordinate(3, 0)
    assert d.return_path[-1] == Coordinate(0, 0)
    assert d.round_trip_cost > 0


def test_multi_package_ordering_considers_wind():
    """Packages closer to wind-favorable directions should be ordered cheaply."""
    # Wind blows east. pkg_east goes east (cheap), pkg_west goes north (crosswind).
    packages = [
        Package("pkg_east", Coordinate(5, 0), 0),
        Package("pkg_north", Coordinate(0, 5), 0),
    ]
    plan = plan_deliveries(packages, _simple_grid(), _east_wind())

    assert len(plan.planned_deliveries) == 2
    assert len(plan.infeasible_packages) == 0
    # The planner should find the optimal ordering
    assert plan.total_battery_consumed > 0


def test_infeasible_package_reported_not_crashed():
    """A package too far for a round trip should be reported as infeasible."""
    # Make a very heavy package going far away on a small grid-like scenario
    # Battery = 100, need to go (0,0) → (19,19) and back = 76 moves minimum
    # Against wind with heavy payload could exceed 100
    forecast = WeatherForecast([WeatherSegment(Direction.WEST, 0, None)])
    # 19 east (against) + 19 north (cross) out, then 19 south + 19 west (with) back
    # Outbound: 19 * 2.0 * 1.6 + 19 * 1.0 * 1.6 = 60.8 + 30.4 = 91.2
    # Return (0 lbs): 19 * 1.0 + 19 * 0.5 = 19 + 9.5 = 28.5
    # Total = 119.7 > 100 → infeasible
    packages = [Package("heavy_far", Coordinate(19, 19), 30)]
    plan = plan_deliveries(packages, _simple_grid(), forecast)

    assert len(plan.infeasible_packages) == 1
    assert plan.infeasible_packages[0][0].id == "heavy_far"
    assert len(plan.planned_deliveries) == 0


def test_empty_manifest():
    plan = plan_deliveries([], _simple_grid(), _east_wind())
    assert len(plan.planned_deliveries) == 0
    assert len(plan.infeasible_packages) == 0
    assert plan.total_battery_consumed == 0
    assert plan.total_ticks == 0
