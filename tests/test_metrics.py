"""Tests for the statistics. The passengers are written out finished, so no simulation runs here."""

import pytest

from elevator_sim.metrics import longest_wait, summarize
from elevator_sim.passenger import Passenger


def finished(id, source, dest, request_time, board_time, arrive_time):
    return Passenger(id=id, source=source, dest=dest, request_time=request_time,
                     board_time=board_time, arrive_time=arrive_time)


# The sample with two cars and nearest car, as in out/passengers.csv.
SAMPLE_RUN = [
    finished("passenger1", 1, 51, request_time=0, board_time=0, arrive_time=50),
    finished("passenger2", 1, 37, request_time=0, board_time=0, arrive_time=36),
    finished("passenger3", 20, 1, request_time=10, board_time=81, arrive_time=100),
]


def test_min_max_and_average_cover_every_passenger():
    summary = summarize(SAMPLE_RUN)

    assert summary["wait"] == {"min": 0, "max": 71, "average": pytest.approx(71 / 3)}  # waits 0, 0, 71
    assert summary["travel"] == {"min": 19, "max": 50, "average": 35}  # rides 50, 36, 19
    assert summary["total"] == {"min": 36, "max": 90, "average": pytest.approx(176 / 3)}  # 50, 36, 90


def test_longest_wait_names_the_passenger_and_a_tie_goes_to_the_first_in_the_file():
    assert longest_wait(SAMPLE_RUN).id == "passenger3"

    tied = [finished("a", 1, 2, 0, 5, 6), finished("b", 1, 2, 0, 5, 6)]  # both wait 5
    assert longest_wait(tied).id == "a"
