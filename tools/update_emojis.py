"""Download and filter OpenMoji data for the bundled emoji catalogue."""

import argparse
import csv
import io
import os
from pathlib import Path
import tempfile
from urllib.request import urlopen


SOURCE_URL = "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/data/openmoji.csv"
MAX_UNICODE_VERSION = (17, 0)
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "static" / "emojis.csv"


def is_included(row):
    version = row["unicode"].strip()
    if version in ("", "?"):
        return True

    version_parts = tuple(int(part) for part in version.split("."))
    return version_parts <= MAX_UNICODE_VERSION


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        help="filter a local CSV instead of downloading the current OpenMoji CSV",
    )
    args = parser.parse_args()

    if args.input:
        with args.input.open(encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            rows = [row for row in reader if is_included(row)]
            fieldnames = reader.fieldnames
    else:
        with urlopen(SOURCE_URL) as response:
            source_text = response.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(source_text, newline=""))
        rows = [row for row in reader if is_included(row)]
        fieldnames = reader.fieldnames

    if not fieldnames or "unicode" not in fieldnames:
        raise ValueError("OpenMoji CSV is missing the expected 'unicode' column")

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=OUTPUT_PATH.parent,
            delete=False,
        ) as output:
            temporary_path = Path(output.name)
            writer = csv.DictWriter(
                output, fieldnames=fieldnames, lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary_path, OUTPUT_PATH)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()

    print(f"Wrote {len(rows)} emoji catalogue entries through Unicode 17.0")


if __name__ == "__main__":
    main()
