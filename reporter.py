"""Collate reports for a game into maybe useful data"""

"""Collate reports for a game into maybe useful data"""

import argparse
import importlib.util
import json
import logging
import os
import reporter.report


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.CRITICAL)
# create formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
# add ch to logger
LOGGER.addHandler(ch)


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
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity of logging",
    )
    args = parser.parse_args()

    LOGGER.setLevel(logging.CRITICAL - 10 * args.verbose)

    reports_to_run = get_reports(args.reports)

    for file in os.listdir(args.folder):
        if file.endswith(".json"):
            LOGGER.info(f"Loading {file}")
            with open(os.path.join(args.folder, file)) as f:
                try:
                    raw_play_report = json.load(f)
                    for report in reports_to_run:
                        play_report = [
                            reporter.report.ActionEntry(*entry)
                            for entry in raw_play_report
                        ]
                        report[1].ingest(play_report)
                except json.decoder.JSONDecodeError:
                    LOGGER.warning(f"Failed to parse {file}")

    for report in reports_to_run:
        LOGGER.info(f"Running {report[0]}")
        print(f"# {report[0]}")
        print(report[1].report())
        print("---\n")


if __name__ == "__main__":
    main()
