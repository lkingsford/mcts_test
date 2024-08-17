from reporter.report import Report, ActionEntry


class FirstPlayerAdvantage(Report):
    def __init__(self):
        pass

    def ingest(self, play_report: list[ActionEntry]):
        pass

    def report(self) -> str:
        return "FirstPlayerAdvantage"
