import numpy as np
from mon2y import Node, Child
from mon2y.node import ActResponse


def test_back_propogate_one_player():
    """Test that a value back propogates through when one player. Also tests action != index."""
    root = Node(None, -1, None, "State")
    child_1 = Child(1, 1, "State 1")
    root.expansion([child_1])
    child_1_node = root.get_child(1)
    child_2 = Child(2, 1, "State 2")
    child_1_node.expansion([child_2])
    child_2_node = child_1_node.get_child(2)
    child_2_node.back_propogate(np.array([0, 1]))

    assert child_1_node.visit_count == 1
    assert child_2_node.visit_count == 1
    assert child_1_node.value_estimate == 1
    assert child_2_node.value_estimate == 1


def test_back_propogate_multiple_player():
    """Test that value back propogates through other players without changing them, but effects current player."""
    root = Node(None, -1, None, "State")
    child_1 = Child(1, 1, "State 1")
    root.expansion([child_1])
    child_1_node = root.get_child(1)
    child_2 = Child(2, 0, "State 2")
    child_1_node.expansion([child_2])
    child_2_node = child_1_node.get_child(2)
    child_3 = Child(3, 1, "State 3")
    child_2_node.expansion([child_3])
    child_3_node = child_2_node.get_child(3)
    child_3_node.back_propogate(np.array([0, 1, 0]))

    assert child_1_node.visit_count == 1
    assert child_2_node.visit_count == 1
    assert child_3_node.visit_count == 1
    assert child_1_node.value_estimate == 1
    assert child_2_node.value_estimate == 0
    assert child_3_node.value_estimate == 1


def test_play_out():
    """Test that play out keeps running the action -> result function until there's a reward"""

    def sample_act(action, state):
        return ActResponse(
            [1, 2, 3], state + action, 0, np.array([1]) if state + action > 10 else None
        )

    root = Node(0, -1, None, 1)
    assert root.play_out(sample_act) == np.array([1])
