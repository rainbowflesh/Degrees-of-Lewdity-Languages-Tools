import pandas as pd
import os
from pathlib import Path
import csv

from src.diff_helper import DiffHelper


def test_diff():
    # Create an instance of the class
    diff_helper = DiffHelper()
    # Call the instance method
    diff_helper.process_directories()
