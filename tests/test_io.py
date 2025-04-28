from pathlib import Path
from typing import List

from loguru import logger

from src.io_helper import IOHelper


def test_read_twee() -> List[str]:
    """Read all .twee files from the specified directory."""
    directory_path = Path("tests/test_data")
    recursive = True
    io_helper = IOHelper()
    logger.debug(io_helper.read_files(directory_path, ".twee", recursive))


def test_read_js() -> List[str]:
    """Read all .js files from the specified directory."""
    directory_path = Path("tests/test_data")
    recursive = True
    io_helper = IOHelper()
    logger.debug(io_helper.read_files(directory_path, ".js", recursive))


def test_read_csv() -> List[str]:
    """Read all .csv files from the specified directory."""
    directory_path = Path("tests/test_data")
    recursive = True
    io_helper = IOHelper()
    logger.debug(io_helper.read_files(directory_path, ".csv", recursive))
