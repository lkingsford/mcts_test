from abc import ABC, abstractmethod, abstractproperty
import copy
import sqlite3
import typing


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

    @abstractproperty
    def previous_actions(self) -> list[typing.Union[int, tuple[int, ...]]]:
        pass

    @property
    def next_automated(self) -> bool:
        return False

    @property
    def copy(self) -> "GameState":
        # Slwo, shold be overwritten
        return copy.deepcopy(self)


GameStateType = typing.TypeVar("GameStateType", bound=GameState, covariant=True)
