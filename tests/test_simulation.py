"""Tests for the clock. Each trip was traced by hand before the code ran."""

import pytest

from elevator_sim.config import Config
from elevator_sim.passenger import Passenger
from elevator_sim.schedulers import nearest_car, round_robin
from elevator_sim.simulation import run


def sample_passengers():
    # The three passengers of data/sample_requests.csv.
    passenger1 = Passenger(id="passenger1", source=1, dest=51, request_time=0)
    passenger2 = Passenger(id="passenger2", source=1, dest=37, request_time=0)
    passenger3 = Passenger(id="passenger3", source=20, dest=1, request_time=10)
    return passenger1, passenger2, passenger3


def test_car_fetches_one_passenger_from_above_and_brings_them_down():
    # The car starts idle at floor 1. The passenger asks at tick 2, on floor 4, for floor 2.
    passenger = Passenger(id="p1", source=4, dest=2, request_time=2)

    log = run([passenger])

    # One row per tick, ticks 0 to 7. Each row holds one number, because there is one car.
    assert log == [[1], [1], [1], [2], [3], [4], [3], [2]]
    assert passenger.board_time == 5  # 3 floors to climb from tick 2, one per tick
    assert passenger.arrive_time == 7
    assert passenger.wait_time == 3
    assert passenger.travel_time == 2
    assert passenger.total_time == 5


def test_sample_file_one_car_finishes_going_up_before_turning_round():
    # One car, idle at floor 1.
    passenger1, passenger2, passenger3 = sample_passengers()

    log = run([passenger1, passenger2, passenger3])

    # The first two are at the car's floor when they ask, so they board in the same tick.
    assert passenger1.board_time == 0
    assert passenger2.board_time == 0
    assert passenger2.arrive_time == 36  # 36 floors up
    assert passenger1.arrive_time == 50  # 50 floors up

    # The car does not turn round for passenger3. It goes on up to 51, then comes down 31 floors.
    assert log[10] == [11]  # where the car is when passenger3 asks
    assert passenger3.board_time == 81
    assert passenger3.arrive_time == 100  # 19 floors down
    assert len(log) == 101  # one row per tick, from tick 0 to tick 100


def test_sample_file_two_cars_round_robin_gives_the_third_passenger_to_car_0_again():
    # Two cars, both idle at floor 1. Round robin hands passengers out in turn.
    passenger1, passenger2, passenger3 = sample_passengers()

    log = run([passenger1, passenger2, passenger3], config=Config(num_cars=2), scheduler=round_robin)

    assert passenger1.car_number == 0
    assert passenger2.car_number == 1
    assert passenger3.car_number == 0  # the turn wraps round

    assert passenger1.board_time == 0
    assert passenger1.arrive_time == 50
    assert passenger2.board_time == 0
    assert passenger2.arrive_time == 36

    # Round robin does not look at the cars. Car 0 is the one going all the way to 51,
    # so passenger3 waits exactly as long as with one car.
    assert log[10] == [11, 11]  # both cars are at floor 11 when passenger3 asks
    assert passenger3.board_time == 81
    assert passenger3.arrive_time == 100

    assert log[100] == [1, 37]  # car 1 has been resting at floor 37 since tick 36
    assert len(log) == 101


def test_sample_file_two_cars_nearest_car_gives_everyone_to_car_0():
    # Two cars, both idle at floor 1. Nearest car looks only at how many floors away each car is.
    passenger1, passenger2, passenger3 = sample_passengers()

    log = run([passenger1, passenger2, passenger3], config=Config(num_cars=2), scheduler=nearest_car)

    assert passenger1.car_number == 0  # both cars are at floor 1: a tie, so the lowest number wins
    assert passenger2.car_number == 0  # still a tie: car 0 has not moved yet at tick 0
    assert log[10] == [11, 1]
    assert passenger3.car_number == 0  # car 0 is 9 floors from floor 20, car 1 is 19

    # Car 0 is nearest in floors but it is on its way up to 51, so passenger3 still boards at 81.
    assert passenger3.board_time == 81
    assert passenger3.arrive_time == 100
    assert all(row[1] == 1 for row in log)  # car 1 never moves


def test_one_car_with_room_for_one_comes_back_for_the_passenger_it_left_behind():
    # One car that holds one rider. Two people ask at floor 1 at tick 0.
    p1 = Passenger(id="p1", source=1, dest=5, request_time=0)
    p2 = Passenger(id="p2", source=1, dest=3, request_time=0)

    log = run([p1, p2], config=Config(capacity=1))

    assert p1.board_time == 0  # p1 is first in the file, so p1 boards first
    assert p1.arrive_time == 4
    assert p2.board_time == 8  # the car goes up 4 floors and comes back down 4
    assert p2.arrive_time == 10
    assert log == [[1], [2], [3], [4], [5], [4], [3], [2], [1], [2], [3]]


def test_sample_file_two_cars_with_room_for_one_nearest_car_skips_the_full_car():
    # Two cars that hold one rider each, both idle at floor 1.
    passenger1, passenger2, passenger3 = sample_passengers()

    log = run([passenger1, passenger2, passenger3], config=Config(num_cars=2, capacity=1), scheduler=nearest_car)

    # At tick 0 nobody has boarded yet when passenger2 is assigned, so car 0 does not look full.
    assert passenger1.car_number == 0
    assert passenger2.car_number == 0
    assert passenger1.board_time == 0
    assert passenger1.arrive_time == 50

    # At tick 10 car 0 is full, so it is skipped although it is nearer. Car 1 fetches passenger3.
    assert passenger3.car_number == 1
    assert passenger3.board_time == 29  # 19 floors up from floor 1, starting at tick 10
    assert passenger3.arrive_time == 48

    # passenger2 was left behind at floor 1 and waits for car 0 to come all the way back.
    assert passenger2.board_time == 100
    assert passenger2.arrive_time == 136
    assert len(log) == 137


def test_safety_stop_counts_from_the_last_request_so_a_late_request_still_finishes():
    # The stop allows only 5 ticks, but it counts from the request at tick 100, not from tick 0.
    passenger = Passenger(id="late", source=1, dest=3, request_time=100)

    run([passenger], config=Config(max_ticks=5))

    assert passenger.arrive_time == 102


def test_safety_stop_still_fails_loudly_when_a_run_takes_too_long():
    # The trip needs 2 ticks after the request; the stop allows only 1.
    passenger = Passenger(id="p1", source=1, dest=3, request_time=0)

    with pytest.raises(RuntimeError):
        run([passenger], config=Config(max_ticks=1))


def test_with_a_stop_time_the_stop_where_a_passenger_steps_in_costs_ticks():
    # One passenger, three floors up, and every stop costs 2 ticks.
    passenger = Passenger(id="p1", source=1, dest=4, request_time=0)

    log = run([passenger], config=Config(stop_time=2))

    assert passenger.board_time == 0  # stepping in is still immediate, so the wait is 0
    assert log == [[1], [1], [1], [2], [3], [4]]  # two ticks at the stop, then three floors
    assert passenger.arrive_time == 5  # 2 + 3; with free stops it is 3


def test_with_a_stop_time_a_pick_up_on_the_way_delays_the_rider_already_inside():
    # One car, and every stop costs 1 tick. Ann rides from floor 1 to 5; Ben steps in on floor 3 on the way.
    ann = Passenger(id="Ann", source=1, dest=5, request_time=0)
    ben = Passenger(id="Ben", source=3, dest=5, request_time=0)

    log = run([ann, ben], config=Config(stop_time=1))

    assert log == [[1], [1], [2], [3], [3], [4], [5]]  # one tick at floor 1 for Ann, one at floor 3 for Ben
    assert ben.board_time == 3  # 2 floors, plus the stop where Ann stepped in
    assert ann.arrive_time == 6  # 4 floors, plus her own stop, plus Ben's stop; with free stops it is 4
    assert ben.arrive_time == 6
