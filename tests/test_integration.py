import os

from weather_aware_dispatcher.core.delivery_planner import plan_deliveries
from weather_aware_dispatcher.core.simulation_engine import simulate
from weather_aware_dispatcher.io.input_loader import load_input
from weather_aware_dispatcher.config import LAUNCH_PAD


SAMPLE_INPUT = os.path.join(os.path.dirname(__file__), "..", "sample_input.json")


def _run_pipeline():
    result = load_input(SAMPLE_INPUT)
    assert result.ok, f"Input loading failed: {result.errors}"
    plan = plan_deliveries(result.data.packages, result.data.grid, result.data.weather)
    sim = simulate(plan, result.data.weather)
    return plan, sim


def test_sample_input_all_packages_delivered():
    plan, sim = _run_pipeline()
    assert sim.success
    assert len(plan.planned_deliveries) == 3
    assert len(plan.infeasible_packages) == 0
    delivered_ids = {d.package_id for d in sim.deliveries}
    assert delivered_ids == {"pkg_1", "pkg_2", "pkg_3"}


def test_sample_input_drone_returns_to_base():
    plan, sim = _run_pipeline()
    # Each delivery's return path ends at launch pad
    for delivery in plan.planned_deliveries:
        assert delivery.return_path[-1] == LAUNCH_PAD


def test_sample_input_no_crash():
    plan, sim = _run_pipeline()
    assert sim.success
    assert sim.error is None
    # No move should result in negative battery
    for move in sim.moves:
        assert move.battery_after >= -1e-9


def test_sample_input_battery_consumed_is_positive():
    plan, sim = _run_pipeline()
    assert sim.total_battery_consumed > 0
