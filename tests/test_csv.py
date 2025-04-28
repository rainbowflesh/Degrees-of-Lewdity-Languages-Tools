import asyncio
from src.csv_helper import CSVHelper


def test_trim_csv_version():
    c = CSVHelper(r"dicts/translated/zh-Hans/dol")
    asyncio.run(c.trim_csv_async())
    asyncio.run(c.sort_csv_async())
