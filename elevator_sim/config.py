"""The settings of a run, in one place. Every default lives here and nowhere else."""

from dataclasses import dataclass


@dataclass(frozen=True)  # frozen: once a Config is made, its values cannot be changed
class Config:
    """Everything about the building that can be set. Leave a value out to get its default."""

    num_cars: int = 1  # how many cars the building has
    num_floors: int = 51  # floors are numbered 1 to num_floors; 51 fits the assignment's sample
    capacity: int = 10  # the most riders one car may hold at one time
    start_floor: int = 1  # where every car waits at tick 0
    max_ticks: int = 10_000  # safety stop: the run fails loudly if anyone is still undelivered this long after the last request
