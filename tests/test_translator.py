import logging
from src.translator import Translator


def test_qwen():
    tr = Translator(
        model="qwen3:8b",
        padding_translate_files_path=r"tests/test_data/dolp",
        use_local=True,
        save=True,
    )
    tr.create_translates()
