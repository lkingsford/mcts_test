"""Engine to play connect4 with MCTS
"""

import argparse
from datetime import datetime
from enum import Enum
import logging
import threading
import time
import gc
import os
from typing import NamedTuple, Optional
import json

import numpy as np
import c4.game
import c4.human_play
from game.game import GameType
from game.game_state import GameState
import nt.game
import nt.human_play
import ebr.game
import ebr.human_play
import mcts.tree
import mcts.multi_tree

LOGGER = logging.getLogger(__name__)


class ActionLog(NamedTuple):
    action: int
    player_id: Optional[int]
    state: GameState
    memo: Optional[str]


class ActionLogEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, int):
            return obj
        if isinstance(obj, tuple):
            return tuple(self.default(e) for e in obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, Enum):
            return str(obj)
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, ActionLog):
            return {
                "action": super(ActionLogEncoder, self).default(obj.action),
                "player_id": obj.player_id,
                "state": obj.state,
                "memo": super(ActionLogEncoder, self).default(obj.memo),
            }
        return super(ActionLogEncoder, self).default(obj)


def save_report(folder, actions: list[ActionLog]):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, f"{datetime.now()}.json"), "w") as f:
        json.dump(actions, f, cls=ActionLogEncoder)


def train(
    filename,
    tree: mcts.tree.Tree,
    game_class: GameType,
    episodes: int,
    use_speedo: bool,
    report_folder=Optional[str],
):
    if use_speedo:
        stop_event = threading.Event()
        speedo_thread = threading.Thread(target=speedo, args=(tree, stop_event))
        speedo_thread.start()
    try:
        for episode_no in range(episodes):
            try:
                game = game_class()
                if tree.unload_after_play:
                    tree.new_root(game.state)

                LOGGER.info("Episode %d", episode_no)
                action_log: list[ActionLog] = []
                while game.state.winner == -1:

                    LOGGER.debug("GC tracked objects: %d, %d, %d", *gc.get_count())
                    LOGGER.debug("Playing Non-Player Act")
                    action, state = game.non_player_act()
                    action_log.append(ActionLog(action, None, state.loggable(), None))
                    LOGGER.debug("Deciding/Playing Turn")
                    time_before = time.process_time()
                    action = tree.act(game.state)
                    LOGGER.info(
                        "Player %d: %s (%fs)",
                        game.state.next_player_id,
                        str(action),
                        time.process_time() - time_before,
                    )
                    game.act(action)
                    if game.state.memo is not None:
                        LOGGER.info("Memo: %s", game.state.memo)
                    action_log.append(
                        ActionLog(
                            action,
                            game.state.last_player_id,
                            state.loggable(),
                            game.state.memo,
                        )
                    )

                if report_folder:
                    save_report(report_folder, action_log)

                LOGGER.info("Winner: %d", game.state.winner)
            except Exception as e:
                # I don't like this, but I don't want to just stop making
                # reports on an error, and they still happen far too commonly
                LOGGER.error("Exception occurred during training", exc_info=e)

            if episode_no % 10 == 0 or episode_no == episodes - 1:
                tree.to_disk()
    finally:
        if use_speedo:
            stop_event.set()


def speedo(tree: mcts.tree.Tree, stop_event: threading.Event):
    start_time = time.perf_counter()
    iterations_count = tree.total_iterations
    t_old = start_time
    speeds = []
    while not stop_event.is_set():
        t = time.perf_counter() - start_time
        new_iterations_count = tree.total_iterations
        iterations_per_second = (
            float(new_iterations_count) - float(iterations_count)
        ) / (t - t_old)
        speeds.append(iterations_per_second)
        if len(speeds) > 20:
            del speeds[0]
        LOGGER.info("Iterations/second: %f", sum(speeds) / len(speeds))
        iterations_count = new_iterations_count

        stop_event.wait(2)
        t_old = t


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("game", choices=["c4", "nt", "ebr"], help="Game to play/train")
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
        help="Number of iterations to run per process (default: 100)",
    )
    parser.add_argument(
        "-f",
        "--filename",
        help="Save/load model from filename",
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
    parser.add_argument(
        "-S",
        "--slow",
        action="store_true",
        default=False,
        help="Whether to backtrace all the way to root (default: False)",
    )
    parser.add_argument(
        "-up",
        "--unload-played",
        action="store_true",
        default=False,
        help="Whether to unload the tree before the turn after playing a turn",
    )
    parser.add_argument(
        "--force-multitree",
        action="store_true",
        default=False,
        help="Whether to use MultiTree instead of Tree, even if single job",
    )
    parser.add_argument(
        "--act-const",
        type=float,
        default=0,
        help="Constant to use when acting",
    )
    parser.add_argument(
        "-j", "--jobs", type=int, default=1, help="Number of parallel processes"
    )
    parser.add_argument(
        "-r",
        "--reports",
        help="Save reports to a folder",
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
        "[%(asctime)s][%(levelname)s][%(process)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(max(logging.ERROR - args.verbose * 10, logging.DEBUG))
    logging.getLogger(__name__).debug("Parsed arguments: %s", args)

    state_class = None
    game_class = None
    if args.game == "c4":
        state_class = c4.game.GameState
        game_class = c4.game.Game
        human_play = c4.human_play.human_play
        game = game_class()
    elif args.game == "nt":
        state_class = nt.game.NtState
        game_class = nt.game.NtGame
        human_play = nt.human_play.human_play
        game = game_class()
    elif args.game == "ebr":
        state_class = ebr.game.EbrGameState
        game_class = ebr.game.EbrGame
        human_play = ebr.human_play.human_play
        game = game_class(player_count=4)

    if state_class is None:
        raise ValueError("Unknown game type")

    try:
        if args.jobs == 1 and not args.force_multitree:
            tree = mcts.tree.Tree(
                args.filename,
                state_class,
                game_class,
                game.state,
                args.iterations,
                reward_model=getattr(game_class, "reward_model", None),
                slow_mode=args.slow,
                unload_after_play=args.unload_played,
                act_const=args.act_const,
            )
        else:
            tree = mcts.multi_tree.MultiTree(
                args.filename,
                state_class,
                game_class,
                game.state,
                args.iterations,
                reward_model=getattr(game_class, "reward_model", None),
                slow_mode=args.slow,
                unload_after_play=args.unload_played,
                act_const=args.act_const,
                jobs=args.jobs,
            )
        if args.action == "play":
            human_play(game, tree)
        elif args.action == "train":
            train(
                args.filename,
                tree,
                game_class,
                args.episodes,
                args.speedo,
                args.reports,
            )
    finally:
        tree.close()


if __name__ == "__main__":
    main()
