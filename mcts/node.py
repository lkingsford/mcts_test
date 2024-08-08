import logging
from typing import Optional
import math
import pickle
import numpy as np
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
        player_id: int,
        action: int,
        state: GameState,
        parent: Optional["Node"],
        value_estimate: float,
        visit_count: int,
        leaf: bool,
    ):
        self.action = action
        self.parent = parent
        self.value_estimate = value_estimate
        self.visit_count = visit_count
        self.hash = state.hash
        self.player_id = player_id
        self.state = state
        self.leaf = leaf
        self._constant = None
        self.children: dict[int, "Node"] = {}
        self.child_visit_count = np.zeros(state.max_action_count())
        self.child_value = np.zeros(state.max_action_count())

    def add_child(self, action: int, state: GameState):
        self.children[action] = Node(
            player_id=state.player_id,
            action=action,
            state=state,
            parent=self,
            value_estimate=0,
            visit_count=0,
            leaf=True,
        )
        self.leaf = False

    @property
    def value_estimate(self):
        return self.parent.child_value[self.action]

    @value_estimate.setter
    def value_estimate(self, value):
        self.parent.child_value[self.action] = value

    @property
    def visit_count(self):
        return self.parent.child_visit_count[self.action]

    @visit_count.setter
    def visit_count(self, value):
        self.parent.child_visit_count[self.action] = value

    @property
    def parent_node_visit_count(self):
        return self.parent.visit_count

    def child_ucb(self, constant):
        q = self.child_value / (1 + self.child_visit_count)
        u = np.sqrt(np.log(self.parent_node_visit_count) / (1 + self.child_visit_count))
        return q + u

    def best_pick(self, constant, permitted_actions) -> list[int]:
        ucbs = self.child_ucb(constant)
        LOGGER.debug("Best pick from: %s", (ucbs.tolist()))
        # Not sure how fast this list comprehension is
        return [
            action
            for action in np.argsort(self.child_ucb(constant))[::-1]
            if action in permitted_actions
        ]

    def back_propogate(self, value_d: list[int]):
        """Propogate the value

        Only effects this node if the player_id matches; one tree for both
        players means that the calculation values belong only to the player
        who made the turn.

        Args:
            value_d (_type_): _description_
            player_id (_type_): _description_
        """

        self.value_estimate += value_d[self.player_id]
        self.visit_count += 1
        if self.parent:
            self.parent.back_propogate(value_d)

    @classmethod
    def init_table(Cls, node_store: NodeStore):
        pass


class RootNode(Node):
    def __init__(self, state: GameState):
        super().__init__(0, 255, state, None, 0, 0, True)
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
