"""The rule checker. Given a finished run, it lists every rule that the run broke.

It reads only the results of a run: the positions log, and each passenger's car, board time and
arrive time. It shares no code with car.py or simulation.py, so a bug there cannot hide in here.

The five rules:
    served      everyone was given a real car, then boarded, then arrived
    capacity    no car ever holds more riders than its capacity
    direction   while someone is inside, their car never moves away from their destination
    movement    cars start at the start floor, stay in the building, and move at most one floor per tick
    records     the passenger records and the positions log tell the same story
"""

from elevator_sim.config import Config
from elevator_sim.passenger import Passenger


def check_run(passengers: list[Passenger], log: list[list[int]], config: Config) -> list[str]:
    """Every rule this run broke, as one message each. An empty list means no rule was broken.

    Like read_requests, this only finds problems. What to do about them is up to the caller.
    """
    if len(log) == 0 or any(len(row) != config.num_cars for row in log):
        return ["movement: the log needs at least one row, and every row needs one floor per car"]
    problems = _check_movement(log, config)
    last_tick = len(log) - 1

    # Rule "served". Only the passengers who pass it can be compared with the log further down.
    served = []
    for p in passengers:
        if p.car_number is None or not 0 <= p.car_number < config.num_cars:
            problems.append(f"served: {p.id} was not given a car of this building")
        elif p.board_time is None or p.arrive_time is None:
            problems.append(f"served: {p.id} never boarded or never arrived")
        elif not 0 <= p.request_time <= p.board_time < p.arrive_time:
            problems.append(
                f"served: {p.id} has times out of order: asked at {p.request_time}, "
                f"boarded at {p.board_time}, arrived at {p.arrive_time}"
            )
        else:
            served.append(p)

    # Rule "records", part 1: the log ends at the tick the last passenger steps out.
    last_arrival = max((p.arrive_time for p in passengers if p.arrive_time is not None), default=0)
    if last_arrival != last_tick:
        problems.append(
            f"records: the log ends at tick {last_tick}, but the last passenger steps out at tick {last_arrival}"
        )

    # riders[tick][car]: how many people are inside. Built row by row, so every tick has its own list.
    riders = [[0] * config.num_cars for row in log]
    for p in served:
        if p.arrive_time > last_tick:
            continue  # the log is too short to follow this ride; that was reported just above
        car = p.car_number

        # Rule "records", part 2: the car is where the passenger's record says, when they step in and out.
        if log[p.board_time][car] != p.source:
            problems.append(
                f"records: {p.id} boarded car {car} at tick {p.board_time} on floor {p.source}, "
                f"but the log has that car at floor {log[p.board_time][car]}"
            )
        if log[p.arrive_time][car] != p.dest:
            problems.append(
                f"records: {p.id} left car {car} at tick {p.arrive_time} on floor {p.dest}, "
                f"but the log has that car at floor {log[p.arrive_time][car]}"
            )

        # The passenger is inside from the tick they board up to, but not including, the tick they step out.
        moved_away = []
        for tick in range(p.board_time, p.arrive_time):
            riders[tick][car] += 1
            step = log[tick + 1][car] - log[tick][car]  # +1 the car went up, -1 down, 0 it stayed
            if step * p.direction < 0:  # opposite signs: the car went the other way
                moved_away.append(tick)
        if len(moved_away) > 0:  # rule "direction"
            problems.append(f"direction: car {car} moved away from {p.id}'s destination at tick {moved_away[0]}")

    # Rule "capacity", counted from the passenger records alone.
    for car in range(config.num_cars):
        for tick in range(len(log)):
            if riders[tick][car] > config.capacity:
                problems.append(
                    f"capacity: car {car} holds {riders[tick][car]} riders at tick {tick}, "
                    f"but its capacity is {config.capacity}"
                )
                break  # the first tick is enough: one message per car
    return problems


def _check_movement(log: list[list[int]], config: Config) -> list[str]:
    """Rule "movement", from the log alone. At most one message of each kind per car."""
    problems = []
    for car in range(config.num_cars):
        floors = [row[car] for row in log]  # this car's floor at every tick
        if floors[0] != config.start_floor:
            problems.append(f"movement: car {car} starts at floor {floors[0]}, not at the start floor {config.start_floor}")
        for tick, floor in enumerate(floors):
            if not 1 <= floor <= config.num_floors:
                problems.append(
                    f"movement: car {car} is at floor {floor} at tick {tick}, "
                    f"outside the building (1 to {config.num_floors})"
                )
                break
        for tick in range(1, len(floors)):
            if abs(floors[tick] - floors[tick - 1]) > 1:
                problems.append(f"movement: car {car} jumps from floor {floors[tick - 1]} to {floors[tick]} at tick {tick}")
                break
    return problems
