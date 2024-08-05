from abc import ABC, abstractmethod, abstractproperty
import sqlite3


class GameState(ABC):
    @abstractmethod
    def save_state(self, cursor: sqlite3.Cursor) -> int:
        pass

    @classmethod
    @abstractmethod
    def load_state(cls, cursor: sqlite3.Cursor, state_id: int) -> "GameState":
        pass

    @classmethod
    @abstractmethod
    def create_state_table(cls, cursor: sqlite3.Cursor):
        pass

    @abstractmethod
    def hash(self) -> str:
        pass

    @abstractproperty
    def player_id(self) -> int:
        pass

    @abstractproperty
    def permitted_actions(self) -> list[int]:
        pass

    @abstractproperty
    def winner(self) -> int:
        pass
