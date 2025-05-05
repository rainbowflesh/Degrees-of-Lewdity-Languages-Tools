from loguru import logger
import pandas as pd
from pandas import NA
import os
import glob
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from src.io_helper import IOHelper


def merge_csv_columns(from_file: str, to_file: str):
    # use col1 as key,
    # insert col2 from from_file to to_file col3
    # Read both CSV files without headers
    df_from = pd.read_csv(from_file, header=None)
    df_to = pd.read_csv(to_file, header=None)

    # Ensure the dataframes have the expected columns
    if len(df_from.columns) < 2 or len(df_to.columns) < 2:
        raise ValueError("Both input files must have at least 2 columns")

    # Rename columns for clarity (since we're reading without headers)
    df_from.columns = [0, 1] if len(df_from.columns) == 2 else df_from.columns
    df_to.columns = [0, 1] if len(df_to.columns) == 2 else df_to.columns

    # Merge dataframes on the key column
    merged_df = pd.merge(df_to, df_from[[0, 1]], on=0, how="left")

    # Save the merged dataframe back to to_file without headers
    merged_df.to_csv(to_file, index=False, header=False)

    return merged_df


async def merge_translates(source_path: str, target_path: str):
    # input source_path:str = dicts/translates/zh-Hans/dol col3
    # to target_path:str = dicts/translated/zh-Hans/dolp col3
    # if col2 same
    io_helper = IOHelper()
    processed_count = 0

    # Find all CSV files in source_path
    source_path_obj = Path(source_path)
    source_files = io_helper.read_files(source_path_obj, ".csv", recursive=True)

    # Create a thread pool for file processing
    with ThreadPoolExecutor() as executor:
        # Create tasks for processing each file
        tasks = []
        for source_file in source_files:
            source_file_path = Path(source_file)
            # Determine the corresponding target file path
            rel_path = source_file_path.relative_to(source_path_obj)
            target_file = Path(target_path) / rel_path

            # Check if the target file exists
            if not target_file.exists():
                continue

            # Add task to process this file pair
            task = asyncio.create_task(
                process_file_pair(executor, io_helper, source_file_path, target_file)
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


async def process_file_pair(executor, io_helper, source_file, target_file):
    """Process a pair of source and target files asynchronously"""
    try:
        # Read both files using IOHelper
        loop = asyncio.get_running_loop()
        source_rows, source_success = await loop.run_in_executor(
            executor, io_helper.read_csv, source_file, False
        )
        target_rows, target_success = await loop.run_in_executor(
            executor, io_helper.read_csv, target_file, False
        )

        if not (source_success and target_success):
            return False

        # Ensure files have the required columns
        if len(source_rows) == 0 or len(target_rows) == 0:
            return False

        if len(source_rows[0]) < 3 or len(target_rows[0]) < 2:
            return False

        # Create a copy of DOLP rows and add a column for translations if needed
        result_rows = []
        has_matches = False

        # Process each target row
        for target_row in target_rows:
            # Ensure the result row has at least 3 columns
            result_row = target_row.copy()
            while len(result_row) < 3:
                result_row.append(None)

            # Check if DOLP's col2 matches any DOL's col2
            target_col2 = target_row[1] if len(target_row) > 1 else None

            # Find matching rows in DOL
            for source_row in source_rows:
                if len(source_row) > 2 and source_row[1] == target_col2:
                    # Add DOL's col3 to the result
                    result_row[2] = source_row[2]
                    has_matches = True
                    break

            result_rows.append(result_row)

        # Save the result back to DOLP file if we found matches
        if has_matches:
            success = await loop.run_in_executor(
                executor, io_helper.write_csv, target_file, result_rows, None
            )
            if success:
                logger.info(f"Updated file: {target_file}")
                return True

        return False

    except Exception as e:
        logger.error(f"Error processing {source_file} and {target_file}: {e}")
        return False


def test_merge():
    from_file = "tests/test_data/translated/dolp/04-Variables/decoMod.csv"
    to_file = "dicts/translated/zh-Hans/dolp/04-Variables/decoMod.csv"

    # Ensure directories exist
    os.makedirs(os.path.dirname(from_file), exist_ok=True)
    os.makedirs(os.path.dirname(to_file), exist_ok=True)

    # Run merge function with real files
    result = merge_csv_columns(from_file, to_file)


def test_merge_dol2dolp():
    # Define test paths
    dol_path = "tests/test_data/translates/zh-Hans/dol"
    dolp_path = "tests/test_data/translates/zh-Hans/dolp"

    # Run the async function
    asyncio.run(merge_translates(dol_path, dolp_path))


def test_merge_diff2dolp():
    # Define test paths
    diff_path = "tests/test_data/diff/translates/zh-Hans"
    dolp_path = "tests/test_data/translates/zh-Hans/dolp"

    # Run the async function
    asyncio.run(merge_translates(diff_path, dolp_path))
