import pandas as pd
import os
from pathlib import Path
import csv

from src.diff_helper import DiffHelper


def test_diff():
    # Create an instance of the class
    diff_helper = DiffHelper()
    # Call the instance method
    diff_helper.create_diff()


def test_count_diff_rows():
    diff_helper = DiffHelper(
        Path("dicts/translated/zh-Hans/utf8/"),
        Path("dicts/raw/dolp"),
        Path("dicts/diff/dolp"),
    )
    diff_helper.count_diff_rows()
