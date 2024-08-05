"""Engine to play connect4 with MCTS
"""

import argparse
import logging
import c4.game
import mcts.tree

LOGGER = logging.getLogger(__name__)


def human_play(game, tree):
    done = False
    while not done:
        game.debug_print()
        print("--------")
        print("01234567")
        if game.state.next_player_id == 0:
            action = None
            while not action:
                try:
                    proposed_action = int(input("Enter your action: "))
                    if (proposed_action) in game.state.permitted_actions:
                        action = int(proposed_action)
                    else:
                        print("✖️")
                except ValueError:
                    print("✖️")
        else:
            action = tree.act(game.state)
        next_state = game.act(action)
        state = next_state
        game.debug_print()
        done = next_state.winner != -1


def train(filename, tree: mcts.tree.Tree, episodes: int):
    for episode_no in range(episodes):
        LOGGER.info("Episode %d", episode_no)
        game = c4.game.Game()
        while game.state.winner == -1:
            LOGGER.debug("Playing Turn")
            action = tree.act(game.state)
            game.act(action)

        LOGGER.debug("Winner: %d", game.state.winner)


def main():
    parser = argparse.ArgumentParser()
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
        default="saved_model.sqlite3",
        help="Filename to use for saving/loading model (default: saved_model.pkl)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity of logging",
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

    game = c4.game.Game()
    tree = mcts.tree.Tree(
        args.filename, c4.game.GameState, c4.game.Game, game.state, 2, args.iterations
    )
    if args.action == "play":
        human_play(game, tree)
    elif args.action == "train":
        train(args.filename, tree, args.episodes)


if __name__ == "__main__":
    main()
