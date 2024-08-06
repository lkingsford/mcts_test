from abc import ABC, abstractmethod, abstractproperty
import sqlite3


class GameState(ABC):

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
