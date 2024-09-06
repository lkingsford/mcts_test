import argparse
import math
import logging
import threading
import time
from typing import Callable, NamedTuple

import c4.m2game
from mon2y import train, ActCallable, ActResponse, get_total_iterations

LOGGER = logging.getLogger(__name__)


class GameDetails(NamedTuple):
    initilizer: Callable[[], ActResponse]
    act_fn: ActCallable


GAMES = {"c4": GameDetails(c4.m2game.initialize_game, c4.m2game.act)}


def speedo(stop_event: threading.Event):
    logger = logging.getLogger("speedo")
    logger.setLevel(logging.INFO)
    start_time = time.perf_counter()
    iterations_count = get_total_iterations()
    t_old = start_time
    speeds = []
    while not stop_event.is_set():
        t = time.perf_counter() - start_time
        new_iterations_count = get_total_iterations()
        iterations_per_second = (
            float(new_iterations_count) - float(iterations_count)
        ) / (t - t_old)
        speeds.append(iterations_per_second)
        if len(speeds) > 20:
            del speeds[0]
        logger.info("Iterations/second: %f", sum(speeds) / len(speeds))
        iterations_count = new_iterations_count

        stop_event.wait(2)
        t_old = t


def positive_int(value):
    try:
        v = int(value)
        if v < 1:
            raise argparse.ArgumentTypeError(f"{value} is not a positive integer")
        return v
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value} is not an integer")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("game", help="Game to play/train", choices=GAMES.keys())
    parser.add_argument(
        "-i",
        "--iterations",
        type=positive_int,
        default=100,
        help="Number of iterations to run per process (default: 100)",
    )
    parser.add_argument(
        "-e",
        "--episodes",
        type=positive_int,
        default=100,
        help="Number of episodes to run (default: 100)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity of logging",
    )
    parser.add_argument(
        "-f",
        "--report_folder",
        help="Folder to store reports",
        default=None,
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=positive_int,
        default=1,
        help="Number of processes to run (default: 1)",
    )
    parser.add_argument(
        "-c",
        "--constant",
        type=float,
        default=math.sqrt(2),
        help="Explore constant (default: sqrt(2))",
    )
    parser.add_argument(
        "-s",
        "--speedo",
        action="store_true",
        default=False,
        help="Whether to display a nodes/second count (default: False)",
    )
    args = parser.parse_args()
    logger = logging.getLogger()
    logger.setLevel(logging.CRITICAL - 10 * args.verbose)
    formatter = logging.Formatter(
        fmt="[%(asctime)s][%(levelname)s][%(process)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if args.speedo:
        stop_event = threading.Event()
        speedo_thread = threading.Thread(target=speedo, args=(stop_event,))
        speedo_thread.start()

    train(
        GAMES[args.game].initilizer,
        GAMES[args.game].act_fn,
        args.iterations,
        args.episodes,
        args.constant,
        args.jobs,
    )


if __name__ == "__main__":
    main()
