from __future__ import annotations

from enum import Enum


class Direction(Enum):
    NORTH = "NORTH"
    SOUTH = "SOUTH"
    EAST = "EAST"
    WEST = "WEST"

    def opposite(self) -> Direction:
        return _OPPOSITES[self]

    def is_perpendicular(self, other: Direction) -> bool:
        return other not in (self, self.opposite())

    def to_delta(self) -> tuple[int, int]:
        return _DELTAS[self]


_OPPOSITES = {
    Direction.NORTH: Direction.SOUTH,
    Direction.SOUTH: Direction.NORTH,
    Direction.EAST: Direction.WEST,
    Direction.WEST: Direction.EAST,
}

_DELTAS = {
    Direction.NORTH: (0, 1),
    Direction.SOUTH: (0, -1),
    Direction.EAST: (1, 0),
    Direction.WEST: (-1, 0),
}

# Reverse lookup: delta -> Direction
DELTA_TO_DIRECTION: dict[tuple[int, int], Direction] = {v: k for k, v in _DELTAS.items()}
