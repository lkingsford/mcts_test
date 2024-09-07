from abc import ABC, abstractmethod
from typing import NamedTuple, Optional
import numpy as np
from mon2y.action_log import ActionLog


class Report(ABC):
    def ingest(
        self,
        reward: list[float],
        play_report: list[ActionLog],
    ):
        self.winner = np.argmax(reward)

    @abstractmethod
    def report(self) -> str:
        pass
