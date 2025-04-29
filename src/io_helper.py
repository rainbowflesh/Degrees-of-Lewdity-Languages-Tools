import logging
from pathlib import Path
from typing import List
import csv

logger = logging.getLogger("IO Helper")


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
            List of file paths (as strings)
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
            if recursive:
                pattern = f"*{file_ext}"
                for file_path in directory_path.rglob(pattern):
                    files_list.append(str(file_path))
                    logger.info(f"Found {file_ext} file: {file_path}")
            else:
                pattern = f"*{file_ext}"
                for file_path in directory_path.glob(pattern):
                    files_list.append(str(file_path))
                    logger.info(f"Found {file_ext} file: {file_path}")

            if not files_list:
                search_scope = (
                    f"{directory_path} and its subdirectories"
                    if recursive
                    else directory_path
                )
                logger.warning(f"No {file_ext} files found in: {search_scope}")

            return files_list
        except Exception as e:
            logger.error(f"Error reading {file_ext} files: {str(e)}")
            return []
