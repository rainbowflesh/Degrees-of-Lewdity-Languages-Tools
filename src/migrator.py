import json
from pathlib import Path

from loguru import logger
from src.io_helper import IOHelper


class Migrator:
    def __init__(self, game_root: Path = Path(r"lib/degrees-of-lewdity/game")):
        self._game_root = game_root
        self._io_helper = IOHelper()

    def migrate_wbfile_list(self):
        """migrate old blacklist/whitelist to new format"""
        self._blacklist = {}
        self._whitelist = {}

        new_blacklist = {"blacklist": []}
        new_whitelist = {"whitelist": []}

        try:
            with open(r"dicts/old_blacklists.json", "r", encoding="utf-8") as blacklist:
                self._blacklist = json.load(blacklist)

            with open(r"dicts/old_whitelists.json", "r", encoding="utf-8") as whitelist:
                self._whitelist = json.load(whitelist)
        except Exception as e:
            logger.error(f"Failed to load old blacklist/whitelist: {e}")
            return

        js_files = self._io_helper.read_files(self._game_root, ".js", True)
        twee_files = self._io_helper.read_files(self._game_root, ".twee", True)

        # create file path mapping
        game_file_paths = {}
        for file_path in js_files + twee_files:
            path = Path(file_path)
            rel_path = path.relative_to(self._game_root)
            dir_name = path.parent.name
            file_name = path.name

            if str(rel_path.parent) == ".":  # game_root
                full_rel_path = file_name
            else:
                full_rel_path = str(rel_path)

            game_file_paths[(dir_name, file_name)] = full_rel_path

        # blacklist
        for dir_name, files in self._blacklist.items():
            if not files:
                for (folder, file), path in game_file_paths.items():
                    if folder == dir_name or path.startswith(f"{dir_name}/"):
                        new_blacklist["blacklist"].append(path)
            else:
                for file in files:
                    if (dir_name, file) in game_file_paths:
                        new_blacklist["blacklist"].append(
                            game_file_paths[(dir_name, file)]
                        )
                    else:
                        for _, path in game_file_paths.items():
                            if path.endswith(f"/{file}") and (
                                f"/{dir_name}/" in f"/{path}"
                                or path.startswith(f"{dir_name}/")
                            ):
                                new_blacklist["blacklist"].append(path)
                                break

        # whitelist
        for dir_name, files in self._whitelist.items():
            for file in files:
                if (dir_name, file) in game_file_paths:
                    new_whitelist["whitelist"].append(game_file_paths[(dir_name, file)])
                else:
                    for _, path in game_file_paths.items():
                        if path.endswith(f"/{file}") and (
                            f"/{dir_name}/" in f"/{path}"
                            or path.startswith(f"{dir_name}/")
                        ):
                            new_whitelist["whitelist"].append(path)
                            break

        # save to file
        self._io_helper.ensure_dir_exists(Path("dicts"))
        with open(r"dicts/blacklists.json", "w", encoding="utf-8") as fp:
            json.dump(new_blacklist, fp, ensure_ascii=False, indent=2)
            logger.info(f"New format blacklist written to dicts/blacklists.json")

        with open(r"dicts/whitelists.json", "w", encoding="utf-8") as fp:
            json.dump(new_whitelist, fp, ensure_ascii=False, indent=2)
            logger.info(f"New format whitelist written to dicts/whitelists.json")
