from src.io_helper import IOHelper
import logging
import re
import csv
from pathlib import Path
from typing import List

logger = logging.getLogger("CSV Helper")

"""
    CSVHelper is a helper class for reading and sorting CSV files.
    It provides methods to read all CSV files from a specified directory and its subdirectories,
    and to sort the CSV files by numeric ID in ascending order.
    Useful to format chaotic zh-hans translation files.
"""


class CSVHelper:

    def __init__(self, csv_files_path: Path):
        self.csv_files_path = csv_files_path
        self.io_helper = IOHelper()
        logger.info(f"Initialized CSVHelper with path: {self.csv_files_path}")

    def read_csv(self) -> List[str]:
        """Read all CSV files from the specified directory and its subdirectories."""
        logger.info("Using IOHelper to read CSV files")
        return self.io_helper.read_csv(self.csv_files_path, recursive=True)

    def sort_csv(self):
        """Sort CSV files by numeric ID in ascending order."""
        logger.info("Starting sort_csv")
        csv_files = self.read_csv()
        if not csv_files:
            logger.warning("No CSV files to sort")
            return

        for csv_file in csv_files:
            try:
                # Read the CSV file
                with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.reader(f)
                    rows = list(reader)

                logger.debug(f"Open {csv_file}")

                if not rows:
                    logger.debug(f"Nothing to change in {csv_file}, skipping")
                    continue

                # Sort by numeric ID (first column)
                sorted_data = sorted(
                    rows,
                    key=lambda x: int(x[0]) if x and x[0].isdigit() else float("inf"),
                )

                # Write sorted data back to file
                with open(csv_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerows(sorted_data)

                logger.info(f"Successfully sorted CSV file: {csv_file}")

            except Exception as e:
                logger.error(
                    f"Error sorting CSV file {csv_file}: {str(e)}", exc_info=True
                )

    def trim_csv_key(self) -> None:
        """
        Process CSV files to clean up IDs in the first column.
        - trim \"""    1" / \"""  1" -> 1
        - trim "﻿""  1" -> 1
        - trim 40_5_3_2| -> 40
        - trim 40_5_3_2|_5_3_2| -> 40
        - trim "  239,1" -> 239
        - trim rows with no key in first column
        - handle non-UTF8 characters + ID patterns
        - handle IDs with leading spaces
        """
        # TODO: use regex
        logger.info("Starting trim_csv_key")
        csv_files = self.read_csv()
        if not csv_files:
            logger.warning("No CSV files to trim")
            return

        for csv_file in csv_files:
            try:
                # Read the CSV file
                with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.reader(f)
                    rows = list(reader)

                logger.debug(f"Open {csv_file}")

                if not rows:
                    logger.debug(f"Nothing to change in {csv_file}, skipping")
                    continue

                # Process each row
                processed_data = []
                for row in rows:
                    # Skip rows without a key in the first column
                    if not row or not row[0] or row[0].strip() == "":
                        logger.debug(f"Skipping row with no key: {row}")
                        continue

                    # Apply trimming to the first column
                    if row[0]:
                        original = row[0]

                        # Handle triple quotes pattern (with or without non-UTF8 chars)
                        if '"""' in row[0]:
                            match = re.search(r'""".*?(\d+)[^0-9]*', row[0])
                            if match:
                                row[0] = match.group(1)

                        # Handle patterns with quotes
                        elif row[0].startswith('"'):
                            match = re.search(r'".*?(\d+)[^0-9]*', row[0])
                            if match:
                                row[0] = match.group(1)

                        # Handle patterns with underscores (possibly with non-UTF8 chars)
                        elif "_" in row[0]:
                            # Extract numbers before first _
                            match = re.search(r".*?(\d+)_", row[0])
                            if match:
                                row[0] = match.group(1)

                        # Handle patterns with commas
                        elif "," in row[0]:
                            # Extract number part
                            match = re.search(r".*?(\d+),", row[0])
                            if match:
                                row[0] = match.group(1)

                        # Handle patterns with just numbers and potential spaces/non-UTF8 chars
                        else:
                            # Try to extract just the numbers
                            match = re.search(r".*?(\d+)", row[0])
                            if match:
                                row[0] = match.group(1)

                        # Final check - if it's not a pure number after all our efforts, skip the row
                        if not row[0].isdigit():
                            logger.debug(
                                f"Could not extract numeric ID from '{original}', skipping row"
                            )
                            continue

                    processed_data.append(row)

                # Write processed data back to file
                with open(csv_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerows(processed_data)

                logger.info(
                    f"Successfully trimmed CSV file: {csv_file} ({len(rows)} rows to {len(processed_data)} rows)"
                )

            except Exception as e:
                logger.error(
                    f"Error trimming CSV file {csv_file}: {str(e)}", exc_info=True
                )
