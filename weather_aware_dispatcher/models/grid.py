from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from weather_aware_dispatcher.models.coordinate import Coordinate


@dataclass(frozen=True)
class Grid:
    width: int
    height: int
    obstacles: frozenset[Coordinate]

    def is_valid(self, coord: Coordinate) -> bool:
        return (
            0 <= coord.x < self.width
            and 0 <= coord.y < self.height
            and coord not in self.obstacles
        )

    def passable_neighbors(self, coord: Coordinate) -> list[Coordinate]:
        return [n for n in coord.neighbors() if self.is_valid(n)]

    def is_reachable(self, start: Coordinate, end: Coordinate) -> bool:
        if not self.is_valid(start) or not self.is_valid(end):
            return False
        if start == end:
            return True

        visited: set[Coordinate] = {start}
        queue: deque[Coordinate] = deque([start])

        while queue:
            current = queue.popleft()
            for neighbor in self.passable_neighbors(current):
                if neighbor == end:
                    return True
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return False
