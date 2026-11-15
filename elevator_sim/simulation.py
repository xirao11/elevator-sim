"""The clock. Runs all the cars, tick by tick, until every passenger is delivered."""

from elevator_sim.car import Car
from elevator_sim.config import Config
from elevator_sim.passenger import Passenger
from elevator_sim.schedulers import round_robin


def run(
    passengers: list[Passenger],
    config: Config = Config(),  # the building's settings; Config() means "every default"
    scheduler=round_robin,  # the "which car?" rule: a function, passed in by name without brackets
) -> list[list[int]]:
    """Simulate the building described by `config` serving `passengers`.

    Fills in each passenger's car_number, board_time and arrive_time, and returns
    the positions log: one row per tick from tick 0. A row holds every car's floor
    at the start of that tick, in car order.
    """
    cars = [
        Car(number=number, capacity=config.capacity, stop_time=config.stop_time, floor=config.start_floor)
        for number in range(config.num_cars)
    ]
    # The safety stop counts from the last request, so a valid file never trips it, however late it starts.
    last_request = max((passenger.request_time for passenger in passengers), default=0)  # default: no passengers
    log = []
    tick = 0
    while True:
        # Steps 1 and 2: people who request at this tick appear, one at a time in file order,
        # and the scheduler gives each of them a car.
        for passenger in passengers:
            if passenger.request_time == tick:
                car = scheduler(passenger, cars)
                car.assign(passenger)

        # Steps 3 to 5, for every car: people step out, the car picks its direction, people step in.
        for car in cars:
            car.serve_floor(tick)

        # Step 6: write down where every car is, before any of them moves.
        log.append([car.floor for car in cars])

        if all(passenger.arrive_time is not None for passenger in passengers):
            return log
        if tick >= last_request + config.max_ticks:
            raise RuntimeError(
                f"Not everyone was delivered {config.max_ticks} ticks after the last request (tick {last_request})."
            )

        # Step 7: every car travels one floor. This is what takes us to the next tick.
        for car in cars:
            car.move()
        tick += 1
