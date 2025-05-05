import asyncio
import json
import os
import re
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

from aiofiles import open as aopen
from loguru import logger


class Regexes(Enum):
    # match $name
    MATCH_VARIABLES = re.compile(r"([$_][$A-Z_a-z][$0-9A-Z_a-z]*)")
    # match <<run>> or <<set>>
    # eg: <<set $name to "Alice">> -> "Alice"
    # <<run $inventory.push("item")>> -> "item"
    MATCH_SETS = re.compile(
        r'<<(run|set)(?:\s+((?:(?:\/\*[^*]*\*+(?:[^/*][^*]*\*+)*\/)|(?:\/\/.*\n)|(?:`(?:\\.|[^`\\\n])*?`)|(?:"(?:\\.|[^"\\\n])*?")|(?:\'(?:\\.|[^\'\\\n])*?\')|(?:\[(?:[<>]?[Ii][Mm][Gg])?\[[^\r\n]*?\]\]+)|[^>]|(?:>(?!>)))*?))?>>'
    )


class Dumper:
    def __init__(self):
        self._pending_translate: List[str] = []
        self._sets: List[str] = []
        self._sets_cache = None
        self._formatted_pending_translate: List[Dict] = []
        self._formatted_sets: List[Dict] = []
        self._formatted_variables: List[Dict] = []
        self._twee_files: Set[Path] = set()
        self._twee_variables: List[str] = []

        self._twee_functions = {
            ".push(",
            ".pushUnique(",
            ".delete(",
            ".deleteAt(",
            ".splice(",
        }

        asyncio.run(self._get_twees())

    """dump and cache variables from .twee files"""

    async def dump_variables(self) -> None:
        results = await asyncio.gather(
            *[self._dump_variables(file) for file in self._twee_files]
        )

        self._formatted_variables = [r for r in results if r]
        self._twee_variables = sorted(
            list(
                set(var for result in results if result for var in result["variables"])
            )
        )

        await self._cache_variables()

    """dump and cache <<set>> from .twee files"""

    async def dump_sets(self) -> List[Dict]:
        # try load from cache
        if self._sets_cache:
            return self._sets_cache
        cache_path = Path("lib/dicts/cache/padding_translate.json")
        try:
            if cache_path.exists():
                async with aopen(cache_path, "r", encoding="utf-8") as fp:
                    data = json.loads(await fp.read())
                self._sets_cache = data
                return data
        except (IOError, json.JSONDecodeError) as e:
            logger.info(f"No cache founded in {cache_path}: {e}")

        # dump sets
        results = await asyncio.gather(
            *[self._dump_sets(file) for file in self._twee_files]
        )

        # deduplication
        for result in results:
            if not result:
                continue
            self._formatted_sets.append(result["categorize"])
            self._sets.extend(result["all_contents"])
            if result["padding_translate"]:
                self._formatted_pending_translate.append(
                    result["padding_translate"]["categorize"]
                )
                self._pending_translate.extend(result["padding_translate"]["contents"])

        self._sets = sorted(list(set(self._sets)))
        self._pending_translate = sorted(list(set(self._pending_translate)))

        await self._cache_sets()

        self._sets_cache = self._formatted_pending_translate
        return self._formatted_pending_translate

    """Extract and process <<set>> and <<run>> statements from a Twee file"""

    async def _dump_sets(self, file: Path) -> Optional[Dict]:
        # Extract raw content and set statements
        extraction_result = await self._extract_set_statements(file)
        if not extraction_result:
            return None

        heads, sets = extraction_result

        # Process variables and targets
        process_result = self._process_variable_targets(heads, sets)
        if not process_result:
            return None

        var_targets_dict, var_lines_dict, formatted_set_contents = process_result

        # Create formatted content structure
        format_contents = {
            "path": str(file),
            "vars": [
                {"var": var, "targets": targets, "lines": lines}
                for (var, targets), (_, lines) in zip(
                    var_targets_dict.items(), var_lines_dict.items()
                )
            ],
        }

        # Find content that needs translation
        padding_translate = self._find_translatable_content(
            var_targets_dict, var_lines_dict, formatted_set_contents, file
        )

        return {
            "categorize": format_contents,
            "all_contents": formatted_set_contents,
            "padding_translate": padding_translate,
        }

    """Extract <<set>> and <<run>> statements from a file"""

    async def _extract_set_statements(
        self, file: Path
    ) -> Optional[Tuple[List[str], List[str]]]:
        logger.info(f"Extracting <<set>> statements from {file}")

        try:
            async with aopen(file, "r", encoding="utf-8") as fp:
                raw = await fp.read()

            sets = re.findall(Regexes.MATCH_SETS.value, raw)
            if len(sets) < 2:
                logger.warning(f"No <<set>> found in {file}")
                return None

            heads = [item[0] for item in sets]
            content_parts = [item[1] for item in sets]
            return heads, content_parts

        except IOError as e:
            logger.error(f"Failed to read {file}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error processing {file}: {e}")
            return None

    """Process variable targets from set statements"""

    def _process_variable_targets(
        self, heads: List[str], sets: List[str]
    ) -> Optional[Tuple[Dict, Dict, List[str]]]:
        var_targets_dict = {}
        var_lines_dict = {}

        for idx, content in enumerate(sets):
            head = heads[idx]
            var, target, line = self._process_content(head, content)
            if not any([var, target, line]):
                continue

            # Store variables and targets
            if var in var_targets_dict:
                var_targets_dict[var].append(target)
            else:
                var_targets_dict[var] = [target]

            if var in var_lines_dict:
                var_lines_dict[var].append(line)
            else:
                var_lines_dict[var] = [line]

        if not var_targets_dict:
            logger.debug(f"No valid variables found in {len(sets)} set statements")
            return None

        formatted_set_contents = [f"set {content}" for content in sets]
        return var_targets_dict, var_lines_dict, formatted_set_contents

    """Find content that needs translation"""

    def _find_translatable_content(
        self,
        var_targets_dict: Dict,
        var_lines_dict: Dict,
        formatted_set_contents: List[str],
        file: Path,
    ) -> Optional[Dict]:
        padding_translate_vars = []

        for (var, targets), (_, lines) in zip(
            var_targets_dict.items(), var_lines_dict.items()
        ):
            translatable_targets = []
            translatable_lines = []

            for idx, target in enumerate(targets):
                if self.is_padding_translate(target):
                    translatable_targets.append(target)
                    translatable_lines.append(lines[idx])

            if translatable_targets:
                padding_translate_vars.append(
                    {
                        "var": var,
                        "targets": translatable_targets,
                        "lines": translatable_lines,
                    }
                )

        if not padding_translate_vars:
            return None

        vars_padding_translate = {
            var_item["var"] for var_item in padding_translate_vars
        }

        return {
            "categorize": {"path": str(file), "vars": padding_translate_vars},
            "contents": [
                content
                for content in formatted_set_contents
                if content.split(" ")[1] in vars_padding_translate
            ],
        }

    """Dump variables from a Twee file"""

    async def _dump_variables(self, file: Path) -> Optional[Dict]:
        async with aopen(file, "r", encoding="utf-8") as fp:
            raw = await fp.read()

        variables = re.findall(Regexes.MATCH_VARIABLES.value, raw)
        if not variables:
            return None

        return {
            "path": str(file).split("\\game\\")[1],
            "variables": sorted(list(set(variables))),
        }

    """Get all .twee files absolute paths"""

    async def _get_twees(self) -> Set[Path]:
        self._twee_files.clear()
        for root, _, file_list in os.walk("lib/degrees-of-lewdity-plus/game"):
            for file in file_list:
                if file.endswith(".twee"):
                    self._twee_files.add(Path(root).absolute() / file)
        return self._twee_files

    async def _cache_variables(self) -> None:
        try:
            async with aopen(
                "lib/dicts/cache/_formatted_variables.json", "w", encoding="utf-8"
            ) as fp:
                await fp.write(
                    json.dumps(self._formatted_variables, ensure_ascii=False, indent=2)
                )

            async with aopen(
                "lib/dicts/cache/_variables.json", "w", encoding="utf-8"
            ) as fp:
                await fp.write(
                    json.dumps(self._twee_variables, ensure_ascii=False, indent=2)
                )
        except IOError as e:
            logger.error(f"Failed to cache files: {e}")
            raise

    async def _cache_variables_notations(self) -> None:
        filepath = Path("lib/dicts/cache/variables_notation.json")

        old_data = {}
        if filepath.exists():
            async with aopen(filepath, "r", encoding="utf-8") as fp:
                content = await fp.read()
                old_data = json.loads(content)

        new_data = {
            var: {"var": var, "desc": "", "canBeTranslated": False}
            for var in self._twee_variables
        }

        if old_data:
            for key, items in old_data.items():
                if items["desc"]:
                    new_data[key] = items

        async with aopen(filepath, "w", encoding="utf-8") as fp:
            await fp.write(json.dumps(new_data, ensure_ascii=False, indent=2))

    async def _cache_sets(self) -> None:
        try:
            async with aopen(
                "lib/dicts/cache/_formatted_sets.json", "w", encoding="utf-8"
            ) as fp:
                await fp.write(
                    json.dumps(self._formatted_sets, ensure_ascii=False, indent=2)
                )

            async with aopen("lib/dicts/cache/_sets.json", "w", encoding="utf-8") as fp:
                await fp.write(json.dumps(self._sets, ensure_ascii=False, indent=2))

            async with aopen(
                "lib/dicts/cache/_formatted_pending_translate_sets.json",
                "w",
                encoding="utf-8",
            ) as fp:
                await fp.write(
                    json.dumps(
                        self._formatted_pending_translate, ensure_ascii=False, indent=2
                    )
                )

            async with aopen(
                "lib/dicts/cache/_pending_translate_sets.json", "w", encoding="utf-8"
            ) as fp:
                await fp.write(
                    json.dumps(self._pending_translate, ensure_ascii=False, indent=2)
                )
        except IOError as e:
            logger.error(f"Failed to cache files: {e}")
            raise

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
        elif any(f in content for f in self._twee_functions):
            for func in self._twee_functions:
                if func not in content:
                    continue
                vars_ = re.findall(Regexes.MATCH_VARIABLES.value, content)
                if not vars_:
                    return None, None, None
                var = vars_[0]
                target = content.split(func)[-1]
                break
        # 括号包起来的是 target
        elif "(" in content:
            vars_ = re.findall(Regexes.MATCH_VARIABLES.value, content)
            if not vars_:
                return None, None, None
            var = vars_[0]
            target = "(".join(content.split("(")[1:]).rstrip(")")
        # 没括号，纯变量
        else:
            vars_ = re.findall(Regexes.MATCH_VARIABLES.value, content)
            if not vars_:
                return None, None, None
            var = vars_[0]
            target = content

        var = var.strip()
        target = target.strip()
        line = f"<<{head} {content}>>"

        # 转换目标值类型
        if target.isnumeric():
            target = float(target)
        elif target in {"true", "false"}:
            target = target == "true"
        elif target == "null":
            target = None

        return var, target, line

    @staticmethod
    def is_padding_translate(target: Any) -> bool:
        """判断目标值是否需要翻译"""
        return False if target is None else not isinstance(target, (float, bool))
