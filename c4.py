"""Engine to play connect4 with MCTS
"""

import argparse
import c4.game


def human_play():
    game = c4.game.Game()
    done = False
    while not done:
        game.debug_print()
        print("--------")
        print("01234567")
        if game.state.next_player_id < 3:
            action = None
            while not action:
                try:
                    proposed_action = int(input("Enter your action: "))
                    if (proposed_action) in game.state.actions:
                        action = int(proposed_action)
                    else:
                        print("✖️")
                except ValueError:
                    print("✖️")
        else:
            pass
        next_state = game.act(action)
        state = next_state
        game.debug_print()
        done = next_state.winner != -1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=["play", "train"],
        default="play",
        help="action to perform",
        nargs="?",
    )
    parser.add_argument(
        "-e",
        "--episodes",
        type=int,
        default=1000,
        help="number of episodes to run (default: 1000)",
        required=("train" == parser.parse_args().action),
    )
    parser.add_argument(
        "-f",
        "--filename",
        default="saved_model.pkl",
        help="filename to use for saving/loading model " "(default: saved_model.pkl)",
    )

    args = parser.parse_args()
    if args.action == "play":
        human_play()
    elif args.action == "train":
        c4.game.train(args.filename, args.episodes)
