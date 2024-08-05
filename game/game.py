from abc import ABC, abstractmethod
from typing import Optional
from game.game_state import GameState


class Game(ABC):
    @abstractmethod
    def act(self, column) -> "GameState":
        pass

    @classmethod
    @abstractmethod
    def from_state(cls, state: GameState) -> "Game":
        pass
