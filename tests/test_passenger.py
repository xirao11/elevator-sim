"""Tests for the passenger record."""

from elevator_sim.passenger import DOWN, UP, Passenger


def test_times_are_computed_from_the_three_timestamps():
    passenger = Passenger(id="p1", source=7, dest=12, request_time=10)
    passenger.board_time = 13
    passenger.arrive_time = 18

    assert passenger.wait_time == 3
    assert passenger.travel_time == 5
    assert passenger.total_time == 8


def test_direction_follows_from_source_and_dest():
    assert Passenger(id="up", source=1, dest=5, request_time=0).direction == UP
    assert Passenger(id="down", source=5, dest=1, request_time=0).direction == DOWN
