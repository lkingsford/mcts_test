from abc import ABC, abstractmethod
from typing import Optional
import typing
from game.game_state import GameState


class Game(ABC):
    @abstractmethod
    def act(self, action) -> "GameState":
        pass

    @classmethod
    @abstractmethod
    def from_state(cls, state: GameState) -> "Game":
        pass

    @classmethod
    @abstractmethod
    def max_action_count(cls) -> int:
        pass

    def non_player_act(self) -> tuple[tuple[int, ...], "GameState"]:
        """
        Perform a non-player action on the current state
        """
        if "_state" in self.__dict__:
            return (tuple(), getattr(self, "_state"))
        else:
            raise NotImplementedError

    def apply_non_player_acts(self, actions: tuple[int, ...]) -> "GameState":
        """
        Apply a sequence of non-player actions to the current state
        """
        if "_state" in self.__dict__:
            return getattr(self, "_state")
        else:
            raise NotImplementedError


GameType = typing.TypeVar("GameType", bound=Game, covariant=True)
