from dataclasses import dataclass
import typing
from typing import Optional
import os
import random
import logging
import game.game_state
import game.game
from mcts.node import Node, NodeStore, RootNode


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
    ):
        self.filename = filename
        self.constant = constant
        self.loss_estimate = -1
        self.win_estimate = 1
        self.draw_estimate = 0
        self.iterations = iterations
        self.player_count = player_count
        self.total_iterations = 0
        self.total_select_inspections = 0

        self.game_state_class = game_state_class
        self.game_class = game_class

        # Used for other threadabilith
        self.count_conn = None

        if os.path.exists(filename):
            self.node_store = NodeStore.from_disk(filename)
            self.root = self.node_store.root
        else:
            self.root = RootNode(initial_state)
            self.node_store = NodeStore(self.root)
        self.expansion(self.root)

    def get_node(self, state: game.game_state.GameState) -> Node:
        # Slow for late game
        node = self.root
        for action in state.previous_actions:
            node = node.children.get(action)
        return node

    def act(self, state: game.game_state.GameState) -> int:
        current_action_node = self.get_node(state)

        iteration = 0

        def unexplored_first_level_nodes(node):
            return [
                action
                for action, visit_count in enumerate(node.child_visit_count)
                if visit_count == 0
            ]

        while iteration < self.iterations or any(
            [node for node in unexplored_first_level_nodes(current_action_node)]
        ):
            iteration += 1
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

        children = current_action_node.children.values()
        potential_actions = [
            child for child in children if child.action in state.permitted_actions
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
        self.total_select_inspections += 1

        nodes = list(checking_node.children.values())
        nodes.sort(key=lambda n: n.ucb(self.constant), reverse=True)
        LOGGER.debug(
            "Node order: %s",
            ",".join([f"{n.hash}: {n.ucb(self.constant)}" for n in nodes]),
        )

        for node_to_check in nodes:
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
            node.add_child(action, new_state)

        node.leaf = False

    def play_out(self, node: "Node"):
        LOGGER.debug("## Play Out")
        state = node.state
        game = self.game_class.from_state(state)
        while state.winner == -1:
            # TODO: Generalize Action Selection so can make not just random
            action = random.choice(state.permitted_actions)
            LOGGER.debug("Action: %d", action)
            state = game.act(action)

        if node.parent:
            # TODO: This shouldn't be done here. Constructor maybe?
            assert node.parent

        reward = [0] * self.player_count
        if state.winner == -2:
            # Draw
            reward = [self.draw_estimate] * self.player_count
        else:
            reward = [self.loss_estimate] * self.player_count
            reward[state.winner] = self.win_estimate

        node.leaf = False
        node.back_propogate(reward)

    def node_count(self):
        # Creates a new conn, because it's not thread safe
        return self.node_store.count()

    def to_disk(self):
        self.node_store.to_disk(self.filename)
