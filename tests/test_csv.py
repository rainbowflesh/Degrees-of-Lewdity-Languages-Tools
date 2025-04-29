import asyncio
from src.formatter import Formatter
from asyncio.log import logger


def test_trim_csv_version():
    logger.debug("Testing trim_csv_key")
    c = Formatter(r"tests/test_data")
    c.trim_csv_key()
    c.sort_csv()
