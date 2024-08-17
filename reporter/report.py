from abc import ABC, abstractmethod
from typing import NamedTuple, Optional


class ActionEntry(NamedTuple):
    action: str
    player_id: Optional[int]
    state: dict
    memo: Optional[str]


class Report(ABC):
    @abstractmethod
    def ingest(self, play_report: list[ActionEntry]):
        pass

    @abstractmethod
    def report(self) -> str:
        pass
