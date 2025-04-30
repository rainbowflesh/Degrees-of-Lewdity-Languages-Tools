from src.translator import Translator


def test_qwen():
    tr = Translator(
        model="qwen3:8b",
        input_path=r"tests/test_data/dolp",
        use_local=True,
        save=False,
    )
    tr.search_and_translate()
