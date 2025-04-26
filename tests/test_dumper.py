import asyncio
import logging
from src.dumper import Dumper

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("asyncio:TEST")


def test_dump_sets():
    dumper = Dumper()
    asyncio.run(dumper.dump_sets())
    asyncio.run(dumper.dump_variables())
