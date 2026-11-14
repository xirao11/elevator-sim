"""Tests on random traffic. Nobody knows the right answer for a random run, but the five rules must hold in every one."""

import random

import pytest

from elevator_sim.config import Config
from elevator_sim.passenger import Passenger
from elevator_sim.rules import check_run
from elevator_sim.schedulers import SCHEDULERS
from elevator_sim.simulation import run

NUM_BUILDINGS = 300  # how many random buildings each scheduler is run on


def random_building(seed: int) -> tuple[Config, list[Passenger]]:
    """One random building and its passengers. The same seed always gives exactly the same ones.

    A run writes on its passengers, so every run needs fresh ones: call this again with the same seed.
    """
    rng = random.Random(seed)  # a private generator started from the seed, like np.random.default_rng(seed)
    config = Config(
        num_cars=rng.randint(1, 10),  # the assignment's example range. This randint includes both ends
        num_floors=rng.randint(2, 50),
        capacity=rng.randint(1, 10),
    )
    passengers = []
    for number in range(rng.randint(1, 20 * config.num_cars)):  # up to 20 people per car keeps every car busy
        source, dest = rng.sample(range(1, config.num_floors + 1), 2)  # two different floors
        request_time = rng.randint(0, 100)  # squeezed together, so people ask at the same tick and cars fill up
        passengers.append(Passenger(id=f"p{number}", source=source, dest=dest, request_time=request_time))
    return config, passengers


# One test per scheduler in the SCHEDULERS table. A scheduler added to the table later is tested with no new code.
@pytest.mark.parametrize("name", list(SCHEDULERS))
def test_no_rule_is_broken_on_random_buildings(name):
    for seed in range(NUM_BUILDINGS):
        config, passengers = random_building(seed)

        log = run(passengers, config, scheduler=SCHEDULERS[name])

        # The text after the comma is shown if the check fails. It names the seed, so the building can be rebuilt.
        problems = check_run(passengers, log, config)
        assert len(problems) == 0, f"seed {seed}, {config}: {problems[:3]}"


@pytest.mark.parametrize("name", list(SCHEDULERS))
def test_a_lobby_rush_with_small_cars_breaks_no_rule(name):
    # Thirty people at floor 1 at tick 0, and two cars with room for four: as crowded as it gets.
    config = Config(num_cars=2, num_floors=12, capacity=4)
    passengers = [Passenger(id=f"p{n}", source=1, dest=2 + n % 11, request_time=0) for n in range(30)]

    log = run(passengers, config, scheduler=SCHEDULERS[name])

    assert check_run(passengers, log, config) == []


@pytest.mark.parametrize("name", list(SCHEDULERS))
def test_a_later_request_cannot_change_anything_earlier(name):
    """No peeking ahead. A newcomer who asks halfway through must leave everything before that tick as it was."""
    for seed in range(NUM_BUILDINGS):
        config, passengers = random_building(seed)
        log = run(passengers, config, scheduler=SCHEDULERS[name])
        halfway = len(log) // 2  # a tick in the middle of the run

        # The same building again, plus one newcomer who asks at that tick.
        config, again = random_building(seed)
        newcomer = Passenger(id="newcomer", source=1, dest=config.num_floors, request_time=halfway)
        log_again = run(again + [newcomer], config, scheduler=SCHEDULERS[name])

        # Rows 0 to halfway of the positions log: every car is where it was.
        assert log_again[: halfway + 1] == log[: halfway + 1], f"seed {seed}: a car moved differently before tick {halfway}"
        for before, after in zip(passengers, again):  # zip pairs each passenger with their twin in the second run
            if before.request_time < halfway:
                assert after.car_number == before.car_number, f"seed {seed}: {before.id} was given a different car"
