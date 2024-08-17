"""Collate reports for a game into maybe useful data"""

import argparse
import importlib.util
import json
import os
import reporter.report


def get_reports(reports) -> list[tuple[str, reporter.report.Report]]:
    return_reports = []
    for report_path in reports:
        module_path, class_name = report_path.split(":")
        spec = importlib.util.spec_from_file_location(
            f"module.{class_name}", module_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        found_class = getattr(module, class_name)
        assert issubclass(
            found_class, reporter.report.Report
        ), f"{class_name} is not a subclass of Report"
        return_reports.append((module_path, found_class()))
    return return_reports


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", help="Folder to collate")
    parser.add_argument("reports", help="Reports to collate", nargs="+")
    args = parser.parse_args()

    reports_to_run = get_reports(args.reports)

    for file in os.listdir(args.folder):
        if file.endswith(".json"):
            with open(os.path.join(args.folder, file)) as f:
                raw_play_report = json.load(f)
                for report in reports_to_run:
                    play_report = [
                        reporter.report.ActionEntry(*entry) for entry in raw_play_report
                    ]
                    report[1].ingest(play_report)

    for report in reports_to_run:
        print(f"# {report[0]}")
        print(report[1].report())
        print("---\n")


if __name__ == "__main__":
    main()
