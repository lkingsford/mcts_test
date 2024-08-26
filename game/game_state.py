from abc import ABC, abstractmethod, abstractproperty
import copy
from hashlib import sha256
import sqlite3
import typing


class GameState(ABC):
    def hash(self) -> str:
        hash_object = sha256()
        hash_object.update(str(tuple(self.previous_actions)).encode())
        return hash_object.hexdigest()

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
    def previous_actions(self) -> list[typing.Hashable]:
        pass

    @property
    def next_automated(self) -> bool:
        return False

    def copy(self) -> "GameState":
        # Slwo, shold be overwritten
        return copy.deepcopy(self)

    @property
    def player_count(self) -> int:
        return 2

    @abstractmethod
    def loggable(self) -> dict:
        pass

    def add_action(self, action):
        if "_previous_actions" in self.__dict__:
            self._previous_actions.append(action)
        else:
            raise NotImplementedError

    @property
    def memo(self):
        if "_memo" in self.__dict__:
            return self._memo
        else:
            raise NotImplementedError


GameStateType = typing.TypeVar("GameStateType", bound=GameState, covariant=True)
