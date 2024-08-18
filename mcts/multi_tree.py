import multiprocessing
import time
from typing import NamedTuple, Optional
import logging

import numpy as np
from game.game_state import GameState
from mcts.tree import Tree

LOGGER = logging.getLogger(__name__)


def process_worker(
    q: multiprocessing.Queue,
    result_q: multiprocessing.Queue,
    game_state_class,
    game_class,
    initial_state,
    iterations,
    constant,
    reward_model,
    slow_mode,
    unload_after_play,
):
    tree = Tree(
        None,
        game_state_class,
        game_class,
        initial_state,
        iterations,
        constant,
        reward_model,
        slow_mode,
        unload_after_play,
    )
    while True:
        state = q.get(block=True)
        node = tree.get_node(state)
        tree._process_turn(node, state)
        ucbs = node.child_ucb(0.0)
        keys = list(node.children.keys())
        result_q.put((keys, ucbs, tree.total_iterations))


class MultiTree:
    def __init__(
        self,
        filename,
        game_state_class,
        game_class,
        initial_state,
        iterations,
        constant: float = 1.4142135623730951,
        reward_model: Optional[callable] = None,
        slow_mode: bool = False,
        unload_after_play: bool = False,
        jobs=4,
    ):
        self.game_state_class = game_state_class
        self.game_class = game_class
        self.initial_state = initial_state
        self.iterations = iterations
        self.constant = constant
        self.reward_model = reward_model
        self.slow_mode = slow_mode
        self.unload_after_play = unload_after_play
        self.jobs = jobs
        self.total_iterations = 0
        self.setup_processes()

    def setup_processes(self):
        self.q = multiprocessing.Queue()
        self.result_q = multiprocessing.Queue()
        self.processes = []
        for _ in range(self.jobs):
            p = multiprocessing.Process(
                target=process_worker,
                args=(
                    self.q,
                    self.result_q,
                    self.game_state_class,
                    self.game_class,
                    self.initial_state,
                    self.iterations,
                    self.constant,
                    self.reward_model,
                    self.slow_mode,
                    self.unload_after_play,
                ),
            )
            p.start()
            self.processes.append(p)

    @staticmethod
    def best_action(permitted_actions, process_output) -> int:
        sums = np.zeros(len(permitted_actions))
        for value_group in process_output:
            for key, ucb in zip(value_group[0], value_group[1]):
                array_index = permitted_actions.index(key)
                sums[array_index] += ucb
        LOGGER.debug("Sums of ucbs: %s", str(sums))
        return permitted_actions[int(np.argmax(sums))]

    def act(self, state: GameState) -> int:
        # Strategy is 'sum' voting - see p3 of
        # https://www-users.cse.umn.edu/~gini/publications/papers/Steinmetz2020TG.pdf
        # We probably want to be able to add 'majority' voting as an option
        for _ in range(self.jobs):
            self.q.put(state)

        # Result is keys, ucbs, total_iterations
        keys_ucbs = [self.result_q.get() for _ in range(self.jobs)]
        self.total_iterations = sum([k[2] for k in keys_ucbs])
        return MultiTree.best_action(state.permitted_actions, keys_ucbs)

    def new_root(self, state):
        # We're not actually rerooting...
        # We're just killing it and starting again
        for p in self.processes:
            p.terminate()
        self.initial_state = state
        self.setup_processes()

    def to_disk(self):
        LOGGER.warn("MultiTree to_disk not yet implemented")

    def close(self):
        for p in self.processes:
            p.terminate()
