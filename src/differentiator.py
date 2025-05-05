from loguru import logger
import pandas as pd
from pathlib import Path
import csv
import shutil
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Any, Callable
from .io_helper import IOHelper

"""
    Differentiator use for creating translations different files.
    Useful to find the differences between the raw English and translated files, allow translator only focus differences.
    This implementation uses asyncio for high performance processing of multiple files in parallel.
"""


class Differentiator:
    def __init__(
        self,
        translation_files_path: Path,
        raw_files_path: Path,
        diff_files_path: Path,
        max_workers: int = None,
    ):
        self._io_helper = IOHelper()
        self._translation_files_path = translation_files_path
        self._raw_files_path = raw_files_path
        self._diff_files_path = diff_files_path

        # use core threads as worker number
        self._max_workers = max_workers or os.cpu_count()
        self._executor = ThreadPoolExecutor(max_workers=self._max_workers)

    async def create_diff(self):
        """Processes all CSV files in the raw directory and compares them to translated files asynchronously."""
        # Define base paths using Path objects
        translated_base = Path(self._translation_files_path)
        raw_base = Path(self._raw_files_path)
        diff_base = Path(self._diff_files_path)

        logger.debug(f"Starting diff process with {self._max_workers} workers...")
        logger.debug(f"Raw directory: {raw_base}")
        logger.debug(f"Translated directory: {translated_base}")
        logger.debug(f"Diff output directory: {diff_base}")

        # collect all files to process
        raw_files = list(raw_base.rglob("**/*.csv"))
        total_files = len(raw_files)
        logger.debug(f"Found {total_files} CSV files to process")

        # create task list
        tasks = []
        for raw_file in raw_files:
            # Get the relative path of the raw file for logger, debug usage
            relative_path = raw_file.relative_to(raw_base)
            translated_file = translated_base / relative_path
            diff_file = diff_base / relative_path

            tasks.append(
                self.diff_single_csv(
                    raw_file, translated_file, diff_file, relative_path
                )
            )

        results = await asyncio.gather(*tasks)

        # count successfully processed files
        processed_files = sum(1 for r in results if r)
        logger.info(
            f"\nDiff process finished. Successfully processed {processed_files}/{total_files} files."
        )
        return processed_files

    async def diff_single_csv(
        self,
        raw_file: Path,
        translated_file: Path,
        diff_file: Path,
        relative_path: Path,
    ):
        """Compares a single raw CSV file with its translated counterpart and writes the diff asynchronously."""
        try:
            # Check if translated file exists
            if not translated_file.is_file():
                logger.info(
                    f"Translated file not found for {relative_path}. Copying raw file to diff."
                )
                self._io_helper.ensure_dir_exists(diff_file.parent)
                return await self._run_in_executor(shutil.copy2, raw_file, diff_file)

            # run pandas operation in thread pool
            return await self._run_in_executor(
                self._process_csv_files,
                raw_file,
                translated_file,
                diff_file,
                relative_path,
            )

        except Exception as e:
            logger.error(f"Unexpected error processing {relative_path}: {e}")
            return False

    async def _run_in_executor(self, func: Callable, *args, **kwargs) -> Any:
        """Run function in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, lambda: func(*args, **kwargs))

    def _process_csv_files(
        self,
        raw_file: Path,
        translated_file: Path,
        diff_file: Path,
        relative_path: Path,
    ) -> bool:
        """
        Core logic for CSV file comparison, executed in thread pool
        This code remains synchronous because pandas operations are CPU-intensive and not I/O-bound
        """
        try:
            # Load raw CSV
            df_raw = self._load_csv_to_dataframe(
                raw_file, ["id_r", "english"], relative_path, "raw"
            )

            if df_raw is None or df_raw.empty:
                logger.info(f"Skipping empty raw file: {relative_path}")
                return True

            # Load translated CSV to determine column structure
            df_translated = self._load_csv_to_dataframe(
                translated_file, None, relative_path, "translated"
            )

            if df_translated is None or df_translated.empty:
                logger.info(
                    f"Translated file is empty: {relative_path}. Copying raw file to diff."
                )
                os.makedirs(diff_file.parent, exist_ok=True)
                shutil.copy2(raw_file, diff_file)
                return True

            # Assign proper column names based on column count
            if len(df_translated.columns) >= 3:
                df_translated.columns = ["id_t", "eng", "translated_text"] + [
                    f"col{i}" for i in range(4, len(df_translated.columns) + 1)
                ]
            else:
                logger.error(
                    f"Translated file has only {len(df_translated.columns)} columns, expected at least 3. {translated_file.absolute()}"
                )
                os.makedirs(diff_file.parent, exist_ok=True)
                shutil.copy2(raw_file, diff_file)
                return True

            # Create a set of translated English texts (col2) for faster lookup
            translated_eng_texts = set(df_translated["eng"].dropna())

            # Find rows in raw where the english text doesn't exist in translated eng column
            diff_mask = ~df_raw["english"].isin(translated_eng_texts)

            if not diff_mask.any():
                logger.info(f"No diff found for: {relative_path}")
                return True
            else:
                diff_count = diff_mask.sum()
                logger.info(f"Writing diff for: {relative_path} ({diff_count} rows)")
                os.makedirs(diff_file.parent, exist_ok=True)

                # Select only id_r and english columns for the diff rows
                diff_rows = df_raw.loc[diff_mask, ["id_r", "english"]]
                diff_rows.to_csv(diff_file, index=False, header=False)
                return True

        except Exception as e:
            logger.error(
                f"Unexpected error in _process_csv_files for {relative_path}: {e}"
            )
            # Try to copy the raw file to diff in case of error
            try:
                os.makedirs(diff_file.parent, exist_ok=True)
                shutil.copy2(raw_file, diff_file)
                logger.info(f"Copied raw file to diff after error: {relative_path}")
                return True
            except Exception as copy_error:
                logger.error(f"Failed to copy raw file after error: {copy_error}")
                return False

    def _load_csv_to_dataframe(
        self,
        file_path: Path,
        column_names: Optional[List[str]],
        relative_path: Path,
        file_type: str,
    ) -> Optional[pd.DataFrame]:
        """加载CSV文件到DataFrame，处理可能的错误"""
        try:
            df = pd.read_csv(
                file_path,
                header=None,
                names=column_names,
                engine="python",
                sep=",",
                quoting=csv.QUOTE_MINIMAL,
            )
            return df
        except pd.errors.ParserError as e:
            logger.error(
                f"Error parsing {file_type} file {file_path.absolute()} ({relative_path}): {e}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Error reading {file_type} file {file_path.absolute()} ({relative_path}): {e}"
            )
            return None

    async def count_diff_rows(self):
        """Count the number of diff rows in the diff files asynchronously."""
        diff_files = list(self._diff_files_path.rglob("*.csv"))

        if not diff_files:
            logger.warning(f"No CSV files found in {self._diff_files_path}")
            return 0

        # create async tasks
        tasks = []
        for file_path in diff_files:
            tasks.append(self._count_rows_in_file(file_path))

        # run all tasks in parallel
        results = await asyncio.gather(*tasks)

        # calculate total rows
        total_rows = sum(count for count in results if count is not None)

        logger.info(f"Total diff rows: {total_rows} in {len(diff_files)} files")
        return total_rows

    async def _count_rows_in_file(self, file_path: Path) -> Optional[int]:
        """Count the number of rows in a single file asynchronously."""
        try:
            # use thread pool to read file
            row_count = await self._run_in_executor(
                self._io_helper.count_csv_rows(), file_path
            )
            logger.debug(f"File {file_path}: {row_count} rows")
            return row_count
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return None
