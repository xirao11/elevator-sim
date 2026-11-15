"""One car. A "car" is one elevator."""

import copy
from dataclasses import dataclass, field
from typing import Optional

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
    stop_time: int = 0  # extra ticks the car stays at a floor when anyone steps in or out; 0 means a stop is free
    stop_ticks_left: int = 0  # how many of those ticks are still to come at the stop it is making now

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
        """Step 7 of a tick: travel one floor in the chosen direction. An idle car stays, and so does a car in the middle of a stop."""
        if self.stop_ticks_left > 0:
            self.stop_ticks_left -= 1  # this tick is spent at the stop
            return  # leave the method here: the car does not move
        self.floor += self.direction

    def estimate_arrivals(self, tick: int, newcomer: Optional[Passenger] = None) -> dict[str, int]:
        """An estimate: the tick at which each passenger this car has been given would arrive.

        It counts only people who have already asked: those waiting for this car, those riding in it,
        and `newcomer` if one is passed ("what if this car got them?"). It knows nothing about requests
        that have not been made yet, so the estimate is exact only if nobody else asks for this car.

        `tick` is now. The work is done on a copy that follows the same rules as the real car, so the
        real car and its passengers are not touched. What comes back looks like {"p7": 31, "p9": 44}.
        """
        car = copy.deepcopy(self)  # a full copy: the car, its two lists and every passenger in them
        if newcomer is not None:
            car.assign(copy.deepcopy(newcomer))
        everyone = car.waiting + car.riders  # a list of its own, so it still names them after they have left the car
        while True:
            car.serve_floor(tick)  # the same steps the real car takes in every tick
            if len(car.waiting) == 0 and len(car.riders) == 0:
                break  # everyone has arrived
            car.move()
            tick += 1
        return {passenger.id: passenger.arrive_time for passenger in everyone}

    def _hold(self) -> None:
        """Someone stepped in or out, so the car has made a stop: it stays here `stop_time` more ticks.

        A method cannot make time pass; only the simulation's loop does that. So this writes down how
        many ticks the car still has to stay, and `move` uses them up one tick at a time. It sets the
        number and does not add to it: five people at one floor are still one stop.
        """
        self.stop_ticks_left = self.stop_time

    def _unload(self, tick: int) -> None:
        """Riders whose floor this is step out."""
        staying = []
        for passenger in self.riders:
            if passenger.dest == self.floor:
                passenger.arrive_time = tick
                self._hold()
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
        """People waiting here who are going the car's way step in while there is room."""
        still_waiting = []
        # `waiting` is in the order people were given to the car, so whoever asked first boards first.
        for passenger in self.waiting:
            here_and_my_way = passenger.source == self.floor and passenger.direction == self.direction
            if here_and_my_way and not self.is_full:  # the door rule: nobody boards a full car
                passenger.board_time = tick
                self.riders.append(passenger)
                self._hold()
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
