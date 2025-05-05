import asyncio
from pathlib import Path
import click
import datetime
from dotenv import dotenv_values
from loguru import logger

from src.formatter import Formatter
from src.differentiator import Differentiator
from src.dumper import Dumper
from src.translator import Translator
from src.downloader import Downloader

__doc_pipelines__ = """
    Dumper pipeline:
    1. search .js .twee files.
    2. Extract dicts from files as raw_dicts.
    3. Compare raw_dicts with translated_dicts, add newlines to translated_dicts, create .diff file.
    4. In this stage, we can build game as none-new-translate version.

    Translator pipeline:
    1. Use MT to translate .diff file, create .translated_diff file.
    2. Upload .translated_diff as help wanted.

    MergeHelper pipeline:
    1. Merge .translated_diff into translated_dicts, bump version.
    2. convert translated_dicts to modloader format, send tooltip or signal to build translates as mod.
    3. In this stage, we can build game as new-translate version.
"""

__doc_project_structure__ = """
    - src/ code resource
    - lib/ game files, extra lib, local lib
        - degrees-of-lewdity-plus
        - degrees-of-lewdity
    - dicts
        - raw ~70mb
        - translated ~70mb/lang
            - ${lang}
        - diff
            - ${lang}
                - diff files
                - mt_translated
    - dist/ output, build, dists
        - degrees-of-lewdity-plus
            - ${lang}
                - game build
                - mod
        - degrees-of-lewdity
            - ${lang}
                - game build
                - mod
"""

__doc_args__ = """ """

__doc_parser__ = """ """

__doc_translator__ = """ """

__doc_merge_helper__ = """ """


# log helper
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"{timestamp}_run.log"
logger.add(
    log_file,
    rotation="10 MB",
    retention="7 days",
    compression="zip",
    level="INFO",
    enqueue=True,
)


_env = dotenv_values(".env")


def UseDumper():
    _dumper = Dumper()
    _dumper.dump_sets()
    _dumper.dump_variables()


def UseDownloader(lang: str):
    _downloader = Downloader(_env)
    logger.info(f"Downloading {lang} dicts")
    match lang:
        case "zh-hans" | "zh-Hans" | "zh-CN" | "zh-cn" | "cn":
            result = _downloader.download_dol_zh_hans()
            _downloader.extract_download(result, "dicts/translated/zh-Hans/")
        case _:
            raise ValueError(f"Unsupported language: {lang}")


def UseTranslator(input_files_path: Path, output_files_path: Path, resume: bool):
    _translator = Translator(
        input_path=input_files_path,
        save=True,
        output_path=output_files_path,
    )
    if resume:
        _translator.resume_translate
    else:
        # start new run
        _translator.search_and_translate()


def UseFormatTranslates(format_translates: str):
    path_obj = Path(format_translates)
    _csv_helper = Formatter(path_obj)
    _csv_helper.trim_csv_key()
    _csv_helper.sort_csv()


def UseDiff(translation_files_path: Path, raw_files_path: Path, diff_files_path: Path):
    differ = Differentiator(translation_files_path, raw_files_path, diff_files_path)
    asyncio.run(differ.create_diff())
    asyncio.run(differ.count_diff_rows())


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option("-d", "--dump", is_flag=True, default=False, help="Run raw dicts dump")
@click.option(
    "-t",
    "--translate",
    nargs=2,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Run machine translate. Usage: --translate <input_path> <output_path>",
)
@click.option(
    "--resume",
    is_flag=True,
    default=False,
    help="Automatic check translate state and resume, used to check for missing translations, or to continue the last batch translation job",
)
@click.option(
    "--format-translates",
    help="Format the translated file, basically made for chaotic zh-hans translation files, need to provide the path of translated dicts.",
)
@click.option(
    "--provider",
    help="LLM provider (Available: cursor, gemini, gpt, deepseek [API,local], X-ALMA [Local]).",
)
@click.option(
    "--local",
    is_flag=True,
    default=False,
    help="Use a local model via Ollama instead of using API.",
)
@click.option(
    "--full", is_flag=True, default=False, help="Use the full version of local models."
)
@click.option(
    "--diff",
    nargs=3,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Create diff files between raw and translated dicts. Usage: --diff <translation_path> <raw_path> <diff_path>",
)
@click.option(
    "--download",
    help="Download the translated dicts. Usage: --download <language code>, eg. --download zh-hans",
)
@click.pass_context
def ClickHelper(
    ctx,
    dump: bool,
    translate: tuple,
    format_translates: str,
    provider: str,
    local: bool,
    full: bool,
    diff: tuple,
    resume: bool,
    download: str,
):
    """
    Degrees of Lewdity Languages Tool - Utilities for managing Degrees of Lewdity translations.

    Run without arguments to show this help message.
    """

    if dump:
        UseDumper()
    if translate:
        input_files_path, output_files_path = map(Path, translate)
        UseTranslator(input_files_path, output_files_path, resume)
    if format_translates:
        UseFormatTranslates(format_translates)
    if diff:
        translation_files_path, raw_files_path, diff_files_path = map(Path, diff)
        UseDiff(translation_files_path, raw_files_path, diff_files_path)
    if download:
        UseDownloader(download)
    else:
        click.echo(ctx.get_help())


if __name__ == "__main__":
    ClickHelper()
