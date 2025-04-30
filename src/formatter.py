from loguru import logger
from src.io_helper import IOHelper
import re
import csv
from pathlib import Path
from typing import List


"""
    Formatter is a helper class for reading and sorting CSV files.
    It provides methods to read all CSV files from a specified directory and its subdirectories,
    and to sort the CSV files by numeric ID in ascending order.
    Useful to format chaotic zh-hans translation files.
"""


class Formatter:
    def __init__(self, csv_files_path: Path):
        self.csv_files_path = csv_files_path
        self.io_helper = IOHelper()

        # 提前编译正则表达式以提高性能
        self.id_patterns = {
            "triple_quotes": re.compile(r'""".*?(\d+)[^0-9]*'),
            "quotes": re.compile(r'".*?(\d+)[^0-9]*'),
            "underscore": re.compile(r".*?(\d+)_"),
            "comma": re.compile(r".*?(\d+),"),
            "plain_number": re.compile(r".*?(\d+)"),
        }
        self.quote_one_pattern = re.compile(r'["\'].*?1.*?["\']')

    def read_csv(self) -> List[str]:
        """Read all CSV files from the specified directory and its subdirectories."""
        return self.io_helper.read_files(self.csv_files_path, ".csv", recursive=True)

    def sort_csv(self):
        """Sort CSV files by numeric ID in ascending order."""
        csv_files = self.read_csv()
        if not csv_files:
            logger.warning("No CSV files to sort")
            return

        for csv_file in csv_files:
            try:
                self._sort_single_csv(csv_file)
            except Exception as e:
                logger.error(
                    f"Error sorting CSV file {csv_file}: {str(e)}", exc_info=True
                )

    def _sort_single_csv(self, csv_file: str):
        """排序单个CSV文件"""
        # Read the CSV file
        with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            rows = list(reader)

        if not rows:
            logger.warning(f"Nothing to change in {csv_file}, skipping")
            return

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
        - remove column 2 if it contains "1\"\"\"
        """
        csv_files = self.read_csv()
        if not csv_files:
            logger.warning("No CSV files to trim, skipping")
            return

        for csv_file in csv_files:
            try:
                self._trim_single_csv(csv_file)
            except Exception as e:
                logger.error(
                    f"Error trimming CSV file {csv_file}: {str(e)}", exc_info=True
                )

    def _trim_single_csv(self, csv_file: str) -> None:
        """处理单个CSV文件的ID列和其他清理工作"""
        # Read the CSV file
        with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Process each row
        processed_data = []
        for row in rows:
            # Skip rows without a key in the first column
            if not row or not row[0] or row[0].strip() == "":
                logger.warning(f"Skipping row with no key: {row}")
                continue

            # Apply trimming to the first column
            if row[0]:
                original = row[0]
                row[0] = self._extract_numeric_id(row[0])

                # Final check - if it's not a pure number after all our efforts, skip the row
                if not row[0].isdigit():
                    logger.warning(
                        f"Could not extract numeric ID from '{original}', skipping row"
                    )
                    continue

            # Process special case for column 2
            if len(row) > 3:
                if self._should_remove_column2(row[1]):
                    logger.info(f"Removing column 2 with content: {repr(row[1])}")
                    row.pop(1)

            processed_data.append(row)

        # Write processed data back to file
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(processed_data)

        logger.info(
            f"Successfully trimmed CSV file: {csv_file} ({len(rows)} rows to {len(processed_data)} rows)"
        )

    def _extract_numeric_id(self, raw_id: str) -> str:
        """从各种格式的ID中提取纯数字ID"""
        # 按顺序尝试各种模式
        if '"""' in raw_id:
            match = self.id_patterns["triple_quotes"].search(raw_id)
            if match:
                return match.group(1)

        # Handle patterns with quotes
        elif raw_id.startswith('"'):
            match = self.id_patterns["quotes"].search(raw_id)
            if match:
                return match.group(1)

        # Handle patterns with underscores
        elif "_" in raw_id:
            match = self.id_patterns["underscore"].search(raw_id)
            if match:
                return match.group(1)

        # Handle patterns with commas
        elif "," in raw_id:
            match = self.id_patterns["comma"].search(raw_id)
            if match:
                return match.group(1)

        # Handle patterns with just numbers and potential spaces/non-UTF8 chars
        else:
            match = self.id_patterns["plain_number"].search(raw_id)
            if match:
                return match.group(1)

        return raw_id  # 如果没有匹配，返回原始ID

    def _should_remove_column2(self, col_content: str) -> bool:
        """判断是否应该移除第二列"""
        # 特别针对 "1""" 格式的检测
        # 在CSV解析后，可能会变为1"，因为双引号被转义了
        common_patterns = ['1"', '2"', '"1""', '1"""', '"1"""', '"2""', '2"""', '"2"""']

        if col_content in common_patterns:
            return True

        if "1" in col_content and '"' in col_content:
            return True

        if self.quote_one_pattern.search(col_content):
            return True

        return False
