import random
from typing import Callable, Hashable, NamedTuple, Optional

import numpy as np

Action = Hashable
PlayerId = int
State = Hashable
Reward = np.ndarray

NON_PLAYER_ACTION = -1


class ActResponse(NamedTuple):
    permitted_actions: tuple[Action, ...]
    state: State
    next_player: PlayerId
    reward: Optional[np.ndarray]


ActCallable = Callable[[State, Action], ActResponse]


class Node:
    def __init__(
        self,
        action: Action = None,
        player_id: int = -1,
        parent: Optional["Node"] = None,
        state: State = None,
    ):
        self.parent = parent
        self.action = action
        self.state = state
        self.player_id = player_id
        self._fully_explored_branch = False
        # Fully explored could be a property, but this stops it turning into a

        # These are used when parent is None
        self._override_parent_state: Optional[State] = None

        # Spending memory to decrease CPU usage
        # These map actions to the index of children, child visits and child values
        self._child_idx_action_map: dict[int, Action] = {}
        self._child_action_idx_map: dict[Action, int] = {}
        self._children: list["Node"] = []
        self._child_visit_count: Optional[np.array] = None
        self._child_value: Optional[np.array] = None

    @property
    def value_estimate(self):
        return (
            self.parent._child_value[self.parent._child_action_idx_map[self.action]]
            if self.parent
            else np.sum(self._child_value)
        )

    @property
    def visit_count(self):
        return (
            self.parent._child_visit_count[
                self.parent._child_action_idx_map[self.action]
            ]
            if self.parent
            else np.sum(self._child_visit_count)
        )

    @property
    def fully_explored(self):
        return self._fully_explored_branch or (
            len(self._children) > 0
            and all(child.fully_explored for child in self._children)
        )

    @property
    def leaf(self):
        return len(self._children) == 0

    def selection(self, constant=np.sqrt(2)) -> Optional["Node"]:
        if self.fully_explored:
            return None

        if self.leaf:
            return self

        current_selection: "Node" = self

        while not current_selection.leaf:
            best_picks = current_selection.best_pick(constant)
            best_pick = next(
                pick
                for pick in best_picks
                if not current_selection.get_child(pick).fully_explored
            )
            current_selection = current_selection.get_child(best_pick)

        return current_selection

    def expansion(
        self,
        act_fn: ActCallable,
        parent_state: Optional[State] = None,
    ):
        if parent_state is None:
            assert self.parent
            assert self.parent.state is not None
            parent_state = self.parent.state

        actions, self.state, player_id, self.reward = act_fn(self.action, parent_state)
        if self.reward is not None:
            self._fully_explored_branch = True
            return

        """Create a new child node for an action"""
        if not self._child_visit_count:
            self._child_visit_count = np.zeros(len(actions))
        else:
            new_visit_counts = np.zeros(len(actions))
            self._child_visit_count = np.append(
                self._child_visit_count, new_visit_counts
            )

        if not self._child_value:
            self._child_value = np.zeros(len(actions))
        else:
            new_values = np.zeros(len(actions))
            self._child_value = np.append(self._child_value, new_values)

        for action in actions:
            self._child_action_idx_map[action] = len(self._children)
            self._child_idx_action_map[len(self._children)] = action
            self._children.append(
                Node(action=action, player_id=player_id, parent=self, state=None)
            )

    def play_out(self, act_fn: ActCallable) -> Reward:
        if self._override_parent_state is not None:
            parent_state = self._override_parent_state
        else:
            assert self.parent
            assert self.parent.state is not None
            parent_state = self.parent.state

        result = act_fn(parent_state, self.action)
        while result.reward is None:
            action = random.choice(result.permitted_actions)
            result = act_fn(result.state, action)

        return result.reward

    def get_child(self, action: Action) -> "Node":
        return self._children[self._child_action_idx_map[action]]

    def detach_from_parent(self):
        self._override_parent_state = self.parent.state
        self.parent = None
        pass

    def override_parent_state(self, state: State):
        self._override_parent_state = state

    def back_propogate(self, value_d: np.array):
        """Propogate the value back to the root of the tree

        Args:
            value_d (np.array): Value to propogate for each player
        """
        node = self
        while node.parent:
            if node.player_id >= 0:
                assert node.parent._child_visit_count is not None
                node.parent._child_visit_count[
                    node.parent._child_action_idx_map[node.action]
                ] += 1
                node.parent._child_value[
                    node.parent._child_action_idx_map[node.action]
                ] += value_d[node.player_id]
            node = node.parent

    def child_ucb(self, constant):
        q = (self._child_value) / (1 + self._child_visit_count)
        u = np.sqrt(np.log(np.divide(self.visit_count, self._child_visit_count)))
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
