import numpy as np
from mon2y import Node

from mon2y.node import ActResponse


class SampleActState:
    def __init__(self, v):
        self.v = v

    def copy(self):
        return SampleActState(self.v)


def sample_act(output_permitted_actions, state, action):
    """Fake "Game" that adds numbers, and returns a reward if greater than 10"""
    return ActResponse(
        output_permitted_actions,
        SampleActState(state.v + action),
        (state.v + action) % 2,
        np.array([1, 0]) if state.v + action > 10 else None,
    )


default_sample_act = lambda state, action: sample_act([1, 2, 3], state, action)


def test_back_propogate_one_player():
    """Test that a value back propogates through when one player. Also tests action != index."""
    root = Node(0, -1, None, SampleActState(0), permitted_actions=[2], next_player=0)
    root.expansion((lambda state, action: sample_act([2], state, action)))
    child_1_node = root.get_child(2)
    child_1_node.expansion((lambda state, action: sample_act([2], state, action)))
    child_2_node = child_1_node.get_child(2)
    child_2_node.back_propogate(np.array([1, 0]))

    assert child_1_node.visit_count == 1
    assert child_2_node.visit_count == 1
    assert child_1_node.value_estimate == 1
    assert child_2_node.value_estimate == 1


def test_back_propogate_multiple_player():
    """Test that value back propogates through other players without changing them, but effects current player."""
    add_one_act = lambda state, action: sample_act([1], state, action)
    root = Node(0, -1, None, SampleActState(1), permitted_actions=[1], next_player=1)
    root.expansion(add_one_act)
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

    root = Node(
        0, -1, None, SampleActState(1), permitted_actions=[1, 2, 3], next_player=1
    )
    result = root.play_out(lambda state, action: sample_act([1, 2, 3], state, action))
    assert len(result) == 2
    assert result[0] == 1
    assert result[1] == 0


def test_expansion_fully_explored():
    """Test that if all children fully explored, the node is fully explored"""

    root = Node(
        0, -1, None, SampleActState(8), permitted_actions=[1, 2, 3], next_player=1
    )
    root.expansion(
        default_sample_act,
    )
    root.get_child(1).expansion(lambda state, action: sample_act([4], state, action))
    root.get_child(1).get_child(4).expansion(default_sample_act)
    root.get_child(2).expansion(lambda state, action: sample_act([3], state, action))
    root.get_child(2).get_child(3).expansion(default_sample_act)
    root.get_child(3).expansion(default_sample_act)
    assert root.fully_explored


def test_expansion_not_fully_explored():
    """Test that if not all children fully explored, the node is not fully explored"""

    root = Node(
        0, -1, None, SampleActState(8), permitted_actions=[1, 2, 3], next_player=1
    )
    root.expansion(default_sample_act)
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

    root = Node(0, -1, None, SampleActState(0), permitted_actions=[1, 2], next_player=1)
    root.expansion((lambda state, action: sample_act([1, 2], state, action)))
    result = root.get_child(1).play_out(default_sample_act)
    root.get_child(1).back_propogate(result)
    root.get_child(2).expansion((lambda state, action: sample_act([1], state, action)))
    expected = root.get_child(2).get_child(1)
    selected = root.selection()
    assert selected == expected
