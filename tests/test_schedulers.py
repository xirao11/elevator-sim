"""Tests for the "which car?" rules."""

from elevator_sim.car import Car
from elevator_sim.passenger import Passenger
from elevator_sim.schedulers import nearest_car, round_robin


def test_round_robin_takes_turns_and_wraps_round():
    cars = [Car(number=0, capacity=10), Car(number=1, capacity=10), Car(number=2, capacity=10)]

    picked = []
    for n in range(4):
        passenger = Passenger(id=f"p{n}", source=1, dest=5, request_time=0)
        car = round_robin(passenger, cars)
        car.assign(passenger)
        picked.append(car.number)

    assert picked == [0, 1, 2, 0]  # the fourth passenger goes back to car 0


def test_nearest_car_picks_the_car_fewest_floors_away():
    cars = [
        Car(number=0, capacity=10, floor=1),
        Car(number=1, capacity=10, floor=12),
        Car(number=2, capacity=10, floor=30),
    ]
    passenger = Passenger(id="p", source=10, dest=20, request_time=0)

    # Distances from floor 10 are 9, 2 and 20.
    assert nearest_car(passenger, cars).number == 1


def test_nearest_car_tie_goes_to_the_lowest_car_number():
    cars = [Car(number=0, capacity=10, floor=8), Car(number=1, capacity=10, floor=12)]
    passenger = Passenger(id="p", source=10, dest=20, request_time=0)

    # Both cars are 2 floors away.
    assert nearest_car(passenger, cars).number == 0


def rider():
    # Someone to put inside a car, so that a car with room for one is full.
    return Passenger(id="rider", source=1, dest=50, request_time=0)


def test_nearest_car_skips_a_car_that_is_full():
    cars = [Car(number=0, capacity=1, floor=10), Car(number=1, capacity=1, floor=30)]
    cars[0].riders.append(rider())  # car 0 is now full
    passenger = Passenger(id="p", source=11, dest=20, request_time=0)

    # Car 0 is 1 floor away and car 1 is 19, but car 0 is full.
    assert nearest_car(passenger, cars).number == 1


def test_round_robin_skips_a_car_that_is_full():
    cars = [Car(number=0, capacity=1), Car(number=1, capacity=1)]
    cars[0].riders.append(rider())  # car 0 is now full
    passenger = Passenger(id="p", source=1, dest=5, request_time=0)

    # It would be car 0's turn, but car 0 is full.
    assert round_robin(passenger, cars).number == 1


def test_when_every_car_is_full_a_car_is_still_picked():
    cars = [Car(number=0, capacity=1, floor=10), Car(number=1, capacity=1, floor=30)]
    cars[0].riders.append(rider())
    cars[1].riders.append(rider())
    passenger = Passenger(id="p", source=28, dest=20, request_time=0)

    # Nobody is left without a car: with every car full, the usual rule picks among all of them.
    assert nearest_car(passenger, cars).number == 1
