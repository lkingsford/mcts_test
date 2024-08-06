from hashlib import sha256
from dataclasses import dataclass
from typing import Optional
import logging
import game.game
import game.game_state

LOGGER = logging.getLogger(__name__)


class GameState(game.game_state.GameState):

    def __init__(
        self,
        next_player_id,
        last_player_id,
        board,
        winner,
        permitted_actions,
        previous_actions,
    ):
        self.next_player_id = next_player_id
        self.last_player_id = last_player_id
        self.board = board
        self._winner = winner
        self._permitted_actions = permitted_actions
        self.previous_actions = previous_actions

    def hash(self) -> str:
        # return sha256(bytes(self.previous_actions)).hexdigest()
        return "".join([str(action) for action in self.previous_actions])

    def copy(self) -> "GameState":
        return GameState(
            self.next_player_id,
            self.last_player_id,
            [[column for column in row] for row in self.board],
            self._winner,
            [action for action in self._permitted_actions],
            [action for action in self.previous_actions],
        )

    @property
    def player_id(self):
        return self.last_player_id

    @property
    def permitted_actions(self):
        return self._permitted_actions

    @permitted_actions.setter
    def permitted_actions(self, value):
        self._permitted_actions = value

    @property
    def winner(self):
        return self._winner

    @winner.setter
    def winner(self, value):
        self._winner = value


class Game(game.game.Game):
    def __init__(self, state: Optional[GameState] = None) -> None:
        if not (state):
            self.initialize_game()
        else:
            self.state = state.copy()

    @classmethod
    def from_state(cls, state: game.game.GameState) -> "Game":
        # Separate to allow abstract method to work
        assert isinstance(state, GameState)
        return cls(state)

    def initialize_game(self) -> GameState:
        self.finished = False
        self.state = GameState(
            1, -1, [[255 for _ in range(8)] for _ in range(8)], -1, list(range(8)), []
        )
        return self.state

    def act(self, column) -> GameState:
        self.state.previous_actions.append(column)

        board = self.state.board
        for row in reversed(board):
            if row[column] == 255:
                row[column] = self.state.next_player_id
                break

        self.state.last_player_id = self.state.next_player_id
        self.state.next_player_id = (self.state.next_player_id + 1) % 2

        self.state.permitted_actions = [ix for ix in range(8) if board[0][ix] == 255]

        # Check horizontal win
        for row in board:
            for ix in range(0, 4):
                winner = row[ix] == row[ix + 1] == row[ix + 2] == row[ix + 3] != 255
                if winner:
                    self.state.winner = row[ix]
                    return self.state

        # Check vertical win
        for iy in range(0, 5):
            for ix in range(0, 8):
                winner = (
                    board[iy][ix]
                    == board[iy + 1][ix]
                    == board[iy + 2][ix]
                    == board[iy + 3][ix]
                    != 255
                )
                if winner:
                    self.state.winner = board[iy][ix]
                    return self.state

        # Check for \ win
        for iy in range(0, 5):
            for ix in range(0, 4):
                winner = (
                    board[iy][ix]
                    == board[iy + 1][ix + 1]
                    == board[iy + 2][ix + 2]
                    == board[iy + 3][ix + 3]
                    != 255
                )
                if winner:
                    self.state.winner = board[iy][ix]
                    return self.state

        for iy in range(0, 5):
            for ix in range(4, 8):
                winner = (
                    board[iy][ix]
                    == board[iy + 1][ix - 1]
                    == board[iy + 2][ix - 2]
                    == board[iy + 3][ix - 3]
                    != 255
                )
                if winner:
                    self.state.winner = board[iy][ix]
                    return self.state

        stalemate = not (any([any([cell == 255 for cell in row]) for row in board]))

        if stalemate:
            self.state.winner = -2

        self.debug_log()

        return self.state

    def debug_print(self):
        for row in self.state.board:
            print("".join([str(column) if column != 255 else "." for column in row]))
        print()

    def debug_log(self):
        for row in self.state.board:
            LOGGER.debug(
                "".join([str(column) if column != 255 else "." for column in row])
            )
