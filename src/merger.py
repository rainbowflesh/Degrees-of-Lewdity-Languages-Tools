import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from loguru import logger
from src.io_helper import IOHelper


class Merger:
    def __init__(self, source_path: Path, target_path: Path):
        self._source_path = source_path
        self._target_path = target_path
        self._io_helper = IOHelper()
        pass

    async def merge_translates(self):
        """merge col3 from source_path to target_path if col2 same"""
        processed_count = 0

        source_files = self._io_helper.read_files(
            self._source_path, ".csv", recursive=True
        )

        # Create a thread pool for file processing
        with ThreadPoolExecutor() as executor:
            # Create tasks for processing each file
            tasks = []
            for source_file in source_files:
                source_file_path = Path(source_file)
                # Determine the corresponding target file path
                rel_path = source_file_path.relative_to(self._source_path)
                target_file = Path(self._target_path) / rel_path

                # Check if the target file exists
                if not target_file.exists():
                    continue

                # Add task to process this file pair
                task = asyncio.create_task(
                    self._process_file_pair(
                        executor, self._io_helper, source_file_path, target_file
                    )
                )
                tasks.append(task)

            # Wait for all tasks to complete and collect results
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count successful operations and log exceptions
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error in file processing: {result}")
                elif result:
                    processed_count += 1

        return processed_count

    async def _process_file_pair(self, executor, source_file, target_file):
        """Process a pair of source and target files asynchronously"""
        try:
            loop = asyncio.get_running_loop()
            source_rows, source_success = await loop.run_in_executor(
                executor, self._io_helper.read_csv, source_file, False
            )
            target_rows, target_success = await loop.run_in_executor(
                executor, self._io_helper.read_csv, target_file, False
            )

            if not (source_success and target_success):
                return False

            # Ensure files have the required columns
            if len(source_rows) == 0 or len(target_rows) == 0:
                return False

            if len(source_rows[0]) < 3 or len(target_rows[0]) < 2:
                return False

            result_rows = []
            has_matches = False

            # Process each target row
            for target_row in target_rows:
                # Ensure the result row has at least 3 columns
                result_row = target_row.copy()
                while len(result_row) < 3:
                    result_row.append(None)

                # Check if compare col2 matches any source col2
                target_col2 = target_row[1] if len(target_row) > 1 else None

                # Find matching rows in source
                for source_row in source_rows:
                    if len(source_row) > 2 and source_row[1] == target_col2:
                        # Add source col3 to the result
                        result_row[2] = source_row[2]
                        has_matches = True
                        break

                result_rows.append(result_row)

            # Save the result back to target file if we found matches
            if has_matches:
                success = await loop.run_in_executor(
                    executor,
                    self._io_helper.write_csv,
                    target_file,
                    result_rows,
                    None,
                )
                if success:
                    logger.info(f"Updated file: {target_file}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error processing {source_file} and {target_file}: {e}")
            return False
