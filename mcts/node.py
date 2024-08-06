import logging
from typing import Optional
import math
from game.game_state import GameState

LOGGER = logging.getLogger(__name__)


class NodeStore:
    def __init__(self):
        self._store: dict[str, "Node"] = dict()
        # Not ideal - but this is a first take
        self._children_store: dict[str, set[str]] = dict()

    def load(self, hash: str) -> Optional["Node"]:
        return self._store[hash]

    def load_all_children(self, node: "Node") -> list["Node"]:
        return [self._store[child] for child in self._children_store[node.hash]]

    def save(self, node: "Node"):
        self._store[node.hash] = node
        if node.parent_hash not in self._children_store:
            self._children_store[node.parent_hash] = set()
        if node.parent_hash != None:
            self._children_store[node.parent_hash].add(node.hash)

    def count(self) -> int:
        return len(self._store)


class Node:
    def __init__(
        self,
        hash: str,
        player_id: int,
        action: int,
        state: GameState,
        parent_node_visit_count: int,
        parent_hash: Optional[str],
        value_estimate: float,
        visit_count: int,
        leaf: bool = True,
    ):
        self.hash = hash
        self.player_id = player_id
        self.action = action
        self.state = state
        self.parent_hash = parent_hash
        self._value_estimate = value_estimate
        self._visit_count = visit_count
        self._parent_node_visit_count = parent_node_visit_count
        self._ucb = None
        self._constant = None
        self.leaf = leaf

    @property
    def value_estimate(self):
        return self._value_estimate

    @value_estimate.setter
    def value_estimate(self, value):
        self._value_estimate = value
        self._ucb = None

    @property
    def visit_count(self):
        return self._visit_count

    @visit_count.setter
    def visit_count(self, value):
        self._visit_count = value
        self._ucb = None

    @property
    def parent_node_visit_count(self):
        return self._parent_node_visit_count

    @parent_node_visit_count.setter
    def parent_node_visit_count(self, value):
        self._parent_node_visit_count = value
        self._ucb = None

    def ucb(self, constant):
        # Caching, because potentially expensive to compute
        if self._ucb is None or self._constant != constant:
            try:
                self._ucb = self.value_estimate + constant * math.sqrt(
                    math.log(max(1, self.parent_node_visit_count)) / self.visit_count
                )
            except ZeroDivisionError:
                self._ucb = float("inf")
        self._constant = constant
        return self._ucb

    def back_propogate(self, value_d: list[int], node_store: NodeStore):
        """Propogate the value

        Only effects this node if the player_id matches; one tree for both
        players means that the calculation values belong only to the player
        who made the turn.

        Args:
            value_d (_type_): _description_
            player_id (_type_): _description_
            cursor (sqlite3.Cursor): _description_
        """

        self.value_estimate += value_d[self.player_id]
        self.visit_count += 1
        if self.parent_hash:
            parent = Node.load(node_store, self.parent_hash)
            assert parent
            parent.back_propogate(value_d, node_store)

            # last_action_node = self.last_action_node(cursor, self.player_id)
            self.parent_node_visit_count = parent.visit_count

        self.save(node_store)

    @classmethod
    def init_table(Cls, node_store: NodeStore):
        pass

    def save(self, node_store: NodeStore):
        node_store.save(self)

        if self.parent_hash:
            parent = Node.load(node_store, self.parent_hash)
            assert parent
            parent.leaf = False
            parent.save(node_store)

    @classmethod
    def load(cls, node_store: NodeStore, hash: str) -> Optional["Node"]:
        return node_store.load(hash)

    def load_children(self, node_store: NodeStore) -> list["Node"]:
        return node_store.load_all_children(self)
