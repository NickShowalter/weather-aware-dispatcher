from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from weather_aware_dispatcher.models.coordinate import Coordinate
from weather_aware_dispatcher.models.package import Package


@dataclass(frozen=True)
class DroneState:
    position: Coordinate
    battery: float
    tick: int
    carrying: Optional[Package] = None
    delivered: frozenset[str] = frozenset()
