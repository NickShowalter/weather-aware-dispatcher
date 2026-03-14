from __future__ import annotations

import math
from dataclasses import dataclass

from weather_aware_dispatcher.models.coordinate import Coordinate


@dataclass(frozen=True)
class Package:
    id: str
    destination: Coordinate
    weight_lbs: float

    @property
    def weight_penalty_multiplier(self) -> float:
        increments = math.floor(self.weight_lbs / 5)
        return 1.0 + increments * 0.10
