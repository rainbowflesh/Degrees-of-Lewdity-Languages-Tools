import json
from pathlib import Path

from loguru import logger
from src.io_helper import IOHelper


class DictionaryHelper:
    def __init__(self, game_root: Path = Path(r"lib/degrees-of-lewdity/game")):
        self._io_helper = IOHelper()
        self._game_root = game_root
        self._preprocess_files_list = []
        self._relative_paths = []
        self._js_files_count = 0
        self._twee_files_count = 0
        self._blacklist = {}
        self._whitelist = {}

    def get_preprocess_files_list(self):
        """Get preprocess game files according to blacklist/whitelist rules"""
        self._preprocess_files_list = []
        self._relative_paths = []
        self._js_files_count = 0
        self._twee_files_count = 0

        self._load_preprocess_files_wblists()

        js_files = self._get_files_by_extension(".js")
        twee_files = self._get_files_by_extension(".twee")

        logger.debug(
            f"Found {len(js_files)} JS files and {len(twee_files)} Twee files in game directory"
        )

        self._process_js_files(js_files)
        self._process_twee_files(twee_files)

        total_count = self._js_files_count + self._twee_files_count
        logger.debug(
            f"Total files: {total_count} (JS: {self._js_files_count}, Twee: {self._twee_files_count})"
        )

        return self._preprocess_files_list

    def cache_preprocess_files_list(self):
        """
        Cache preprocessed files list to JSON file
        """
        if not self._relative_paths:
            logger.warning(
                "No preprocessed files to cache. get_preprocess_files_list first."
            )
            return False

        self._io_helper.ensure_dir_exists(Path("dicts/cache"))

        js_files = self._io_helper.read_files(self._game_root, ".js", True)
        twee_files = self._io_helper.read_files(self._game_root, ".twee", True)

        total_js_count = len(js_files)
        total_twee_count = len(twee_files)
        total_files_count = total_js_count + total_twee_count

        if not self._blacklist or not self._whitelist:
            self._load_preprocess_files_wblists()

        blacklist_files_count = self._count_blacklisted_files()
        whitelist_files_count = sum(len(files) for files in self._whitelist.values())

        data = {
            "preprocess_files_list": sorted(self._relative_paths),
            "statistics": {
                "total": total_files_count,
                "total_js_files": total_js_count,
                "total_twee_files": total_twee_count,
                "preprocess_files": len(self._relative_paths),
                "js_files": self._js_files_count,
                "twee_files": self._twee_files_count,
                "blacklist_files": blacklist_files_count,
                "whitelist_files": whitelist_files_count,
            },
        }

        cache_path = "dicts/cache/preprocess_file_list.json"
        with open(cache_path, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
            logger.info(f"Preprocess file list saved to {cache_path}")

        return True

    def _load_preprocess_files_wblists(self):
        """Load blacklist and whitelist configuration from files"""
        with open(r"dicts/blacklists.json", "r", encoding="utf-8") as blacklist:
            self._blacklist = json.load(blacklist)

        with open(r"dicts/whitelists.json", "r", encoding="utf-8") as whitelist:
            self._whitelist = json.load(whitelist)

    def _get_files_by_extension(self, extension):
        """Get all files with specified extension from game directory"""
        return [
            Path(p)
            for p in self._io_helper.read_files(self._game_root, extension, True)
        ]

    def _process_js_files(self, js_files):
        """Process JS files according to whitelist rules"""
        # Build whitelist paths lookup
        whitelist_paths = set()
        for dir_name, files in self._whitelist.items():
            for file in files:
                for js_file in js_files:
                    if js_file.name == file and dir_name in js_file.parts:
                        whitelist_paths.add(js_file)

        # Add whitelisted files
        for file_path in js_files:
            if file_path in whitelist_paths:
                self._add_file_to_list(file_path)
                self._js_files_count += 1

    def _process_twee_files(self, twee_files):
        """Process Twee files according to blacklist rules"""
        for file_path in twee_files:
            if not self._is_blacklisted(file_path):
                self._add_file_to_list(file_path)
                self._twee_files_count += 1

    def _is_blacklisted(self, file_path):
        """Check if a file is blacklisted"""
        for blacklist_dir, blacklist_files in self._blacklist.items():
            if blacklist_dir in file_path.parts:
                if not blacklist_files or file_path.name in blacklist_files:
                    return True
        return False

    def _add_file_to_list(self, file_path):
        """Add a file to the processed files list"""
        self._preprocess_files_list.append(file_path)
        rel_path = file_path.relative_to(self._game_root)
        self._relative_paths.append(str(rel_path))

    def _count_blacklisted_files(self):
        """Count the number of blacklisted files"""
        blacklist_files_count = 0
        for dir_name, files in self._blacklist.items():
            if files:
                blacklist_files_count += len(files)
            else:
                dir_path = self._game_root / dir_name
                if dir_path.exists():
                    js_in_dir = len(self._io_helper.read_files(dir_path, ".js", True))
                    twee_in_dir = len(
                        self._io_helper.read_files(dir_path, ".twee", True)
                    )
                    blacklist_files_count += js_in_dir + twee_in_dir
        return blacklist_files_count
