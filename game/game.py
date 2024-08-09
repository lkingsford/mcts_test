from abc import ABC, abstractmethod
from typing import Optional
import typing
from game.game_state import GameState


class Game(ABC):
    @abstractmethod
    def act(self, column) -> "GameState":
        pass

    @classmethod
    @abstractmethod
    def from_state(cls, state: GameState) -> "Game":
        pass

    @classmethod
    @abstractmethod
    def max_action_count(cls) -> int:
        pass


GameType = typing.TypeVar("GameType", bound=Game, covariant=True)
