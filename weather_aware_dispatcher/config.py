from __future__ import annotations

from dataclasses import dataclass, field

from weather_aware_dispatcher.models.coordinate import Coordinate


@dataclass(frozen=True)
class SimulationConfig:
    battery_capacity: float = 100.0
    base_move_cost: float = 1.0
    wind_with_multiplier: float = 0.5
    wind_against_multiplier: float = 2.0
    wind_cross_multiplier: float = 1.0
    payload_penalty_rate: float = 0.10
    payload_penalty_increment_lbs: float = 5.0
    launch_pad: Coordinate = field(default_factory=lambda: Coordinate(0, 0))


DEFAULT_CONFIG = SimulationConfig()

# Backward-compatible module-level constants
BATTERY_CAPACITY = DEFAULT_CONFIG.battery_capacity
BASE_MOVE_COST = DEFAULT_CONFIG.base_move_cost
WIND_WITH_MULTIPLIER = DEFAULT_CONFIG.wind_with_multiplier
WIND_AGAINST_MULTIPLIER = DEFAULT_CONFIG.wind_against_multiplier
WIND_CROSS_MULTIPLIER = DEFAULT_CONFIG.wind_cross_multiplier
PAYLOAD_PENALTY_RATE = DEFAULT_CONFIG.payload_penalty_rate
PAYLOAD_PENALTY_INCREMENT_LBS = DEFAULT_CONFIG.payload_penalty_increment_lbs
LAUNCH_PAD = DEFAULT_CONFIG.launch_pad
