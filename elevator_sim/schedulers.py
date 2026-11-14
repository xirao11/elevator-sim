"""The "which car?" rules. Every scheduler has the same shape: one new passenger and all the cars in, one car out."""

from elevator_sim.car import Car
from elevator_sim.passenger import Passenger


def available(cars: list[Car]) -> list[Car]:
    """The cars a scheduler may choose from: those that are not full right now.

    If every car is full, all of them are returned, so a passenger is never left without a car.
    """
    not_full = [car for car in cars if not car.is_full]
    if len(not_full) == 0:
        return cars
    return not_full


def round_robin(passenger: Passenger, cars: list[Car]) -> Car:
    """The cars that are not full take turns. It looks at nothing else."""
    handed_out = sum(car.assigned_count for car in cars)  # passengers given to any car so far
    candidates = available(cars)
    turn = handed_out % len(candidates)  # % is the remainder, so the turn wraps round to 0
    return candidates[turn]


def nearest_car(passenger: Passenger, cars: list[Car]) -> Car:
    """The car that is the fewest floors from the passenger right now, among those that are not full.

    It ignores which way the car is going and who else it has been given.
    When several cars are equally near, the lowest car number wins.
    """
    candidates = available(cars)
    best = candidates[0]
    best_distance = abs(best.floor - passenger.source)
    for car in candidates[1:]:  # every candidate after the first
        distance = abs(car.floor - passenger.source)
        if distance < best_distance:  # strictly nearer; on a tie the earlier car is kept
            best = car
            best_distance = distance
    return best


# The name typed on the command line -> the function it means. Add a scheduler here to make it selectable.
SCHEDULERS = {"round_robin": round_robin, "nearest_car": nearest_car}
