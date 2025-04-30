import asyncio
from src.dumper import Dumper


def test_dump_sets():
    dumper = Dumper()
    asyncio.run(dumper.dump_sets())
    asyncio.run(dumper.dump_variables())
