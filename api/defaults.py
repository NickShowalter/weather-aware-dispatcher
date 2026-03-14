from http.server import BaseHTTPRequestHandler
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from weather_aware_dispatcher.config import DEFAULT_CONFIG


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
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
                "edge_no_wind": "All wind multipliers set to 1.0",
            },
        }

        body = json.dumps(defaults).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
