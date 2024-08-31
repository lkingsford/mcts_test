from typing import Any
from reporter.report import ActionEntry, Report


class IpoPurchaseAdvantage(Report):
    def __init__(self):
        self.winner_purchased: dict[str, int] = {}
        self.game_count = 0

    def ingest(self, play_report: list[ActionEntry]):
        winner = play_report[-1].state["winner"]
        self.game_count += 1
        ipo_auctions = [
            i
            for i in play_report
            if i.memo
            and "Auction" in i.memo
            and i.memo["Auction"]["Started By"] == "IPO"
        ]
        for auction in ipo_auctions:
            assert auction.memo
            if auction.memo["Auction"]["Winner"] == winner:
                stock = auction.memo["Auction"]["Company"]
                if stock in self.winner_purchased:
                    self.winner_purchased[stock] += 1
                else:
                    self.winner_purchased[stock] = 1

    def report(self) -> str:
        result = []
        for k, v in self.winner_purchased.items():
            result.append(f"{k}: {v/self.game_count}")
        return "\n".join(result)


class OverallEndGameReasons(Report):
    def __init__(self) -> None:
        self.end_game_reason: dict[str, int] = {}
        self.game_count = 0

    def ingest(self, play_report: list[ActionEntry]):
        self.game_count += 1
        for entry in play_report:
            if entry.memo and entry.memo.get("End Game"):
                if entry.memo["End Game"]["Reason"] in self.end_game_reason:
                    self.end_game_reason[entry.memo["End Game"]["Reason"]] += 1
                else:
                    self.end_game_reason[entry.memo["End Game"]["Reason"]] = 1

    def report(self) -> str:
        result = []
        for k, v in sorted(
            self.end_game_reason.items(), key=lambda x: x[1], reverse=True
        ):
            result.append(f"{k}: {v/self.game_count}")
        return "\n".join(result)


class OverallEndGameLastDividend(Report):
    def __init__(self) -> None:
        self.last_dividend_was: dict[str, int] = {}
        self.game_count = 0

    def ingest(self, play_report: list[ActionEntry]):
        self.game_count += 1
        for entry in play_report:
            if entry.memo and entry.memo.get("End Game"):
                if entry.memo["End Game"]["Last Dividend"] in self.last_dividend_was:
                    self.last_dividend_was[entry.memo["End Game"]["Last Dividend"]] += 1
                else:
                    self.last_dividend_was[entry.memo["End Game"]["Last Dividend"]] = 1

    def report(self) -> str:
        result = []
        for k, v in sorted(
            self.last_dividend_was.items(), key=lambda x: x[1], reverse=True
        ):
            result.append(f"{k}: {v/self.game_count}")
        return "\n".join(result)


class EndGameReasonAndLastDividend(Report):
    def __init__(self) -> None:
        self.last_dividend_and_reason_was: dict[tuple[str, str], int] = {}
        self.game_count = 0

    def ingest(self, play_report: list[ActionEntry]):
        self.game_count += 1
        for entry in play_report:
            if entry.memo and entry.memo.get("End Game"):
                if (
                    entry.memo["End Game"]["Last Dividend"],
                    entry.memo["End Game"]["Reason"],
                ) in self.last_dividend_and_reason_was:
                    self.last_dividend_and_reason_was[
                        (
                            entry.memo["End Game"]["Last Dividend"],
                            entry.memo["End Game"]["Reason"],
                        )
                    ] += 1
                else:
                    self.last_dividend_and_reason_was[
                        (
                            entry.memo["End Game"]["Last Dividend"],
                            entry.memo["End Game"]["Reason"],
                        )
                    ] = 1

    def report(self) -> str:
        result = []
        for k, v in sorted(
            self.last_dividend_and_reason_was.items(), key=lambda x: x[1], reverse=True
        ):
            result.append(f"{k[0]}: {k[1]}: {v/self.game_count}")
        return "\n".join(result)


class MostCommonTrackBuild(Report):
    def __init__(self) -> None:
        self.track: dict[str, int] = {}
        self.game_count = 0

    def ingest(self, play_report: list[ActionEntry]):
        self.game_count += 1
        for entry in play_report:
            if entry.memo and entry.memo.get("Build track"):
                track = tuple(entry.memo["Build track"]["location"])
                if track in self.track:
                    self.track[(track)] += 1
                else:
                    self.track[(track)] = 1

    def report(self) -> str:
        result = []
        for k, v in sorted(self.track.items(), key=lambda x: x[1], reverse=True):
            result.append(f"{k}: {v/self.game_count}")
        return "\n".join(result)
