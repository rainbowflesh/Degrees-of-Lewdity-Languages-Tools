import asyncio
from src.csv_helper import CSVHelper
from asyncio.log import logger


def test_trim_csv_version():
    logger.debug("Testing trim_csv_key")
    c = CSVHelper(r"tests/test_data")
    c.trim_csv_key()
    c.sort_csv()
