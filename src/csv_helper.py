import csv
import logging
import os
import asyncio
import shutil
import aiofiles
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Tuple, Callable, Any
from pathlib import Path
from src.io_helper import IOHelper


logger = logging.getLogger("CSVHelper")


class CSVHelper:
    def __init__(self, base_directory: str):
        self.base_directory = base_directory
        self.io_helper = IOHelper

    # Main Public Entry Points

    def trim_csv(
        self,
        input_csv_path: str = None,
        output_csv_path: str = None,
        in_place: bool = True,
    ) -> bool:
        if input_csv_path is None:
            input_csv_path = self.base_directory

        if os.path.isdir(input_csv_path):
            return self._trim_directory(input_csv_path, in_place)
        else:
            return self._trim_single_file(input_csv_path, output_csv_path, in_place)

    def sort_csv(
        self, input_csv_path=None, output_csv_path=None, in_place=True
    ) -> Optional[str]:
        if input_csv_path is None:
            csv_files = self._collect_csv_files()
            if not csv_files:
                logger.info(f"No CSV files found in {self.base_directory}")
                return None

            for csv_file in csv_files:
                self.sort_csv(csv_file, in_place=True)
            return None

        temp_file = None
        try:
            if output_csv_path is None and in_place:
                temp_file = f"{input_csv_path}.sorted.temp"
                output_csv_path = temp_file
            elif output_csv_path is None:
                output_csv_path = f"{input_csv_path}.sorted"

            logger.info(f"Sorting {input_csv_path} -> {output_csv_path}")

            os.makedirs(os.path.dirname(output_csv_path) or ".", exist_ok=True)

            rows = self._read_csv_sync(input_csv_path)
            if not rows:
                logger.warning(f"No valid rows found in {input_csv_path}")
                return None

            try:
                rows.sort(key=self._extract_sort_key)
                logger.info(f"Sorted {len(rows)} rows")
            except Exception as e:
                logger.warning(
                    f"Error during sorting: {e}. Proceeding with unsorted data."
                )

            self._write_csv_sync(output_csv_path, rows)

            if temp_file and in_place:
                shutil.move(temp_file, input_csv_path)
                logger.debug(
                    f"Replaced original file with sorted content: {input_csv_path}"
                )

            return input_csv_path if in_place else output_csv_path

        except Exception as e:
            logger.error(f"Error sorting file {input_csv_path}: {e}")
            self._cleanup_temp_file(temp_file)
            return None

    # Async Entry Points

    async def trim_csv_async(
        self, input_path: str = None
    ) -> Tuple[List[Any], List[Exception]]:
        input_path = input_path or self.base_directory
        return await self._process_files_concurrently(
            self._trim_file_async, directory=input_path
        )

    async def sort_csv_async(
        self, input_path: Optional[str] = None
    ) -> Tuple[List[Any], List[Exception]]:
        input_path = input_path or self.base_directory

        if os.path.isdir(input_path):
            return await self._process_files_concurrently(
                self._sort_file_async, directory=input_path
            )
        else:
            result = await self._sort_file_async(input_path)
            return [result], []

    # Internal Trim Functions

    def _trim_directory(self, directory: str, in_place: bool) -> bool:
        success = True
        csv_files = self._collect_csv_files(directory)

        if not csv_files:
            logger.warning(f"No CSV files found in {directory}")
            return False

        for csv_file in csv_files:
            if not self._trim_single_file(csv_file, None, in_place):
                success = False

        return success

    def _trim_single_file(
        self, input_csv_path: str, output_csv_path: str = None, in_place: bool = True
    ) -> bool:
        if output_csv_path is None and in_place:
            output_csv_path = f"{input_csv_path}.temp"
            overwrite_original = True
        else:
            overwrite_original = False

        logger.debug(f"Trimming version suffix from {input_csv_path}")

        try:
            output_dir = os.path.dirname(output_csv_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            rows = self._read_csv_sync(input_csv_path)
            if not rows:
                logger.warning(f"No valid rows found in {input_csv_path}")
                return False

            processed_rows = []
            for row in rows:
                if row:  # Ensure row is not empty
                    try:
                        # Clean the first column using the helper function
                        original_id = row[0]
                        cleaned_id = self._clean_id(original_id)
                        # Create a new row list to avoid modifying the original during iteration
                        new_row = [cleaned_id] + row[1:]
                        processed_rows.append(new_row)
                    except IndexError:
                        logger.warning(f"Skipping row with too few columns: {row}")
                        processed_rows.append(row)  # Keep original row if error
                    except Exception as e:
                        logger.warning(
                            f"Error cleaning ID '{row[0]}': {e}. Keeping original."
                        )
                        processed_rows.append(row)  # Keep original row if error
                else:
                    processed_rows.append(row)  # Keep empty rows

            self._write_csv_sync(output_csv_path, processed_rows)

            if overwrite_original:
                shutil.move(output_csv_path, input_csv_path)
                logger.debug(f"Replaced original file: {input_csv_path}")
            else:
                logger.debug(f"Written to: {output_csv_path}")

            return True

        except FileNotFoundError:
            logger.error(f"Input file not found: {input_csv_path}")
        except Exception as e:
            logger.error(f"Error processing {input_csv_path}: {e}")
            if overwrite_original:
                self._cleanup_temp_file(output_csv_path)

        return False

    # For backward compatibility
    async def trim_version(self):
        return await self.trim_csv_async()

    def _clean_id(self, original_id: str) -> str:
        """Cleans the ID string based on specified rules."""
        cleaned_id = original_id.strip()

        # trim """  11" -> 11
        if cleaned_id.startswith('"""') and cleaned_id.endswith('"'):
            content = cleaned_id[3:-3].strip()
            numeric_part = "".join(filter(str.isdigit, content.split(" ", 1)[0]))
            if numeric_part:
                return numeric_part
            else:
                logger.warning(f"Could not extract numeric ID from: {original_id}")
                return content

        # trim 629_5_2_3|5_2_3| -> 629
        if "|" in cleaned_id:
            first_part = cleaned_id.split("|", 1)[0].strip()
            if "_" in first_part:
                id_segment = first_part.split("_")[0].strip()
                return id_segment if id_segment else first_part
            else:
                return first_part

        # Handle comma character (takes precedence over just underscore)
        if "," in cleaned_id:
            first_part = cleaned_id.split(",", 1)[0].strip()
            # No need to check for underscore here, we assume the part before comma is the final ID
            return first_part

        # Handle underscore only (if no pipe or comma)
        if "_" in cleaned_id:
            id_segment = cleaned_id.split("_")[0].strip()
            return id_segment if id_segment else cleaned_id

        # If none of the above, return the stripped original ID
        return cleaned_id

    # Async Processing Functions

    async def _process_files_concurrently(
        self, process_func: Callable, directory: Optional[str] = None
    ) -> Tuple[List[Any], List[Exception]]:
        directory = directory or self.base_directory
        csv_files = self._collect_csv_files(directory)

        if not csv_files:
            logger.warning(f"No CSV files found in {directory}")
            return [], []

        logger.debug(f"Found {len(csv_files)} CSV files to process")

        semaphore = asyncio.Semaphore(8)
        tasks = []

        for csv_file in csv_files:
            task = asyncio.create_task(
                self._run_with_semaphore(semaphore, process_func, csv_file)
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        failures = [r for r in results if isinstance(r, Exception)]
        successes = [r for r in results if not isinstance(r, Exception)]

        if failures:
            logger.error(f"Failed to process {len(failures)}/{len(results)} files")
            for failure in failures:
                logger.error(f"  - {failure}")

        logger.debug(f"Successfully processed {len(successes)}/{len(results)} files")
        return successes, failures

    async def _trim_file_async(self, file_path: str) -> str:
        logger.debug(f"Processing {file_path}")
        temp_file_path = f"{file_path}.temp"

        try:
            modified_rows = await self._read_and_trim_csv_async(file_path)

            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor() as executor:
                await loop.run_in_executor(
                    executor,
                    lambda: self._write_csv_sync(temp_file_path, modified_rows),
                )

            shutil.move(temp_file_path, file_path)
            return file_path

        except Exception as e:
            self._cleanup_temp_file(temp_file_path)
            logger.error(f"Error processing {file_path}: {e}")
            raise

    async def _sort_file_async(self, file_path: str) -> str:
        logger.info(f"Sorting {file_path}")
        loop = asyncio.get_running_loop()

        with ThreadPoolExecutor() as executor:
            try:
                return await loop.run_in_executor(
                    executor, lambda: self.sort_csv(file_path, None, True)
                )
            except Exception as e:
                logger.error(f"Error sorting {file_path}: {e}")
                raise

    # Helper Functions

    async def _run_with_semaphore(self, semaphore, func, *args, **kwargs):
        async with semaphore:
            return await func(*args, **kwargs)

    async def _read_and_trim_csv_async(self, file_path: str) -> List[List[str]]:
        modified_rows = []
        try:
            async with aiofiles.open(
                file_path, "r", encoding="utf-8-sig", newline=""
            ) as file:
                content = await file.read()
                # Use csv.reader for better handling of quotes within fields if standard format occurs
                reader = csv.reader(content.splitlines())

                for row in reader:
                    if not row:  # Skip empty rows
                        modified_rows.append(row)
                        continue

                    try:
                        # Clean the first column using the helper function
                        original_id = row[0]
                        cleaned_id = self._clean_id(original_id)
                        # Create a new row list to avoid modifying the original during iteration
                        new_row = [cleaned_id] + row[1:]
                        modified_rows.append(new_row)
                    except IndexError:
                        logger.warning(
                            f"Skipping row with too few columns in {file_path}: {row}"
                        )
                        modified_rows.append(row)
                    except Exception as e:
                        logger.warning(
                            f"Error cleaning ID '{row[0]}' in {file_path}: {e}. Keeping original."
                        )
                        modified_rows.append(row)

        except Exception as e:
            logger.error(f"Error reading or processing {file_path}: {e}")
            # Depending on desired behavior, maybe return partial results or empty list
            # raise # Or re-raise the exception

        return modified_rows

    def _write_csv_sync(self, file_path: str, rows: List[List[str]]) -> None:
        try:
            output_dir = os.path.dirname(file_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            with open(file_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerows(rows)
        except Exception as e:
            logger.error(f"Error writing to {file_path}: {e}")
            raise

    def _read_csv_sync(self, file_path: str) -> List[List[str]]:
        rows = []
        try:
            with open(file_path, "r", encoding="utf-8-sig", newline="") as infile:
                reader = csv.reader(infile)
                rows = [row for row in reader if row]
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
        return rows

    def _extract_sort_key(self, row: List[str]) -> Tuple[Any, ...]:
        """Extract numerical sort key from the first column, placing errors last."""
        try:
            if not row or not row[0]:
                # Place empty rows or rows with empty first column last
                return (float("inf"),)

            id_part = row[0]

            if "|" in id_part:
                id_part = id_part.split("|", 1)[0]

            # Remove any non-numeric characters except _ before processing
            # This handles potential variations or artifacts in the ID
            cleaned_id_part = "".join(c for c in id_part if c.isdigit() or c == "_")

            if not cleaned_id_part:  # If cleaning results in empty string
                return (float("inf"),)

            if "_" in cleaned_id_part:
                # Handle multi-part keys like 1_2_3
                return tuple(map(int, cleaned_id_part.split("_")))
            else:
                # Handle single-part keys like 10
                return (int(cleaned_id_part),)

        except (ValueError, IndexError, Exception) as e:
            # Place rows that cause errors during parsing last
            logger.warning(f"Could not extract sort key from row: {row}. Error: {e}")
            return (float("inf"),)

    def _collect_csv_files(self, directory: str = None) -> List[str]:
        directory = directory or self.base_directory
        csv_files = []

        try:
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith(".csv"):
                        csv_files.append(os.path.join(root, file))
        except Exception as e:
            logger.error(f"Error collecting CSV files from {directory}: {e}")

        return csv_files

    def _cleanup_temp_file(self, temp_file: str) -> None:
        try:
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)
        except Exception as e:
            logger.warning(f"Failed to clean up temporary file {temp_file}: {e}")
