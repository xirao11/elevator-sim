"""Tests for the "which car?" rules."""

from elevator_sim.car import Car
from elevator_sim.passenger import DOWN, UP, Passenger
from elevator_sim.schedulers import combined_time, least_combined_time, least_newcomer_time, nearest_car, round_robin


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


def test_the_estimate_plays_a_copy_of_the_car_with_and_without_a_newcomer():
    # Tick 0. The car is at floor 10 going up, with Rita inside for floor 20. Pat waits at floor 5 for floor 1.
    car = Car(number=0, capacity=10, floor=10, direction=UP)
    rita = Passenger(id="rita", source=1, dest=20, request_time=0)
    pat = Passenger(id="pat", source=5, dest=1, request_time=0)
    car.riders.append(rita)
    car.assign(pat)
    me = Passenger(id="me", source=15, dest=40, request_time=0)  # I have just asked, and no car is mine yet

    without_me = car.estimate_arrivals(tick=0)
    with_me = car.estimate_arrivals(tick=0, newcomer=me)

    # Without me the car turns round at floor 20 and reaches Pat at tick 25. With me it first goes on up to floor 40.
    assert without_me == {"rita": 10, "pat": 29}
    assert with_me == {"rita": 10, "pat": 69, "me": 30}

    # The estimate ran on a copy: the real car has not moved, nobody has really arrived, and I still have no car.
    assert car.floor == 10
    assert pat.arrive_time is None
    assert me.car_number is None


def test_least_newcomer_time_passes_over_a_near_car_that_is_moving_away():
    # I am at floor 7 and want floor 10. Car 0 is 2 floors away but going down, with a rider for floor 1.
    # Car 1 stands idle at floor 3, 4 floors away.
    busy = Car(number=0, capacity=10, floor=9, direction=DOWN)
    busy.riders.append(Passenger(id="rider", source=20, dest=1, request_time=0))
    idle = Car(number=1, capacity=10, floor=3)
    me = Passenger(id="me", source=7, dest=10, request_time=0)

    # Car 0 would go down to floor 1 first and be back at my floor at tick 14. Car 1 reaches me at tick 4.
    assert busy.estimate_arrivals(0, newcomer=me)["me"] == 17
    assert idle.estimate_arrivals(0, newcomer=me)["me"] == 7

    assert nearest_car(me, [busy, idle]) is busy  # counts floors
    assert least_newcomer_time(me, [busy, idle]) is idle  # counts ticks


def test_least_newcomer_time_passes_over_a_car_that_will_have_no_room():
    # Two people already wait at floor 1 for car 0, which holds two. I ask at the same floor.
    crowded = Car(number=0, capacity=2, floor=1)
    crowded.assign(Passenger(id="first", source=1, dest=9, request_time=0))
    crowded.assign(Passenger(id="second", source=1, dest=9, request_time=0))
    empty = Car(number=1, capacity=2, floor=3)
    me = Passenger(id="me", source=1, dest=9, request_time=0)

    # Car 0 is at my floor but leaves full without me and comes back at tick 16. Car 1 reaches me at tick 2.
    assert crowded.estimate_arrivals(0, newcomer=me)["me"] == 24
    assert empty.estimate_arrivals(0, newcomer=me)["me"] == 10

    assert nearest_car(me, [crowded, empty]) is crowded  # it is not full yet: nobody has boarded
    assert least_newcomer_time(me, [crowded, empty]) is empty


def test_least_newcomer_time_tie_goes_to_the_lowest_car_number():
    cars = [Car(number=0, capacity=10, floor=4), Car(number=1, capacity=10, floor=4)]
    me = Passenger(id="me", source=6, dest=8, request_time=0)

    assert least_newcomer_time(me, cars) is cars[0]


def test_least_combined_time_counts_the_delay_to_someone_already_waiting():
    # Tick 0. Car A is at floor 10 going up, with Rita inside for floor 20. Pat waits at floor 5 for floor 1.
    # Car B stands idle at floor 3. I ask at floor 15 for floor 40.
    car_a = Car(number=0, capacity=10, floor=10, direction=UP)
    car_a.riders.append(Passenger(id="rita", source=1, dest=20, request_time=0))
    car_a.assign(Passenger(id="pat", source=5, dest=1, request_time=0))
    car_b = Car(number=1, capacity=10, floor=3)
    me = Passenger(id="me", source=15, dest=40, request_time=0)

    # Car A: I arrive at tick 30, Rita is not delayed, and Pat arrives at 69 instead of 29.
    assert combined_time(me, car_a) == 30 + 0 + 40
    # Car B: I arrive at tick 37 and nobody else is on it.
    assert combined_time(me, car_b) == 37

    assert least_newcomer_time(me, [car_a, car_b]) is car_a  # 30 against 37: best for me
    assert least_combined_time(me, [car_a, car_b]) is car_b  # 70 against 37: best for Pat and me together


def test_least_combined_time_tie_goes_to_the_lowest_car_number():
    cars = [Car(number=0, capacity=10, floor=4), Car(number=1, capacity=10, floor=4)]
    me = Passenger(id="me", source=6, dest=8, request_time=0)

    assert least_combined_time(me, cars) is cars[0]


def test_the_estimate_schedulers_also_skip_a_car_that_is_full_right_now():
    # Car 0 holds two and is full, one floor below me; both riders get out at my floor. Car 1 is idle, nine floors away.
    full = Car(number=0, capacity=2, floor=5, direction=UP)
    full.riders.append(Passenger(id="r1", source=1, dest=6, request_time=0))
    full.riders.append(Passenger(id="r2", source=1, dest=6, request_time=0))
    idle = Car(number=1, capacity=2, floor=15)
    me = Passenger(id="me", source=6, dest=10, request_time=0)

    # The full car would bring me there at tick 5 and the idle one at tick 13, but a full car is not a candidate.
    assert full.estimate_arrivals(0, newcomer=me)["me"] == 5
    assert idle.estimate_arrivals(0, newcomer=me)["me"] == 13
    assert least_newcomer_time(me, [full, idle]) is idle
    assert least_combined_time(me, [full, idle]) is idle
