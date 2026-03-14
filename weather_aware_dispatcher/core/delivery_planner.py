from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass, field
from typing import Optional

from weather_aware_dispatcher.config import DEFAULT_CONFIG, SimulationConfig
from weather_aware_dispatcher.core.pathfinder import find_path_cost_aware
from weather_aware_dispatcher.models.coordinate import Coordinate
from weather_aware_dispatcher.models.grid import Grid
from weather_aware_dispatcher.models.package import Package
from weather_aware_dispatcher.models.weather import WeatherForecast

logger = logging.getLogger(__name__)

PERMUTATION_THRESHOLD = 8


@dataclass
class PlannedDelivery:
    package: Package
    outbound_path: list[Coordinate]
    return_path: list[Coordinate]
    outbound_cost: float
    return_cost: float
    start_tick: int
    end_tick: int

    @property
    def round_trip_cost(self) -> float:
        return self.outbound_cost + self.return_cost


@dataclass
class DeliveryPlan:
    planned_deliveries: list[PlannedDelivery] = field(default_factory=list)
    infeasible_packages: list[tuple[Package, str]] = field(default_factory=list)

    @property
    def total_battery_consumed(self) -> float:
        return sum(d.round_trip_cost for d in self.planned_deliveries)

    @property
    def total_ticks(self) -> int:
        if not self.planned_deliveries:
            return 0
        return self.planned_deliveries[-1].end_tick


def _plan_round_trip(
    package: Package,
    current_tick: int,
    grid: Grid,
    weather: WeatherForecast,
    config: SimulationConfig,
) -> Optional[PlannedDelivery]:
    """Plan a single round trip for a package. Returns None if infeasible."""
    outbound = find_path_cost_aware(
        config.launch_pad, package.destination, grid, current_tick, weather, package.weight_lbs, config
    )
    if outbound is None:
        return None

    outbound_path, outbound_cost = outbound
    outbound_ticks = len(outbound_path) - 1
    arrival_tick = current_tick + outbound_ticks

    return_result = find_path_cost_aware(
        package.destination, config.launch_pad, grid, arrival_tick, weather, 0.0, config
    )
    if return_result is None:
        return None

    return_path, return_cost = return_result
    return_ticks = len(return_path) - 1
    total_cost = outbound_cost + return_cost

    if total_cost > config.battery_capacity:
        return None

    end_tick = arrival_tick + return_ticks
    return PlannedDelivery(
        package=package,
        outbound_path=outbound_path,
        return_path=return_path,
        outbound_cost=outbound_cost,
        return_cost=return_cost,
        start_tick=current_tick,
        end_tick=end_tick,
    )


def _simulate_ordering(
    packages: list[Package],
    grid: Grid,
    weather: WeatherForecast,
    config: SimulationConfig,
) -> Optional[tuple[list[PlannedDelivery], float]]:
    """Simulate a specific ordering. Returns (deliveries, total_cost) or None if any is infeasible."""
    deliveries: list[PlannedDelivery] = []
    current_tick = 0
    total_cost = 0.0

    for pkg in packages:
        delivery = _plan_round_trip(pkg, current_tick, grid, weather, config)
        if delivery is None:
            return None
        deliveries.append(delivery)
        total_cost += delivery.round_trip_cost
        current_tick = delivery.end_tick

    return deliveries, total_cost


def plan_deliveries(
    packages: list[Package],
    grid: Grid,
    weather: WeatherForecast,
    config: Optional[SimulationConfig] = None,
) -> DeliveryPlan:
    """Plan delivery order for all packages."""
    cfg = config or DEFAULT_CONFIG

    if not packages:
        return DeliveryPlan()

    feasible: list[Package] = []
    infeasible: list[tuple[Package, str]] = []

    for pkg in packages:
        delivery = _plan_round_trip(pkg, 0, grid, weather, cfg)
        if delivery is None:
            outbound = find_path_cost_aware(
                cfg.launch_pad, pkg.destination, grid, 0, weather, pkg.weight_lbs, cfg
            )
            if outbound is None:
                infeasible.append((pkg, f"No path from {cfg.launch_pad} to {pkg.destination}"))
            else:
                infeasible.append((pkg, f"Round trip cost exceeds battery capacity of {cfg.battery_capacity}"))
        else:
            feasible.append(pkg)

    if not feasible:
        return DeliveryPlan(infeasible_packages=infeasible)

    if len(feasible) <= PERMUTATION_THRESHOLD:
        best_deliveries, best_cost = None, float("inf")

        for perm in itertools.permutations(feasible):
            result = _simulate_ordering(list(perm), grid, weather, cfg)
            if result is not None:
                deliveries, cost = result
                if cost < best_cost:
                    best_cost = cost
                    best_deliveries = deliveries

        if best_deliveries is not None:
            logger.info(
                "Optimal ordering found via permutation search (%.2f battery)",
                best_cost,
            )
            return DeliveryPlan(
                planned_deliveries=best_deliveries,
                infeasible_packages=infeasible,
            )

    return _greedy_plan(feasible, infeasible, grid, weather, cfg)


def _greedy_plan(
    remaining: list[Package],
    infeasible: list[tuple[Package, str]],
    grid: Grid,
    weather: WeatherForecast,
    config: SimulationConfig,
) -> DeliveryPlan:
    remaining = list(remaining)
    planned: list[PlannedDelivery] = []
    current_tick = 0

    while remaining:
        best_delivery: Optional[PlannedDelivery] = None
        best_idx: int = -1

        for i, pkg in enumerate(remaining):
            delivery = _plan_round_trip(pkg, current_tick, grid, weather, config)
            if delivery is None:
                continue
            if best_delivery is None or delivery.round_trip_cost < best_delivery.round_trip_cost:
                best_delivery = delivery
                best_idx = i

        if best_delivery is None:
            for pkg in remaining:
                infeasible.append((pkg, f"Infeasible at tick {current_tick}"))
            break

        planned.append(best_delivery)
        current_tick = best_delivery.end_tick
        remaining.pop(best_idx)

    return DeliveryPlan(planned_deliveries=planned, infeasible_packages=infeasible)
