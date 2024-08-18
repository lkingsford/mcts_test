"""Tests that the definitely correct actions are returned.

Slightly fragile and lucky - but unavoidably."""

import pytest
import numpy as np
import c4.game
import mcts.tree
import mcts.multi_tree


def c4_about_to_win_state():
    """Player is one turn from winning

    Returns tuple of state and required action"""
    state = c4.game.GameState(
        next_player_id=1,
        last_player_id=0,
        board=np.array(
            [
                [0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 2, 0, 0, 0, 0, 0],
                [0, 0, 2, 1, 1, 0, 0, 0],
                [0, 1, 2, 1, 1, 0, 0, 0],
            ]
        ),
        winner=-1,
        permitted_actions=range(8),
        previous_actions=[255],
    )
    return state, 2


def c4_must_prevent_loss_state():
    """
    Generate a Connect Four game state where the next player (player with ID 1) must
    prevent the opponent (player with ID 2) from winning.

    Returns:
        tuple: A tuple containing the generated game state and the column index where the
        next player must place their token to prevent the opponent from winning.
    """
    state = c4.game.GameState(
        board=np.array(
            [
                [0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 2, 0, 2, 0, 0, 0],
                [0, 0, 2, 1, 1, 0, 0, 0],
                [0, 1, 2, 1, 1, 0, 0, 0],
            ]
        ),
        next_player_id=0,
        last_player_id=1,
        winner=-1,
        permitted_actions=range(8),
        previous_actions=[255],
    )
    return state, 2


def c4_some_actions_not_available_state():
    """
    Generate a Connect Four game state where the next player (player with ID 1) must
    make a winning turn, but some columns are full.

    Returns:
        tuple: A tuple containing the generated game state and the column index where the
        next player must place their token to win
    """
    state = c4.game.GameState(
        board=np.array(
            [
                [1, 2, 1, 0, 0, 1, 0, 0],
                [2, 1, 2, 0, 0, 2, 0, 0],
                [2, 1, 2, 0, 0, 1, 2, 0],
                [1, 1, 2, 0, 1, 2, 2, 0],
                [1, 2, 1, 0, 1, 2, 2, 0],
                [1, 1, 2, 2, 2, 1, 1, 0],
                [2, 2, 2, 1, 1, 2, 1, 0],
                [2, 1, 2, 1, 1, 2, 1, 0],
            ]
        ),
        next_player_id=0,
        last_player_id=1,
        winner=-1,
        permitted_actions=range(8),
        previous_actions=[255],
    )
    return state, 6


@pytest.fixture(
    scope="module",
    params=[None, None, None],
    ids=["C4: About to win", "C4: Lose unless", "C4: Some actions not available"],
)
def c4_states():
    yield c4_about_to_win_state()
    yield c4_must_prevent_loss_state()
    yield c4_some_actions_not_available_state()


def test_act_tree(c4_states):
    state, correct_action = c4_states
    tree = mcts.tree.Tree(None, c4.game.GameState, c4.game.Game, state)
    tree.root.leaf = True
    action = tree.act(state)
    assert action == correct_action


def test_act_multitree(c4_states):
    state, correct_action = c4_states
    tree = mcts.tree.Tree(None, c4.game.GameState, c4.game.Game, state)
    tree.root.leaf = True
    action = tree.act(state)
    assert action == correct_action
