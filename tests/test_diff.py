import pandas as pd
import os
from pathlib import Path
import csv

from src.differentiator import Differentiator


def test_diff():
    # Create an instance of the class
    diff_helper = Differentiator()
    # Call the instance method
    diff_helper.create_diff()


def test_count_diff_rows():
    diff_helper = Differentiator(
        Path("dicts/translated/zh-Hans/utf8/"),
        Path("dicts/raw/dolp"),
        Path("dicts/diff/dolp"),
    )
    diff_helper.count_diff_rows()
