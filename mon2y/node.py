import random
from typing import Callable, Hashable, NamedTuple, Optional
import logging

import numpy as np


LOGGER = logging.getLogger(__name__)

Action = Hashable
PlayerId = int
State = Hashable
Reward = np.ndarray

NON_PLAYER_ACTION = -1


class ActResponse(NamedTuple):
    permitted_actions: tuple[Action, ...]
    state: State
    next_player: PlayerId
    reward: Optional[Reward]


ActCallable = Callable[[State, Action], ActResponse]


class Node:
    def __init__(
        self,
        action: Action = None,
        player_id: int = -1,
        parent: Optional["Node"] = None,
        state: State = None,
        reward: Optional[Reward] = None,
        permitted_actions: Optional[tuple[Action, ...]] = None,
        next_player: Optional[int] = None,
    ):
        self.parent = parent
        self.action = action
        self.state = state
        self.player_id = player_id
        self.reward = None
        self._fully_explored_branch = False
        # Fully explored could be a property, but this stops it turning into a

        # These are used when this is the root
        self.permitted_actions = permitted_actions
        self.reward = reward
        self.next_player = next_player

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
    ):
        if (
            self.permitted_actions is not None
            and self.state is not None
            and self.next_player is not None
        ):
            actions = self.permitted_actions
            player_id = self.next_player
        else:
            if any([self.permitted_actions is not None, self.next_player is not None]):
                LOGGER.warning(
                    "Not state provided, but permitted actions and/or next player are set"
                )
            # This is the expected state, except in root
            assert self.parent
            assert self.parent.state is not None
            actions, self.state, player_id, self.reward = act_fn(
                self.parent.state, self.action
            )

        # These allow us to reroot later without rerunning
        self.permitted_actions = actions
        self.next_player = player_id

        assert actions

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
        if (
            self.permitted_actions is not None
            and self.state is not None
            and self.next_player is not None
        ):
            result = ActResponse(
                self.permitted_actions, self.state, self.next_player, self.reward
            )
        else:
            if any([self.permitted_actions is not None, self.next_player is not None]):
                LOGGER.warning(
                    "No state provided, but permitted action and/or next_player are set."
                )
            assert self.parent
            assert self.parent.state is not None
            result = act_fn(self.parent.state, self.action)

        while result.reward is None:
            action = random.choice(result.permitted_actions)
            result = act_fn(result.state, action)

        return result.reward

    def get_child(self, action: Action) -> "Node":
        return self._children[self._child_action_idx_map[action]]

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
        # We rely on div/0 on when calculating UCB - it's not helpful to have them as
        # warnings
        np.seterr(divide="ignore")
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

    def best_pick_with_values(self, constant) -> list[tuple[Action, float]]:
        # I ack there's dupe code here, but I don't want to slow down best_pick
        # when we don't need the values - even if it's not big
        # (unmeasured, as of writing)
        ucbs = self.child_ucb(constant)
        best_picks = [child_action_idx for child_action_idx in np.argsort(ucbs)[::-1]]
        best_pick_ucbs = ucbs[best_picks]
        return [
            (
                self._child_idx_action_map[child_action_idx],
                best_pick_ucbs[child_action_idx],
            )
            for child_action_idx in best_picks
        ]

    def make_root(self):
        if not self.state:
            raise ValueError("Cannot root an unexpanded node")
        self.parent = None
