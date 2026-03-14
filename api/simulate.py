from http.server import BaseHTTPRequestHandler
import json
import sys
import os

# Add project root to path so weather_aware_dispatcher is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from weather_aware_dispatcher.config import DEFAULT_CONFIG
from weather_aware_dispatcher.core.delivery_planner import plan_deliveries
from weather_aware_dispatcher.core.simulation_engine import simulate
from weather_aware_dispatcher.io.input_loader import load_from_dict


def _serialize_result(plan, result, config):
    planned = []
    for d in plan.planned_deliveries:
        planned.append({
            "package_id": d.package.id,
            "destination": [d.package.destination.x, d.package.destination.y],
            "weight_lbs": d.package.weight_lbs,
            "outbound_path": [[c.x, c.y] for c in d.outbound_path],
            "return_path": [[c.x, c.y] for c in d.return_path],
            "outbound_cost": round(d.outbound_cost, 4),
            "return_cost": round(d.return_cost, 4),
            "round_trip_cost": round(d.round_trip_cost, 4),
            "start_tick": d.start_tick,
            "end_tick": d.end_tick,
        })

    moves = []
    for m in result.moves:
        moves.append({
            "tick": m.tick,
            "from": [m.from_coord.x, m.from_coord.y],
            "to": [m.to_coord.x, m.to_coord.y],
            "direction": m.direction.value,
            "wind": m.wind.value,
            "cost": round(m.cost, 4),
            "battery_after": round(m.battery_after, 4),
        })

    deliveries = []
    for d in result.deliveries:
        deliveries.append({
            "package_id": d.package_id,
            "tick": d.tick,
            "outbound_cost": round(d.outbound_cost, 4),
            "return_cost": round(d.return_cost, 4),
        })

    recharges = []
    for r in result.recharges:
        recharges.append({
            "tick": r.tick,
            "battery_before_swap": round(r.battery_before_swap, 4),
        })

    infeasible = []
    for pkg_id, reason in result.infeasible_packages:
        infeasible.append({"package_id": pkg_id, "reason": reason})

    return {
        "success": result.success,
        "error": result.error,
        "planned_deliveries": planned,
        "moves": moves,
        "deliveries": deliveries,
        "recharges": recharges,
        "infeasible_packages": infeasible,
        "total_battery_consumed": round(result.total_battery_consumed, 4),
        "total_ticks": result.total_ticks,
        "battery_capacity": config.battery_capacity,
    }


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            raw = json.loads(body)

            load_result = load_from_dict(raw)
            if not load_result.ok:
                self._json_response(400, {"success": False, "errors": load_result.errors})
                return

            data = load_result.data
            plan = plan_deliveries(data.packages, data.grid, data.weather, data.config)
            result = simulate(plan, data.weather, data.config)
            response = _serialize_result(plan, result, data.config)
            self._json_response(200, response)

        except Exception as e:
            self._json_response(500, {"success": False, "errors": [str(e)]})

    def _json_response(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
