"""One passenger: the record of a single trip."""

from dataclasses import dataclass
from typing import Optional

# Directions are numbers so that "move one floor" is simply floor + direction.
UP = 1
DOWN = -1


@dataclass
class Passenger:
    """One person making one trip. One row of the input becomes one Passenger."""

    id: str
    source: int  # floor where they start
    dest: int  # floor where they want to go
    request_time: int  # tick at which they asked for a car

    # Set by the simulation when it happens. None means "has not happened yet".
    car_number: Optional[int] = None  # number of the car they were given
    board_time: Optional[int] = None  # tick at which they stepped into the car
    arrive_time: Optional[int] = None  # tick at which they stepped out at dest

    @property
    def direction(self) -> int:
        """UP or DOWN: the way this passenger needs to travel."""
        return UP if self.dest > self.source else DOWN

    @property
    def wait_time(self) -> int:
        """Ticks between asking for a car and stepping into it."""
        return self.board_time - self.request_time

    @property
    def travel_time(self) -> int:
        """Ticks spent inside the car."""
        return self.arrive_time - self.board_time

    @property
    def total_time(self) -> int:
        """Ticks between asking for a car and stepping out at the destination."""
        return self.arrive_time - self.request_time
