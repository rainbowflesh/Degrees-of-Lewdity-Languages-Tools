import json
import os
from pathlib import Path

from loguru import logger
from src.dictionary_helper import DictionaryHelper


def test_filename_list():
    dh = DictionaryHelper()
    dh.get_preprocess_files_list()
    dh.cache_preprocess_files_list()
