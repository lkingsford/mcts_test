import logging
import numpy as np

from mon2y.node import ActResponse
from .game import check_for_win


LOGGER = logging.getLogger(__name__)


class c4State:
    def __init__(
        self,
        next_player,
        board,
    ):
        self.next_player = next_player
        self.board = board

    def copy(self) -> "c4State":
        return c4State(
            self.next_player,
            np.array(
                [[column for column in row] for row in self.board], dtype=np.uint8
            ),
        )

    def loggable(self) -> dict:
        return {
            "board": self.board.tolist(),
        }


def initialize_game() -> ActResponse:
    return ActResponse(
        tuple(range(8)), c4State(0, np.zeros((8, 8), dtype=np.uint8)), 0, None
    )


def act(old_state: c4State, action) -> ActResponse:
    state = old_state.copy()

    board = state.board
    for row in reversed(board):
        if row[action] == 0:
            row[action] = state.next_player + 1
            break

    permitted_actions: tuple[int, ...] = tuple(
        ix for ix in range(8) if board[0][ix] == 0
    )

    winner = check_for_win(board)
    if winner == 0:
        reward = np.array([1, 0])
    elif winner == 1:
        reward = np.array([0, 1])
    elif winner == -2:
        # Stalemate - discourage with some negative reward
        reward = np.array([-0.5, -0.5])
    else:
        reward = None

    state.next_player = (state.next_player + 1) % 2

    return ActResponse(permitted_actions, state, state.next_player, reward)
