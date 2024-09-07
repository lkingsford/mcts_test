"""Collate reports for a game into maybe useful data"""

import argparse
import fnmatch
import importlib.util
import inspect
import json
import logging
import os
import mon2y.action_log
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

        matching_classes = []
        for name in dir(module):
            if fnmatch.fnmatch(name, class_name):
                found_class = getattr(module, name)
                if (
                    inspect.isclass(found_class)
                    and issubclass(found_class, reporter.report.Report)
                    and found_class is not reporter.report.Report
                ):
                    matching_classes.append((name, found_class()))

        LOGGER.warning(f"No classes in {module_path} match {class_name}")
        return_reports.extend(matching_classes)
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
                            mon2y.action_log.ActionLog(*entry)
                            for entry in raw_play_report["log"]
                        ]
                        reward = raw_play_report["reward"]
                        report[1].ingest(reward, play_report)
                except json.decoder.JSONDecodeError:
                    LOGGER.warning(f"Failed to parse {file}")

    for report in reports_to_run:
        LOGGER.info(f"Running {report[0]}")
        print(f"# {report[0]}")
        print(report[1].report())
        print("---\n")


if __name__ == "__main__":
    main()
