"""The gate between a request file and the simulation. Every row is checked before it becomes a passenger."""

import csv

from elevator_sim.config import Config
from elevator_sim.passenger import Passenger

COLUMNS = ["time", "id", "source", "dest"]  # the first line of a request file


def check_request(passenger: Passenger, config: Config) -> list[str]:
    """Every reason this one request cannot be served in this building. An empty list means it is fine."""
    problems = []
    if passenger.request_time < 0:
        problems.append(f"time {passenger.request_time} is before tick 0")
    for name, floor in [("source", passenger.source), ("dest", passenger.dest)]:
        if floor < 1 or floor > config.num_floors:
            problems.append(f"{name} {floor} is not a floor of this building (1 to {config.num_floors})")
    if passenger.source == passenger.dest:
        problems.append(f"source and dest are the same floor ({passenger.source})")
    return problems


def read_requests(lines, config: Config) -> tuple[list[Passenger], list[str]]:
    """Turn the lines of a request file into passengers, checking every row.

    `lines` is an open file, or just a list of text lines. Two lists come back:
    the passengers whose row is fine, in file order, and one message for every problem
    found, each starting with its line number.

    This function only finds problems. What to do about them (stop, or carry on
    without the bad rows) is decided by whoever calls it.
    """
    rows = list(csv.reader(lines))  # each row is a list of text values; an empty line gives an empty list
    if len(rows) == 0 or [name.strip().lower() for name in rows[0]] != COLUMNS:
        return [], ["line 1: the first line must be the header " + ",".join(COLUMNS)]

    passengers = []
    problems = []
    first_line_of = {}  # id -> the line where that id was first used, to catch an id used twice
    for line, row in enumerate(rows[1:], start=2):  # line 1 is the header, so the first request is line 2
        if len(row) == 0:
            continue  # an empty line
        if len(row) != len(COLUMNS):
            problems.append(f"line {line}: expected 4 values ({', '.join(COLUMNS)}) but found {len(row)}")
            continue
        time, passenger_id, source, dest = [value.strip() for value in row]
        if not (_is_whole_number(time) and _is_whole_number(source) and _is_whole_number(dest)):
            problems.append(f"line {line}: time, source and dest must be whole numbers")
            continue

        passenger = Passenger(id=passenger_id, source=int(source), dest=int(dest), request_time=int(time))
        found = check_request(passenger, config)
        if passenger_id == "":
            found.append("id is empty")
        elif passenger_id in first_line_of:
            found.append(f"id {passenger_id} was already used on line {first_line_of[passenger_id]}")
        else:
            first_line_of[passenger_id] = line

        if len(found) == 0:
            passengers.append(passenger)
        for problem in found:
            problems.append(f"line {line}: {problem}")
    return passengers, problems


def _is_whole_number(text: str) -> bool:
    """True if `text` reads as a whole number, such as "12" or "-3"."""
    try:
        int(text)  # raises ValueError for text like "two", "4.5" or ""
    except ValueError:
        return False
    return True
