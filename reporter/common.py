from typing import Hashable
from reporter.report import Report
from mon2y import ActionLog


class FirstPlayerAdvantage(Report):
    def __init__(self):
        self.first_player_won = 0
        self.game_count = 0
        pass

    def ingest(self, reward: list[float], play_report: list[ActionLog]):
        super().ingest(reward, play_report)
        first_player = next(
            (turn for turn in play_report if turn.player_id is not None)
        ).player_id
        self.game_count += 1
        if first_player == self.winner:
            self.first_player_won += 1

    def report(self) -> str:
        return f"First player advantage: {self.first_player_won / self.game_count}"


class BestFirstTurn(Report):
    def __init__(self):
        self.episodes_for_each_first_turn: dict[Hashable, int] = {}
        self.episodes_wins_for_each_first_turn: dict[Hashable, int] = {}
        self.game_count = 0

    def ingest(self, reward: list[float], play_report: list[ActionLog]):
        super().ingest(reward, play_report)
        first_turn = next(turn for turn in play_report if turn.player_id is not None)
        first_player = first_turn.player_id
        first_action = first_turn.action
        self.game_count += 1
        if first_action not in self.episodes_for_each_first_turn:
            self.episodes_for_each_first_turn[first_action] = 0
            self.episodes_wins_for_each_first_turn[first_action] = 0
        self.episodes_for_each_first_turn[first_action] += 1
        self.episodes_wins_for_each_first_turn[first_action] += (
            self.winner == first_player
        )

    def report(self) -> str:
        for key, value in self.episodes_for_each_first_turn.items():
            print(
                f"- {key}: {value} - {self.episodes_wins_for_each_first_turn[key] / value}"
            )
