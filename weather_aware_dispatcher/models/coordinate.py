from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Coordinate:
    x: int
    y: int

    def manhattan_distance(self, other: Coordinate) -> int:
        return abs(self.x - other.x) + abs(self.y - other.y)

    def neighbors(self) -> list[Coordinate]:
        """Return 4-directional neighbors (no bounds checking)."""
        return [
            Coordinate(self.x, self.y + 1),  # North
            Coordinate(self.x, self.y - 1),  # South
            Coordinate(self.x + 1, self.y),   # East
            Coordinate(self.x - 1, self.y),   # West
        ]

    def __repr__(self) -> str:
        return f"({self.x}, {self.y})"
