from collections import NamedTuple
from typing import Callable, Hashable, Optional

import numpy as np

Action = Hashable
PlayerId = int
State = Hashable
ActCallable = Callable[[State, Action], tuple[State, tuple[Action]]]

NON_PLAYER_ACTION = -1


class Child(NamedTuple):
    action: Action
    player_id: PlayerId
    state_hash: State


class Node:
    def __init__(
        self,
        action: Action = None,
        player_id: int = -1,
        parent: Optional["Node"] = None,
        state_hash: Hashable = None,
    ):
        self.parent = parent
        self.action = action
        self.state_hash = state_hash
        self.player_id = player_id
        self.leaf = True
        self.fully_explored = False
        # Spending memory to decrease CPU usage
        # These map actions to the index of children, child visits and child values
        self._child_idx_action_map: dict[int, Action] = {}
        self._child_action_idx_map: dict[Action, int] = {}
        self._children: list["Node"] = []
        self._child_visit_count: Optional[np.array] = None
        self._child_value: Optional[np.array] = None
        pass

    def selection(self, constant) -> Optional["Node"]:
        if self.fully_explored:
            return None

        if self.leaf:
            return self

        selection_found = None
        while not selection_found and not self.fully_explored:
            best_picks = self.best_pick(constant)
            best_pick = next(
                pick for pick in best_picks if not self.get_child(pick).fully_explored
            )
            return self.get_child(best_pick)

    def expansion(self, children: list[Child]):
        """Create a new child node for an action"""
        if not self._child_visit_count:
            self._child_visit_count = np.zeros(len(children))
        else:
            new_visit_counts = np.zeros(len(children))
            self._child_visit_count = np.append(
                self._child_visit_count, new_visit_counts
            )

        if not self._child_value:
            self._child_value = np.zeros(len(children))
        else:
            new_values = np.zeros(len(children))
            self._child_value = np.append(self._child_value, new_values)

        for child in children:
            self._child_action_idx_map[child.action] = len(self._children)
            self._child_idx_action_map[len(self._children)] = child.action
            self._children.append(
                Node(
                    action=child.action,
                    player_id=child.player_id,
                    parent=self,
                    state_hash=child.state_hash,
                )
            )

        self.leaf = False

    def play_out(self, state: State, act_fn: ActCallable):
        self.fully_explored = all(child.fully_explored for child in self._children)

    def get_child(self, action: Action) -> "Node":
        return self._children[self._child_action_idx_map[action]]

    def detach_from_parent(self):
        self.parent = None
        pass

    def back_propogate(self, value_d: np.array):
        """Propogate the value back to the root of the tree

        Args:
            value_d (np.array): Value to propogate for each player
        """
        node = self
        while node.parent:
            if node.player_id >= 0:
                assert node.parent._child_visit_count
                node.parent._child_visit_count[
                    node._child_action_idx_map[node.action]
                ] += 1
                node.parent._child_value[
                    node._child_action_idx_map[node.action]
                ] += value_d[node.player_id]
            node = node.parent

    def child_ucb(self, constant):
        q = (self._child_value) / (1 + self._child_visit_count)
        u = np.sqrt(np.log(self.parent.visit_count) / (1 + self._child_visit_count))
        # Small amount of randomness to prevent bias when there's multiple of the same value
        # (especially in the beginning)
        r = np.random.rand(len(q)) * 1e-6
        return q + constant * u + r

    def best_pick(self, constant) -> list[Action]:
        ucbs = self.child_ucb(constant)
        best_picks = [child_action_idx for child_action_idx in np.argsort(ucbs)[::-1]]
        return [
            self._child_idx_action_map[child_action_idx]
            for child_action_idx in best_picks
        ]
