import logging
import os
from pathlib import Path
import click
from asyncio.log import logger

from src.csv_helper import CSVHelper
from src.diff_helper import DiffHelper
from src.dumper import Dumper
from src.translator import Translator


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


log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

log_file = log_dir / "application.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(filename=log_file, encoding="utf-8"),
    ],
)

logger = logging.getLogger("asyncio:Run")


@click.command()
@click.option("-d", "--dump", is_flag=True, default=False, help="Run raw dicts dump")
@click.option(
    "-t", "--translate", is_flag=True, default=False, help="Run machine translate"
)
@click.option(
    "--format-translates",
    help="Format the translates file, basically made for chaotic zh-hans translation files, need provide the path of translated dicts.",
)
@click.option(
    "--diff",
    is_flag=True,
    default=False,
    help="Create diff files between raw and translated dicts.",
)
@click.option(
    "-p",
    "--provider",
    help="LLM provider (Available: cursor, gemini, gpt, deepseek [API,local], X-ALMA [Local]).",
)
@click.option(
    "-l",
    "--local",
    is_flag=True,
    default=False,
    help="Use a local model via Ollama instead of use API.",
)
@click.option(
    "--full", is_flag=True, default=False, help="Use the full version of local models."
)
@click.pass_context
def ClickHelper(
    ctx,
    dump: bool,
    translate: bool,
    format_translates: str,
    diff: bool,
    provider: str,
    local: bool,
    full: bool,
):
    """
    Degrees of Lewdity Languages Tool - Utilities for managing Degrees of Lewdity translations.

    Run without arguments will show this help message.
    """
    if not any([dump, translate, format_translates, diff]):
        click.echo(ctx.get_help())
        return
    if dump:
        UseDumper()
    if translate:
        UseTranslator(provider, local, full)
    if format_translates:
        UseFormatTranslates(format_translates)
    if diff:
        UseDiff()


def UseDumper():
    _dumper = Dumper()
    _dumper.dump()


def UseTranslator(provider: str, local: bool, full: bool):
    _translator = Translator()
    _llm_provider = provider
    _use_local = local
    _use_full = full
    _vram = None
    _vram_gb = None

    if _use_local:

        import torch

        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            for i in range(device_count):
                _vram = torch.cuda.get_device_properties(i).total_memory
                _vram_gb = _vram / (1024**3)
                logger.info(
                    f"Device {i}: {torch.cuda.get_device_name(i)} VRAM: {_vram_gb} GB"
                )
                if _vram_gb <= 8:
                    raise Warning(
                        f"No enough VRAM (<= 8GB) to run local models on device {i}"
                    )
        else:
            raise Exception("Run failed: CUDA is not available.")

    match _llm_provider:
        # --provider=X-ALMA
        case "X-ALMA":
            if _use_full:
                _translator.x_alma(_use_full)  # 27GB
            else:
                _translator.x_alma()  # 7.05GB Q4 XS GGUF

        # --provider=deepseek (--local)
        case "deepseek":
            if _use_local:
                if _use_full:
                    _translator.deepseek(_use_local, _use_full)  # 400GB
                else:
                    _translator.deepseek(_use_local)  # 6GB Q4
            else:
                _translator.deepseek()

        # --provider=cursor
        case "cursor":
            _translator.cursor()

        # --provider=gemini
        case "gemini":
            _translator.gemini()

        # --provider=gpt
        case "gpt":
            _translator.gpt()

        case _:
            raise ValueError(
                f"Invalid LLM provider: {_llm_provider}, use --help get helps"
            )


def UseFormatTranslates(format_translates: str):
    path_obj = Path(format_translates)
    _csv_helper = CSVHelper(path_obj)
    _csv_helper.trim_csv_key()
    _csv_helper.sort_csv()


def UseDiff():
    diff_helper = DiffHelper()
    diff_helper.create_diff()


if __name__ == "__main__":
    ClickHelper()
