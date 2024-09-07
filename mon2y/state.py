from typing import Protocol, Hashable


class State(Protocol, Hashable):
    def copy(self): ...
    def loggable(self) -> dict:
        # Naive implementation, but something
        return {k: v for k, v in self.__dict__.items()}
