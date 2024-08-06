from dataclasses import dataclass
import sqlite3
import typing
from typing import Optional
import math
import random
import logging
import game.game_state
import game.game


LOGGER = logging.getLogger(__name__)


class Tree:

    GameStateType = typing.TypeVar(
        "GameStateType", bound=game.game_state.GameState, covariant=True
    )
    GameType = typing.TypeVar("GameType", bound=game.game.Game, covariant=True)

    def __init__(
        self,
        filename: str,
        game_state_class: GameStateType,
        game_class: GameType,
        initial_state: game.game_state.GameState,
        player_count: int = 2,
        iterations: int = 1000,
        constant: float = 1.4142135623730951,
        commit: bool = True,
    ):
        self.connection = sqlite3.connect(filename, autocommit=False)
        self.cursor = self.connection.cursor()

        self.filename = filename
        self.commit = commit
        self.constant = constant
        self.loss_estimate = -1
        self.win_estimate = 1
        self.draw_estimate = 0
        self.iterations = iterations
        self.player_count = player_count
        self.total_iterations = 0

        self.game_state_class = game_state_class
        self.game_class = game_class

        # Used for other threadabilith
        self.count_conn = None

        # Check if init'd
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        requires_init = self.cursor.fetchone() is None

        LOGGER.info("DB Connection to %s", filename)

        if requires_init:
            LOGGER.info("Initialising database")
            Node.init_table(self.cursor)
            self.game_state_class.create_state_table(self.cursor)

            self.root = self.build_state_node(initial_state, 255, None)
            self.expansion(self.root)
        else:
            root = Node.load(self.cursor, initial_state.hash())
            assert root
            self.root = root

    def act(self, current_state: game.game_state.GameState) -> int:
        current_action_node = Node.load(self.cursor, current_state.hash())
        if not current_action_node:
            LOGGER.warn("Current state not found in database")
            current_action_node = self.build_state_node(current_state, 255, self.root)
        for iteration in range(self.iterations):
            self.total_iterations += 1
            LOGGER.debug("---------------------")
            LOGGER.debug("Iteration %d", iteration)
            LOGGER.debug("## Selection")
            node = self.selection(current_action_node)
            if node and node.leaf:
                self.expansion(node)
                self.play_out(node)
            if not node:
                break
            # This could be taken out if multithreaded
            if self.commit:
                LOGGER.debug("Committing")
                self.connection.commit()

        children = current_action_node.load_children(self.cursor)
        potential_actions = [
            child
            for child in children
            if child.action in current_state.permitted_actions
        ]
        contains_255 = [n.action for n in children if n.action == 255]
        LOGGER.debug(
            "Potential actions: %s",
            ",".join(
                [f"{n.action}: {n.ucb(self.constant)}" for n in potential_actions]
            ),
        )
        # Problem appearing here - action '255' keeps appearing
        best_action = max(potential_actions, key=lambda n: n.ucb(self.constant))
        return best_action.action

    def selection(self, node: "Node") -> Optional["Node"]:
        checking_node = node
        LOGGER.debug("Selection checking %s", node.hash)

        # Reorder nodes so the order isn't always the same when there's a tie
        # ... doesn't work maybe?
        nodes = sorted(
            checking_node.load_children(self.cursor), key=lambda _: random.random()
        )
        node_order = sorted(nodes, key=lambda n: n.ucb(self.constant), reverse=True)
        LOGGER.debug(
            "Node order: %s",
            ",".join([f"{n.hash}: {n.ucb(self.constant)}" for n in node_order]),
        )

        for node_to_check in node_order:
            LOGGER.debug(
                "   Checking node %s (UCB: %s} (from %s)",
                node_to_check.hash,
                node.ucb(self.constant),
                node.hash,
            )
            if node_to_check.leaf:
                return node_to_check
            else:
                recurse_result = self.selection(node_to_check)
                if recurse_result:
                    return recurse_result

        return None

    def expansion(self, node: "Node"):
        # Create nodes for all legal actions
        LOGGER.debug("## Expansion")
        LOGGER.debug("Expanding node %s", node.hash)
        state = self.game_state_class.load_state(self.cursor, node.state_id)
        for action in state.permitted_actions:
            game = self.game_class.from_state(state)
            new_state = game.act(action)

            self.build_state_node(new_state, action, node)
            LOGGER.debug("Building node %s", new_state.hash())

        node.leaf = False
        node.save(self.cursor)

    def play_out(self, node: "Node"):
        LOGGER.debug("## Play Out")
        state = self.game_state_class.load_state(self.cursor, node.state_id)
        game = self.game_class.from_state(state)
        while state.winner == -1:
            # TODO: Generalize Action Selection so can make not just random
            action = random.choice(state.permitted_actions)
            LOGGER.debug("Action: %d", action)
            state = game.act(action)

        if node.parent_hash:
            # TODO: This shouldn't be done here. Constructor maybe?
            parent_node = Node.load(self.cursor, node.parent_hash)
            assert parent_node
            node.parent_node_visit_count = parent_node.visit_count

        reward = [0] * self.player_count
        if state.winner == -2:
            # Draw
            reward = [self.draw_estimate] * self.player_count
        else:
            reward = [self.loss_estimate] * self.player_count
            reward[state.winner] = self.win_estimate

        node.leaf = False
        node.back_propogate(reward, self.cursor)

    def build_state_node(
        self,
        new_state: game.game_state.GameState,
        action: int,
        parent_node: Optional["Node"],
    ) -> "Node":
        LOGGER.debug("### Build State Node")
        # Builds and propogates if done
        state_id = new_state.save_state(self.cursor)

        new_node = Node(
            hash=new_state.hash(),
            player_id=new_state.player_id,
            action=action,
            state_id=state_id,
            parent_hash=parent_node.hash if parent_node else None,
            value_estimate=0,
            visit_count=0,
            parent_node_visit_count=0,
            leaf=True,
        )

        new_node.save(self.cursor)
        return new_node

    def node_count(self):
        # Creates a new conn, because it's not thread safe
        self.count_conn = self.count_conn or sqlite3.connect(self.filename)
        cursor = self.count_conn.cursor()
        return cursor.execute("SELECT COUNT(*) FROM node").fetchone()[0]


class Node:
    def __init__(
        self,
        hash: str,
        player_id: int,
        action: int,
        state_id: int,
        parent_hash: Optional[str],
        value_estimate: float,
        visit_count: int,
        parent_node_visit_count: int,
        leaf: bool = True,
    ):
        self.hash = hash
        self.player_id = player_id
        self.action = action
        self.state_id = state_id
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

    def back_propogate(self, value_d: list[int], cursor: sqlite3.Cursor):
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
            parent = Node.load(cursor, self.parent_hash)
            assert parent
            parent.back_propogate(value_d, cursor)

            # last_action_node = self.last_action_node(cursor, self.player_id)
            self.parent_node_visit_count = parent.visit_count

        self.save(cursor)

    @classmethod
    def init_table(Cls, cursor: sqlite3.Cursor):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS node (
                hash TEXT PRIMARY KEY,
                player_id INTEGER,
                action INTEGER,
                state_id INTEGER,
                parent_hash TEXT,
                value_estimate REAL, 
                visit_count INTEGER,
                parent_node_visit_count INTEGER,
                leaf BOOLEAN
            )
            """
        )

    def save(self, cursor: sqlite3.Cursor):
        cursor.execute(
            """
            INSERT OR REPLACE INTO node
                (hash, player_id, action, state_id, parent_hash, value_estimate, visit_count, parent_node_visit_count, leaf)
            VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.hash,
                self.player_id,
                self.action,
                self.state_id,
                self.parent_hash,
                self.value_estimate,
                self.visit_count,
                self.parent_node_visit_count,
                self.leaf,
            ),
        )

        if self.parent_hash:
            parent = Node.load(cursor, self.parent_hash)
            assert parent
            parent.leaf = False
            parent.save(cursor)

    @classmethod
    def load(cls, cursor: sqlite3.Cursor, hash: str) -> Optional["Node"]:
        row = cursor.execute("SELECT * FROM node WHERE hash = ?", (hash,)).fetchone()
        if not row:
            return None
        return cls(
            hash=row[0],
            player_id=row[1],
            action=row[2],
            state_id=row[3],
            parent_hash=row[4],
            value_estimate=row[5],
            visit_count=row[6],
            parent_node_visit_count=row[7],
            leaf=row[8],
        )

    def load_children(self, cursor: sqlite3.Cursor) -> list["Node"]:
        rows = cursor.execute(
            "SELECT * FROM node WHERE parent_hash = ?", (self.hash,)
        ).fetchall()
        return [
            Node(
                hash=row[0],
                player_id=row[1],
                action=row[2],
                state_id=row[3],
                parent_hash=row[4],
                value_estimate=row[5],
                visit_count=row[6],
                parent_node_visit_count=row[7],
                leaf=row[8],
            )
            for row in rows
        ]
