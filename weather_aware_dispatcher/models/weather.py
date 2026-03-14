from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from weather_aware_dispatcher.models.direction import Direction


@dataclass(frozen=True)
class WeatherSegment:
    direction: Direction
    start_tick: int
    end_tick: Optional[int]

    def contains_tick(self, tick: int) -> bool:
        if tick < self.start_tick:
            return False
        if self.end_tick is None:
            return True
        return tick <= self.end_tick


class WeatherForecast:
    def __init__(self, segments: list[WeatherSegment]) -> None:
        self.segments = sorted(segments, key=lambda s: s.start_tick)

    def wind_at_tick(self, tick: int) -> Direction:
        for segment in self.segments:
            if segment.contains_tick(tick):
                return segment.direction
        # Fallback: return the last segment's direction (should have null end_tick)
        return self.segments[-1].direction
