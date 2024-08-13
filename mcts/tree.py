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
MAX_SELECTION_DEPTH = 5000


class Tree:
    def __init__(
        self,
        filename: Optional[str],
        game_state_class: GameStateType,
        game_class: GameType,
        initial_state: game.game_state.GameState,
        iterations: int = 1000,
        constant: float = 1.4142135623730951,
        reward_model: Optional[callable] = None,
        slow_mode: bool = False,
        unload_after_play: bool = False,
    ):
        self.filename = filename
        self.constant = constant
        self.iterations = iterations
        self.player_count = initial_state.player_count
        self.total_iterations = 0
        self.total_select_inspections = 0
        self.slow_mode = slow_mode
        self.unload_after_play = unload_after_play
        self.game_state_class = game_state_class
        self.game_class = game_class
        self.reward_model = reward_model or Tree.RewardModels.reward_model_binary
        self._actions_unloaded = 0

        # Used for other threadabilith
        self.count_conn = None

        self.filename = filename
        if filename and os.path.exists(filename):
            self.node_store = NodeStore.from_disk(filename)
            self.root = self.node_store.root
        else:
            self.root = RootNode(initial_state, game_class)
            if filename:
                self.node_store = NodeStore(self.root)

        self.expansion(self.root)

    def new_root(self, state: game.game_state.GameState) -> RootNode:
        self.root = RootNode(state, self.game_class)
        self.expansion(self.root)
        self._actions_unloaded = 0
        return self.root

    def get_node(self, state: game.game_state.GameState) -> Node:
        # Slow for late game
        node = self.root
        for action in state.previous_actions[self._actions_unloaded :]:
            if node.leaf:
                # Risk with lower iterations
                return node
            node = node.children.get(action)
        return node

    def reroot(self, node):
        if node is self.root:
            return
        LOGGER.debug("Rerooting")

        visit_count = node.visit_count
        value_estimate = node.value_estimate

        temp_node = node
        self._actions_unloaded += 1
        while temp_node.parent and temp_node.parent is not self.root:
            self._actions_unloaded += 1
            temp_node = temp_node.parent

        # Oh - this is _bad_. I should not be doing this.
        # But... it's also actually kind of elegant, if brittle.
        node.__class__ = RootNode
        # OK - dragons are passed by.
        node.visit_count = visit_count
        # parent_node_visit_count is set by visit_count too
        node._value_estimate = value_estimate
        if node.parent:
            node._parent_state = node.parent.state
        node.parent = None

        self.root = node

    def act(self, state: game.game_state.GameState) -> int:
        current_action_node = self.get_node(state)
        if self.unload_after_play:
            self.reroot(current_action_node)

        self.expansion(current_action_node)

        iteration = 0

        while iteration < self.iterations:
            iteration += 1
            self.total_iterations += 1
            LOGGER.debug("---------------------")
            LOGGER.debug("Iteration %d", iteration)
            LOGGER.debug("## Selection")
            path_to_selected_node = self.selection(current_action_node)
            if len(path_to_selected_node) > 0:
                node = path_to_selected_node[-1]
                self.expansion(node)
                self.play_out(path_to_selected_node)

        best_pick = current_action_node.best_pick(
            self.constant, state.permitted_actions
        )
        return best_pick[0]

    def selection(self, node: "Node") -> list["Node"]:
        LOGGER.debug("Selection checking %s ", str(node.action))
        self.total_select_inspections += 1
        path = [node]
        if self.slow_mode:
            backtrace_node = node
            while backtrace_node.parent:
                backtrace_node = backtrace_node.parent
                path.insert(0, backtrace_node)
        for _ in range(MAX_SELECTION_DEPTH):
            order = node.best_pick(self.constant, node.state.permitted_actions)
            for action in order:
                node_to_check = node.children.get(action)
                if node_to_check:
                    if node_to_check.leaf:
                        path.append(node_to_check)
                        return path
                    else:
                        node = node_to_check
                        path.append(node)
                        break
        LOGGER.warning("Failed to select within MAX_SELECTION_DEPTH")
        return path

    def expansion(self, node: "Node"):
        # Create nodes for all legal actions
        LOGGER.debug("## Expansion")
        LOGGER.debug("Expanding node %s", str(node.action))
        state = node.state
        if node.child_visit_count is None:
            node.child_visit_count = np.zeros(len(state.permitted_actions))
        if node.child_value is None:
            node.child_value = np.zeros(len(state.permitted_actions))
        for action in state.permitted_actions:
            if action in node.children:
                continue
            node.add_child(action)

        node.leaf = False

    def play_out(self, path_to_node: list["Node"]):
        LOGGER.debug("## Play Out")
        node = path_to_node[-1]
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

        reward = self.reward_model(state)
        node.leaf = False
        node.back_propogate(path_to_node, reward)

    def node_count(self):
        # Creates a new conn, because it's not thread safe
        return self.node_store.count()

    def to_disk(self):
        if self.filename:

            self.node_store.to_disk(self.filename)

    class RewardModels:
        @staticmethod
        def reward_model_binary(state: game.game_state.GameState) -> list[float]:
            player_count = state.player_count
            if state.winner == -1:
                raise ValueError("No valid reward - game not over")
            if state.winner == -2:
                # Draw
                reward = [0] * player_count
            else:
                reward = [-1] * player_count
                reward[state.winner] = 1
            return reward
