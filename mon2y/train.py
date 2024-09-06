import logging
from typing import Callable
import numpy as np
from mon2y import Node, ActCallable, Action, ActResponse


LOGGER = logging.getLogger(__name__)

total_iterations = 0


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
        LOGGER.info("Playout reward is %s", selection.reward)
        selection.back_propogate(reward)
    else:
        LOGGER.info("Reward without playout is %s", selection.reward)
        selection.back_propogate(selection.reward)

    global total_iterations
    total_iterations += 1


def calculate_next_action(
    node: Node, act_fn: ActCallable, iterations: int, constant: np.float32 = np.sqrt(2)
) -> Action:
    for _ in range(iterations):
        iterate(node, act_fn)
    picks = node.best_pick_with_values(0)
    LOGGER.info("Picks: %s", picks)
    return picks[0][0]


def episode(
    initializer: Callable[[], ActResponse],
    act_fn: ActCallable,
    iterations: int,
    constant: np.float32 = np.sqrt(2),
):
    """Execute whole episode"""
    initial_state = initializer()
    node = Node(
        state=initial_state.state,
        permitted_actions=initial_state.permitted_actions,
        next_player=initial_state.next_player,
        reward=initial_state.reward,
    )
    while node.reward is None:
        LOGGER.info("Action %s", node.action)
        action = calculate_next_action(node, act_fn, iterations, constant)
        node = node.get_child(action)
        node.make_root()

    LOGGER.info("Episode done - reward: %s", node.reward)


def train(
    initializer: Callable[[], ActResponse],
    act_fn: ActCallable,
    iterations: int,
    episodes: int,
    constant: np.float32 = np.sqrt(2),
):
    for episode_no in range(episodes):
        LOGGER.info("Episode %d", episode_no)
        episode(initializer, act_fn, iterations, constant)
