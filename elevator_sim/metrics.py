"""Turns the facts of a finished run into numbers. It computes only; printing is the command line's job."""

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


def longest_wait(passengers: list[Passenger]) -> Passenger:
    """The passenger who waited longest. On a tie, the first in file order, like idxmax in pandas."""
    return max(passengers, key=lambda p: p.wait_time)  # key: what to compare each passenger by
