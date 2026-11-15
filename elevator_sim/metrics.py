"""Turns the facts of a finished run into numbers. It computes only; printing is the command line's job."""

import math

from elevator_sim.passenger import Passenger


def summarize(passengers: list[Passenger]) -> dict[str, dict[str, float]]:
    """Min, max and average of wait, travel and total time, in ticks, over every passenger.

    The pandas equivalent is df[["wait", "travel", "total"]].agg(["min", "max", "mean"]).
    What comes back looks like {"wait": {"min": 0, "max": 71, "average": 23.67}, "travel": {...}, "total": {...}}.
    Every passenger must have arrived, which is always true after a run: it only ends when they all have.
    """
    times = {
        "wait": [p.wait_time for p in passengers],
        "travel": [p.travel_time for p in passengers],
        "total": [p.total_time for p in passengers],
    }
    summary = {}
    for measure, values in times.items():
        summary[measure] = {"min": min(values), "max": max(values), "average": sum(values) / len(values)}
    return summary


def percentile(values: list[float], percent: int) -> float:
    """The value that `percent` % of the values are at or below. percentile(waits, 90) is the p90 wait.

    The answer is always one of the values themselves (the "nearest rank" method): sort them and
    count up `percent` % of the way. numpy's default interpolates between two neighbours instead,
    so its answer can differ slightly.
    """
    ordered = sorted(values)
    rank = math.ceil(percent * len(ordered) / 100)  # how many values to count, starting from the smallest
    return ordered[max(rank, 1) - 1]  # a list counts from 0, so the rank-th value sits at rank - 1


def longest_wait(passengers: list[Passenger]) -> Passenger:
    """The passenger who waited longest. On a tie, the first in file order, like idxmax in pandas."""
    return max(passengers, key=lambda p: p.wait_time)  # key: what to compare each passenger by
