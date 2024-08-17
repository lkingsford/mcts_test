from reporter.report import Report, ActionEntry


class FirstPlayerAdvantage(Report):
    def ingest(self, play_report: list[ActionEntry]):
        pass

    def report(self) -> str:
        return "FirstPlayerAdvantage"
