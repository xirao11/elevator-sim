"""Tests for the traffic scenarios and the scheduler comparison."""

import pytest

from elevator_sim.config import Config
from elevator_sim.input_validation import check_request, read_requests
from elevator_sim.scenarios import (
    BASELINE, PATTERNS, WINDOW, compare, difference_from_baseline, main, make_passengers, write_requests,
)
from elevator_sim.schedulers import SCHEDULERS

SMALL = Config(num_cars=2, num_floors=8, capacity=4)  # a small building keeps these tests fast


# The traffic.

def test_the_same_seed_gives_the_same_passengers_and_another_seed_gives_others():
    assert make_passengers("lunch", 50, 20, seed=1) == make_passengers("lunch", 50, 20, seed=1)
    assert make_passengers("lunch", 50, 20, seed=1) != make_passengers("lunch", 50, 20, seed=2)


@pytest.mark.parametrize("pattern", list(PATTERNS))
def test_every_generated_request_is_valid_and_inside_the_window(pattern):
    passengers = make_passengers(pattern, 500, 20, seed=0)

    assert len(passengers) == 500
    assert len({p.id for p in passengers}) == 500  # a set drops repeats, so every id is different
    for p in passengers:
        assert check_request(p, Config(num_floors=20)) == []  # the same check a request file goes through
        assert 0 <= p.request_time < WINDOW
    times = [p.request_time for p in passengers]
    assert times == sorted(times)  # in time order, as in a request file


@pytest.mark.parametrize("pattern", list(PATTERNS))
def test_each_pattern_has_its_share_of_lobby_traffic(pattern):
    up_share, down_share = PATTERNS[pattern]
    passengers = make_passengers(pattern, 2000, 20, seed=0)

    # Adding up True and False counts the Trues, like (df.source == 1).mean() in pandas.
    from_lobby = sum(p.source == 1 for p in passengers) / 2000
    to_lobby = sum(p.dest == 1 for p in passengers) / 2000

    # With 2,000 passengers the shares land within 3 points of the pattern's.
    assert from_lobby == pytest.approx(up_share, abs=0.03)
    assert to_lobby == pytest.approx(down_share, abs=0.03)


def test_generated_traffic_can_be_saved_and_read_back_as_a_request_file(tmp_path):
    passengers = make_passengers("morning", 40, 20, seed=3)
    write_requests(passengers, tmp_path / "morning.csv")

    with open(tmp_path / "morning.csv", newline="") as file:
        read_back, problems = read_requests(file, Config(num_floors=20))

    assert problems == []
    assert read_back == passengers


def test_a_building_without_two_floors_above_the_lobby_is_refused():
    with pytest.raises(ValueError):
        make_passengers("lunch", 10, 2, seed=0)


# The comparison.

def test_there_is_one_row_per_pattern_scheduler_and_seed():
    rows = compare(SMALL, num_people=30, num_seeds=3)

    assert len(rows) == len(PATTERNS) * len(SCHEDULERS) * 3
    assert rows[0].keys() == {"pattern", "scheduler", "seed", "total", "wait", "p90", "max"}
    for row in rows:
        assert 0 <= row["wait"] <= row["max"]
        assert row["p90"] <= row["max"]
        assert row["total"] > row["wait"]  # total is wait plus travel, and every trip is at least one floor


def test_the_comparison_gives_the_same_numbers_every_time():
    assert compare(SMALL, num_people=30, num_seeds=3) == compare(SMALL, num_people=30, num_seeds=3)


def test_the_difference_from_the_baseline_is_paired_seed_by_seed():
    # Results written by hand for three seeds: the baseline's total time is 10, 12, 14 and the other scheduler's 11, 15, 14.
    rows = []
    for seed, (baseline_total, other_total) in enumerate([(10, 11), (12, 15), (14, 14)]):
        rows.append({"pattern": "morning", "scheduler": BASELINE, "seed": seed, "total": baseline_total})
        rows.append({"pattern": "morning", "scheduler": "other", "seed": seed, "total": other_total})

    difference, error = difference_from_baseline(rows, "morning", "other")

    # The differences are 1, 3 and 0: their mean is 4/3, and their standard error is 1.528 / sqrt(3).
    assert difference == pytest.approx(4 / 3)
    assert error == pytest.approx(0.882, abs=0.001)


# The command.

def test_the_command_prints_its_tables(capsys):
    exit_code = main(["--cars", "2", "--floors", "8", "--capacity", "4", "--people", "30", "--seeds", "3"])
    printed = capsys.readouterr().out

    assert exit_code == 0
    for word in list(PATTERNS) + list(SCHEDULERS) + ["Total time in ticks", "Wait in ticks", "compared with"]:
        assert word in printed
    runs = len(PATTERNS) * len(SCHEDULERS) * 3  # patterns x schedulers x seeds
    assert f"All {runs} runs passed the rule check" in printed
    # The settings of this run, then the defaults. The default number of people follows the cars: 75 for each.
    assert "Settings in this run: --cars 2  --floors 8  --capacity 4  --stop-time 0  --people 30  --seeds 3" in printed
    assert "Defaults:             --cars 4  --floors 20  --capacity 8  --stop-time 0  --people 150  --seeds 20" in printed


def test_one_seed_is_refused_because_a_standard_error_needs_two():
    with pytest.raises(SystemExit) as stopped:
        main(["--seeds", "1"])

    assert stopped.value.code == 2


def test_the_command_can_save_one_set_of_passengers_as_a_request_file(tmp_path, capsys):
    out = tmp_path / "traffic" / "evening.csv"  # a folder that does not exist yet

    exit_code = main(["--write-requests", "evening", str(out), "--people", "25", "--floors", "12"])

    assert exit_code == 0
    assert "Total time in ticks" not in capsys.readouterr().out  # it saved the file and compared nothing
    with open(out, newline="") as file:
        read_back, problems = read_requests(file, Config(num_floors=12))
    assert problems == []
    assert read_back == make_passengers("evening", 25, 12, seed=0)  # the comparison's first set for this pattern


def test_an_unknown_pattern_is_refused(tmp_path):
    with pytest.raises(SystemExit) as stopped:
        main(["--write-requests", "midnight", str(tmp_path / "midnight.csv")])

    assert stopped.value.code == 2
    assert not (tmp_path / "midnight.csv").exists()
