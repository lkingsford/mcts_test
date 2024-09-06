"""Various connect 4 states that test expected behaviour of the engine"""

import pytest
import numpy as np
import mon2y.node
import c4.m2game
import mon2y.train


def c4_about_to_win_state():
    """Player is one turn from winning

    Returns tuple of state, required action, and permitted actions"""
    state = c4.m2game.c4State(
        next_player=1,
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
    )
    return state, 2, list(range(8))


def c4_must_prevent_loss_state():
    """
    Generate a Connect Four game state where the next player must
    prevent the opponent from winning.

    Returns:
        tuple: A tuple containing the generated game state and the column index where the
        next player must place their token to prevent the opponent from winning, and
        permitted actions
    """
    state = c4.m2game.c4State(
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
        next_player=0,
    )
    return state, 2, list(range(8))


def c4_some_actions_not_available_state():
    """
    Generate a Connect Four game state where the next player (player with ID 1) must
    make a winning turn, but some columns are full.

    Returns:
        tuple: A tuple containing the generated game state and the column index where the
        next player must place their token to win and permitted_actions
    """
    state = c4.m2game.c4State(
        board=np.array(
            [
                [1, 2, 1, 0, 0, 1, 0, 0],
                [2, 1, 2, 0, 0, 2, 0, 0],
                [2, 1, 2, 0, 0, 1, 2, 0],
                [1, 1, 2, 0, 1, 2, 2, 0],
                [1, 2, 1, 1, 1, 2, 2, 0],
                [1, 1, 2, 2, 2, 1, 1, 0],
                [2, 2, 2, 1, 1, 2, 1, 0],
                [2, 1, 2, 1, 1, 2, 1, 0],
            ]
        ),
        next_player=1,
    )
    return state, 6, [3, 4, 6, 7]


@pytest.mark.parametrize(
    "state,correct_action,permitted_actions",
    [
        c4_about_to_win_state(),
        c4_must_prevent_loss_state(),
        c4_some_actions_not_available_state(),
    ],
    ids=["C4: About to win", "C4: Lose unless", "C4: Some actions not available"],
)
def test_calculate_next_action(state, correct_action, permitted_actions):
    node = mon2y.Node(
        state=state, permitted_actions=permitted_actions, next_player=state.next_player
    )
    action = mon2y.calculate_next_action(node, c4.m2game.act, 1000)
    assert action == correct_action


def test_play_c4_episode():
    """Just play through an episode of connect 4"""
    mon2y.episode(c4.m2game.initialize_game, c4.m2game.act, 25)
