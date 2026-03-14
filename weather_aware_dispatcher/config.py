from weather_aware_dispatcher.models.coordinate import Coordinate

BATTERY_CAPACITY: float = 100.0
BASE_MOVE_COST: float = 1.0
WIND_WITH_MULTIPLIER: float = 0.5
WIND_AGAINST_MULTIPLIER: float = 2.0
WIND_CROSS_MULTIPLIER: float = 1.0
PAYLOAD_PENALTY_RATE: float = 0.10
PAYLOAD_PENALTY_INCREMENT_LBS: float = 5.0
LAUNCH_PAD: Coordinate = Coordinate(0, 0)
