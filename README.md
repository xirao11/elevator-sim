# Elevator dispatch simulation

A discrete-time simulation of a destination-dispatch elevator system.

Work in progress.

## How the code fits together

Every file has one job. A *car* is one elevator, and a *scheduler* is the rule that picks a car for each new passenger.

```
python -m elevator_sim requests.csv
│
└─ __main__.py             the command line: reads the request file, prints and writes the results
     ├─ input_validation.py   turns the file into passengers, or lists every bad row
     ├─ simulation.py         run(): the simulation itself, a loop that advances one tick at a time
     │     ├─ schedulers.py      picks a car for each new passenger
     │     └─ car.py             one car during one tick: riders out, choose direction, riders in, move
     ├─ rule_checker.py       checks the finished run against five rules, using only its results
     └─ metrics.py            min, max and average of wait, travel and total time

passenger.py and config.py hold the two records that every file above passes around:
one passenger's trip, and the building's settings.
```

A good order to read it in:

1. `passenger.py`: the record of one trip. Wait, travel and total time are computed from three time stamps.
2. `car.py`: how one car behaves. It keeps going one way until nothing is left that way, and nobody boards a car that is full or heading the wrong way. A car can also estimate when its passengers would arrive, by running these same rules on a copy of itself.
3. `simulation.py`: the clock. In every tick, new requests appear and are given a car, riders step out, each car chooses its direction, waiting passengers step in, the positions are logged, and the cars move one floor.
4. `schedulers.py`: the "which car?" rules. Each is a function that receives the new passenger and the cars as they are now, and returns one car. It never sees the request list, so it cannot look ahead. `round_robin` counts turns and `nearest_car` counts floors; `least_newcomer_time` asks each car for its estimate and takes the car that gets the newcomer, the passenger asking now, to their destination soonest. `least_combined_time` adds one term to that: the time the newcomer adds to the people already given to that car.
5. `rule_checker.py`: the five rules every run must keep: everyone served, capacity, direction, legal movement, and records that agree with the positions log.

The tests in `tests/` mirror the code files, one test file each. `test_random_runs.py` also runs every scheduler on 300 random buildings and passes each run through the rule checker.

One more command uses the same engine. `scenarios.py` holds the whole experiment: it makes traffic that follows a pattern of the day (`morning`, `lunch` or `evening`), runs every scheduler on it, and prints the results.

- `python -m elevator_sim.scenarios` runs every scheduler on identical traffic over 20 seeds and prints their wait times side by side.
- `python -m elevator_sim.scenarios --write-requests morning out/morning.csv` saves one set of those passengers as a request file instead, so the main command can run it.

## Assumptions

The assignment leaves some behaviour open. These are the choices this simulation makes. Throughout, a *car* is one elevator.

### Direction logic

**No passenger is ever inside a car that is moving away from their destination.**

The assignment asks the system to honor "direction logic" without defining it. This is my reading of it. Two rules make it hold, and the simulation engine enforces both, whichever scheduler is in use:

- **A car never turns round with anyone inside.** It keeps going in one direction until it has nothing left to do that way, and only then reverses.
- **A passenger boards only a car that is heading their way.** A car going up passes a passenger who wants to go down, and collects them on its way back.

What this costs: a passenger can watch their assigned car go past in the other direction and has to wait for it to return.

What it buys: every ride is the direct trip. A scheduler can make someone wait longer, but it cannot send anyone the wrong way.

### Time

**The system reacts within the tick.** A request made at tick *t* is assigned a car at tick *t*, and that car can start moving during tick *t*.

**A stop is free unless you set a stop time.** By default, boarding and stepping out take no time. A passenger boards in the same tick their car is at their floor and heading their way. A passenger whose car is already there waits 0, and a trip from floor 1 to floor 51 takes exactly 50 ticks, as "one time unit = one floor of travel" requires. The assignment says nothing about doors, so this is its literal reading. `--stop-time N` changes it: whenever anyone steps in or out at a floor, the car stays there N more ticks before it moves on. The charge is once per stop, however many people use it.

**The positions log shows the start of each tick.** The row for tick *t* gives each car's floor before it moves in that tick, so row 0 is the starting position.

### Passengers and requests

**One request is one passenger.** Each row of the input is one person with a unique id, so a group of three is three rows. The system counts people by counting requests, which means it always knows exactly how many people are waiting for each car and how many are inside. A real building cannot assume this, because people board without entering a call; real systems also weigh the car.

**Passengers do as they are told.** A passenger takes only the car they were assigned, boards it the first time it is at their floor heading their way with room, and never gives up waiting.
