"""Tests for the command line. They call main() with a list of words, as if typed in a terminal."""

import csv
from pathlib import Path

import pytest

from elevator_sim.__main__ import main

# The data folder sits next to the tests folder; this finds it wherever pytest is started from.
SAMPLE = str(Path(__file__).parent.parent / "data" / "sample_requests.csv")
# The two files that the README's first command writes, kept in the repo so they can be read without running anything.
SAMPLE_OUTPUT = Path(__file__).parent.parent / "data" / "sample_output"


def read_csv(path):
    with open(path, newline="") as file:
        return list(csv.reader(file))  # every value comes back as text


def test_sample_two_cars_nearest_car_writes_my_hand_trace(tmp_path):
    # tmp_path is a fresh empty folder that pytest makes for this test, so nothing lands in the project.
    exit_code = main([SAMPLE, "--cars", "2", "--scheduler", "nearest_car", "--out", str(tmp_path)])

    assert exit_code == 0
    # My hand-trace of 2026-11-14: nearest car gives all three to car 0.
    assert read_csv(tmp_path / "passengers.csv") == [
        ["time", "id", "source", "dest", "car", "board", "arrive", "wait", "travel", "total"],
        ["0", "passenger1", "1", "51", "0", "0", "50", "0", "50", "50"],
        ["0", "passenger2", "1", "37", "0", "0", "36", "0", "36", "36"],
        ["10", "passenger3", "20", "1", "0", "81", "100", "71", "19", "90"],
    ]
    positions = read_csv(tmp_path / "positions.csv")
    assert positions[0] == ["tick", "car0", "car1"]
    assert positions[1:4] == [["0", "1", "1"], ["1", "2", "1"], ["2", "3", "1"]]  # floors start at 1; car 1 never moves
    assert positions[-1] == ["100", "1", "1"]
    assert len(positions) == 1 + 101  # the header, then ticks 0 to 100


def test_the_statistics_are_printed_after_the_run(tmp_path, capsys):
    # capsys is a pytest tool that catches everything the code prints, so the test can read it.
    main([SAMPLE, "--cars", "2", "--scheduler", "nearest_car", "--out", str(tmp_path)])
    printed = capsys.readouterr().out

    lines = [line.split() for line in printed.splitlines()]  # each line as a list of words
    assert ["min", "max", "average"] in lines
    assert ["wait", "0", "71", "23.7"] in lines
    assert ["travel", "19", "50", "35.0"] in lines
    assert ["total", "36", "90", "58.7"] in lines
    assert "Longest wait: passenger3, 71 ticks." in printed
    assert "Rule check passed" in printed  # every run is checked against the five rules


def test_every_run_prints_its_settings_and_the_defaults(tmp_path, capsys):
    main([SAMPLE, "--cars", "2", "--out", str(tmp_path)])  # only --cars is typed; the rest are defaults
    printed = capsys.readouterr().out

    assert "Settings in this run: --cars 2  --floors 51  --capacity 10  --stop-time 0  --scheduler least_combined_time" in printed
    assert "Defaults:             --cars 1  --floors 51  --capacity 10  --stop-time 0  --scheduler least_combined_time" in printed


def test_a_stop_time_of_1_adds_one_tick_for_every_stop_on_the_way(tmp_path):
    main([SAMPLE, "--stop-time", "1", "--out", str(tmp_path)])  # one car, the default

    # Traced by hand before the run. With free stops the arrivals are 50, 36 and 100.
    assert read_csv(tmp_path / "passengers.csv")[1:] == [
        ["0", "passenger1", "1", "51", "0", "0", "52", "0", "52", "52"],  # 50 floors, the stop at 1 and the stop at 37
        ["0", "passenger2", "1", "37", "0", "0", "37", "0", "37", "37"],  # 36 floors and the stop at 1
        ["10", "passenger3", "20", "1", "0", "84", "104", "74", "20", "94"],  # the car is 3 stops late; then 19 floors and one stop
    ]


def test_without_out_every_request_file_gets_its_own_folder(tmp_path, monkeypatch):
    # monkeypatch is a pytest tool for temporary changes. chdir runs this test from the empty folder,
    # as if `cd` had been typed, so "out" is made there and not in the project. pytest undoes it afterwards.
    monkeypatch.chdir(tmp_path)
    one_trip = tmp_path / "one_trip.csv"
    one_trip.write_text("time,id,source,dest\n0,a,1,5\n")

    main([SAMPLE])
    main([str(one_trip)])  # a second request file

    # Each folder is named after its request file, so the second run did not replace the first one's output.
    assert len(read_csv(tmp_path / "out" / "sample_requests" / "passengers.csv")) == 1 + 3  # the header, then 3 passengers
    assert len(read_csv(tmp_path / "out" / "one_trip" / "passengers.csv")) == 1 + 1


def test_the_sample_output_in_the_repo_is_what_the_code_writes(tmp_path):
    main([SAMPLE, "--cars", "2", "--out", str(tmp_path)])  # the README's first command

    # If this fails, the code's result changed and data/sample_output is out of date.
    # Write it again: python3 -m elevator_sim data/sample_requests.csv --cars 2 --out data/sample_output
    for name in ["positions.csv", "passengers.csv"]:
        assert read_csv(tmp_path / name) == read_csv(SAMPLE_OUTPUT / name)


def test_a_file_with_a_bad_row_stops_and_writes_nothing(tmp_path, capsys):
    bad_file = tmp_path / "bad.csv"
    bad_file.write_text("time,id,source,dest\n0,a,1,5\n0,b,5,5\n")  # \n is a line break; line 3 goes nowhere
    out = tmp_path / "out"

    exit_code = main([str(bad_file), "--out", str(out)])

    assert exit_code == 1  # a bad row stops the run
    assert "line 3: source and dest are the same floor (5)" in capsys.readouterr().err  # err: the error channel
    assert not out.exists()  # the good row on line 2 was not simulated either


# parametrize runs the same test once per line of values: four tests written once.
@pytest.mark.parametrize("flag, value", [("--cars", "0"), ("--floors", "1"), ("--capacity", "0"), ("--stop-time", "-1")])
def test_a_building_that_cannot_exist_is_refused_before_anything_runs(tmp_path, flag, value):
    out = tmp_path / "out"

    with pytest.raises(SystemExit) as stopped:  # parser.error stops the program; the test catches that
        main([SAMPLE, flag, value, "--out", str(out)])

    assert stopped.value.code == 2
    assert not out.exists()  # nothing was written
