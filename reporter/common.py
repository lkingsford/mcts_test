from reporter.report import Report, ActionEntry


class FirstPlayerAdvantage(Report):
    def __init__(self):
        self.first_player_won = 0
        self.game_count = 0
        pass

    def ingest(self, play_report: list[ActionEntry]):
        winner = play_report[-1].state["winner"]
        first_player = next(
            (turn for turn in play_report if turn.player_id is not None)
        ).player_id
        self.game_count += 1
        if first_player == winner:
            self.first_player_won += 1

    def report(self) -> str:
        return f"First player advantage: {self.first_player_won / self.game_count}"
