import os
import csv
from pathlib import Path

class IOHelper:
    def __init__(self):
        pass

    def read_twee():
        pass

    def read_js():
        pass

    """read .csv from given path"""
    def read_csv(self,path:Path):
        csv_files = []
        for root, _, files in os.walk(path):
            for file in files:
                if file.lower().endswith('.csv'):
                    csv_files.append(os.path.join(root, file))
        return csv_files


    def write_csv_sync(self, file_path, rows):
        """Write rows to a CSV file synchronously."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)