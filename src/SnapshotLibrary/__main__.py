"""Command line: ``python -m SnapshotLibrary unused <output dir> [--delete]``."""

from __future__ import annotations

import argparse
import os
import shutil
import sys

from . import unused as unused_module


def _relative(path) -> str:
    try:
        return os.path.relpath(path)
    except ValueError:
        return str(path)


def unused_command(arguments) -> int:
    result = unused_module.report(arguments.output_directory)
    if result is None:
        print(
            f"No snapshot usage records found below '{arguments.output_directory}'. "
            "Pass the output directory of a run that used SnapshotLibrary."
        )
        return 2
    print(f"Checked {len(result.checked)} suite(s).")
    if result.not_checked:
        print(
            f"Not checked, because not all tests ran and passed: {len(result.not_checked)} suite(s)."
        )
        for source in result.not_checked:
            print(f"  {_relative(source)}")
    if result.clean:
        print("No unused snapshots.")
        return 0
    if result.unused:
        print(f"Unused snapshots: {len(result.unused)}")
        for path in result.unused:
            print(f"  {_relative(path)}")
    if result.orphan_directories:
        print(f"Snapshot directories without a suite file: {len(result.orphan_directories)}")
        for path in result.orphan_directories:
            print(f"  {_relative(path)}")
    if arguments.delete:
        for path in result.unused:
            path.unlink()
        for path in result.orphan_directories:
            shutil.rmtree(path)
        print("Deleted.")
        return 0
    print("Delete them, or run again with --delete.")
    return 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m SnapshotLibrary")
    commands = parser.add_subparsers(dest="command", required=True)
    unused = commands.add_parser(
        "unused",
        help="report snapshot files that no test used in a finished run",
        description=(
            "Reads the usage records of a finished robot or pabot run and lists snapshot "
            "files no test used. Exit code 0: nothing unused, 1: unused snapshots found, "
            "2: no records found."
        ),
    )
    unused.add_argument("output_directory", help="the --outputdir of the run")
    unused.add_argument("--delete", action="store_true", help="delete what is reported")
    unused.set_defaults(handler=unused_command)
    arguments = parser.parse_args(argv)
    return arguments.handler(arguments)


if __name__ == "__main__":
    sys.exit(main())
