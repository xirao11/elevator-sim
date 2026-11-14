"""The command line. Run it from the project folder:

    python -m elevator_sim REQUEST_FILE [--cars N] [--floors N] [--capacity N] [--scheduler NAME] [--out FOLDER]

It reads a request file, runs the simulation and writes two files to the output folder:
positions.csv (every car's floor at every tick) and passengers.csv (one row per passenger).
"""

import argparse
import csv
import sys
from pathlib import Path

from elevator_sim.config import Config
from elevator_sim.metrics import longest_wait, summarize
from elevator_sim.passenger import Passenger
from elevator_sim.rules import check_run
from elevator_sim.schedulers import SCHEDULERS
from elevator_sim.simulation import run
from elevator_sim.validation import COLUMNS, read_requests

DEFAULTS = Config()  # every default is read from config.py, so it is written in one place only


def main(argv=None) -> int:
    """Run the command line and hand back the exit code: 0 if it worked, 1 if the request file has problems.

    `argv` is the list of typed words. None means "whatever was typed in the terminal";
    tests pass a list instead, such as ["data/sample_requests.csv", "--cars", "2"].
    """
    parser = argparse.ArgumentParser(
        prog="python -m elevator_sim",
        description="Simulate a destination-dispatch elevator system.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,  # makes --help show every default
    )
    parser.add_argument("requests", help="the request file: a CSV whose first line is time,id,source,dest")
    parser.add_argument("--cars", type=int, default=DEFAULTS.num_cars, help="number of cars")
    parser.add_argument("--floors", type=int, default=DEFAULTS.num_floors, help="floors are numbered 1 to N")
    parser.add_argument("--capacity", type=int, default=DEFAULTS.capacity, help="most riders one car may hold")
    parser.add_argument("--scheduler", choices=list(SCHEDULERS), default="round_robin", help="the rule that picks a car")
    parser.add_argument("--out", default="out", help="folder for positions.csv and passengers.csv")
    args = parser.parse_args(argv)

    # type=int only checks for a whole number. These check for a building that can exist.
    # parser.error prints the message and stops with exit code 2, the usual code for "command typed wrong".
    if args.cars < 1:
        parser.error("--cars must be at least 1")
    if args.floors < 2:
        parser.error("--floors must be at least 2 (with one floor, every trip goes nowhere)")
    if args.capacity < 1:
        parser.error("--capacity must be at least 1")
    request_file = Path(args.requests)
    if not request_file.is_file():
        parser.error(f"cannot find the request file {request_file}")

    config = Config(num_cars=args.cars, num_floors=args.floors, capacity=args.capacity)

    # utf-8-sig also reads a file saved by Excel, which starts with an invisible marker.
    # newline="" is how the csv module asks for its files to be opened.
    with open(request_file, encoding="utf-8-sig", newline="") as file:
        passengers, problems = read_requests(file, config)
    if len(problems) == 0 and len(passengers) == 0:
        problems.append("the file has no requests after the header")

    # A bad row stops the run: list every problem, simulate nothing, write nothing.
    if len(problems) > 0:
        print(f"{request_file}: {len(problems)} problem(s) found, so nothing was simulated.", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    log = run(passengers, config, scheduler=SCHEDULERS[args.scheduler])

    # Every run is checked against the five rules before anything is written. A broken rule is a bug
    # in the simulator, not a mistake in the input, so this is a crash with a traceback, not a stop.
    broken = check_run(passengers, log, config)
    if len(broken) > 0:
        raise RuntimeError("The simulation broke its own rules:\n  " + "\n  ".join(broken[:20]))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)  # make the folder if it is not there yet
    positions_file = out / "positions.csv"  # / joins folder and file name
    passengers_file = out / "passengers.csv"
    _write_positions(positions_file, log)
    _write_passengers(passengers_file, passengers)

    last_arrival = max(passenger.arrive_time for passenger in passengers)
    print(f"All {len(passengers)} passengers delivered; the last one stepped out at tick {last_arrival}.")
    print("Rule check passed: served, capacity, direction, movement, records.")
    _print_summary(passengers)
    print(f"Wrote {positions_file} and {passengers_file}.")
    return 0


def _print_summary(passengers: list[Passenger]) -> None:
    """The statistics as a small table, in ticks, then who waited longest."""
    # In {x:>6}, >6 means "right-aligned in 6 characters"; .1f means "1 decimal place".
    print()
    print(f"{'':8}{'min':>6}{'max':>6}{'average':>9}")
    for measure, numbers in summarize(passengers).items():
        print(f"{measure:8}{numbers['min']:>6}{numbers['max']:>6}{numbers['average']:>9.1f}")
    worst = longest_wait(passengers)
    print(f"\nLongest wait: {worst.id}, {worst.wait_time} ticks.\n")


def _write_positions(path: Path, log: list[list[int]]) -> None:
    """One row per tick: the tick, then every car's floor at the start of that tick."""
    num_cars = len(log[0])
    with open(path, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["tick"] + [f"car{number}" for number in range(num_cars)])
        for tick, floors in enumerate(log):
            writer.writerow([tick] + floors)


def _write_passengers(path: Path, passengers: list[Passenger]) -> None:
    """One row per passenger in file order: the request exactly as it was read, then what happened."""
    with open(path, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(COLUMNS + ["car", "board", "arrive", "wait", "travel", "total"])
        for p in passengers:
            writer.writerow([
                p.request_time, p.id, p.source, p.dest,
                p.car_number, p.board_time, p.arrive_time, p.wait_time, p.travel_time, p.total_time,
            ])


if __name__ == "__main__":  # true when run as `python -m elevator_sim`, false when a test imports this file
    sys.exit(main())
