from dataclasses import dataclass
import sqlite3
import typing
from typing import Optional
import math
import random
import logging
import game.game_state
import game.game
from mcts.node import Node, NodeStore


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

        self.node_store = NodeStore()

        self.root = self.build_state_node(initial_state, 255, None)
        self.expansion(self.root)

    def act(self, current_state: game.game_state.GameState) -> int:
        current_action_node = Node.load(self.node_store, current_state.hash())
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

        children = current_action_node.load_children(self.node_store)
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
            checking_node.load_children(self.node_store), key=lambda _: random.random()
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
        state = node.state
        for action in state.permitted_actions:
            game = self.game_class.from_state(state)
            new_state = game.act(action)

            self.build_state_node(new_state, action, node)
            LOGGER.debug("Building node %s", new_state.hash())

        node.leaf = False
        node.save(self.node_store)

    def play_out(self, node: "Node"):
        LOGGER.debug("## Play Out")
        state = node.state
        game = self.game_class.from_state(state)
        while state.winner == -1:
            # TODO: Generalize Action Selection so can make not just random
            action = random.choice(state.permitted_actions)
            LOGGER.debug("Action: %d", action)
            state = game.act(action)

        if node.parent_hash:
            # TODO: This shouldn't be done here. Constructor maybe?
            parent_node = Node.load(self.node_store, node.parent_hash)
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
        node.back_propogate(reward, self.node_store)

    def build_state_node(
        self,
        new_state: game.game_state.GameState,
        action: int,
        parent_node: Optional["Node"],
    ) -> "Node":
        LOGGER.debug("### Build State Node")
        # Builds and propogates if done

        new_node = Node(
            hash=new_state.hash(),
            player_id=new_state.player_id,
            action=action,
            state=new_state,
            parent_hash=parent_node.hash if parent_node else None,
            value_estimate=0,
            visit_count=0,
            parent_node_visit_count=0,
            leaf=True,
        )

        new_node.save(self.node_store)
        return new_node

    def node_count(self):
        # Creates a new conn, because it's not thread safe
        return self.node_store.count()
