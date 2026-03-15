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

COST_MISMATCH_TOLERANCE = 0.001


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
class CostMismatch:
    package_id: str
    leg: str  # "outbound" or "return"
    planner_cost: float
    simulator_cost: float


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
    warnings: list[str] = field(default_factory=list)
    cost_mismatches: list[CostMismatch] = field(default_factory=list)


def simulate(
    plan: DeliveryPlan,
    weather: WeatherForecast,
    config: Optional[SimulationConfig] = None,
    cross_check: bool = True,
) -> SimulationResult:
    """Execute the delivery plan tick-by-tick, independently recomputing all costs.

    Args:
        cross_check: If True, abort delivery on cost mismatch with planner.
                     If False, log warnings but continue.
    """
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

        # --- Cross-check planner costs ---
        outbound_diff = abs(outbound_cost - delivery.outbound_cost)
        return_diff = abs(return_cost - delivery.return_cost)

        if outbound_diff > COST_MISMATCH_TOLERANCE:
            mismatch = CostMismatch(
                package_id=delivery.package.id,
                leg="outbound",
                planner_cost=delivery.outbound_cost,
                simulator_cost=outbound_cost,
            )
            result.cost_mismatches.append(mismatch)
            msg = (
                f"Cost mismatch for {delivery.package.id} outbound: "
                f"planner={delivery.outbound_cost:.4f}, simulator={outbound_cost:.4f}"
            )
            logger.warning(msg)
            result.warnings.append(msg)

            if cross_check:
                result.success = False
                result.error = f"Cross-check failure: {msg}. Aborting to prevent unsafe flight."
                return result

        if return_diff > COST_MISMATCH_TOLERANCE:
            mismatch = CostMismatch(
                package_id=delivery.package.id,
                leg="return",
                planner_cost=delivery.return_cost,
                simulator_cost=return_cost,
            )
            result.cost_mismatches.append(mismatch)
            msg = (
                f"Cost mismatch for {delivery.package.id} return: "
                f"planner={delivery.return_cost:.4f}, simulator={return_cost:.4f}"
            )
            logger.warning(msg)
            result.warnings.append(msg)

            if cross_check:
                result.success = False
                result.error = f"Cross-check failure: {msg}. Aborting to prevent unsafe flight."
                return result

        result.recharges.append(RechargeRecord(tick=tick, battery_before_swap=battery))
        result.total_battery_consumed += outbound_cost + return_cost
        battery = cfg.battery_capacity

    result.total_ticks = tick
    return result
