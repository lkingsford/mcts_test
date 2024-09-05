import logging
import numpy as np
from mon2y import Node, ActCallable, Action, State


LOGGER = logging.getLogger(__name__)

total_iterations = 0


def iterate(node: Node, act_fn: ActCallable, constant: np.float32 = np.sqrt(2)):
    selection = node.selection(constant)
    if not selection:
        return
    selection.expansion(act_fn)
    reward = selection.play_out(act_fn)
    selection.back_propogate(reward)
    global total_iterations
    total_iterations += 1


def calculate_next_action(
    node: Node, act_fn: ActCallable, iterations: int, constant: np.float32 = np.sqrt(2)
) -> Action:
    for _ in range(iterations):
        iterate(node, act_fn)
    return node.best_pick(constant)[0]


def episode(
    initial_state: State,
    act_fn: ActCallable,
    iterations: int,
    constant: np.float32 = np.sqrt(2),
):
    """Execute whole episode"""
    node = Node(state=initial_state)
    while node.reward is None:
        for _ in range(iterations):
            action = calculate_next_action(node, act_fn, iterations, constant)
            node = node.get_child(action)
