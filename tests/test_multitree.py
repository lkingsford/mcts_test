import pytest
from mcts.multi_tree import MultiTree


@pytest.mark.parametrize(
    "permitted_actions, process_output, expected_result",
    [
        (
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            [
                (
                    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
                    [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                    0,
                ),
                (
                    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
                    [0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                    0,
                ),
            ],
            1,
        ),
        (
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            [
                (
                    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
                    [0.0, 0.5, 0.5, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                    0,
                ),
                (
                    (5, 6, 7, 8, 9, 0, 1, 2, 3, 4),
                    [1.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.5, 0.0, 0.0],
                    0,
                ),
            ],
            2,
        ),
        (
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            [
                (
                    (0, 1, 2, 3, 4, 6, 7, 8, 9),
                    [0.0, 0.5, 0.5, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                    0,
                ),
                (
                    (5, 6, 7, 8, 9, 0, 1, 2, 3, 4),
                    [1.0, 0.0, 0.5, 0.0, 0.0, 0, 0.0, 0.5, 0.0, 0.0],
                    0,
                ),
            ],
            2,
        ),
    ],
    ids=[
        "All actions represented in order",
        "Actions in each group different order",
        "PermittedAction missing from list",
    ],
)
def test_best_action(permitted_actions, process_output, expected_result):
    assert MultiTree.best_action(permitted_actions, process_output) == expected_result
