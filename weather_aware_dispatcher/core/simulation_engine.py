from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from weather_aware_dispatcher.config import DEFAULT_CONFIG, SimulationConfig
from weather_aware_dispatcher.core.cost_calculator import direction_from_coords, move_cost
from weather_aware_dispatcher.core.delivery_planner import DeliveryPlan
from weather_aware_dispatcher.models.coordinate import Coordinate
from weather_aware_dispatcher.models.direction import Direction
from weather_aware_dispatcher.models.weather import WeatherForecast

logger = logging.getLogger(__name__)


@dataclass
class MoveRecord:
    tick: int
    from_coord: Coordinate
    to_coord: Coordinate
    direction: Direction
    wind: Direction
    cost: float
    battery_after: float


@dataclass
class DeliveryRecord:
    package_id: str
    tick: int
    outbound_cost: float
    return_cost: float


@dataclass
class RechargeRecord:
    tick: int
    battery_before_swap: float


@dataclass
class SimulationResult:
    success: bool
    moves: list[MoveRecord] = field(default_factory=list)
    deliveries: list[DeliveryRecord] = field(default_factory=list)
    recharges: list[RechargeRecord] = field(default_factory=list)
    total_battery_consumed: float = 0.0
    total_ticks: int = 0
    error: Optional[str] = None
    infeasible_packages: list[tuple[str, str]] = field(default_factory=list)


def simulate(
    plan: DeliveryPlan,
    weather: WeatherForecast,
    config: Optional[SimulationConfig] = None,
) -> SimulationResult:
    """Execute the delivery plan tick-by-tick, independently recomputing all costs."""
    cfg = config or DEFAULT_CONFIG
    result = SimulationResult(success=True)

    for pkg, reason in plan.infeasible_packages:
        result.infeasible_packages.append((pkg.id, reason))

    battery = cfg.battery_capacity
    tick = 0

    for delivery in plan.planned_deliveries:
        if delivery.outbound_path[0] != cfg.launch_pad:
            result.success = False
            result.error = f"Delivery {delivery.package.id}: outbound doesn't start at launch pad"
            return result

        # --- Outbound leg ---
        outbound_cost = 0.0
        weight = delivery.package.weight_lbs
        for i in range(len(delivery.outbound_path) - 1):
            a, b = delivery.outbound_path[i], delivery.outbound_path[i + 1]
            direction = direction_from_coords(a, b)
            wind = weather.wind_at_tick(tick)
            cost = move_cost(direction, wind, weight, cfg)
            battery -= cost
            outbound_cost += cost

            result.moves.append(MoveRecord(
                tick=tick, from_coord=a, to_coord=b,
                direction=direction, wind=wind, cost=cost, battery_after=battery,
            ))

            if battery < -1e-9:
                result.success = False
                result.error = (
                    f"Battery depleted at tick {tick}: {battery:.4f} remaining "
                    f"at {b} during delivery of {delivery.package.id}"
                )
                return result

            tick += 1

        result.deliveries.append(DeliveryRecord(
            package_id=delivery.package.id,
            tick=tick,
            outbound_cost=outbound_cost,
            return_cost=0.0,
        ))

        # --- Return leg ---
        return_cost = 0.0
        for i in range(len(delivery.return_path) - 1):
            a, b = delivery.return_path[i], delivery.return_path[i + 1]
            direction = direction_from_coords(a, b)
            wind = weather.wind_at_tick(tick)
            cost = move_cost(direction, wind, 0.0, cfg)
            battery -= cost
            return_cost += cost

            result.moves.append(MoveRecord(
                tick=tick, from_coord=a, to_coord=b,
                direction=direction, wind=wind, cost=cost, battery_after=battery,
            ))

            if battery < -1e-9:
                result.success = False
                result.error = (
                    f"Battery depleted at tick {tick}: {battery:.4f} remaining "
                    f"at {b} during return from {delivery.package.id}"
                )
                return result

            tick += 1

        result.deliveries[-1].return_cost = return_cost

        if abs(outbound_cost - delivery.outbound_cost) > 0.001:
            logger.warning(
                "Cost mismatch for %s outbound: planner=%.4f, simulator=%.4f",
                delivery.package.id, delivery.outbound_cost, outbound_cost,
            )
        if abs(return_cost - delivery.return_cost) > 0.001:
            logger.warning(
                "Cost mismatch for %s return: planner=%.4f, simulator=%.4f",
                delivery.package.id, delivery.return_cost, return_cost,
            )

        result.recharges.append(RechargeRecord(tick=tick, battery_before_swap=battery))
        result.total_battery_consumed += outbound_cost + return_cost
        battery = cfg.battery_capacity

    result.total_ticks = tick
    return result
