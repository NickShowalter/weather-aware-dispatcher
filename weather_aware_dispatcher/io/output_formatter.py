from __future__ import annotations

from weather_aware_dispatcher.core.delivery_planner import DeliveryPlan
from weather_aware_dispatcher.core.simulation_engine import SimulationResult


def format_result(plan: DeliveryPlan, result: SimulationResult) -> str:
    lines: list[str] = []

    lines.append("=== WEATHER-AWARE DISPATCHER — FLIGHT PLAN ===")
    lines.append("")

    if not result.success:
        lines.append(f"FLIGHT PLAN FAILED: {result.error}")
        return "\n".join(lines)

    # Delivery sequence summary
    lines.append("Delivery Sequence:")
    for i, delivery in enumerate(plan.planned_deliveries, 1):
        pkg = delivery.package
        lines.append(f"  {i}. {pkg.id} → {pkg.destination} [{pkg.weight_lbs:.1f} lbs]")

    if not plan.planned_deliveries:
        lines.append("  (no deliveries)")

    lines.append("")

    # Detailed delivery info
    for i, delivery in enumerate(plan.planned_deliveries, 1):
        pkg = delivery.package
        outbound_moves = len(delivery.outbound_path) - 1
        return_moves = len(delivery.return_path) - 1

        lines.append(f"--- Delivery {i}: {pkg.id} ---")
        lines.append(
            f"  Outbound: {delivery.outbound_path[0]} → {delivery.outbound_path[-1]} "
            f"| Moves: {outbound_moves} | Cost: {delivery.outbound_cost:.2f}"
        )
        lines.append(f"  Path: {'→'.join(str(c) for c in delivery.outbound_path)}")
        lines.append(
            f"  Return:  {delivery.return_path[0]} → {delivery.return_path[-1]} "
            f"| Moves: {return_moves} | Cost: {delivery.return_cost:.2f}"
        )
        lines.append(f"  Path: {'→'.join(str(c) for c in delivery.return_path)}")
        lines.append(
            f"  Round-trip: {delivery.round_trip_cost:.2f} battery "
            f"| Battery swap at tick {delivery.end_tick}"
        )
        lines.append("")

    # Summary
    total_packages = len(plan.planned_deliveries) + len(plan.infeasible_packages)
    delivered = len(plan.planned_deliveries)

    lines.append("=== SUMMARY ===")
    lines.append(f"  Packages delivered: {delivered}/{total_packages}")
    lines.append(f"  Total battery consumed: {result.total_battery_consumed:.2f} units")
    lines.append(f"  Total ticks: {result.total_ticks}")
    lines.append(f"  Battery swaps: {len(result.recharges)}")
    lines.append(f"  Infeasible packages: {len(plan.infeasible_packages)}")

    if plan.infeasible_packages:
        lines.append("")
        lines.append("  Infeasible details:")
        for pkg, reason in plan.infeasible_packages:
            lines.append(f"    - {pkg.id}: {reason}")

    return "\n".join(lines)
