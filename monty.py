"""Engine to play connect4 with MCTS
"""

import argparse
import logging
import threading
import time
import c4.game
import c4.human_play
import nt.game
import nt.human_play
import mcts.tree

LOGGER = logging.getLogger(__name__)


def train(filename, tree: mcts.tree.Tree, episodes: int, use_speedo: bool):
    if use_speedo:
        stop_event = threading.Event()
        speedo_thread = threading.Thread(target=speedo, args=(tree, stop_event))
        speedo_thread.start()
    try:
        for episode_no in range(episodes):
            LOGGER.info("Episode %d", episode_no)
            game = c4.game.Game()
            while game.state.winner == -1:
                LOGGER.debug("Playing Turn")
                action = tree.act(game.state)
                game.act(action)

            LOGGER.info("Winner: %d", game.state.winner)
            if episode_no % 10 == 0 or episode_no == episodes - 1:
                tree.to_disk()
    finally:
        if use_speedo:
            stop_event.set()


def speedo(tree: mcts.tree.Tree, stop_event: threading.Event):
    start_time = time.perf_counter()
    node_count = tree.node_count()
    iterations_count = tree.total_iterations
    selection_count = tree.total_select_inspections
    while not stop_event.is_set():
        t = time.perf_counter() - start_time
        new_node_count = tree.node_count()
        LOGGER.info("Nodes/second: %f", (float(new_node_count) - float(node_count)) / t)
        node_count = new_node_count

        new_iterations_count = tree.total_iterations
        LOGGER.info(
            "Iterations/second: %f",
            (float(new_iterations_count) - float(iterations_count)) / t,
        )
        iterations_count = new_iterations_count

        new_selection_count = tree.total_select_inspections
        LOGGER.info(
            "Selections/second: %f",
            (float(new_selection_count) - float(selection_count)) / t,
        )
        selection_count = new_selection_count
        stop_event.wait(2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("game", choices=["c4", "nt"], help="Game to play/train")
    parser.add_argument(
        "action",
        choices=["play", "train"],
        default="play",
        help="Action to perform",
        nargs="?",
    )
    parser.add_argument(
        "-e",
        "--episodes",
        type=int,
        default=100,
        help="Number of episodes to run (default: 100)",
    )
    parser.add_argument(
        "-i",
        "--iterations",
        type=int,
        default=100,
        help="Number of iterations to run (default: 100)",
    )
    parser.add_argument(
        "-f",
        "--filename",
        help="Filename to use for saving/loading model (default: [gamename].pkl)",
        nargs="?",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity of logging",
    )
    parser.add_argument(
        "-s",
        "--speedo",
        action="store_true",
        default=False,
        help="Whether to display a nodes/second count (default: False)",
    )

    args = parser.parse_args()

    # Ensure that iterations and episodes are set properly based on the action
    if args.iterations <= 0:
        parser.error("--iterations must be greater than 0 for training.")
    if args.action == "train":
        if args.episodes <= 0:
            parser.error("--episodes must be greater than 0 for training.")
    else:
        args.episodes = None

    if args.speedo:
        args.verbose = max(args.verbose, 2)

    # Configure logging
    logger = logging.getLogger()
    formatter = logging.Formatter(
        "[%(asctime)s][%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(max(logging.ERROR - args.verbose * 10, logging.DEBUG))
    logging.getLogger(__name__).debug("Parsed arguments: %s", args)

    filename = args.filename or f"{args.game}.pkl"
    # Not fantastic structure here, but will do for now
    if args.game == "c4":
        game = c4.game.Game()
        tree = mcts.tree.Tree(
            filename, c4.game.GameState, c4.game.Game, game.state, 2, args.iterations
        )
        if args.action == "play":
            c4.human_play.human_play(game, tree)
        elif args.action == "train":
            train(filename, tree, args.episodes, args.speedo)
    elif args.game == "nt":
        game = nt.game.NtGame()
        # tree = mcts.tree.Tree(
        #    filename, nt.game.NtState, nt.game.NtGame, game.state, 2, args.iterations
        # )
        if args.action == "play":
            nt.human_play.human_play(game, None)
        elif args.action == "train":
            train(filename, tree, args.episodes, args.speedo)


if __name__ == "__main__":
    main()
