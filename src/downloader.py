import os
from pysmartdl2 import SmartDL

""" Downloader """
class Downloader:
    def __init__(self):
        self._paratranz_token = os.getenv("PARATRANZ_TOKEN")
        self._paratranz_url = "https://paratranz.cn/api/v2/projects/1/languages"
        self._translates_zh_Hans_dir = "lib/dicts/translated/zh-Hans"

    def fetch_translates_from_paratranz(self):
        result = SmartDL(self._paratranz_url, self._translates_zh_Hans_dir).start()
        downloads_path = result.get_dest()
        return downloads_path
