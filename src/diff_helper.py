import logging
import pandas as pd
from pathlib import Path
import csv
import shutil

logger = logging.getLogger("Diff Helper")

"""
    DiffHelper is a helper class for creating translations different files.
    Useful to find the differences between the raw English and translated files, allow translator only focus differences.
"""


class DiffHelper:
    def __init__(
        self, translation_files_path: Path, raw_files_path: Path, diff_files_path: Path
    ):
        self._translation_files_path = translation_files_path
        self._raw_files_path = raw_files_path
        self._diff_files_path = diff_files_path

    def create_diff(self):
        """Processes all CSV files in the raw directory and compares them to translated files."""
        # Define base paths using Path objects
        translated_base = Path(self._translation_files_path)
        raw_base = Path(self._raw_files_path)
        diff_base = Path(self._diff_files_path)

        logger.info(f"Starting diff process...")
        logger.debug(f"Raw directory: {raw_base}")
        logger.debug(f"Translated directory: {translated_base}")
        logger.debug(f"Diff output directory: {diff_base}")

        # Iterate through all CSV files in the raw directory
        processed_files = 0
        for raw_file in raw_base.rglob("**/*.csv"):
            processed_files += 1

            # Get the relative path of the raw file for logger, debug usage
            relative_path = raw_file.relative_to(raw_base)

            translated_file = translated_base / relative_path
            diff_file = diff_base / relative_path

            self.diff_single_csv(raw_file, translated_file, diff_file, relative_path)

        logger.info(f"\nDiff process finished. Processed {processed_files} files.")

    def diff_single_csv(
        self,
        raw_file: Path,
        translated_file: Path,
        diff_file: Path,
        relative_path: Path,
    ):
        """Compares a single raw CSV file with its translated counterpart and writes the diff."""
        # Check if translated file exists
        if not translated_file.is_file():
            logger.info(
                f"Translated file not found for {relative_path}. Copying raw file to diff."
            )
            diff_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(raw_file, diff_file)
            return

        try:
            # Load raw CSV
            df_raw = pd.read_csv(
                raw_file,
                header=None,
                names=["id_r", "english"],
                engine="python",
                sep=",",
                quoting=csv.QUOTE_MINIMAL,
            )

            if df_raw.empty:
                logger.info(f"Skipping empty raw file: {relative_path}")
                return

            # Load translated CSV to determine column structure
            try:
                df_translated = pd.read_csv(
                    translated_file,
                    header=None,
                    engine="python",
                    sep=",",
                    quoting=csv.QUOTE_MINIMAL,
                )

                if df_translated.empty:
                    logger.info(
                        f"Translated file is empty: {relative_path}. Copying raw file to diff."
                    )
                    diff_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(raw_file, diff_file)
                    return

                # Assign proper column names based on column count
                if len(df_translated.columns) >= 3:
                    df_translated.columns = ["id_t", "eng", "translated_text"] + [
                        f"col{i}" for i in range(4, len(df_translated.columns) + 1)
                    ]
                else:
                    logger.error(
                        f"Translated file has only {len(df_translated.columns)} columns, expected at least 3. {translated_file.absolute()}"
                    )
                    diff_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(raw_file, diff_file)
                    return

                # Create a set of translated English texts (col2) for faster lookup
                translated_eng_texts = set(df_translated["eng"].dropna())

                # Find rows in raw where the english text doesn't exist in translated eng column
                diff_mask = ~df_raw["english"].isin(translated_eng_texts)

                if not diff_mask.any():
                    logger.info(f"No diff found for: {relative_path}")
                else:
                    diff_count = diff_mask.sum()
                    logger.info(
                        f"Writing diff for: {relative_path} ({diff_count} rows)"
                    )
                    diff_file.parent.mkdir(parents=True, exist_ok=True)

                    # Select only id_r and english columns for the diff rows
                    diff_rows = df_raw.loc[diff_mask, ["id_r", "english"]]
                    diff_rows.to_csv(diff_file, index=False, header=False)

            except pd.errors.ParserError as e:
                logger.error(
                    f"Error parsing translated file {translated_file.absolute()} ({relative_path}): {e}"
                )
                diff_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(raw_file, diff_file)
            except Exception as e:
                logger.error(
                    f"Error processing translated file {translated_file.absolute()} ({relative_path}): {e}"
                )
                diff_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(raw_file, diff_file)

        except pd.errors.ParserError as e:
            logger.error(
                f"Error parsing raw file {raw_file.absolute()} ({relative_path}): {e}"
            )
            return
        except Exception as e:
            logger.error(f"Unexpected error processing {relative_path}: {e}")
            return

    def count_diff_rows(self):
        """Count the number of diff rows in the diff files."""
        diff_files = list(self._diff_files_path.rglob("*.csv"))

        if not diff_files:
            logger.warning(f"No CSV files found in {self._diff_files_path}")
            return 0

        total_rows = 0

        for file_path in diff_files:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.reader(f)
                    file_rows = len(list(reader))
                    total_rows += file_rows
                    logger.debug(f"File {file_path}: {file_rows} rows")
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {str(e)}")

        logger.info(f"Total diff rows: {total_rows} in {len(diff_files)} files")
        return total_rows
