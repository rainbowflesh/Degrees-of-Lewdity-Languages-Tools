"""
如:
<<set VAR ...>>
<<if VAR ...>>
<<run VAR ...>>
"""

import asyncio
from collections.abc import Set
import json
import os
import re
from enum import Enum
from pathlib import Path
from pprint import pprint
from typing import Any, Dict, List, Optional, Tuple

from src.consts import *
from aiofiles import open as aopen

SELF_ROOT = Path(__file__).parent

ALL_NEEDED_TRANSLATED_set_CONTENTS = None

FREQ_FUNCTIONS = {".push(", ".pushUnique(", ".delete(", ".deleteAt(", ".splice("}


class Regexes(Enum):
    VARS_REGEX = re.compile(r"([$_][$A-Z_a-z][$0-9A-Z_a-z]*)")
    SET_RUN_REGEXES = re.compile(
        r'<<(run|set)(?:\s+((?:(?:\/\*[^*]*\*+(?:[^/*][^*]*\*+)*\/)|(?:\/\/.*\n)|(?:`(?:\\.|[^`\\\n])*?`)|(?:"(?:\\.|[^"\\\n])*?")|(?:\'(?:\\.|[^\'\\\n])*?\')|(?:\[(?:[<>]?[Ii][Mm][Gg])?\[[^\r\n]*?\]\]+)|[^>]|(?:>(?!>)))*?))?>>'
    )


class VariablesProcess:
    def __init__(self):
        self._twee_files: set[Path] = set()
        self._categorize_variables: List[Dict] = []
        self._twee_variables: List[str] = []

        self._categorize_all_set_contents: List[Dict] = []
        self._all_set_contents: List[str] = []
        self._categorize_all_needed_translated_set_contents: List[Dict] = []
        self._all_needed_translated_set_contents: List[str] = []

        self._cached_translated_set_contents = None

    async def search_twee_files(self) -> Set[Path]:
        """获取所有 .twee 文件绝对路径"""
        for root, _, file_list in os.walk("lib/degrees-of-lewdity-plus/game"):
            for file in file_list:
                if file.endswith(".twee"):
                    self._twee_files.add(Path(root).absolute() / file)
        return self._twee_files

    async def fetch_all_variables(self) -> None:
        """获取所有 .twee 文件中存在的变量，写入文件，创建 vars 目录"""
        if not self._twee_files:
            await self.search_twee_files()

        results = await asyncio.gather(
            *[self._fetch_all_variables(file) for file in self._twee_files]
        )

        self._categorize_variables = [r for r in results if r]
        self._twee_variables = sorted(
            list(
                set(var for result in results if result for var in result["variables"])
            )
        )

        await self._write_variables_to_files()

    async def _write_variables_to_files(self) -> None:
        """将变量信息写入文件"""
        os.makedirs(SELF_ROOT / "vars", exist_ok=True)

        async with aopen(
            SELF_ROOT / "vars" / "_variables.json", "w", encoding="utf-8"
        ) as fp:
            await fp.write(
                json.dumps(self._categorize_variables, ensure_ascii=False, indent=2)
            )

        async with aopen(
            SELF_ROOT / "vars" / "_all_variables.json", "w", encoding="utf-8"
        ) as fp:
            await fp.write(
                json.dumps(self._twee_variables, ensure_ascii=False, indent=2)
            )

    async def _fetch_all_variables(self, file: Path) -> Optional[Dict]:
        """从单个文件中提取变量"""
        async with aopen(file, "r", encoding="utf-8") as fp:
            raw = await fp.read()

        variables = re.findall(Regexes.VARS_REGEX.value, raw)
        if not variables:
            return None

        return {
            "path": str(file).split("\\game\\")[1],
            "variables": sorted(list(set(variables))),
        }

    async def build_variables_notations(self):
        """哪些变量可以翻译，写入文件，暂时弃用"""
        filepath = DIR_DATA_ROOT / "json" / "variables_notations.json"

        old_data = {}
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as fp:
                old_data: dict = json.load(fp)

        new_data = {
            var: {"var": var, "desc": "", "canBeTranslated": False}
            for var in self._twee_variables
        }

        if old_data:
            for key, items in old_data.items():
                if items["desc"]:
                    new_data[key] = items

        with open(
            DIR_DATA_ROOT / "json" / "variables_notations.json", "w", encoding="utf-8"
        ) as fp:
            json.dump(new_data, fp, ensure_ascii=False, indent=2)

    async def fetch_all_set_content(self) -> List[Dict]:
        """获取所有 <<set>> 内容，写入 setto 目录里"""

        # check local files
        if self._cached_translated_set_contents:
            return self._cached_translated_set_contents

        # load local files if exist
        content_file = SELF_ROOT / "setto" / "_needed_translated_set_contents.json"
        if content_file.exists():
            async with aopen(content_file, "r", encoding="utf-8") as fp:
                data = json.loads(await fp.read())
            self._cached_translated_set_contents = data
            return data

        # 确保已收集twee文件
        if not self._twee_files:
            await self.search_twee_files()

        # 并行处理所有文件
        results = await asyncio.gather(
            *[self._fetch_all_set_content(file) for file in self._twee_files]
        )

        # 合并结果
        for result in results:
            if not result:
                continue

            self._categorize_all_set_contents.append(result["categorize"])
            self._all_set_contents.extend(result["all_contents"])

            if result["needed_translated"]:
                self._categorize_all_needed_translated_set_contents.append(
                    result["needed_translated"]["categorize"]
                )
                self._all_needed_translated_set_contents.extend(
                    result["needed_translated"]["contents"]
                )

        # 去重和排序
        self._all_set_contents = sorted(list(set(self._all_set_contents)))
        self._all_needed_translated_set_contents = sorted(
            list(set(self._all_needed_translated_set_contents))
        )

        # 写入文件
        await self._write_set_contents_to_files()

        # 缓存并返回结果
        self._cached_translated_set_contents = (
            self._categorize_all_needed_translated_set_contents
        )
        return self._categorize_all_needed_translated_set_contents

    async def _write_set_contents_to_files(self) -> None:
        """将set内容写入文件"""
        os.makedirs(SELF_ROOT / "setto", exist_ok=True)

        async with aopen(
            SELF_ROOT / "setto" / "_set_contents.json", "w", encoding="utf-8"
        ) as fp:
            await fp.write(
                json.dumps(
                    self._categorize_all_set_contents, ensure_ascii=False, indent=2
                )
            )

        ALL_NEEDED_TRANSLATED_set_CONTENTS = (
            self._categorize_all_needed_translated_set_contents
        )
        async with aopen(
            SELF_ROOT / "setto" / "_needed_translated_set_contents.json",
            "w",
            encoding="utf-8",
        ) as fp:
            await fp.write(
                json.dumps(
                    self._categorize_all_needed_translated_set_contents,
                    ensure_ascii=False,
                    indent=2,
                )
            )

        self._all_set_contents = sorted(list(set(self._all_set_contents)))
        async with aopen(
            SELF_ROOT / "setto" / "_all_set_contents.json", "w", encoding="utf-8"
        ) as fp:
            await fp.write(
                json.dumps(self._all_set_contents, ensure_ascii=False, indent=2)
            )

        self._all_needed_translated_set_contents = sorted(
            list(set(self._all_needed_translated_set_contents))
        )
        async with aopen(
            SELF_ROOT / "setto" / "_all_needed_translated_set_contents.json",
            "w",
            encoding="utf-8",
        ) as fp:
            await fp.write(
                json.dumps(
                    self._all_needed_translated_set_contents,
                    ensure_ascii=False,
                    indent=2,
                )
            )

        return self._categorize_all_needed_translated_set_contents

    async def _fetch_all_set_content(self, file: Path) -> Optional[Dict]:
        """从单个文件中提取set内容"""
        async with aopen(file, "r", encoding="utf-8") as fp:
            raw = await fp.read()

        all_set_contents = re.findall(Regexes.SET_RUN_REGEXES.value, raw)

        if len(all_set_contents) < 2:
            return None

        all_heads, all_set_contents = [_[0] for _ in all_set_contents], [
            _[1] for _ in all_set_contents
        ]

        var_targets_dict = {}
        var_lines_dict = {}

        for idx, content in enumerate(all_set_contents):
            head = all_heads[idx]
            var, target, line = self._process_content(head, content)
            if not any([var, target, line]):
                continue

            if var in var_targets_dict:
                var_targets_dict[var].append(target)
            else:
                var_targets_dict[var] = [target]

            if var in var_lines_dict:
                var_lines_dict[var].append(line)
            else:
                var_lines_dict[var] = [line]

        if not var_targets_dict:
            return None

        categorize_content = {
            "path": str(file),
            "vars": [
                {"var": var, "targets": targets, "lines": lines}
                for (var, targets), (_, lines) in zip(
                    var_targets_dict.items(), var_lines_dict.items()
                )
            ],
        }

        formatted_set_contents = [f"set {content}" for content in all_set_contents]

        # 处理需要翻译的内容
        needed_translated_vars = []
        for (var, targets), (_, lines) in zip(
            var_targets_dict.items(), var_lines_dict.items()
        ):
            translatable_targets = []
            translatable_lines = []

            for idx, target in enumerate(targets):
                if self.is_needed_translated(target):
                    translatable_targets.append(target)
                    translatable_lines.append(lines[idx])

            if translatable_targets:
                needed_translated_vars.append(
                    {
                        "var": var,
                        "targets": translatable_targets,
                        "lines": translatable_lines,
                    }
                )

        needed_translated = None
        if needed_translated_vars:
            vars_needed_translated = {
                var_item["var"] for var_item in needed_translated_vars
            }

            needed_translated = {
                "categorize": {"path": str(file), "vars": needed_translated_vars},
                "contents": [
                    content
                    for content in formatted_set_contents
                    if content.split(" ")[1] in vars_needed_translated
                ],
            }

        return {
            "categorize": categorize_content,
            "all_contents": formatted_set_contents,
            "needed_translated": needed_translated,
        }

    def _process_content(
        self, head: str, content: str
    ) -> Tuple[Optional[str], Optional[Any], Optional[str]]:
        """处理内容，提取变量、目标值和原始行"""
        # 不需要处理的情况
        if content.endswith("++") or content.endswith("--") or "Time.set" in content:
            return None, None, None

        var = content
        target = content

        # 有明显分隔符的情况
        if re.findall(r"\sto", content):
            var, target = re.split(r"\sto", content, 1)
        elif re.findall(r"[+\-*/%]*=", content):
            var, target = re.split(r"[+\-*/%]*=", content, 1)
        elif re.findall(r"\sis\s", content):
            var, target = re.split(r"\sis\s", content, 1)
        # 处理函数调用
        elif any(f in content for f in FREQ_FUNCTIONS):
            for func in FREQ_FUNCTIONS:
                if func not in content:
                    continue
                vars_ = re.findall(Regexes.VARS_REGEX.value, content)
                if not vars_:
                    return None, None, None
                var = vars_[0]
                target = content.split(func)[-1]
                break
        # 括号包起来的就是 target
        elif "(" in content:
            vars_ = re.findall(Regexes.VARS_REGEX.value, content)
            if not vars_:
                return None, None, None
            var = vars_[0]
            target = "(".join(content.split("(")[1:]).rstrip(")")
        # 没括号，纯变量
        else:
            vars_ = re.findall(Regexes.VARS_REGEX.value, content)
            if not vars_:
                return None, None, None
            var = vars_[0]
            target = content

        var = var.strip()
        target = target.strip()
        line = f"<<{head} {content}>>"

        if target.isnumeric():
            target = float(target)
        elif target in {"true", "false"}:
            target = target == "true"
        elif target == "null":
            target = None

        return var, target, line

    @staticmethod
    def is_needed_translated(target: Any) -> bool:
        """判断目标值是否需要翻译"""
        return False if target is None else not isinstance(target, (float, bool))


__all__ = ["VariablesProcess"]
