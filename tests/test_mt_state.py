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


def use_qwen(str):
    pass  # dummy


def process_translation(
    padding_file: str, translates_file: str, start_idx: int, mode: str, save: bool
) -> None:
    with open(padding_file, "r", encoding="utf-8") as input_file:
        reader = csv.reader(input_file)

        if save:
            os.makedirs(os.path.dirname(translates_file), exist_ok=True)
            with open(
                translates_file, mode, encoding="utf-8", newline=""
            ) as output_file:
                writer = csv.writer(output_file)
                for row_idx, row in enumerate(reader):
                    if row_idx < start_idx:
                        continue  # skip already translated rows
                    if len(row) < 2:
                        continue  # skip invalid row
                    input_text = row[1]
                    translation = use_qwen(input_text)
                    row.append(translation)
                    writer.writerow(row)
                    logger.info(
                        f"Writeing translation for row {row_idx}: {translation} in {translates_file}"
                    )
        else:
            for row_idx, row in enumerate(reader):
                if row_idx < start_idx:
                    continue  # skip already translated rows
                if len(row) < 2:
                    continue  # skip invalid row
                input_text = row[1]
                translation = use_qwen(input_text)
                logger.info(translation)


def create_translates(_save_to_file, _input_files_path, _output_files_path) -> None:
    if _save_to_file:
        os.makedirs(_output_files_path, exist_ok=True)

    for dirpath, _, filenames in os.walk(_input_files_path):
        for filename in filenames:
            if not filename.endswith(".csv"):
                continue  # ignore non-csv files

            padding_file = os.path.join(dirpath, filename)
            padding_file_relpath = os.path.relpath(
                padding_file, _input_files_path
            )  # this path use to write files with same structure

            translates_file = os.path.join(_output_files_path, padding_file_relpath)

            if not os.path.exists(translates_file):
                logger.info(
                    f"File {padding_file} contain no translates, start a new run"
                )

                os.makedirs(os.path.dirname(translates_file), exist_ok=True)

                process_translation(
                    padding_file,
                    translates_file,
                    start_idx=0,
                    mode="w",
                    save=_save_to_file,
                )
                continue

            padding_total_rows = get_valid_row_count(padding_file)
            translated_total_rows = get_valid_row_count(translates_file)

            if translated_total_rows >= padding_total_rows:
                logger.info(f"File {padding_file} translation is finished, skipping")
                continue  # already fully translated

            logger.info(
                f"File {padding_file} contain unfinished translates, continue from last line {translated_total_rows}"
            )
            process_translation(
                padding_file,
                translates_file,
                start_idx=translated_total_rows,
                mode="a",
                save=_save_to_file,
            )


def test_mt_state():

    # padding_translate_path = r"tests/test_data/diff/dolp"
    # mt_translate_path = r"tests/test_data/diff/mt_translates"
    padding_translate_path = r"dicts/diff/dolp"
    mt_translate_path = r"dicts/diff/mt_translates"

    # scan_for_translation(padding_translate_path, mt_translate_path)

    create_translates(False, padding_translate_path, mt_translate_path)
