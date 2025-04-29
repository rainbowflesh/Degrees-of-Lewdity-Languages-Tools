import csv
import os

from loguru import logger


import os
import csv

import os
import csv


import os
import pandas as pd

import os
import pandas as pd


def get_valid_row_count(file_path):
    count = 0
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2 and row[1].strip():
                count += 1
    return count


def get_last_translated_row_id(file_path):
    last_valid_row_id = -1
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 3 and row[2].strip():
                try:
                    last_valid_row_id = int(row[0])
                except ValueError:
                    continue
    return last_valid_row_id


def scan_for_translation(padding_path, translated_path):
    for dirpath, _, filenames in os.walk(padding_path):
        for filename in filenames:
            if not filename.endswith(".csv"):
                continue

            padding_file = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(padding_file, padding_path)
            translated_file = os.path.join(translated_path, rel_path)

            padding_total_rows = get_valid_row_count(padding_file)
            if not os.path.exists(translated_file):
                print(f"{padding_file} → do new tr (no translated file)")
                continue

            translated_total_rows = get_valid_row_count(translated_file)
            last_tr_id = get_last_translated_row_id(translated_file)

            if translated_total_rows < padding_total_rows:
                print(
                    "translated_file",
                    translated_file,
                    " missing translated line: ",
                    padding_total_rows - translated_total_rows,
                )
                print("missing id", last_tr_id)


def test_mt_state():

    # padding_translate_path = r"tests/test_data/diff/dolp"
    # mt_translate_path = r"tests/test_data/diff/mt_translates"
    padding_translate_path = r"dicts/diff/dolp"
    mt_translate_path = r"dicts/diff/mt_translates"

    scan_for_translation(padding_translate_path, mt_translate_path)
