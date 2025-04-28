import os
from pysmartdl2 import SmartDL

""" Downloader """
class Downloader:
    def __init__(self):
        self._paratranz_url = "https://paratranz.cn/api/projects/4780/artifacts/download"
        self._paratranz_header = {"Authorization" : os.getenv("PARATRANZ_TOKEN")}
        self._translates_zh_hans_dir = r"dicts/translated/zh-Hans"

    def get_translates_from_paratranz(self):
        result = SmartDL(urls=self._paratranz_url, dest=self._translates_zh_hans_dir,request_args=self._paratranz_header).start()
        return result
