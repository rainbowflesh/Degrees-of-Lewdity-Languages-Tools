from src.translator import Translator


def test_translator_resume():
    t = Translator(input_path=r"tests/test_data/diff/dolp", save=True, use_local=True)
    t.resume_translate()
