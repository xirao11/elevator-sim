"""Tests for the gate between a request file and the simulation."""

from elevator_sim.config import Config
from elevator_sim.passenger import Passenger
from elevator_sim.validation import check_request, read_requests

HEADER = "time,id,source,dest"
TEN_FLOORS = Config(num_floors=10)


def test_the_assignment_sample_passes_with_the_default_building():
    lines = [HEADER, "0,passenger1,1,51", "0,passenger2,1,37", "10,passenger3,20,1"]

    passengers, problems = read_requests(lines, Config())

    assert problems == []
    assert passengers == [
        Passenger(id="passenger1", source=1, dest=51, request_time=0),
        Passenger(id="passenger2", source=1, dest=37, request_time=0),
        Passenger(id="passenger3", source=20, dest=1, request_time=10),
    ]


def test_every_bad_row_is_reported_with_its_line_number_and_the_good_rows_are_kept():
    lines = [
        HEADER,  # line 1
        "0,ann,1,5",  # line 2
        "3,bob,4,4",  # line 3
        "5,cat,2,11",  # line 4
        "-1,dan,1,3",  # line 5
        "7,ann,6,2",  # line 6
        "8,eve,3",  # line 7
        "9,fay,two,5",  # line 8
        "2,gus,9,1",  # line 9: an earlier time than the lines above it
    ]

    passengers, problems = read_requests(lines, TEN_FLOORS)

    assert problems == [
        "line 3: source and dest are the same floor (4)",
        "line 4: dest 11 is not a floor of this building (1 to 10)",
        "line 5: time -1 is before tick 0",
        "line 6: id ann was already used on line 2",
        "line 7: expected 4 values (time, id, source, dest) but found 3",
        "line 8: time, source and dest must be whole numbers",
    ]
    # Times out of order are not a problem: the clock releases each request at its own tick.
    assert [passenger.id for passenger in passengers] == ["ann", "gus"]


def test_a_missing_or_wrong_header_is_one_problem_and_nothing_is_read():
    expected = ([], ["line 1: the first line must be the header time,id,source,dest"])

    assert read_requests(["0,ann,1,5"], TEN_FLOORS) == expected  # no header line
    assert read_requests(["id,time,source,dest", "ann,0,1,5"], TEN_FLOORS) == expected  # wrong order
    assert read_requests([], TEN_FLOORS) == expected  # an empty file


def test_spaces_capitals_and_empty_lines_are_accepted_and_line_numbers_stay_right():
    lines = ["Time, ID, Source, Dest", "", " 0, ann, 1, 5", "", "3,bob,4,4"]

    passengers, problems = read_requests(lines, TEN_FLOORS)

    assert passengers == [Passenger(id="ann", source=1, dest=5, request_time=0)]
    assert problems == ["line 5: source and dest are the same floor (4)"]  # line 5 of the file, not row 2


def test_one_request_with_two_faults_gets_two_messages():
    # check_request works on a passenger made by hand, with no file involved.
    passenger = Passenger(id="p1", source=3, dest=3, request_time=-2)

    assert check_request(passenger, TEN_FLOORS) == [
        "time -2 is before tick 0",
        "source and dest are the same floor (3)",
    ]
