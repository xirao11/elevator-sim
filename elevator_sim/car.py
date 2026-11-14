"""One car. A "car" is one elevator."""

from dataclasses import dataclass, field

from elevator_sim.passenger import DOWN, UP, Passenger

# A passenger travels UP or DOWN. Only a car can also be IDLE.
IDLE = 0


@dataclass
class Car:
    """One elevator. It knows its own passengers, and nothing about other cars or the clock."""

    # These two have no default, so they must always be given. The defaults live in config.py.
    number: int  # which car this is: 0, 1, 2, ...
    capacity: int  # the most riders it may hold at one time
    floor: int = 1  # where the car is now
    direction: int = IDLE  # UP, DOWN or IDLE: the way it moves this tick
    # Every car needs two lists of its own, so a fresh empty list is made for each car.
    waiting: list[Passenger] = field(default_factory=list)  # given to this car, not inside yet
    riders: list[Passenger] = field(default_factory=list)  # inside the car
    assigned_count: int = 0  # how many passengers this car has been given since the start

    @property
    def is_full(self) -> bool:
        """True when the car holds as many riders as it is allowed. Worked out each time it is read."""
        return len(self.riders) >= self.capacity

    def assign(self, passenger: Passenger) -> None:
        """Give a passenger to this car. The car will go and fetch them."""
        passenger.car_number = self.number  # written on the passenger's record
        self.assigned_count += 1
        self.waiting.append(passenger)

    def serve_floor(self, tick: int) -> None:
        """Steps 3 to 5 of a tick: people step out, the car picks its direction, people step in."""
        self._unload(tick)
        self.direction = self._choose_direction()
        self._load(tick)

    def move(self) -> None:
        """Step 7 of a tick: travel one floor in the chosen direction. An idle car stays."""
        self.floor += self.direction

    def _unload(self, tick: int) -> None:
        staying = []
        for passenger in self.riders:
            if passenger.dest == self.floor:
                passenger.arrive_time = tick
            else:
                staying.append(passenger)
        self.riders = staying

    def _choose_direction(self) -> int:
        """Keep going the same way while there is work that way. Otherwise turn round, or rest."""
        if self.direction != IDLE and self._has_work(self.direction):
            return self.direction
        # Nothing left that way, or the car was idle. With work on both sides, UP goes first.
        if self._has_work(UP):
            return UP
        if self._has_work(DOWN):
            return DOWN
        return IDLE

    def _load(self, tick: int) -> None:
        still_waiting = []
        # `waiting` is in the order people were given to the car, so whoever asked first boards first.
        for passenger in self.waiting:
            here_and_my_way = passenger.source == self.floor and passenger.direction == self.direction
            if here_and_my_way and not self.is_full:  # the door rule: nobody boards a full car
                passenger.board_time = tick
                self.riders.append(passenger)
            else:
                still_waiting.append(passenger)
        self.waiting = still_waiting

    def _has_work(self, direction: int) -> bool:
        """True if something gives the car a reason to travel in `direction`."""
        for passenger in self.riders:
            if self._is_ahead(passenger.dest, direction):
                return True  # a rider gets out further that way
        for passenger in self.waiting:
            if self._is_ahead(passenger.source, direction):
                return True  # someone is waiting further that way
            if passenger.source == self.floor and passenger.direction == direction:
                return True  # someone is waiting right here and wants to go that way
        return False

    def _is_ahead(self, target_floor: int, direction: int) -> bool:
        """True if `target_floor` lies beyond the car's own floor when it travels in `direction`."""
        if direction == UP:
            return target_floor > self.floor
        return target_floor < self.floor
