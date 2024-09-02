import numpy as np
from mon2y import Node
from mon2y.node import ActResponse


def sample_act(action, state):
    """Fake "Game" that adds numbers, and returns a result if greater than 10"""
    return ActResponse(
        [1, 2, 3],
        state + action,
        (state + action) % 2,
        np.array([1]) if state + action > 10 else None,
    )


def test_back_propogate_one_player():
    """Test that a value back propogates through when one player. Also tests action != index."""
    root = Node(None, -1, None, 1)
    root.expansion([2], 1, sample_act)
    child_1_node = root.get_child(2)
    child_1_node.expansion([2], 1, sample_act)
    child_2_node = child_1_node.get_child(2)
    child_2_node.back_propogate(np.array([0, 1]))

    assert child_1_node.visit_count == 1
    assert child_2_node.visit_count == 1
    assert child_1_node.value_estimate == 1
    assert child_2_node.value_estimate == 1


def test_back_propogate_multiple_player():
    """Test that value back propogates through other players without changing them, but effects current player."""
    root = Node(None, -1, None, 0)
    root.expansion([1], 1, sample_act)
    child_1_node = root.get_child(1)
    child_1_node.expansion([1], 0, sample_act)
    child_2_node = child_1_node.get_child(1)
    child_2_node.expansion([1], 1, sample_act)
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
    assert root.play_out(sample_act) == np.array([1])


def test_expansion_fully_explored():
    """Test that if all children fully explored, the node is fully explored"""

    initial_state = 10
    root = Node(initial_state, -1, None, 8)
    root.expansion([1, 2, 3], 1, sample_act)
    root.get_child(1).expansion([4], 1, sample_act)
    root.get_child(1).get_child(4).play_out(sample_act)
    root.get_child(2).expansion([1], 1, sample_act)
    root.get_child(2).play_out(sample_act)
    root.get_child(3).play_out(sample_act)
    assert root.fully_explored


def test_expansion_not_fully_explored():
    """Test that if not all children fully explored, the node is not fully explored"""

    initial_state = 10
    root = Node(initial_state, -1, None, 8)
    root.expansion([1, 2, 3], 1, sample_act)
    root.get_child(1).expansion([4], 1, sample_act)
    root.get_child(1).get_child(4).play_out(sample_act)
    root.get_child(3).play_out(sample_act)
    assert not root.fully_explored
