"""Tests for the rule checker: a correct run passes, and each rule catches a run that breaks it."""

from elevator_sim.config import Config
from elevator_sim.passenger import Passenger
from elevator_sim.rules import check_run
from elevator_sim.schedulers import nearest_car
from elevator_sim.simulation import run

TWO_CARS = Config(num_cars=2)


def sample_run():
    """A correct run to start from: the assignment's sample, two cars, nearest car. Everyone rides car 0."""
    passengers = [
        Passenger(id="passenger1", source=1, dest=51, request_time=0),
        Passenger(id="passenger2", source=1, dest=37, request_time=0),
        Passenger(id="passenger3", source=20, dest=1, request_time=10),
    ]
    log = run(passengers, TWO_CARS, scheduler=nearest_car)
    return passengers, log


def test_a_correct_run_breaks_no_rule():
    passengers, log = sample_run()

    assert check_run(passengers, log, TWO_CARS) == []


def test_served_catches_a_passenger_who_boards_before_asking():
    passengers, log = sample_run()
    passengers[2].board_time = 5  # passenger3 asked at tick 10

    assert check_run(passengers, log, TWO_CARS) == [
        "served: passenger3 has times out of order: asked at 10, boarded at 5, arrived at 100"
    ]


def test_served_catches_a_passenger_who_never_arrives():
    passengers, log = sample_run()
    passengers[1].arrive_time = None

    assert check_run(passengers, log, TWO_CARS) == ["served: passenger2 never boarded or never arrived"]


def test_capacity_catches_a_car_holding_too_many():
    passengers, log = sample_run()
    room_for_one = Config(num_cars=2, capacity=1)  # the same run, judged as if each car held one rider

    assert check_run(passengers, log, room_for_one) == [
        "capacity: car 0 holds 2 riders at tick 0, but its capacity is 1"
    ]


def test_direction_catches_a_passenger_carried_the_wrong_way():
    # A run written by hand, in which the car does what my simulation never does. One car goes 1, 2, 3, 2, 1.
    # "up" rides 1 to 3. "down" wants floor 1, but is let in at floor 2 while the car is still going up.
    up = Passenger(id="up", source=1, dest=3, request_time=0, car_number=0, board_time=0, arrive_time=2)
    down = Passenger(id="down", source=2, dest=1, request_time=0, car_number=0, board_time=1, arrive_time=4)
    log = [[1], [2], [3], [2], [1]]

    assert check_run([up, down], log, Config()) == ["direction: car 0 moved away from down's destination at tick 1"]


def test_movement_catches_a_car_that_jumps_or_leaves_the_building():
    passengers, log = sample_run()
    log[5][1] = 3  # car 1 never moves in this run; put it on floor 3 for one tick

    assert check_run(passengers, log, TWO_CARS) == ["movement: car 1 jumps from floor 1 to 3 at tick 5"]

    passengers, log = sample_run()
    log[5][1] = 0  # one floor away, so not a jump, but there is no floor 0

    assert check_run(passengers, log, TWO_CARS) == [
        "movement: car 1 is at floor 0 at tick 5, outside the building (1 to 51)"
    ]


def test_records_catches_a_time_that_disagrees_with_the_log():
    passengers, log = sample_run()
    passengers[1].arrive_time = 30  # passenger2 really steps out at tick 36, on floor 37

    assert check_run(passengers, log, TWO_CARS) == [
        "records: passenger2 left car 0 at tick 30 on floor 37, but the log has that car at floor 31"
    ]


def test_records_catches_a_log_that_runs_past_the_last_arrival():
    passengers, log = sample_run()
    log.append(log[-1])  # one extra tick in which nothing happens

    assert check_run(passengers, log, TWO_CARS) == [
        "records: the log ends at tick 101, but the last passenger steps out at tick 100"
    ]
