import os
from typing import Any
import zipfile
from loguru import logger
from pysmartdl2 import SmartDL

""" Downloader """


class Downloader:
    def __init__(self, env: dict):
        self._env = env

    def extract_download(self, download: SmartDL, dest: str):
        logger.info(f"Extract file {download.get_dest()} to {dest}")
        with zipfile.ZipFile(download.get_dest(), "r") as zip_ref:
            zip_ref.extractall(dest)

    def download_dol_zh_hans(self) -> SmartDL:
        _paratranz_url = "https://paratranz.cn/api/projects/4780/artifacts/download"

        _token = self._env.get("PARATRANZ_API_KEY")

        _paratranz_header = {"Authorization": _token}

        _translates_zh_hans_dir = r"dicts/cache/paratranz"

        download = SmartDL(
            urls=_paratranz_url,
            dest=_translates_zh_hans_dir,
            request_args={"headers": _paratranz_header},
        )
        download.start()
        return download
