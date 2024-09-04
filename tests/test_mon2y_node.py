import numpy as np
from mon2y import Node

from mon2y.node import ActResponse


def sample_act(output_permitted_actions, action, state):
    """Fake "Game" that adds numbers, and returns a result if greater than 10"""
    return ActResponse(
        output_permitted_actions,
        state + action,
        (state + action) % 2,
        np.array([1, 0]) if state + action > 10 else None,
    )


default_sample_act = lambda action, state: sample_act([1, 2, 3], action, state)


def test_back_propogate_one_player():
    """Test that a value back propogates through when one player. Also tests action != index."""
    root = Node(0, -1, None, None)
    root.expansion((lambda action, state: sample_act([2], action, state)), 1)
    child_1_node = root.get_child(2)
    child_1_node.expansion((lambda action, state: sample_act([2], action, state)))
    child_2_node = child_1_node.get_child(2)
    child_2_node.back_propogate(np.array([0, 1]))

    assert child_1_node.visit_count == 1
    assert child_2_node.visit_count == 1
    assert child_1_node.value_estimate == 1
    assert child_2_node.value_estimate == 1


def test_back_propogate_multiple_player():
    """Test that value back propogates through other players without changing them, but effects current player."""
    add_one_act = lambda action, state: sample_act([1], action, state)
    root = Node(0, -1, None)
    root.expansion(add_one_act, 1)
    child_1_node = root.get_child(1)
    child_1_node.expansion(add_one_act)
    child_2_node = child_1_node.get_child(1)
    child_2_node.expansion(add_one_act)
    child_3_node = child_2_node.get_child(1)
    child_3_node.back_propogate(np.array([0, 1]))

    assert child_1_node.visit_count == 1
    assert child_2_node.visit_count == 1
    assert child_3_node.visit_count == 1
    assert child_1_node.value_estimate == 1
    assert child_2_node.value_estimate == 0
    assert child_3_node.value_estimate == 1


def test_play_out():
    """Test that play out keeps running the action -> result function until there's a reward"""

    root = Node(0, -1, None, 1)
    root.override_parent_state(0)
    result = root.play_out(lambda action, state: sample_act([1, 2, 3], action, state))
    assert len(result) == 2
    assert result[0] == 1
    assert result[1] == 0


def test_expansion_fully_explored():
    """Test that if all children fully explored, the node is fully explored"""

    root = Node(0, -1, None, 8)
    root.expansion(
        default_sample_act,
        8,
    )
    root.get_child(1).expansion(lambda action, state: sample_act([4], action, state))
    root.get_child(1).get_child(4).expansion(default_sample_act)
    root.get_child(2).expansion(lambda action, state: sample_act([3], action, state))
    root.get_child(2).get_child(3).expansion(default_sample_act)
    root.get_child(3).expansion(default_sample_act)
    assert root.fully_explored


def test_expansion_not_fully_explored():
    """Test that if not all children fully explored, the node is not fully explored"""

    root = Node(0, -1, None, 8)
    root.expansion(default_sample_act, 8)
    root.get_child(1).expansion(default_sample_act)
    assert not root.fully_explored


def test_selection_unvisited():
    """Test that where a node is unvisited, it's selected"""
    #
    #          Root
    #          /  \
    #          A   B
    #              |
    #              C
    # A has been visited. B has not been visited. C is a leaf and should be selected.

    root = Node(0, -1, None, 0)
    root.expansion((lambda action, state: sample_act([1, 2], action, state)), 0)
    result = root.get_child(1).play_out(default_sample_act)
    root.get_child(1).back_propogate(result)
    root.get_child(2).expansion((lambda action, state: sample_act([1], action, state)))
    expected = root.get_child(2).get_child(1)
    selected = root.selection()
    assert selected == expected
