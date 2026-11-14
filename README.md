# Elevator dispatch simulation

A discrete-time simulation of a destination-dispatch elevator system.

Work in progress.

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

**Boarding and stepping out take no time.** A passenger boards in the same tick their car is at their floor and heading their way. A passenger whose car is already there waits 0, and a trip from floor 1 to floor 51 takes exactly 50 ticks, as "one time unit = one floor of travel" requires.

**The positions log shows the start of each tick.** The row for tick *t* gives each car's floor before it moves in that tick, so row 0 is the starting position.

### Passengers and requests

**One request is one passenger.** Each row of the input is one person with a unique id, so a group of three is three rows. The system counts people by counting requests, which means it always knows exactly how many people are waiting for each car and how many are inside. A real building cannot assume this, because people board without entering a call; real systems also weigh the car.

**Passengers do as they are told.** A passenger takes only the car they were assigned, boards it the first time it is at their floor heading their way with room, and never gives up waiting.
