"""The traffic scenarios, and the comparison of the schedulers on them. Run it as a command:

    python -m elevator_sim.scenarios

A scenario is one traffic pattern of the day: morning, lunch or evening. The file reads from top to
bottom in the order things happen. First the traffic: passengers who follow a pattern. Then the
comparison: for each pattern and each seed it makes one set of passengers and runs every scheduler
on that same set, so a difference in the results comes from the scheduler and not from luck. Then
the two tables, and last the command.

To watch one set of those passengers in the simulator itself, save it as a request file:

    python -m elevator_sim.scenarios --write-requests morning out/morning.csv
"""

import argparse
import csv
import random
import sys
from math import sqrt
from pathlib import Path
from statistics import mean, stdev

from elevator_sim.config import Config
from elevator_sim.input_validation import COLUMNS
from elevator_sim.metrics import percentile
from elevator_sim.passenger import Passenger
from elevator_sim.rule_checker import check_run
from elevator_sim.schedulers import SCHEDULERS
from elevator_sim.simulation import run

LOBBY = 1

# A pattern is the share of passengers who travel (up from the lobby, down to the lobby).
# The rest travel between two other floors. These three mixes are the lift industry's standard ones.
PATTERNS = {
    "morning": (0.85, 0.10),
    "lunch": (0.45, 0.45),
    "evening": (0.10, 0.85),
}

# The standard setup for comparing schedulers: a mid-size office building under the heaviest traffic
# it still handles. At 75 people per car its morning rush is busy but copes; at 100 it is overwhelmed.
BUILDING = Config(num_cars=4, num_floors=20, capacity=8)
PEOPLE_PER_CAR = 75
WINDOW = 300  # requests are spread over ticks 0 to 299

BASELINE = "round_robin"  # the scheduler that every other one is compared with
NUM_SEEDS = 20  # how many different sets of passengers each pattern is run on


def make_passengers(pattern: str, num_people: int, num_floors: int, seed: int) -> list[Passenger]:
    """`num_people` passengers who follow `pattern`, each asking at a random tick inside the window.

    The same four inputs always give exactly the same passengers, so every scheduler can be run on
    identical traffic. The passengers come back in time order, as in a request file.
    """
    if num_floors < 3:
        raise ValueError("a traffic pattern needs at least 3 floors: the lobby and two floors above it")
    up_share, down_share = PATTERNS[pattern]
    rng = random.Random(seed)  # a private generator: the same seed always gives the same numbers

    trips = []
    for _ in range(num_people):  # _ is the usual name for a counter that is not used
        kind = rng.random()  # a number between 0 and 1 decides which kind of trip this is
        if kind < up_share:
            source, dest = LOBBY, rng.randint(2, num_floors)  # randint includes both ends
        elif kind < up_share + down_share:
            source, dest = rng.randint(2, num_floors), LOBBY
        else:
            source, dest = rng.sample(range(2, num_floors + 1), 2)  # two different floors above the lobby
        trips.append((rng.randrange(WINDOW), source, dest))  # randrange(300) gives 0 to 299
    trips.sort(key=lambda trip: trip[0])  # by request time; trips at the same tick keep their order

    return [
        Passenger(id=f"p{number}", source=source, dest=dest, request_time=request_time)
        for number, (request_time, source, dest) in enumerate(trips)
    ]


def write_requests(passengers: list[Passenger], path) -> None:
    """Save passengers as a request file that `python -m elevator_sim` can read."""
    with open(path, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(COLUMNS)
        for p in passengers:
            writer.writerow([p.request_time, p.id, p.source, p.dest])


def compare(config: Config, num_people: int, num_seeds: int) -> list[dict]:
    """Run every scheduler on every pattern and seed. One row comes back per run, like a tidy table.

    A row looks like {"pattern": "morning", "scheduler": "nearest_car", "seed": 3,
    "average": 27.1, "p90": 58, "max": 96}. The three numbers are that run's wait times in ticks.
    """
    rows = []
    for pattern in PATTERNS:
        for seed in range(num_seeds):
            for name, scheduler in SCHEDULERS.items():
                # The same pattern and seed give the same passengers, so every scheduler meets identical traffic.
                passengers = make_passengers(pattern, num_people, config.num_floors, seed)
                log = run(passengers, config, scheduler=scheduler)
                broken = check_run(passengers, log, config)
                if len(broken) > 0:  # a bug in the simulator: crash rather than report numbers from a broken run
                    raise RuntimeError(f"{name} broke a rule on {pattern}, seed {seed}: {broken[:3]}")
                waits = [p.wait_time for p in passengers]
                rows.append({
                    "pattern": pattern, "scheduler": name, "seed": seed,
                    "average": mean(waits), "p90": percentile(waits, 90), "max": max(waits),
                })
    return rows


def values(rows: list[dict], pattern: str, scheduler: str, measure: str) -> list[float]:
    """One number per seed, in seed order. In pandas: df[(df.pattern == pattern) & (df.scheduler == scheduler)][measure]."""
    return [row[measure] for row in rows if row["pattern"] == pattern and row["scheduler"] == scheduler]


def difference_from_baseline(rows: list[dict], pattern: str, scheduler: str) -> tuple[float, float]:
    """How much longer this scheduler's average wait is than the baseline's: the mean over the seeds, and its standard error.

    The difference is paired, taken seed by seed. Both schedulers served the same passengers in each
    seed, so the luck of the draw cancels out and what is left is the effect of the scheduler.
    """
    ours = values(rows, pattern, scheduler, "average")
    baseline = values(rows, pattern, BASELINE, "average")
    differences = [a - b for a, b in zip(ours, baseline)]
    return mean(differences), stdev(differences) / sqrt(len(differences))


def print_tables(rows: list[dict]) -> None:
    """Two small tables: the wait times of every scheduler, then each one's difference from the baseline."""
    # In an f-string, :>20 right-aligns in 20 characters, :22 left-aligns in 22, and :+.1f always shows the sign.
    header = f"{'':22}" + "".join(f"{pattern:>20}" for pattern in PATTERNS)

    print("Wait in ticks: average (p90 / max), each a mean over the seeds")
    print(header)
    for name in SCHEDULERS:
        line = f"{name:22}"
        for pattern in PATTERNS:
            average = mean(values(rows, pattern, name, "average"))
            p90 = mean(values(rows, pattern, name, "p90"))
            longest = mean(values(rows, pattern, name, "max"))
            cell = f"{average:.1f} ({p90:.0f} / {longest:.0f})"
            line += f"{cell:>20}"
        print(line)

    print()
    print(f"Average wait compared with {BASELINE}, ± standard error (minus means shorter waits)")
    print(header)
    for name in SCHEDULERS:
        if name == BASELINE:
            continue
        line = f"{name:22}"
        for pattern in PATTERNS:
            difference, error = difference_from_baseline(rows, pattern, name)
            cell = f"{difference:+.1f} ± {error:.1f}"
            line += f"{cell:>20}"
        print(line)


def main(argv=None) -> int:
    """Run the comparison and print it, or with --write-requests save one set of passengers. Hands back the exit code, 0."""
    parser = argparse.ArgumentParser(
        prog="python -m elevator_sim.scenarios",
        description="Compare the schedulers on identical traffic scenarios.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--cars", type=int, default=BUILDING.num_cars, help="number of cars")
    parser.add_argument("--floors", type=int, default=BUILDING.num_floors, help="floors are numbered 1 to N")
    parser.add_argument("--capacity", type=int, default=BUILDING.capacity, help="most riders one car may hold")
    parser.add_argument("--stop-time", type=int, default=BUILDING.stop_time, help="extra ticks a car stays at a floor when anyone steps in or out")
    parser.add_argument("--people", type=int, help=f"passengers in each run; when left out, {PEOPLE_PER_CAR} per car")
    parser.add_argument("--seeds", type=int, default=NUM_SEEDS, help="sets of passengers per pattern")
    # nargs=2 makes this flag take two words after it; metavar is what --help calls them.
    parser.add_argument(
        "--write-requests", nargs=2, metavar=("PATTERN", "FILE"),
        help="compare nothing; save that pattern's first set of passengers (seed 0) as a request file",
    )
    args = parser.parse_args(argv)
    if args.cars < 1:
        parser.error("--cars must be at least 1")
    if args.floors < 3:
        parser.error("--floors must be at least 3: the lobby and two floors above it")
    if args.capacity < 1:
        parser.error("--capacity must be at least 1")
    if args.stop_time < 0:
        parser.error("--stop-time cannot be negative")
    if args.seeds < 2:
        parser.error("--seeds must be at least 2: a standard error needs two runs")
    num_people = args.people if args.people is not None else PEOPLE_PER_CAR * args.cars  # traffic grows with the cars
    if num_people < 1:
        parser.error("--people must be at least 1")
    if args.write_requests is not None and args.write_requests[0] not in PATTERNS:
        parser.error(f"--write-requests needs one of these patterns: {', '.join(PATTERNS)}")

    config = Config(num_cars=args.cars, num_floors=args.floors, capacity=args.capacity, stop_time=args.stop_time)
    stop_flag = "" if args.stop_time == 0 else f" --stop-time {args.stop_time}"  # only mentioned when stops cost time

    if args.write_requests is not None:
        pattern, path = args.write_requests
        passengers = make_passengers(pattern, num_people, config.num_floors, seed=0)  # the comparison's first set
        Path(path).parent.mkdir(parents=True, exist_ok=True)  # make the folder if it is not there yet
        write_requests(passengers, path)
        print(f"Wrote {len(passengers)} {pattern} requests to {path}.")
        print(
            f"Run them with: python -m elevator_sim {path} "
            f"--cars {args.cars} --floors {args.floors} --capacity {args.capacity}{stop_flag}"
        )
        return 0

    rows = compare(config, num_people, args.seeds)

    stops = "" if args.stop_time == 0 else f" Every stop takes {args.stop_time} extra tick(s)."
    print(f"{args.cars} cars, {args.floors} floors, capacity {args.capacity}. {num_people} people asking over {WINDOW} ticks.{stops}")
    print(f"{args.seeds} seeds per pattern, the same passengers for every scheduler. All {len(rows)} runs passed the rule check.")
    print()
    print_tables(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
