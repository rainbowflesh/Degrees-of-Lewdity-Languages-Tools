from pathlib import Path
from typing import List, Optional, Union, Dict, Any, Tuple
import csv
import os
import shutil

from loguru import logger


class IOHelper:
    def __init__(self):
        pass

    def read_files(
        self, directory_path: Path, file_ext: str, recursive: bool = True
    ) -> List[str]:
        """
        Read all files with the specified extension from the given directory.

        Args:
            directory_path: Path to the directory to search in
            file_ext: File extension to search for (e.g., ".csv", ".js", ".twee")
            recursive: Whether to search in subdirectories (default: True)

        Returns:
            List of files obsolete path obj like [WindowsPath('foo.baa')]
        """
        files_list = []
        try:
            # Check if path exists and is a directory
            if not directory_path.exists():
                logger.error(f"Path does not exist: {directory_path}")
                return []

            if not directory_path.is_dir():
                logger.error(f"Path is not a directory: {directory_path}")
                return []

            logger.info(f"Reading {file_ext} files from: {directory_path}")

            # Make sure file_ext starts with a dot
            if not file_ext.startswith("."):
                file_ext = f".{file_ext}"

            # Use rglob for recursive search, glob for non-recursive
            pattern = f"*{file_ext}"
            if recursive:
                files_list = [
                    str(file_path) for file_path in directory_path.rglob(pattern)
                ]
            else:
                files_list = [
                    str(file_path) for file_path in directory_path.glob(pattern)
                ]

            files_count = len(files_list)
            search_scope = (
                f"{directory_path} and its subdirectories"
                if recursive
                else directory_path
            )

            if files_count == 0:
                logger.warning(f"No {file_ext} files found in: {search_scope}")
            else:
                logger.info(f"Found {files_count} {file_ext} files in: {search_scope}")

            return files_list
        except Exception as e:
            logger.error(f"Error reading {file_ext} files: {str(e)}")
            return []

    def ensure_dir_exists(self, directory_path: Path) -> bool:
        """
        Ensure directory exists, create if not

        Args:
            directory_path: the path

        Returns:
            bool: invoke result
        """
        try:
            os.makedirs(directory_path, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {directory_path}: {str(e)}")
            return False

    def copy_file(self, source: Path, destination: Path) -> bool:
        """
        Copy file and ensure destination directory exists

        Args:
            source: source file path
            destination: destination file path

        Returns:
            bool: invoke result
        """
        try:
            self.ensure_dir_exists(destination.parent)
            shutil.copy2(source, destination)
            return True
        except Exception as e:
            logger.error(
                f"Failed to copy file from {source} to {destination}: {str(e)}"
            )
            return False

    def read_csv(
        self, file_path: Path, with_header: bool = False
    ) -> Tuple[List[List[str]], bool]:
        """
        Read CSV file and return data rows

        Args:
            file_path: CSV file path
            with_header: whether to include header row

        Returns:
            Tuple[List[List[str]], bool]: (CSV data rows list, invoke result)
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                rows = list(reader)

            if with_header and rows:
                header = rows[0]
                data = rows[1:]
                return data, True
            return rows, True
        except Exception as e:
            logger.error(f"Failed to read CSV file {file_path}: {str(e)}")
            return [], False

    def write_csv(
        self, file_path: Path, rows: List[List[str]], header: Optional[List[str]] = None
    ) -> bool:
        """
        Write data to CSV file

        Args:
            file_path: target CSV file path
            rows: data rows to write
            header: optional header row

        Returns:
            bool: invoke result
        """
        try:
            self.ensure_dir_exists(file_path.parent)

            with open(file_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                if header:
                    writer.writerow(header)
                writer.writerows(rows)
            return True
        except Exception as e:
            logger.error(f"Failed to write CSV file {file_path}: {str(e)}")
            return False

    def append_csv(self, file_path: Path, rows: List[List[str]]) -> bool:
        """
        Append data to CSV file

        Args:
            file_path: target CSV file path
            rows: data rows to append

        Returns:
            bool: invoke result
        """
        try:
            self.ensure_dir_exists(file_path.parent)

            with open(file_path, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerows(rows)
            return True
        except Exception as e:
            logger.error(f"Failed to append to CSV file {file_path}: {str(e)}")
            return False

    def count_csv_rows(self, file_path: Path) -> int:
        """Count the number of rows in a CSV file"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                return sum(1 for _ in reader)
        except Exception as e:
            logger.error(f"Failed to count CSV file {file_path}: {str(e)}")
            return 0

    def count_csv_row_translations(
        self, file_path: str, check_translation: bool = False
    ) -> int:
        """count csv row with optional check_translation"""
        count = 0
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or len(row) < 2:
                    continue  # skip invalid rows
                if check_translation:
                    if len(row) >= 3 and row[2].strip():  # translates
                        count += 1
                else:
                    if row[1].strip():  # raw
                        count += 1
        return count

    def truncate_csv_newline(self, file_path: str, n_lines: int):
        with open(file_path, "r", encoding="utf-8") as f:
            rows = list(csv.reader(f))[:n_lines]
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

    def safe_csv_writer(self, file_path: str, mode: str, save_to_file: bool = False):
        """Create CSV writer if needed"""

        class NullWriter:
            def writerow(self, _):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        if not save_to_file:
            return NullWriter()

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        file = open(file_path, mode, encoding="utf-8", newline="")
        writer = csv.writer(file)

        class FileWriterContext:
            def __init__(self, file, writer):
                self.file = file
                self.writer = writer

            def __enter__(self):
                return self.writer

            def __exit__(self, exc_type, exc_val, exc_tb):
                self.file.close()

        return FileWriterContext(file, writer)

    def get_last_translated_line(self, file_path: Path) -> int:
        last_valid_row_id = -1
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3 and row[2].strip():
                    try:
                        last_valid_row_id = int(row[0])
                    except ValueError:
                        continue
        return last_valid_row_id
