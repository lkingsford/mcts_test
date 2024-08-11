from contextlib import contextmanager
import logging
from typing import Optional, OrderedDict
import math
import pickle
import numpy as np
from game.game import GameType
from game.game_state import GameState

LOGGER = logging.getLogger(__name__)


class NodeStore:
    def __init__(self, root: Optional["Node"] = None):
        self.root = root

    def count(self) -> int:
        if self.root:
            return self.root.visit_count
        else:
            return 0

    def to_disk(self, filename: str):
        assert self.root
        LOGGER.info("Saving %d nodes to %s", self.root.visit_count, filename)
        pickle.dump(self.root, open(filename, "wb"))
        LOGGER.info("Saved")

    @classmethod
    def from_disk(cls, filename: str):
        LOGGER.info("Loading nodes from %s", filename)
        root = pickle.load(open(filename, "rb"))
        LOGGER.info("Loaded")
        return cls(root)


class Node:
    def __init__(
        self,
        player_id: Optional[int],
        action: int,
        state: Optional[GameState],
        game_class: GameType,
        parent: Optional["Node"],
        leaf: bool,
    ):
        self.action = action
        self.parent = parent
        self._player_id = player_id
        self._state = state
        self.game_class = game_class
        self.leaf = leaf
        self._constant = None
        self.children: OrderedDict[int, "Node"] = OrderedDict()
        self.child_visit_count: Optional[np.array] = None
        self.child_value: Optional[np.array] = None
        # self._temp_visit_count = np.zeros(state.max_action_count())

    def add_child(self, action: int, state: Optional[GameState] = None):
        self.children[action] = Node(
            player_id=state.player_id if state else None,
            action=action,
            state=state,
            parent=self,
            game_class=self.game_class,
            leaf=True,
        )
        self.leaf = False

    @property
    def player_id(self):
        if self._state:
            return self._state.player_id
        else:
            raise ValueError("State not set")

    @property
    def action_index(self):
        # And I don't like this either!
        return list(self.parent.children.keys()).index(self.action)

    @property
    def value_estimate(self):
        return self.parent.child_value[self.action_index]

    @value_estimate.setter
    def value_estimate(self, value):
        self.parent.child_value[self.action_index] = value

    @property
    def visit_count(self):
        return self.parent.child_visit_count[self.action_index]

    @visit_count.setter
    def visit_count(self, value):
        self.parent.child_visit_count[self.action_index] = value

    @property
    def parent_node_visit_count(self):
        return self.parent.visit_count

    @property
    def hash(self):
        if self._state:
            return self._state.hash()
        else:
            return None

    @property
    def state(self):
        if self._state:
            return self._state
        else:
            # Not sure if I'm comfortable this being in a property
            game = self.game_class.from_state(self.parent.state)
            if self.parent.state.next_automated:
                self._state = game.apply_non_player_acts(self.action)
            else:
                self._state = game.act(self.action)
            assert not isinstance(self._state.previous_actions[-1], np.int64)
            return self._state

    def child_ucb(self, constant):
        # q = (self.temp_visit_count + self.child_value) / (1 + self.child_visit_count)
        q = (self.child_value) / (1 + self.child_visit_count)
        u = np.sqrt(np.log(self.parent_node_visit_count) / (1 + self.child_visit_count))
        return q + u

    def best_pick(self, constant, permitted_actions) -> list[int]:
        ucbs = self.child_ucb(constant)
        LOGGER.debug("Best pick from: %s", (ucbs.tolist()))
        # Not sure how fast this list comprehension is
        # Child value is never set for automated turns - so this shold
        # still work
        best_picks = [
            # I don't like this!
            list(self.children.keys())[action_idx]
            for action_idx in np.argsort(ucbs, stable=False)[::-1]
        ]
        return best_picks

    def back_propogate(self, value_d: list[int]):
        """Propogate the value

        Only effects this node if the player_id matches; one tree for both
        players means that the calculation values belong only to the player
        who made the turn.

        Args:
            value_d (_type_): _description_
            player_id (_type_): _description_
        """

        self.visit_count += 1
        if self.parent:
            if not (self.state.next_automated):
                self.value_estimate += value_d[self.player_id]
            self.parent.back_propogate(value_d)

    @classmethod
    def init_table(Cls, node_store: NodeStore):
        pass


class RootNode(Node):
    def __init__(self, state: GameState, game_class: callable):
        super().__init__(0, 255, state.copy(), game_class, None, True)
        self._visit_count = 1
        self._value_estimate = 0

    @property
    def visit_count(self):
        return self._visit_count

    @visit_count.setter
    def visit_count(self, value):
        self._visit_count = value

    @property
    def parent_node_visit_count(self):
        return self.visit_count

    @property
    def value_estimate(self):
        return self._value_estimate

    @value_estimate.setter
    def value_estimate(self, value):
        self._value_estimate = value
