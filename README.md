# Elevator dispatch simulation

A tick-by-tick simulation of a destination-dispatch elevator system. Each passenger gives their destination before boarding and is told at once which car to take. The number of cars, the number of floors and the car size are settings. The rule that picks a car, the *scheduler*, is swappable. Every run is checked against the rules before any result is shown.

> **Presentation page:** [presentation.html](https://htmlpreview.github.io/?https://github.com/xirao11/elevator-sim/blob/main/presentation.html) shows the four schedulers on one example, the results as charts, the checks and the system design. After cloning, it opens with a double-click.

**The result:** I recommend `least_combined_time`, the best of the four schedulers I built. Before it gives a new passenger a car, it adds up what that choice costs in wait and travel time: the new passenger's own time, plus the time they add to the passengers already given to that car. It has the shortest average total time in every traffic pattern I tested, and the shortest longest wait.

## How to run

It needs Python 3.9 or later and no packages. On Windows, type `python` where it says `python3`.

```
git clone https://github.com/xirao11/elevator-sim.git
cd elevator-sim
python3 -m elevator_sim data/sample_requests.csv --cars 2   # your own scenario: a request file
python3 -m elevator_sim.scenarios                           # the predefined scenarios, 10 to 20 seconds
uv run pytest                                               # 85 tests, about 50 seconds
```

The first two commands run the same simulation and the same rule check. They differ only in where the passengers come from: a file you write, or traffic the program makes. The tests need [uv](https://docs.astral.sh/uv/), which downloads pytest.

**Your own scenario: a request file.** One row per passenger. `data/sample_requests.csv` is the assignment's sample:

```
time,id,source,dest
0,passenger1,1,51
0,passenger2,1,37
10,passenger3,20,1
```

Give the path of your own file in its place. Whatever the file, input validation checks every row first: the header, whole numbers, floors that exist in the building, and ids used once. If anything is wrong, every problem is listed with its line number and nothing runs. Otherwise the run prints its settings, the rule check and the times:

```
           min   max  average
wait         0    19      6.3
travel      19    50     35.0
total       36    50     41.3
```

It also writes two files: `positions.csv`, every car's floor at every tick, and `passengers.csv`, each passenger's car and times. They go to `out/`, in a folder named after the request file: `out/sample_requests/` here. A copy of this run's two files is kept in the repo as `data/sample_output/`, to read without running anything. The settings are `--cars`, `--floors`, `--capacity`, `--stop-time`, `--scheduler` and `--out`; `--help` explains each.

**The predefined scenarios: morning, lunch and evening.** Here the program makes the passengers itself. A scenario is one traffic pattern of an office day: morning (85% go up from the lobby), lunch (mixed) and evening (85% go down to the lobby). For each pattern the command makes 20 random sets of 300 passengers, runs all four schedulers on every set, and prints their times side by side. The Results below come from it. It saves nothing: the same passengers are made again on every run. To run one of those sets with the first command, save it as a request file first:

```
python3 -m elevator_sim.scenarios --write-requests morning out/morning.csv   # morning, lunch or evening, then the file to write
python3 -m elevator_sim out/morning.csv --cars 4 --floors 20 --capacity 8    # run it; the output goes to out/morning/
```

## How it works

Every tick does the same four things, in this order:

1. New requests appear, and the scheduler gives each one a car. The choice is final.
2. In every car, riders who have arrived step out, the car chooses its direction, and waiting passengers step in.
3. Every car's floor is logged.
4. Every car moves one floor.

A scheduler is the function that chooses the car: the new passenger and the cars as they are now go in, and one car comes out. It is never given the request list, so it cannot use a request that has not been made yet.

| Scheduler | It picks the car | It does not count |
|---|---|---|
| `round_robin` | whose turn it is | anything else |
| `nearest_car` | that is the fewest floors away right now | the car's direction or its other passengers |
| `least_newcomer_time` | that brings the new passenger to their destination soonest | what that does to the car's other passengers |
| `least_combined_time` | with the smallest sum: the new passenger's time, plus the time they add to the car's other passengers | people who have not asked yet |

The last two ask each car for an estimate. The car answers by running its own rules on a copy of itself: "with everyone I have now, plus this passenger, when would each of them arrive?" The estimate and the real run are the same code, so the estimate already knows about direction, capacity and stop time.

The files in `elevator_sim/`, in the order a run uses them: `config.py` holds the building's settings → `passenger.py` is the record of one trip and its wait, travel and total time → `input_validation.py` checks the request file → `simulation.py` is the clock → `car.py` is one car and its estimate → `schedulers.py` holds the four rules → `rule_checker.py` checks the finished run → `metrics.py` computes the min, max and average. `__main__.py` and `scenarios.py` are the two commands.

## Results

The building has 4 cars, 20 floors and room for 8 in a car, and 300 passengers ask over 300 ticks. Every scheduler gets the same 20 random sets of passengers per pattern. Average total time in ticks (wait + travel), with the longest wait in brackets:

| | morning | lunch | evening |
|---|---|---|---|
| `round_robin` | 29.8 (61) | 26.3 (39) | 30.0 (132) |
| `nearest_car` | 37.3 (98) | 24.4 (67) | 34.3 (228) |
| `least_newcomer_time` | 22.4 (58) | 16.8 (55) | 23.6 (128) |
| `least_combined_time` | **22.3 (32)** | **15.2 (23)** | **17.5 (33)** |

Against `round_robin`, paired set by set, `least_combined_time` is shorter by 7.5 ± 0.3, 11.0 ± 0.1 and 12.5 ± 0.3 ticks (± standard error). What I take from the numbers:

- **Distance is not time.** `nearest_car` loses to `round_robin` in the morning and the evening. It gives everyone at the lobby the same car, and that car fills up. The objective is time, and an estimate in ticks measures it directly, so both estimate schedulers beat both simple rules in every pattern.
- **Counting the other passengers helps the unluckiest one most.** The average is efficiency and the longest wait is fairness. `least_newcomer_time` lets a newcomer take the place of someone waiting further along; `least_combined_time` counts that as a long delay to that person.
- **When every stop costs time, the order holds.** With `--stop-time 2` a car stays 2 more ticks whenever anyone steps in or out. `least_combined_time` then averages 70.8, 32.6 and 42.5 ticks, against 86.4, 53.0 and 80.8 for `round_robin`.
- **It holds in other buildings.** Across 90 buildings (2 to 8 cars, 10 to 40 floors, room for 4 to 16, stop time 0 and 1) `least_combined_time` has the shortest average total time in 262 of 270 cases. In the other 8, all morning traffic, `least_newcomer_time` leads by about 1 tick or less, within two standard errors.

## Testing

- **Hand-traced examples.** I traced the assignment's sample on paper before running it, and the traces are now tests.
- **A rule checker that shares no code with the engine.** It reads only the results of a run and checks five rules: everyone is served, capacity, direction, legal movement, and records that agree with the positions log. It runs after every simulation and every comparison run.
- **Random buildings, for correctness only.** Each scheduler runs 300 random buildings (1 to 10 cars, 2 to 50 floors, capacity 1 to 10, stop time 0 to 2), and every run must pass the rule checker.
- **No use of later requests, by design and by test.** By design: the simulation hands the scheduler only the passenger who is asking now and the cars as they are now. By test: each of those 300 buildings is run a second time with one more request added halfway through, and everything before that tick must stay exactly as it was.

## Assumptions and trade-offs

| Choice | What it costs |
|---|---|
| **Direction logic: nobody is ever inside a car that is moving away from their destination.** A car never turns round with riders inside, and a passenger boards only a car heading their way. | A passenger can watch their car pass in the other direction. |
| **A choice of car is final.** The passenger is told once, at the moment they ask. | A choice that later requests make bad cannot be repaired. |
| **Stops are free by default.** One tick is one floor, so floor 1 to 51 takes exactly 50. `--stop-time` charges once per stop, however many people use it. | Free stops hide the benefit of making fewer stops, which is why I repeated the comparison with a stop time. |
| **Nobody boards a full car, and every scheduler skips a car that is full right now.** | "Full now" is not "full when it reaches me". Letting the estimate decide gains at most about one tick; I kept one capacity rule for all four schedulers. |
| **An idle car stays where it stopped.** Every car starts at floor 1. | It makes no guess about where the next request comes from. |

## Self-assessment

### What I did well

1. **Reliability first.** The request file is checked before anything runs, and every finished run is checked against the five rules before a result is printed.
2. **A realistic cost.** In a real building every stop takes time, so I added a stop time and repeated the comparison with it.
3. **The best rule I could find, not the first one that works.** I read up on how the elevator industry assigns cars, and built `least_combined_time` on its estimated-time-to-destination (ETD) idea: Smith and Peters, [ETD Algorithm with Destination Dispatch and Booster Options](https://download.peters-research.com/library/ETD_Algorithm_with_Destination_Dispatch_and_Booster_Options.pdf) (2002).
4. **Averages over many random runs**, the way I would run a Monte Carlo backtest, so no single lucky or unlucky set decides the result. The standard errors are small, so the lead is not chance.

### What I would improve

- **Move a passenger to another car before they board**, when new requests make another car better.
- **Idle parking.** Send idle cars to the lobby in the morning, and measure what the empty travel costs.
- **Express cars and zones.** Each car serves a set of floors. This only pays when stops cost time.
- **A fairness setting.** Make a long wait cost more than in proportion, and measure what the average pays for a shorter longest wait.
- **The best mix of settings.** Explore which combination of cars, car size and floors suits a given traffic.

## Time spent

About 12 hours in total.

## How I used AI

I built this with Claude Code. I set the scope and made the design decisions: the assumptions above, the order of events in a tick, which schedulers to build, what to test and what to leave out. Claude wrote most of the test cases and the simulation code, and I reviewed every piece, questioned it, and changed it where I disagreed. Claude also generated the presentation page. I verified what it shows and iterated on it until it presented what I wanted to show.
