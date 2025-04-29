import os
import csv
import json
import shutil
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

from src.translator import Translator


@pytest.fixture
def temp_dirs():
    input_dir = tempfile.mkdtemp()
    output_dir = tempfile.mkdtemp()
    yield Path(input_dir), Path(output_dir)
    shutil.rmtree(input_dir)
    shutil.rmtree(output_dir)


def create_test_csv(file_path, rows):
    with open(file_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)


@patch.object(Translator, "use_qwen", return_value="translated")
@patch.object(Translator, "token_counter", return_value=10000)
def test_batch_stop_and_resume(mock_token, mock_translate, temp_dirs):
    input_dir, output_dir = temp_dirs

    # Prepare input CSV with 4 rows (token count = 10_000 each)
    test_csv = input_dir / "test.csv"
    rows = [["1", "hello"], ["2", "world"], ["3", "foo"], ["4", "bar"]]
    create_test_csv(test_csv, rows)

    # First run should process only first 3 (limit = 32_000)
    t = Translator(input_path=input_dir, output_path=output_dir, save=True)
    t.create_translates()

    # Check state.json written
    state_file = output_dir / "state.json"
    assert state_file.exists()

    with open(state_file) as f:
        state = json.load(f)
    assert state["last_file"] == "test.csv"
    assert state["last_row"] == 2  # third row (index 2)

    # Resume second run
    t = Translator(input_path=input_dir, output_path=output_dir, save=True)
    t.create_translates()

    # Check output file has all 4 rows
    output_csv = output_dir / "test.csv"
    with open(output_csv, "r", encoding="utf-8") as f:
        lines = list(csv.reader(f))
    assert len(lines) == 4
    assert lines[0][-1] == "translated"
    assert lines[3][1] == "bar"

    # Clean state after finish
    assert not os.path.exists(output_dir / "state.json")


@patch.object(Translator, "use_qwen", return_value="translated")
@patch.object(Translator, "token_counter", return_value=1)
def test_reset_state(temp_dirs, mock_token, mock_translate):
    input_dir, output_dir = temp_dirs
    test_csv = input_dir / "test.csv"
    create_test_csv(test_csv, [["1", "abc"]])

    t = Translator(input_path=input_dir, output_path=output_dir, save=True)
    t.save_state("test.csv", 0, 123)

    assert (output_dir / "state.json").exists()

    t.reset_state()
    assert not (output_dir / "state.json").exists()


def test_save_and_load_state(temp_dirs):
    _, output_dir = temp_dirs
    t = Translator(output_path=output_dir)
    t.save_state("somefile.csv", 3, 999)

    loaded = t.load_state()
    assert loaded["last_file"] == "somefile.csv"
    assert loaded["last_row"] == 3
    assert loaded["token_used"] == 999
    assert "timestamp" in loaded
