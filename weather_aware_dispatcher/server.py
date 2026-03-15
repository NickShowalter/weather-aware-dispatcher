from __future__ import annotations

import json
import logging
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Any

from weather_aware_dispatcher.config import DEFAULT_CONFIG
from weather_aware_dispatcher.core.delivery_planner import plan_deliveries
from weather_aware_dispatcher.core.simulation_engine import simulate
from weather_aware_dispatcher.io.input_loader import load_from_dict

logger = logging.getLogger(__name__)

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")


def _serialize_result(plan, result, config) -> dict[str, Any]:
    """Serialize simulation results to JSON-compatible dict."""
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
        "warnings": getattr(result, 'warnings', []),
    }


class DispatcherHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_POST(self):
        if self.path == "/api/simulate":
            self._handle_simulate()
        else:
            self.send_error(404)

    def do_GET(self):
        if self.path == "/api/defaults":
            self._handle_defaults()
        else:
            super().do_GET()

    def _handle_simulate(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            raw = json.loads(body)

            load_result = load_from_dict(raw)
            if not load_result.ok:
                self._json_response(400, {"success": False, "errors": load_result.errors})
                return

            data = load_result.data
            algo = data.algorithm
            plan = plan_deliveries(
                data.packages, data.grid, data.weather, data.config,
                ordering=algo.ordering,
                perm_threshold=algo.perm_threshold,
                pathfinding_mode=algo.pathfinding,
            )
            result = simulate(plan, data.weather, data.config, cross_check=algo.cross_check)
            response = _serialize_result(plan, result, data.config)
            self._json_response(200, response)

        except Exception as e:
            logger.exception("Simulation error")
            self._json_response(500, {"success": False, "errors": [str(e)]})

    def _handle_defaults(self):
        cfg = DEFAULT_CONFIG
        defaults = {
            "config": {
                "battery_capacity": cfg.battery_capacity,
                "base_move_cost": cfg.base_move_cost,
                "wind_with_multiplier": cfg.wind_with_multiplier,
                "wind_against_multiplier": cfg.wind_against_multiplier,
                "wind_cross_multiplier": cfg.wind_cross_multiplier,
                "payload_penalty_rate": cfg.payload_penalty_rate,
                "payload_penalty_increment_lbs": cfg.payload_penalty_increment_lbs,
            },
            "sample_input": {
                "grid_width": 20,
                "grid_height": 20,
                "manifest": [
                    {"id": "pkg_1", "destination": [18, 18], "weight_lbs": 5},
                    {"id": "pkg_2", "destination": [2, 15], "weight_lbs": 10},
                    {"id": "pkg_3", "destination": [15, 2], "weight_lbs": 2},
                ],
                "weather_forecast": [
                    {"direction": "EAST", "start_tick": 0, "end_tick": 49},
                    {"direction": "NORTH", "start_tick": 50, "end_tick": 99},
                    {"direction": "WEST", "start_tick": 100, "end_tick": None},
                ],
                "obstacles": [[5, 5], [5, 6], [5, 7], [12, 15], [12, 16]],
            },
            "presets": {
                "sample": "Default sample scenario",
                "stress_low_battery": "Battery capacity reduced to 40",
                "stress_heavy_wind": "Wind against multiplier set to 4.0",
                "edge_small_grid": "5x5 grid with tight obstacles",
                "edge_no_wind_penalty": "All wind multipliers set to 1.0",
            },
        }
        self._json_response(200, defaults)

    def _json_response(self, code: int, data: dict):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        logger.info(format, *args)


def run_server(port: int = 8080):
    server = HTTPServer(("", port), DispatcherHandler)
    print(f"Weather-Aware Dispatcher server running at http://localhost:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()
