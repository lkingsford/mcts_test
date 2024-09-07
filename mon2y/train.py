from datetime import datetime
import json
import logging
import os
from typing import Callable, NamedTuple, Optional
import multiprocessing
import numpy as np
from reporter.action_log import ActionLog, ActionLogEncoder, save_report
from mon2y import Node, ActCallable, Action, ActResponse


LOGGER = logging.getLogger(__name__)

total_iterations = 0


class EpisodeReport(NamedTuple):
    final_reward: np.array
    log: list[ActionLog]


def get_total_iterations():
    global total_iterations
    return total_iterations


def iterate(node: Node, act_fn: ActCallable, constant: np.float32 = np.sqrt(2)):
    selection = node.selection(constant)
    if not selection:
        return
    selection.expansion(act_fn)

    if selection.reward is None:
        reward = selection.play_out(act_fn)
        LOGGER.debug("Playout reward is %s", selection.reward)
        selection.back_propogate(reward)
    else:
        LOGGER.debug("Reward without playout is %s", selection.reward)
        selection.back_propogate(selection.reward)


def _run_iterations(
    node: Node, act_fn: ActCallable, iterations: int, constant: np.float32 = np.sqrt(2)
) -> list[tuple[Action, float]]:
    for _ in range(iterations):
        iterate(node, act_fn)
    picks = node.best_pick_with_values(0)
    return picks


def calculate_next_action(
    node: Node,
    act_fn: ActCallable,
    iterations: int,
    constant: np.float32 = np.sqrt(2),
    processes: int = 1,
) -> Action:
    with multiprocessing.Pool(processes) as pool:
        all_picks = pool.starmap(
            _run_iterations,
            [(node, act_fn, iterations, constant)] * processes,
        )

    global total_iterations
    total_iterations += iterations * processes

    action_sums: dict[Action, float] = {}
    for picks in all_picks:
        for pick in picks:
            if pick[0] not in action_sums:
                action_sums[pick[0]] = 0.0
            action_sums[pick[0]] += pick[1]
    LOGGER.info("Action sums: %s", action_sums)
    return max(action_sums, key=lambda action: action_sums[action])


def episode(
    initializer: Callable[[], ActResponse],
    act_fn: ActCallable,
    iterations: int,
    constant: np.float32 = np.sqrt(2),
    processes: int = 1,
) -> EpisodeReport:
    """Execute whole episode"""
    action_log = []
    initial_state = initializer()
    node = Node(
        state=initial_state.state,
        permitted_actions=initial_state.permitted_actions,
        next_player=initial_state.next_player,
        reward=initial_state.reward,
    )
    node.expansion(act_fn)
    while node.reward is None:
        LOGGER.info("Action %s", node.action)
        action = calculate_next_action(node, act_fn, iterations, constant, processes)
        node = node.get_child(action)
        node.expansion(act_fn)
        node.make_root()
        assert node.state
        action_log.append(
            ActionLog(action, node.player_id, node.state.loggable(), node.memo)
        )

    LOGGER.info("Episode done - reward: %s", node.reward)

    return EpisodeReport(final_reward=node.reward, log=action_log)


def save_report(episode_result: EpisodeReport, location: str):
    # Maybe this could be moved out of here?
    os.makedirs(location, exist_ok=True)
    filename = f"{datetime.now()}.json"
    path = os.path.join(location, filename)
    LOGGER.info("Saving report to %s", path)
    with open(path, "w") as f:
        json.dump(
            {"log": episode_result.log, "reward": episode_result.final_reward},
            f,
            cls=ActionLogEncoder,
        )


def train(
    initializer: Callable[[], ActResponse],
    act_fn: ActCallable,
    iterations: int,
    episodes: int,
    constant: np.float32 = np.sqrt(2),
    processes: int = 1,
    report_location: Optional[str] = None,
):
    for episode_no in range(episodes):
        LOGGER.info("Episode %d", episode_no)
        result = episode(initializer, act_fn, iterations, constant, processes)
        if report_location:
            save_report(result, report_location)
