import sqlite3
from dataclasses import dataclass
from typing import Optional


@dataclass
class GameState:
    next_player_id: int
    last_player_id: int
    board: list[list[int]]
    winner: int
    actions: list[int]

    def save_state(self, conn: sqlite3.Connection) -> int:
        board_serialized = bytes([cell for row in self.board for cell in row])
        conn.execute(
            """ INSERT INTO state
                (next_player_id, last_player_id, board, winner, actions)
                VALUES (?, ?, ?, ?, ?)
            """,
            (
                self.next_player_id,
                self.last_player_id,
                (board_serialized),
                self.winner,
                bytes(self.actions),
            ),
        )
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    @classmethod
    def load_state(cls, conn: sqlite3.Connection, state_id: int) -> "GameState":
        row = conn.execute("SELECT * FROM state WHERE id = ?", (state_id,)).fetchone()

        board_from_row = [list(row[3 + ix * 8 : 3 + (ix + 1) * 8]) for ix in range(8)]

        return cls(
            row[1],
            row[2],
            board_from_row,
            row[4],
            list(row[5]),
        )


class Game:
    def __init__(self, state: Optional[GameState] = None) -> None:
        if not (state):
            self.initialize_game()
        else:
            self.state = state

    def initialize_game(self) -> GameState:
        self.finished = False
        self.state: GameState = GameState(
            1, -1, [[-1 for _ in range(8)] for _ in range(8)], -1, list(range(8))
        )
        return self.state

    def act(self, column) -> GameState:
        board = self.state.board
        for row in reversed(board):
            if row[column] == -1:
                row[column] = self.state.next_player_id
                break

        self.state.last_player_id = self.state.next_player_id
        self.state.next_player_id = (self.state.next_player_id + 1) % 2

        self.state.actions = [ix for ix in range(8) if board[0][ix] == -1]

        # Check horizontal win
        for row in board:
            for ix in range(0, 4):
                winner = row[ix] == row[ix + 1] == row[ix + 2] == row[ix + 3] != -1
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
                    != -1
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
                    != -1
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
                    != -1
                )
                if winner:
                    self.state.winner = board[iy][ix]
                    return self.state

        stalemate = not (any([any([cell == -1 for cell in row]) for row in board]))

        if stalemate:
            self.state.winner = -2

        return self.state

    def debug_print(self):
        for row in self.state.board:
            print("".join([str(column) if column >= 0 else "." for column in row]))
        print()

    @classmethod
    def create_state_table(cls, conn: sqlite3.Connection):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS state (
                id INTEGER PRIMARY KEY,
                next_player_id INTEGER,
                last_player_id INTEGER,
                board BLOB,
                winner INTEGER,
                actions BLOB
            )
            """
        )
        conn.commit()
