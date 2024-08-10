from dataclasses import dataclass
import typing
from typing import Optional
import os
import random
import logging
import numpy as np
import game.game_state
import game.game
from game.game_state import GameStateType
from game.game import GameType
from mcts.node import Node, NodeStore, RootNode


LOGGER = logging.getLogger(__name__)


class Tree:
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
            self.root = RootNode(initial_state, game_class)
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
        self.expansion(current_action_node)

        iteration = 0

        while iteration < self.iterations:
            iteration += 1
            self.total_iterations += 1
            LOGGER.debug("---------------------")
            LOGGER.debug("Iteration %d", iteration)
            LOGGER.debug("## Selection")
            node = self.selection(current_action_node)
            if node:
                self.expansion(node)
                self.play_out(node)

        best_pick = current_action_node.best_pick(
            self.constant, state.permitted_actions
        )
        return best_pick[0]

    def selection(self, node: "Node") -> Optional["Node"]:
        LOGGER.debug("Selection checking %s ", str(node.action))
        self.total_select_inspections += 1

        order = node.best_pick(self.constant, node.state.permitted_actions)

        for action in order:
            node_to_check = node.children[action]
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
        LOGGER.debug("Expanding node %s", str(node.action))
        state = node.state
        for action in state.permitted_actions:
            if action in node.children:
                continue
            node.add_child(action)

        node.leaf = False

    def play_out(self, node: "Node"):
        LOGGER.debug("## Play Out")
        state = node.state
        game = self.game_class.from_state(state)
        while state.winner == -1:
            # TODO: Generalize Action Selection so can make not just random
            action = random.choice(state.permitted_actions)
            LOGGER.debug("Action: %s", str(action))
            if state.next_automated:
                state = game.apply_non_player_acts(action)
            else:
                state = game.act(action)

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
