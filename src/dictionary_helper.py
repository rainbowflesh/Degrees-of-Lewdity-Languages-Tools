import json
import os
from pathlib import Path

from loguru import logger
from src.io_helper import IOHelper


class DictionaryHelper:
    def __init__(self, game_root: Path = Path(r"lib/degrees-of-lewdity/game")):
        self._game_root = game_root
        self._io_helper = IOHelper()
        with open(r"dicts/blacklists.json", "r", encoding="utf-8") as fp:
            self._blacklists: list = json.load(fp)["blacklist"]

        with open(r"dicts/whitelists.json", "r", encoding="utf-8") as fp:
            self._whitelists: list = json.load(fp)["whitelist"]

    def get_preprocess_files_list(self):
        filecount = 0
        self.preprocess_files_list = []
        for root, _, file_list in os.walk(self._game_root):
            rel_path = Path(root).relative_to(self._game_root)
            for file in file_list:
                file_path = rel_path / file
                file_path_str = str(file_path).replace("/", "\\")

                if file.endswith(".twee"):
                    if file_path_str not in self._blacklists:
                        self.preprocess_files_list.append(Path(root).absolute() / file)
                        filecount += 1
                elif file.endswith(".js") and file_path_str in self._whitelists:
                    self.preprocess_files_list.append(Path(root).absolute() / file)
                    filecount += 1

        logger.info(f"##### 共获取 {filecount} 个文本文件位置 !\n")
