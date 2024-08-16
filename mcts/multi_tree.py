import multiprocessing
import time
from typing import NamedTuple

import numpy as np
from mcts.tree import Tree


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
        ucbs = node.child_ucb(constant)
        keys = list(node.children.keys())
        result_q.put((keys, ucbs))


class MultiTree:
    def __init__(
        self,
        filename,
        game_state_class,
        game_class,
        initial_state,
        iterations,
        constant,
        reward_model,
        slow_mode,
        unload_after_play,
        jobs,
    ):
        self.q = multiprocessing.Queue()
        self.result_q = multiprocessing.Queue()
        for _ in range(jobs):
            p = multiprocessing.Process(
                target=process_worker,
                args=(
                    self.q,
                    self.result_q,
                    game_state_class,
                    game_class,
                    initial_state,
                    iterations,
                    constant,
                    reward_model,
                    slow_mode,
                    unload_after_play,
                ),
            )
            p.start()

        self.jobs = jobs

    def act(self, state) -> int:
        # Strategy is 'sum' voting - see p3 of
        # https://www-users.cse.umn.edu/~gini/publications/papers/Steinmetz2020TG.pdf
        # We probably want to be able to add 'majority' voting as an option
        for _ in range(self.jobs):
            self.q.put(state)

        # Result is keys, ucbs
        keys_ucbs = [self.result_q.get() for _ in range(self.jobs)]
        all_keys = set({key for keys, _ in keys_ucbs for key in keys})
        sums: dict[int, float] = {}
        for key in all_keys:
            sums[key] = 0
            for keys, ucbs in keys_ucbs:
                if key == keys:
                    sums[key] += ucbs[keys.index(key)]
        return max(sums.items(), key=lambda x: x[1])[0]
