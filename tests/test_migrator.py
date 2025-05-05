import json
from pathlib import Path

from loguru import logger
from src.io_helper import IOHelper


def test_migrate_wbfile_list():
    _io_helper = IOHelper()
    _game_root = Path("game")
    _blacklist = json.load(open("dicts/blacklists.json", "r", encoding="utf-8"))
    _whitelist = json.load(open("dicts/whitelists.json", "r", encoding="utf-8"))
    """转换黑白名单到新格式，以相对于game目录的路径表示"""

    new_blacklist = {"blacklist": []}
    new_whitelist = {"whitelist": []}

    # 一次性读取所有文件
    js_files = _io_helper.read_files(_game_root, ".js", True)
    twee_files = _io_helper.read_files(_game_root, ".twee", True)

    # 创建文件路径映射
    game_file_paths = {}
    for file_path in js_files + twee_files:
        path = Path(file_path)
        rel_path = path.relative_to(_game_root)
        dir_name = path.parent.name
        file_name = path.name

        if str(rel_path.parent) == ".":  # 处理根目录
            full_rel_path = file_name
        else:
            full_rel_path = str(rel_path)

        game_file_paths[(dir_name, file_name)] = full_rel_path

    # 处理黑名单
    for dir_name, files in _blacklist.items():
        if not files:  # 整个目录被排除
            for (folder, file), path in game_file_paths.items():
                if folder == dir_name or path.startswith(f"{dir_name}/"):
                    new_blacklist["blacklist"].append(path)
        else:  # 特定文件被排除
            for file in files:
                if (dir_name, file) in game_file_paths:
                    new_blacklist["blacklist"].append(game_file_paths[(dir_name, file)])
                else:
                    # 尝试查找深层目录匹配
                    for _, path in game_file_paths.items():
                        if path.endswith(f"/{file}") and (
                            f"/{dir_name}/" in f"/{path}"
                            or path.startswith(f"{dir_name}/")
                        ):
                            new_blacklist["blacklist"].append(path)
                            break

    # 处理白名单，逻辑与黑名单类似
    for dir_name, files in _whitelist.items():
        for file in files:
            if (dir_name, file) in game_file_paths:
                new_whitelist["whitelist"].append(game_file_paths[(dir_name, file)])
            else:
                for _, path in game_file_paths.items():
                    if path.endswith(f"/{file}") and (
                        f"/{dir_name}/" in f"/{path}" or path.startswith(f"{dir_name}/")
                    ):
                        new_whitelist["whitelist"].append(path)
                        break

    # 写入文件
    _io_helper.ensure_dir_exists(Path("dicts"))
    with open(r"dicts/new_blacklists.json", "w", encoding="utf-8") as fp:
        json.dump(new_blacklist, fp, ensure_ascii=False, indent=2)
        logger.info(f"New blacklist written to dicts/new_blacklists.json")

    with open(r"dicts/new_whitelists.json", "w", encoding="utf-8") as fp:
        json.dump(new_whitelist, fp, ensure_ascii=False, indent=2)
        logger.info(f"New whitelist written to dicts/new_whitelists.json")

    return new_blacklist, new_whitelist
