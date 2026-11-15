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


def least_newcomer_time(passenger: Passenger, cars: list[Car]) -> Car:
    """The car that would bring the newcomer, the passenger asking now, to their destination soonest, among those that are not full.

    Each car is asked for an estimate: "if you were given this passenger, at which tick would they arrive?"
    The estimate knows where the car has to go first and whether it will have room, but it counts only
    people who have already asked. What the choice does to the car's other passengers is ignored.
    When several cars are equally fast, the lowest car number wins.
    """
    now = passenger.request_time  # a scheduler is called at the tick the passenger asks
    candidates = available(cars)
    best = candidates[0]
    best_arrival = best.estimate_arrivals(now, newcomer=passenger)[passenger.id]
    for car in candidates[1:]:
        arrival = car.estimate_arrivals(now, newcomer=passenger)[passenger.id]
        if arrival < best_arrival:  # strictly sooner; on a tie the earlier car is kept
            best = car
            best_arrival = arrival
    return best


def combined_time(passenger: Passenger, car: Car) -> int:
    """The newcomer's own time in this car, plus the time they add to everyone already given to it, in ticks.

    The car is asked for two estimates: as it stands, and with the newcomer added. The newcomer's own
    time is their arrival minus now. The time added to someone else is how much later they arrive in
    the second estimate than in the first.
    """
    now = passenger.request_time
    without = car.estimate_arrivals(now)
    with_newcomer = car.estimate_arrivals(now, newcomer=passenger)
    own_time = with_newcomer[passenger.id] - now
    added_to_others = sum(with_newcomer[name] - without[name] for name in without)  # one term per person already on this car
    return own_time + added_to_others


def least_combined_time(passenger: Passenger, cars: list[Car]) -> Car:
    """The car where the combined time is smallest, among those that are not full.

    This is least_newcomer_time with one more term: the time the newcomer adds to the car's other
    passengers. Passengers of other cars are not affected by the choice, so nothing else can change.
    When several cars are equally good, the lowest car number wins.
    """
    candidates = available(cars)
    best = candidates[0]
    best_time = combined_time(passenger, best)
    for car in candidates[1:]:
        time = combined_time(passenger, car)
        if time < best_time:  # strictly less; on a tie the earlier car is kept
            best = car
            best_time = time
    return best


# The name typed on the command line -> the function it means. Add a scheduler here to make it selectable.
SCHEDULERS = {
    "round_robin": round_robin,
    "nearest_car": nearest_car,
    "least_newcomer_time": least_newcomer_time,
    "least_combined_time": least_combined_time,
}
