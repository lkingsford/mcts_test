import argparse
import math
import logging
from typing import Callable, NamedTuple
import c4.m2game

from mon2y import train
from mon2y.node import ActCallable, ActResponse


class GameDetails(NamedTuple):
    initilizer: Callable[[], ActResponse]
    act_fn: ActCallable


GAMES = {"c4": GameDetails(c4.m2game.initialize_game, c4.m2game.act)}


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

    train(
        GAMES[args.game].initilizer,
        GAMES[args.game].act_fn,
        args.iterations,
        args.episodes,
        args.constant,
    )


if __name__ == "__main__":
    main()
