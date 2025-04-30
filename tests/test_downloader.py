from dotenv import dotenv_values
from loguru import logger
from src.downloader import Downloader

_env = dotenv_values(".env.test")


def test_download():
    d = Downloader(_env)
    r = d.download_dol_zh_hans()
    d.extract_download(r, "dicts/cache/paratranz")
    logger.info(f"result {r}")
