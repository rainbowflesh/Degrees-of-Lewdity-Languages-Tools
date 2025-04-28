from enum import Enum
import re
from pathlib import Path

from .consts import *
from .tools.process_variables import VariablesProcess


class ParseTwee:
    def __init__(self, lines: list[str], filepath: Path):
        self._lines = lines
        self._filepath = filepath

        self._filename = self._filepath.name  # 文件名
        self._filedir = self._filepath.parent  # 文件夹

        self._categorize_all_set_run: list[dict] | None = None
        self._set_run_bool_list = []

    @property
    def pre_bool_list(self):
        return self._set_run_bool_list

    async def pre_parse_set_run(self, debug: bool = False):
        varp = VariablesProcess()
        await varp.search_twee_files()
        self._categorize_all_set_run = await varp.fetch_all_set_content()

        compared_vars = next(
            (
                item["vars"]
                for item in self._categorize_all_set_run
                if Path(item["path"]) == self._filepath
            ),
            None,
        )
        if not compared_vars:
            return []

        self._set_run_bool_list = []
        for line in self._lines:
            s = line.strip()
            if not s or ("<<set " not in s and "<<run " not in s):
                self._set_run_bool_list.append(False)
                continue
            found = False
            for var_item in compared_vars:
                if (
                    f"<<set {var_item['var']}" in s or f"run {var_item['var']}" in s
                ) and any(var_line in s for var_line in var_item["lines"]):
                    found = True
                    break
            self._set_run_bool_list.append(found)

        if debug:
            for idx, flag in enumerate(self._set_run_bool_list):
                if flag:
                    print(f"{idx+1}: {self._lines[idx].rstrip()}")

        return self._set_run_bool_list

    def parse(self) -> list[bool]:
        dir_name = self._filedir.name
        parent_name = self._filedir.parent.name

        # Check directory prefixes first (highest priority)
        if any(prefix in dir_name for prefix in ["overworld-", "loc-", "special-"]):
            return self._parse_normal()

        # Check directories where parent name matters
        parent_dir_handlers = {
            "00-framework-tools": self.parse_framework,
            "base-combat": self.parse_base_combat,
            "base-system": self.parse_base_system,
        }
        for dir_key, handler in parent_dir_handlers.items():
            if dir_key in (dir_name, parent_name):
                return handler()

        # Direct directory name mapping
        dir_handlers = {
            "01-config": self.parse_config,
            "04-Variables": self.parse_variables,
            "base-clothing": self.parse_base_clothing,
            "flavour-text-generators": self.parse_flavour_text,
        }

        # Use mapped handler or default to _parse_normal
        handler = dir_handlers.get(dir_name, self._parse_normal)
        return handler()

    """00-framework-tools"""

    def parse_framework(self):
        if "waiting-room.twee" == self._filename:
            return self._parse_waiting_room()
        return self._parse_normal()

    def _parse_waiting_room(self):
        """很少很简单"""
        return [
            line.strip()
            and (
                "<span " in line.strip()
                or (not line.startswith("<") and "::" not in line)
            )
            for line in self._lines
        ]

    """√ config """

    def parse_config(self):
        """01-config"""
        if "start.twee" == self._filename:
            return self._parse_start()
        elif "versionInfo.twee" == self._filename:
            return self._parse_version_info()
        return self._parse_normal()

    def _parse_start(self):
        """很少很简单"""
        return [
            line.strip()
            and (
                "<span " in line.strip()
                or "<<link [[" in line.strip()
                or any(re.findall(r"^(\w|- )", line.strip()))
            )
            for line in self._lines
        ]

    def _parse_version_info(self):
        """很少很简单"""
        return [
            line.strip()
            and (
                line.strip().startswith("<h")
                or line.strip().startswith("<p")
                or line.strip().startswith("[[")
            )
            for line in self._lines
        ]

    """√ variables """

    def parse_variables(self):
        """04-Variables"""
        if "canvasmodel-example.twee" == self._filename:
            return self._parse_canvasmodel()
        elif "variables-versionUpdate.twee" == self._filename:
            return self._parse_version_update()
        elif "variables-passageFooter.twee" == self._filename:
            return self._parse_passage_footer()
        elif "pregnancyVar.twee" == self._filename:
            return self.parse_type_only({'"name": '})
        elif "variables-static.twee" == self._filename:
            return self._parse_variables_static()
        elif "hair-styles.twee" == self._filename:
            return self.parse_type_only("name_cap")
        return self._parse_normal()

    def _parse_canvasmodel(self):
        """只有一个<<link"""
        return self.parse_type_only("<<link [[")

    def _parse_version_update(self):
        """只有 <span 和 <<link"""
        return self.parse_type_only(
            {"<span ", "<<link ", "replace(/[^a-zA-Z", "if $earSlime.event"}
        )

    def _parse_passage_footer(self):
        """有点麻烦"""
        results = []
        multirow_error_flag = False
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            """跨行error，逆天"""
            if line in ["<<error {", "<<script>>"]:
                multirow_error_flag = True
                results.append(False)
                continue
            elif line in ["}>>", "<</script>>"]:
                multirow_error_flag = False
                results.append(False)
                continue
            elif multirow_error_flag:
                results.append(False)
                continue

            if self.is_comment(line) or self.is_event(line) or self.is_only_marks(line):
                results.append(False)
            elif "<span" in line or "<<link" in line or not line.startswith("<"):
                results.append(True)
            else:
                results.append(False)
        return results

    def _parse_variables_static(self):
        """variables-static.twee"""
        results = []
        multirow_set_flag = False
        multirow_comment_flag = False

        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            """跨行注释，逆天"""
            if line in ["/*", "<!--"] or (
                any(line.startswith(_) for _ in {"/*", "<!--"})
                and all(_ not in line for _ in {"*/", "-->"})
            ):
                multirow_comment_flag = True
                results.append(False)
                continue
            elif multirow_comment_flag and (
                line in ["*/", "-->"] or any(line.endswith(_) for _ in {"*/", "-->"})
            ):
                multirow_comment_flag = False
                results.append(False)
                continue
            elif multirow_comment_flag:
                results.append(False)
                continue

            if "<<set setup." in line:
                multirow_set_flag = True
                results.append(False)
                continue
            elif multirow_set_flag and "}>>" in line:
                multirow_set_flag = False
                results.append(False)
                continue
            elif multirow_set_flag:
                if self.is_comment(line):
                    results.append(False)
                    continue
                results.append(True)
                continue

            if "setup.breastsizes" in line:
                results.append(True)
            elif '"name": "' in line or '"message": "' in line:
                results.append(True)
            else:
                results.append(False)
        return results

    """√ base-clothing """

    def parse_base_clothing(self):
        """base-clothing"""
        if "captiontext.twee" == self._filename:
            return self._parse_captiontext()
        elif "clothing-sets.twee" == self._filename:
            return self._parse_clothing_sets()
        elif "images.twee" == self._filename:
            return self.parse_type_only("<span ")
        elif "init.twee" == self._filename:
            return self.parse_type_only({"desc:", "V.outfit = ", 'word:"', 'name: "'})
        elif "wardrobes.twee" == self._filename:
            return self._parse_wardrobes()
        return self._parse_normal()

    def _parse_captiontext(self):
        """有点麻烦"""
        results = []
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            if self.is_comment(line) or self.is_event(line) or self.is_only_marks(line):
                results.append(False)
            elif self.is_tag_span(line) or self.is_widget_print(line):
                results.append(True)
            elif "<<run $_output " in line:
                results.append(True)
            elif self.is_only_widgets(line):
                results.append(False)
            else:
                results.append(True)

        return results

    def _parse_clothing_sets(self):
        """好麻烦"""
        results = []
        multirow_comment_flag = False
        multirow_json_flag = False
        for idx, line in enumerate(self._lines):
            line = line.strip()
            if not line:
                results.append(False)
                continue

            """跨行注释，逆天"""
            if line in ["/*", "<!--"] or (
                any(line.startswith(_) for _ in {"/*", "<!--"})
                and all(_ not in line for _ in {"*/", "-->"})
            ):
                multirow_comment_flag = True
                results.append(False)
                continue
            elif multirow_comment_flag and (
                line in ["*/", "-->"] or any(line.endswith(_) for _ in {"*/", "-->"})
            ):
                multirow_comment_flag = False
                results.append(False)
                continue
            elif multirow_comment_flag:
                results.append(False)
                continue

            """就为这一个单开一档，逆天"""
            if (
                line.startswith("<<run ") or line.startswith("<<set ")
            ) and ">>" not in line:
                multirow_json_flag = True
                results.append(False)
                continue
            elif multirow_json_flag and any(_ in line for _ in {"}>>", "})>>"}):
                multirow_json_flag = False
                results.append(False)
                continue
            elif multirow_json_flag and any(
                _ in line
                for _ in {
                    '"start"',
                    '"joiner"',
                    '"end"',
                    "replace(/[^a-zA-Z",
                    "notEquippedItem.name",
                }
            ):
                results.append(True)
                continue
            elif multirow_json_flag:
                results.append(False)
                continue

            if self.is_comment(line) or self.is_event(line) or self.is_only_marks(line):
                results.append(False)
            elif (
                self.is_tag_span(line)
                or self.is_tag_label(line)
                or self.is_widget_option(line)
                or self.is_widget_link(line)
                or "$_value2.name" in line
                or "<<print $_label" in line
                or "<<= $_label" in line
                or "<<- $_label" in line
                or "(No access)" in line
                or self.is_widget_print(line)
                or "replace(/[^a-zA-Z" in line
                or "notEquippedItem.name" in line
            ):
                results.append(True)
            elif self.is_only_widgets(line):
                results.append(False)
            else:
                results.append(True)
        return results

    def _parse_wardrobes(self):
        """多了一个<<wearlink_norefresh " """
        results = []
        multirow_if_flag = False
        multirow_set_flag = False
        multirow_run_flag = False
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            """跨行if，逆天"""
            if line.startswith("<<if ") and ">>" not in line:
                multirow_if_flag = True
                results.append(False)
                continue
            elif multirow_if_flag and ">>" in line:
                multirow_if_flag = False
                results.append(False)
                continue
            elif multirow_if_flag:
                results.append(False)
                continue

            """跨行set，逆天"""
            if (
                line.startswith("<<set _itemStats ")
                or line.startswith("<<set _sortedItemColors")
            ) and ">>" not in line:
                multirow_set_flag = True
                results.append(False)
                continue
            elif multirow_set_flag and line in {"]>>", "})>>", "}>>"}:
                multirow_set_flag = False
                results.append(False)
                continue
            elif multirow_set_flag:
                results.append(False)
                continue

            """跨行run，逆天"""
            if line.startswith("<<run ") and ">>" not in line:
                multirow_run_flag = True
                results.append(False)
                continue
            elif multirow_run_flag and line in {"})>>", "}>>", ")>>", "]>>", "});>>"}:
                multirow_run_flag = False
                results.append(False)
                continue
            elif multirow_run_flag:
                results.append(False)
                continue

            if self.is_comment(line) or self.is_event(line) or self.is_only_marks(line):
                results.append(False)
            elif (
                self.is_tag_span(line)
                or "<<wearlink_norefresh" in line
                or ">>." in line
                or self.is_tag_label(line)
                or self.is_widget_print(line)
                or self.is_widget_option(line)
                or self.is_widget_link(line)
                or "__" in line
                or '? "' in line
                or ".replace(/[^a-zA-Z" in line
                or "<<clothingicon" in line
            ):
                results.append(True)
            elif self.is_only_widgets(line) or self.is_json_line(line):
                results.append(False)
            else:
                results.append(True)
        return results

    """√ base-combat """

    def parse_base_combat(self):
        """base-combat"""
        if "actions.twee" == self._filename or "actions" in self._filename:
            return self._parse_actions()
        if "stalk.twee" == self._filename:
            return self._parse_stalk()
        elif "generation.twee" in self._filename:
            return self._parse_generation()
        elif "tentacle-adv.twee" == self._filename:
            return self._parse_tentacle_adv()
        elif "tentacles.twee" == self._filename:
            return self._parse_tentacles()
        elif "effects.twee" == self._filename:
            return self._parse_combat_effects()
        elif self._filename in {
            "npc-generation.twee",
            "npc-damage.twee",
        }:
            return self.parse_type_only(
                {
                    "<span ",
                    "<<set $NPCList[_n].fullDescription",
                    "<<set $NPCList[_n].breastdesc",
                }
            )
        elif "speech-sydney.twee" == self._filename:
            return self._parse_speech_sydney()
        elif "speech.twee" == self._filename:
            return self._parse_speech()
        elif "struggle.twee" == self._filename:
            return self._parse_struggle()
        elif "swarms.twee" == self._filename:
            return self._parse_swarms()
        elif "swarm-effects.twee" == self._filename:
            return self._parse_swarm_effects()
        elif "widgets.twee" == self._filename:
            return self._parse_combat_widgets()
        elif "images.twee" == self._filename:
            return self._parse_combat_images()
        return self._parse_normal()

    def _parse_actions(self):
        """麻烦"""
        results = []
        multirow_if_flag = False
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            """跨行if，逆天"""
            if line.startswith("<<if ") and ">>" not in line:
                multirow_if_flag = True
                results.append(False)
                continue
            elif multirow_if_flag and ">>" in line:
                multirow_if_flag = False
                results.append(False)
                continue
            elif multirow_if_flag:
                results.append(False)
                continue

            if (
                self.is_comment(line)
                or self.is_event(line)
                or self.is_only_marks(line)
                or line == "<<print either("
                or line == "<<= either("
                or line == "<<- either("
            ):
                results.append(False)
            elif (
                self.is_tag_span(line)
                or self.is_widget_print(line)
                or self.is_tag_label(line)
                or self.is_widget_option(line)
                or "<<run delete " in line
                or "<<if $NPCList" in line
                or "<<if ($NPCList" in line
                or "<<takeKissVirginityNamed" in line
                or "_smollertext.includes" in line
                or "$NPCList[_j].breastsdesc." in line
                or "$NPCList[_j].breastdesc." in line
            ):
                results.append(True)
            elif self.is_only_widgets(line) or self.is_json_line(line):
                results.append(False)
            else:
                results.append(True)
        return results

    def _parse_stalk(self):
        """麻烦"""
        results = []
        multirow_if_flag = False
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            """跨行if，逆天"""
            if line.startswith("<<if ") and ">>" not in line:
                multirow_if_flag = True
                results.append(False)
                continue
            elif multirow_if_flag and ">>" in line:
                multirow_if_flag = False
                results.append(False)
                continue
            elif multirow_if_flag:
                results.append(False)
                continue

            if (
                self.is_comment(line)
                or self.is_event(line)
                or self.is_only_marks(line)
                or line == "<<print either("
                or line == "<<= either("
                or line == "<<- either("
            ):
                results.append(False)
            elif (
                self.is_tag_span(line)
                or "<<skill_difficulty " in line
                or ">>." in line
                or "<<print $NPCList[0].fullDescription>>" in line
                or "<<= $NPCList[0].fullDescription>>" in line
                or "<<- $NPCList[0].fullDescription>>" in line
            ):
                results.append(True)
            elif self.is_only_widgets(line) or self.is_json_line(line):
                results.append(False)
            else:
                results.append(True)
        return results

    def _parse_generation(self):
        """只有 <span"""
        results = []
        multirow_d_flag = False
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            if "set _d to" in line:
                multirow_d_flag = True
                results.append(True)
                continue
            elif multirow_d_flag and "]>>" in line:
                multirow_d_flag = False
                results.append(False)
                continue
            elif multirow_d_flag:
                results.append(True)
                continue

            if self.is_tag_span(line):
                results.append(True)
            else:
                results.append(False)
        return results

    def _parse_tentacle_adv(self):
        """有点麻烦"""
        results = []
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            if (
                self.is_comment(line)
                or self.is_event(line)
                or self.is_only_marks(line)
                or line == "_tentacle.desc"
            ):
                results.append(False)
            elif (
                self.is_tag_span(line)
                or "<<actionstentacleadvcheckbox" in line
                or any(re.findall(r"<<if\s.*?>>\w", line))
            ):
                results.append(True)
            elif (
                ".desc.includes" in line
                or "fullDesc.includes" in line
                or "<<takeHandholdingVirginity" in line
            ):
                results.append(True)
            elif self.is_only_widgets(line):
                results.append(False)
            else:
                results.append(True)
        return results

    def _parse_tentacles(self):
        """有点麻烦"""
        results = []
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            if self.is_comment(line) or self.is_event(line) or self.is_only_marks(line):
                results.append(False)
            elif any(
                _ in line
                for _ in {
                    "_tentacledata.desc",
                    "fullDesc.includes",
                    '{"desc":',
                    "you",
                    "You",
                    "YOU",
                }
            ):
                results.append(True)
            elif self.is_only_widgets(line):
                results.append(False)
            else:
                results.append(False)
        return results

    def _parse_combat_effects(self):
        """有点麻烦"""
        results = []
        multirow_widget_flag = False
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            """跨行注释/script，逆天"""
            if line in ["/*", "<!--"] or (
                any(line.startswith(_) for _ in {"/*", "<!--"})
                and all(_ not in line for _ in {"*/", "-->"})
            ):
                multirow_widget_flag = True
                results.append(False)
                continue
            elif (
                multirow_widget_flag
                and line in ["*/", "-->"]
                or any(line.endswith(_) for _ in {"*/", "-->"})
            ):
                multirow_widget_flag = False
                results.append(False)
                continue
            elif multirow_widget_flag:
                results.append(False)
                continue

            if self.is_comment(line) or self.is_event(line) or self.is_only_marks(line):
                results.append(False)
            elif self.is_tag_span(line) or self.is_widget_print(line):
                results.append(True)
            elif any(
                _ in line for _ in {"<<wheeze", ">>.", "$worn.", "fullDescription"}
            ):
                results.append(True)
            elif (
                self.is_only_widgets(line)
                or self.is_json_line(line)
                or ("<<set " in line and ">>" not in line)
            ):
                results.append(False)
            else:
                results.append(True)
        return results

    def _parse_speech_sydney(self):
        """有点麻烦"""
        results = []
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            if self.is_comment(line) or self.is_event(line) or self.is_only_marks(line):
                results.append(False)
            elif line.startswith("`"):
                results.append(True)
            elif self.is_only_widgets(line) or ("<<set " in line and ">>" not in line):
                results.append(False)
            else:
                results.append(True)
        return results

    def _parse_speech(self):
        """有点麻烦"""
        results = []
        multirow_set_flag = False
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            if line.startswith("<<set ") and ">>" not in line:
                multirow_set_flag = True
                results.append(True)
                continue
            elif multirow_set_flag and line.endswith("]>>"):
                multirow_set_flag = False
                results.append(True)
                continue
            elif multirow_set_flag:
                results.append(True)
                continue

            if self.is_comment(line) or self.is_event(line) or self.is_only_marks(line):
                results.append(False)
            elif (
                line.startswith('"')
                or line.startswith("`")
                or line.startswith("[")
                or line.startswith("<<default>>")
                or line.startswith("<<He>> ")
                or line.startswith("<<bHe>> ")
                or "<span " in line
                or any(re.findall(r"<<case \d", line))
            ):
                results.append(True)
            elif self.is_only_widgets(line):
                results.append(False)
            else:
                results.append(False)
        return results

    def _parse_struggle(self):
        """有点麻烦"""
        results = []
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            if (
                self.is_comment(line)
                or self.is_event(line)
                or self.is_only_marks(line)
                or self.is_json_line(line)
            ):
                results.append(False)
            elif self.is_widget_print(line):
                results.append(True)
            elif self.is_only_widgets(line):
                results.append(False)
            else:
                results.append(True)
        return results

    def _parse_swarms(self):
        """有点麻烦"""
        results = []
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue
            if re.findall(r"\$worn\..*?\.name", line):
                results.append(True)
            elif (
                self.is_comment(line)
                or self.is_event(line)
                or self.is_only_marks(line)
                or self.is_json_line(line)
            ):
                results.append(False)
            elif self.is_only_widgets(line):
                results.append(False)
            else:
                results.append(True)
        return results

    def _parse_swarm_effects(self):
        results = []
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            if self.is_comment(line) or self.is_event(line) or self.is_only_marks(line):
                results.append(False)
            elif "<" in line and (self.is_tag_span(line) or self.is_tag_label(line)):
                results.append(True)
            elif "<" in line and (
                self.is_only_widgets(line) or self.is_json_line(line)
            ):
                results.append(False)
            else:
                results.append(True)
        return results

    def _parse_combat_widgets(self):
        """有点麻烦"""
        results = []
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            if (
                self.is_comment(line)
                or self.is_event(line)
                or self.is_only_marks(line)
                or self.is_json_line(line)
            ):
                results.append(False)
            elif self.is_tag_span(line):
                results.append(True)
            elif (
                "<<if $_npc" in line
                or "<<if ($NPCList[$_" in line
                or "<<if $NPCList[$_" in line
            ):
                results.append(True)
            elif self.is_only_widgets(line):
                results.append(False)
            else:
                results.append(True)
        return results

    def _parse_combat_images(self):
        results = []
        for idx, line in enumerate(self._lines):
            line = line.strip()
            if not line:
                results.append(False)
                continue

            if "if $NPCList[$_target" in line:
                results.append(True)
            else:
                results.append(False)
        return results

    """ base-system """

    def parse_base_system(self):
        """base-system"""
        if "characteristics.twee" == self._filename:
            return self._parse_characteristic()
        elif "social.twee" == self._filename:
            return self._parse_social()
        elif "traits.twee" == self._filename:
            return self.parse_type_only(
                {
                    "name:",
                    "text:",
                    "title:",
                    "<summary",
                    "<<option",
                    'return "',
                    "Display Format:",
                    "<label>S",
                    "<<link",
                    "return `",
                    "result",
                    "<span",
                }
            )
        elif "bodywriting.twee" == self._filename:
            return self._parse_body_writing()
        elif "bodywriting-objects.twee" == self._filename:
            return self.parse_type_only({"writing: ", "special: ", "sprites: "})
        elif "caption.twee" == self._filename:
            return self._parse_caption()
        elif self._filename in {
            "deviancy.twee",
            "exhibitionism.twee",
            "promiscuity.twee",
        }:
            return self._parse_sex_stat()
        elif "fame.twee" == self._filename:
            return self.parse_type_only({"<<set $_output"})
        elif "feats.twee" == self._filename:
            return self._parse_feats()
        elif "images.twee" == self._filename:
            return self.parse_type_only_regex(r"<span.*?>[\"\w]")
        elif "mobile-stats.twee" == self._filename:
            return self.parse_type_only("<span>")
        elif "name-list.twee" == self._filename:
            return self.parse_type_startwith('"')
        elif "nicknames.twee" == self._filename:
            return self._parse_nicknames()
        elif "plant-objects.twee" == self._filename:
            return self.parse_type_only({"plural:", "singular:"})
        elif "radio.twee" == self._filename:
            return self._parse_radio()
        elif "settings.twee" == self._filename:
            return self._parse_settings()
        elif "skill-difficulties.twee" == self._filename:
            return self._parse_skill_difficulties()
        elif "sleep.twee" == self._filename:
            return self._parse_sleep()
        elif "stat-changes.twee" == self._filename:
            return self.parse_type_only("<span ")
        elif "tending.twee" == self._filename:
            return self._parse_tending()
        elif "text.twee" == self._filename:
            return self._parse_system_text()
        elif "time.twee" == self._filename:
            return self.parse_type_only("<span ")
        elif "tips.twee" == self._filename:
            return self.parse_type_startwith({'"', "<h3>", "<<link"})
        elif "transformations.twee" == self._filename:
            return self._parse_transformations()
        elif "widgets.twee" == self._filename:
            return self._parse_system_widgets()
        elif "named-npcs.twee" == self._filename:
            return self._parse_named_npcs()
        elif "persistent-npcs.twee" == self._filename:
            return self._parse_persistent_npcs()
        return self._parse_normal()

    def _parse_characteristic(self):
        """有点麻烦"""
        results = []
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            if self.is_comment(line) or self.is_event(line) or self.is_only_marks(line):
                results.append(False)
            elif (
                "description: " in line
                or "{ name :" in line
                or "preText: " in line
                or 'level: "None"' in line
                or line
                == '<<if $_number isnot "an unknown number of" and $_number isnot "more than one" and $_number gt 1>>'
                or self.is_tag_span(line)
                or "bad.pushUnique" in line
                or "good.pushUnique" in line
                or ">>." in line
                or "$_source.push" in line
                or "$_arousal.push" in line
            ):
                results.append(True)
            elif (
                self.is_only_widgets(line)
                or ("<<set " in line and ">>" not in line and "preText: " not in line)
                or line == "states : ["
            ):
                results.append(False)
            else:
                results.append(True)
        return results

    def _parse_social(self):
        """有点麻烦"""
        results = []
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            if self.is_comment(line) or self.is_event(line) or self.is_only_marks(line):
                results.append(False)
            elif (
                "description: '" in line
                or self.is_tag_span(line)
                or "preText: " in line
            ):
                results.append(True)
            elif self.is_json_line(line) or self.is_only_widgets(line):
                results.append(False)
            else:
                results.append(True)
        return results

    def _parse_body_writing(self):
        """有点麻烦"""
        results = []
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            if self.is_comment(line) or self.is_event(line) or self.is_only_marks(line):
                results.append(False)
            elif self.is_tag_span(line) or self.is_widget_print(line):
                results.append(True)
            elif self.is_only_widgets(line):
                results.append(False)
            else:
                results.append(True)
        return results

    def _parse_caption(self):
        """竟然还有css"""
        results = []
        multirow_style_flag = False
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            """跨行注释/script，逆天"""
            if line == "<style>":
                multirow_style_flag = True
                results.append(False)
                continue
            elif line == "</style>":
                multirow_style_flag = False
                results.append(False)
                continue
            elif multirow_style_flag:
                results.append(False)
                continue

            if self.is_comment(line) or self.is_event(line) or self.is_only_marks(line):
                results.append(False)
            elif (
                self.is_tag_span(line)
                or self.is_widget_button(line)
                or self.is_widget_print(line)
            ):
                results.append(True)
            elif self.is_only_widgets(line):
                results.append(False)
            else:
                results.append(True)
        return results

    def _parse_sex_stat(self):
        """纯文本 和 span"""
        results = []
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            if self.is_tag_span(line):
                results.append(True)
            elif line.startswith("<<"):
                results.append(False)
            elif "::" in line:
                results.append(False)
            elif self.is_comment(line):
                results.append(False)
            elif line.replace("<br>", "") == "":
                results.append(False)
            else:
                results.append(True)

        return results

    def _parse_feats(self):
        """json"""
        results = []
        json_flag = False
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            if line in {"missing:{", "name:{"}:
                json_flag = True
                results.append(False)
            elif line == "},":
                json_flag = False
                results.append(False)
            elif json_flag:
                results.append(True)
            else:
                results.append(False)

        return results

    def _parse_named_npcs(self):
        """有点麻烦"""
        results = []
        multirow_comment_flag = False
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            """跨行注释/set，逆天"""
            if line in ["/*", "<!--"] or (
                any(line.startswith(_) for _ in {"/*", "<!--"})
                and all(_ not in line for _ in {"*/", "-->"})
            ):
                multirow_comment_flag = True
                results.append(False)
                continue
            elif multirow_comment_flag and (
                line in ["*/", "-->"] or any(line.endswith(_) for _ in {"*/", "-->"})
            ):
                multirow_comment_flag = False
                results.append(False)
                continue
            elif multirow_comment_flag:
                results.append(False)
                continue

            if self.is_comment(line) or self.is_event(line) or self.is_only_marks(line):
                results.append(False)
            elif line == "_npc":
                results.append(True)
            elif (
                "<<set $NPCList[_ii].breastsdesc" in line
                or "<<set $NPCList[_ii].breastdesc" in line
                or "<<set $NPCList[_ii].penisdesc" in line
            ):
                results.append(True)
            elif "<<set $NPCName[_i" in line and all(
                _ not in line
                for _ in {
                    ".gender",
                    ".pronoun",
                    "size to",
                    "1>>",
                    "0>>",
                    ".outfits.pushUnique(",
                    "_val",
                    "_rollover",
                    "9>>",
                    "random",
                    "undefined",
                    "delete",
                    "crossdressing",
                }
            ):
                results.append(True)
            elif self.is_tag_span(line):
                results.append(True)
            elif self.is_only_widgets(line):
                results.append(False)
            else:
                results.append(True)
        return results

    def _parse_nicknames(self):
        """只有 " """
        results = []
        multirow_set_flag = False
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            if line.startswith("<<set ") and ">>" not in line:
                multirow_set_flag = True
                results.append(False)
                continue
            elif multirow_set_flag and line in {"]>>", "})>>", "}>>", ")>>"}:
                multirow_set_flag = False
                results.append(False)
                continue
            elif multirow_set_flag and any(
                _ in line for _ in {"_names.push", "_pre.push"}
            ):
                results.append(False)
                continue
            elif multirow_set_flag:
                results.append(True)
                continue

            results.append(False)
        return results

    def _parse_radio(self):
        """有点麻烦"""
        results = []
        multirow_comment_flag = False
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            """跨行注释，逆天"""
            if line in ["/*", "<!--"] or (
                any(line.startswith(_) for _ in {"/*", "<!--"})
                and all(_ not in line for _ in {"*/", "-->"})
            ):
                multirow_comment_flag = True
                results.append(False)
                continue
            elif line in ["*/", "-->"] or any(line.endswith(_) for _ in {"*/", "-->"}):
                multirow_comment_flag = False
                results.append(False)
                continue
            elif multirow_comment_flag:
                results.append(False)
                continue

            if self.is_comment(line) or self.is_event(line):
                results.append(False)
            elif (
                self.is_widget_link(line)
                or "<i>" in line
                or "<b>" in line
                or any(re.findall(r"^\"\w", line))
            ):
                results.append(True)
            else:
                results.append(False)
        return results

    def _parse_settings(self):
        """草"""
        results = []
        multirow_comment_flag = False
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            """跨行注释/error，逆天"""
            if line in ["/*", "<!--", "<<error {"] or (
                any(line.startswith(_) for _ in {"/*", "<!--", "<<error {"})
                and all(_ not in line for _ in {"*/", "-->", "}>>"})
            ):
                multirow_comment_flag = True
                results.append(False)
                continue
            elif multirow_comment_flag and (
                line in ["*/", "-->", "}>>"]
                or any(line.endswith(_) for _ in {"*/", "-->", "}>>"})
            ):
                multirow_comment_flag = False
                results.append(False)
                continue
            elif multirow_comment_flag:
                results.append(False)
                continue

            if self.is_comment(line) or self.is_event(line) or self.is_only_marks(line):
                results.append(False)
            elif (
                self.is_widget_button(line)
                or self.is_tag_span(line)
                or self.is_tag_label(line)
                or self.is_tag_input(line)
                or self.is_widget_print(line)
                or self.is_widget_link(line)
            ):
                results.append(True)
            elif (
                "<<set _npcList[clone($NPCNameList[$_i])]" in line
                or "<<run delete _npcList" in line
                or ".toUpperFirst()" in line
                or "<<if _npcList[$NPCName[_npcId].nam] is undefined>>" in line
                or "<<startOptionsComplexityButton" in line
                or "<<settingsTabButton" in line
                or "<<subsectionSettingsTabButton" in line
                or ".replace(/[^a-zA-Z" in line
            ):
                results.append(True)
            elif "<" in line and self.is_only_widgets(line):
                results.append(False)
            else:
                results.append(True)
        return results

    def _parse_skill_difficulties(self):
        """麻烦"""
        results = []
        multirow_comment_flag = False
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            """跨行注释/error，逆天"""
            if line in ["/*", "<!--", "<<error {"] or (
                any(line.startswith(_) for _ in {"/*", "<!--", "<<error {"})
                and all(_ not in line for _ in {"*/", "-->", "}>>"})
            ):
                multirow_comment_flag = True
                results.append(False)
                continue
            elif line in ["*/", "-->", "}>>"] or any(
                line.endswith(_) for _ in {"*/", "-->", "}>>"}
            ):
                multirow_comment_flag = False
                results.append(False)
                continue
            elif multirow_comment_flag:
                results.append(False)
                continue

            if self.is_comment(line) or self.is_event(line) or self.is_only_marks(line):
                results.append(False)
            elif "<span " in line or "<<set _text_output" in line:
                results.append(True)
            elif line.startswith("<"):
                results.append(False)
            else:
                results.append(True)
        return results

    def _parse_sleep(self):
        """<span , <<link, 纯文本"""
        return [
            line.strip()
            and (
                "<<link [[" in line.strip()
                or (
                    not line.strip().startswith("<")
                    and not line.strip().startswith("/*")
                    and "::" not in line.strip()
                )
                or "<span " in line.strip()
                or "$earSlimeEvent" in line.strip()
                or "$earSlime.event" in line.strip()
                or "<<case " in line.strip()
            )
            for line in self._lines
        ]

    def _parse_tending(self):
        """麻烦"""
        results = []
        multirow_comment_flag = False
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            """跨行注释，逆天"""
            if line in ["/*", "<!--"] or (
                any(line.startswith(_) for _ in {"/*", "<!--"})
                and all(_ not in line for _ in {"*/", "-->"})
            ):
                multirow_comment_flag = True
                results.append(False)
                continue
            elif line in ["*/", "-->"] or any(line.endswith(_) for _ in {"*/", "-->"}):
                multirow_comment_flag = False
                results.append(False)
                continue
            elif multirow_comment_flag:
                results.append(False)
                continue

            if self.is_comment(line) or self.is_event(line):
                results.append(False)
            elif (
                "<span " in line
                or "<<link " in line
                or not line.startswith("<")
                or '<<set _bedType to "' in line
                or "<<print $_plant.plural.toLocaleUpperFirst()>>" in line
                or "<<= $_plant.plural.toLocaleUpperFirst()>>" in line
                or "<<- $_plant.plural.toLocaleUpperFirst()>>" in line
                or self.is_widget_print(line)
            ):
                results.append(True)
            else:
                results.append(False)
        return results

    def _parse_system_text(self):
        """麻烦"""
        results = []
        multirow_comment_flag = False
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            """跨行注释，逆天"""
            if line in ["/*", "<!--"] or (
                any(line.startswith(_) for _ in {"/*", "<!--"})
                and all(_ not in line for _ in {"*/", "-->"})
            ):
                multirow_comment_flag = True
                results.append(False)
                continue
            elif line in ["*/", "-->"] or any(line.endswith(_) for _ in {"*/", "-->"}):
                multirow_comment_flag = False
                results.append(False)
                continue
            elif multirow_comment_flag:
                results.append(False)
                continue

            if self.is_comment(line) or self.is_event(line):
                results.append(False)
            elif (
                line.startswith('"')
                or "<span " in line
                or self.is_widget_print(line)
                or "<<set _args[0]" in line
                or "<<if $_npc.penisdesc" in line
                or "<<insufficientStat" in line
            ):
                results.append(True)
            elif any(
                _ == line
                for _ in {
                    "$worn.over_upper.name\\",
                    "$worn.over_lower.name\\",
                    "$worn.upper.name\\",
                    "$worn.lower.name\\",
                    "$worn.under_lower.name\\",
                    "$worn.genitals.name",
                }
            ):
                results.append(True)
            elif self.is_only_widgets(line):
                results.append(False)
            else:
                results.append(True)
        return results

    def _parse_transformations(self):
        """<span, <<print, 纯文本"""
        return [
            line.strip()
            and (
                "<span " in line.strip()
                or "<<print " in line.strip()
                or "<<= " in line.strip()
                or "<<- " in line.strip()
                or (
                    "::" not in line.strip()
                    and not line.strip().startswith("<")
                    and not line.strip().startswith("}")
                    and not line.strip().startswith("/*")
                    and not self.is_json_line(line.strip())
                )
            )
            for line in self._lines
        ]

    def _parse_system_widgets(self):
        results = []
        multirow_comment_flag = False
        multirow_error_flag = False
        multirow_script_flag = False
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            """跨行注释，逆天"""
            if line in ["/*", "<!--"] or (
                any(line.startswith(_) for _ in {"/*", "<!--"})
                and all(_ not in line for _ in {"*/", "-->"})
            ):
                multirow_comment_flag = True
                results.append(False)
                continue
            elif multirow_comment_flag and (
                line in ["*/", "-->"] or any(line.endswith(_) for _ in {"*/", "-->"})
            ):
                multirow_comment_flag = False
                results.append(False)
                continue
            elif multirow_comment_flag:
                results.append(False)
                continue

            """跨行script，逆天"""
            if line == "<<script>>":
                multirow_script_flag = True
                results.append(False)
                continue
            elif multirow_script_flag and line == "<</script>>":
                multirow_script_flag = False
                results.append(False)
                continue
            elif multirow_script_flag and any(
                _ in line for _ in {".replace(/[^a-zA-Z"}
            ):
                results.append(True)
                continue
            elif multirow_script_flag:
                results.append(False)
                continue

            if line.startswith("<<error {"):
                multirow_error_flag = True
                results.append(False)
                continue
            elif multirow_error_flag and line == "}>>":
                multirow_error_flag = False
                results.append(False)
                continue
            elif multirow_error_flag:
                results.append(False)
                continue

            if self.is_comment(line) or self.is_event(line) or self.is_only_marks(line):
                results.append(False)
            elif (
                self.is_tag_span(line)
                or self.is_tag_label(line)
                or self.is_widget_print(line)
                or "<<print either(" in line
                or "<<= either(" in line
                or "<<- either(" in line
                and ">>" in line
                or 'name: "' in line
                or 'name : "' in line
                or ">>." in line
                or self.is_widget_link(line)
                or "if $earSlime.event" in line
                or "_args[2].toLowerCase()" in line
                or "config.name" in line
            ):
                results.append(True)
            elif "<" in line and self.is_only_widgets(line):
                results.append(False)
            else:
                results.append(True)
        return results

    def _parse_persistent_npcs(self):
        results = []
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            results.append(False)
        return results

    """ flavour-text-generators """

    def parse_flavour_text(self):
        """flavour-text-generators"""
        if "body-comments.twee" == self._filename:
            return self._parse_body_comments()
        elif "exhibitionism.twee" == self._filename:
            return self._parse_exhibitionism()
        elif "ez-thesaurus.twee" == self._filename:
            return self.parse_type_between(["<<set _possibilities to ["], ["]>>"])
        return self._parse_normal()

    def _parse_body_comments(self):
        """json"""
        results = []
        json_flag = False
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            if "<<set " in line and line.endswith("["):
                json_flag = True
                results.append(False)
            elif json_flag and "]>>" in line:
                json_flag = False
                results.append(False)
            elif json_flag or any(
                {"<<Penisremarkquote>>" in line, "_output_line" in line}
            ):
                results.append(True)
            else:
                results.append(False)
        return results

    def _parse_exhibitionism(self):
        """json"""
        results = []
        needed_flag = False
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            """跨行注释/script，逆天"""
            if line == "<<set _seatedflashcrotchunderskirtlines to [":
                needed_flag = True
                results.append(False)
                continue
            elif line in "]>>":
                needed_flag = False
                results.append(False)
                continue
            elif needed_flag:
                results.append(True)
                continue

            if "_output_line" in line:
                results.append(True)
            else:
                results.append(False)
        return results

    def _parse_normal(self):
        results = []
        multirow_comment_flag = False
        multirow_script_flag = False
        multirow_run_flag = False
        multirow_if_flag = False
        multirow_error_flag = False
        maybe_json_flag = False
        multirow_run_line_pool_flag = False  # 草!
        multirow_print_flag = False  # 叠屎山了开始
        multirow_switch_slime_flag = False
        multirow_switch_material_flag = False

        shop_clothes_hint_flag = False  # 草
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            """跨行注释，逆天"""
            if line in ["/*", "<!--"] or (
                any(line.startswith(_) for _ in {"/*", "<!--"})
                and all(_ not in line for _ in {"*/", "-->"})
            ):
                multirow_comment_flag = True
                results.append(False)
                continue
            elif multirow_comment_flag and (
                line in ["*/", "-->"] or any(line.endswith(_) for _ in {"*/", "-->"})
            ):
                multirow_comment_flag = False
                results.append(False)
                continue
            elif multirow_comment_flag:
                results.append(False)
                continue

            """还有跨行print"""
            if (
                line.endswith("<<print either(")
                or line.endswith("<<= either")
                or line.endswith("<<- either")
            ):
                multirow_print_flag = True
                results.append(True)
                continue
            elif multirow_print_flag and (
                line.startswith(")>>") or line.endswith(')>></span>"')
            ):
                if line != ")>>":
                    results.append(True)
                else:
                    results.append(False)
                multirow_print_flag = False
                continue
            elif multirow_print_flag:
                results.append(True)
                continue

            """跨行script，逆天"""
            if line == "<<script>>":
                multirow_script_flag = True
                results.append(False)
                continue
            elif multirow_script_flag and line == "<</script>>":
                multirow_script_flag = False
                results.append(False)
                continue
            elif multirow_script_flag and any(
                _ in line for _ in {".replace(/[^a-zA-Z"}
            ):
                results.append(True)
                continue
            elif multirow_script_flag:
                results.append(False)
                continue

            """跨行if，逆天"""
            if line.startswith("<<if ") and ">>" not in line:
                multirow_if_flag = True
                results.append(False)
                continue
            elif multirow_if_flag and ">>" in line:
                multirow_if_flag = False
                results.append(False)
                continue
            elif multirow_if_flag:
                results.append(False)
                continue

            """跨行error，逆天"""
            if line.startswith("<<error ") and ">>" not in line:
                multirow_error_flag = True
                results.append(False)
                continue
            elif multirow_error_flag and ">>" in line:
                multirow_error_flag = False
                results.append(False)
                continue
            elif multirow_error_flag:
                results.append(False)
                continue

            """就这个特殊"""
            if line == "<<set _specialClothesHint to {":
                shop_clothes_hint_flag = True
                results.append(False)
                continue
            elif shop_clothes_hint_flag and line == "}>>":
                shop_clothes_hint_flag = False
                results.append(False)
                continue
            elif shop_clothes_hint_flag:
                results.append(True)
                continue

            """就为了 earSlime 专门弄这个"""
            if "<<switch $earSlime" in line:
                multirow_switch_slime_flag = True
                results.append(True)
                continue
            elif multirow_switch_slime_flag and "<</switch>>" in line:
                multirow_switch_slime_flag = False
                results.append(True)
                continue
            elif multirow_switch_slime_flag:
                results.append(True)
                continue

            """现在又有 material 了"""
            if "<<switch _material" in line:
                multirow_switch_material_flag = True
                results.append(True)
                continue
            elif multirow_switch_material_flag and "<</switch>>" in line:
                multirow_switch_material_flag = False
                results.append(True)
                continue
            elif multirow_switch_material_flag:
                results.append(True)
                continue

            """突如其来的json"""
            if (
                (
                    (line.startswith("<<set ") or line.startswith("<<error {"))
                    and ">>" not in line
                )
                or line.endswith("[")
                or line.endswith("{")
                or line.endswith("(")
            ):
                maybe_json_flag = True
                if any(
                    _ in line
                    for _ in {
                        "<<set _hairColorByName",
                        "<<set _fringeColorByName",
                        "<<set $savedHairStyles",
                        "<<numberStepper",
                    }
                ):
                    results.append(True)
                    continue
                results.append(False)
                continue
            elif maybe_json_flag and line.endswith(">>") and self.is_only_marks(line):
                maybe_json_flag = False
                results.append(False)
                continue
            elif maybe_json_flag and (
                '"Orphan":"orphan"' in line
                or "hint:" in line
                or "museum:" in line
                or "journal:" in line
                or "name:" in line
                or "stolen:" in line
                or "recovered:" in line
                or '"Rest":' in line
                or '"Stroke":' in line
                or '"Vines"' in line
                or '"Tentacles"' in line
                or '"Plainwhite"' in line
                or '"Wavywhite"' in line
                or '"Cowgirls"' in line
                or '"Hearts"' in line
                or '"Trees"' in line
                or '"Crosses"' in line
                or '"Cowgirl"' in line
                or '"Cat"' in line
                or '"Puppy"' in line
                or "'Owl plushie'" in line
                or '"Loose"' in line
                or '"Messy"' in line
                or '"Pigtails"' in line
                or '"Ponytail"' in line
                or '"Short"' in line
                or '"Straight"' in line
                or '"Twintails"' in line
                or '"Curl"' in line
                or '"Neat"' in line
                or '"Dreads"' in line
                or '"Ruffled"' in line
                or '"Shaved"' in line
                or '"Sidecut"' in line
                or '":"' in line
                or '": "' in line
                or '" : "' in line
                or "Default: {" in line
                or ("<<run " in line and "$worn." in line)
                or "<<numberStepper" in line
            ):
                results.append(True)
                continue

            """还有这个"""
            if line.startswith("<<run $(`#${_id}") and (
                '"Take" : ' in line or '"Present" : ' in line
            ):
                results.append(True)
                continue

            """以及这个"""
            if line.startswith("<<run _linePool"):
                if line.endswith(">>"):
                    results.append(True)
                else:
                    multirow_run_line_pool_flag = True
                    results.append(False)
                continue
            elif multirow_run_line_pool_flag and line.endswith(")>>"):
                multirow_run_line_pool_flag = False
                results.append(False)
                continue
            elif multirow_run_line_pool_flag:
                results.append(True)
                continue

            """跨行run，逆天"""
            if line.startswith("<<run ") and ">>" not in line:
                multirow_run_flag = True
                results.append(False)
                continue
            elif multirow_run_flag and line in {"})>>", "}>>", ")>>", "]>>", "});>>"}:
                multirow_run_flag = False
                results.append(False)
                continue
            elif multirow_run_flag and ("Enable indexedDB" in line):
                multirow_run_flag = False
                results.append(True)
                continue
            elif multirow_run_flag and ("'Owl plushie'" in line):
                results.append(True)
                continue
            elif multirow_run_flag:
                results.append(False)
                continue

            if self.is_comment(line) or self.is_event(line) or self.is_only_marks(line):
                results.append(False)
                continue
            elif "<" in line and (
                self.is_tag_span(line)
                or self.is_tag_label(line)
                or self.is_tag_input(line)
                or any(re.findall(r"<td data-label=", line))
                or any(re.findall(r"<<note\s\"", line))
                or self.is_widget_print(line)
                or self.is_widget_option(line)
                or self.is_widget_button(line)
                or self.is_widget_link(line)
                or any(re.findall(r"<<textbox\s\"", line))
                or any(re.findall(r"<<numberStepper\s\"", line))
            ):
                if '.replaceAll("["' in line or ".replace(/\[/g" in line:
                    results.append(False)
                    continue
                results.append(True)
                continue
            elif (
                '<<if $tentacles[$tentacleindex].desc.includes("pale")>>' in line
                or "<<if $_mirror is 'mirror'>>" in line
                or "<<run _bodyPartOptions.delete($featsBoosts.tattoos[_l].bodypart)>>"
                in line
                or "$_examine" in line
                or "<<if $pubtask is" in line
                or "<<run _featsTattooOptions.push(" in line
                or "<<if $NPCList[_nn].penis" in line
                or '<<if $watersportsdisable is "f" and $consensual is 0 and $enemyanger gte random(20, 200) and ($NPCList[_nn].penis is "none" or !$NPCList[_nn].penisdesc.includes("strap-on")) and _condomResult isnot "contained" and _args[0] isnot "short">>'
                in line
                or "<<if $NPCList[0].penisdesc" in line
                or "<<if $NPCList[_n].condom" in line
                or "<<takeKissVirginityNamed" in line
                or "<<cheatBodyliquidOnPart" in line
                or "<<generateRole" in line
                or "<<takeVirginity" in line
                or "<<recordSperm " in line
                or "<<NPCVirginityTakenByOther" in line
                or "<<run $rebuy_" in line
                or "<<swarminit" in line
                or "<<set _buy = Time.dayState" in line
                or "<<set _naked" in line
                or "<<optionsfrom " in line
                or "<<run _options" in line
                or "<<listbox " in line
                or "<<run _potentialLoveInterests.delete" in line
                or "<<run _selectedToy.colour_options.forEach" in line
                or "$worn.upper.name." in line
                or "$worn.lower.name." in line
                or "$worn.over_upper.name." in line
                or "$worn.under_upper.name." in line
                or "<<girlfriend>>?" in line
                or "$_slaps" in line
                or '? "' in line
                or "<<gagged_speech" in line
                or "<<mirror" in line
                or ">>." in line
                or "<<skill_difficulty " in line
                or ".replace(/[^a-zA-Z" in line
                or "$earSlime.event" in line
                or "if $slimePoundTask" in line
                or '<<case "Sweep">>' in line
                or '<<case "Feed">>' in line
                or '<<case "Brush">>' in line
                or '<<case "Wash">>' in line
                or '<<case "Walk">>' in line
                or '<<case "' in line
                or "<<case `" in line
                or "<<case '" in line
                or "<span" in line
                or "<<if _args[0] is" in line
                or "<<if _args[1] is" in line
                or "<<if _args[2] is" in line
                or "<<if _args[3] is" in line
                or "<<if _args[4] is" in line
                or "<<if _args[5] is" in line
                or "tooltip=" in line
                or "$_tempObjClothing" in line
                or "<<insufficientStat" in line
                or "<<moneyStatsTitle" in line
                or "<td " in line
                or "confirm(" in line
            ):
                results.append(True)
            elif ("<" in line and self.is_only_widgets(line)) or (
                maybe_json_flag and self.is_json_line(line)
            ):
                results.append(False)
                continue
            else:
                results.append(True)
        return results

    """ 归整 """

    def parse_type_only(self, pattern: str | set[str]) -> list[bool]:
        """Check if any pattern exists in each non-empty line"""
        if isinstance(pattern, str):
            return [
                bool(line.strip() and pattern in line.strip()) for line in self._lines
            ]

        return [
            bool(line.strip() and any(p in line.strip() for p in pattern))
            for line in self._lines
        ]

    def parse_type_only_regex(self, pattern: str | set[str]) -> list[bool]:
        """Check if any regex pattern matches each non-empty line"""
        if isinstance(pattern, str):
            return [
                bool(line.strip() and re.search(pattern, line.strip()))
                for line in self._lines
            ]

        return [
            bool(line.strip() and any(re.search(p, line.strip()) for p in pattern))
            for line in self._lines
        ]

    def parse_type_startwith(self, pattern: str | set[str]) -> list[bool]:
        """Check if each non-empty line starts with any pattern"""
        if isinstance(pattern, str):
            return [
                bool(line.strip() and line.strip().startswith(pattern))
                for line in self._lines
            ]

        return [
            bool(line.strip() and any(line.strip().startswith(p) for p in pattern))
            for line in self._lines
        ]

    def parse_type_between(
        self, starts: list[str], ends: list[str], contain: bool = False
    ) -> list[bool]:
        """Extract content between start and end markers"""
        results = []
        in_section = False

        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            if line in starts:
                in_section = True
                results.append(contain)
            elif line in ends:
                in_section = False
                results.append(contain)
            elif in_section:
                results.append(True)
            else:
                results.append(False)

        return results

    """ 判断 """

    @staticmethod
    def is_comment(line: str) -> bool:
        """Check if line is a comment"""
        if line.startswith("*") or line.startswith("*/") or line.startswith("-->"):
            return True
        return (line.startswith("/*") or line.startswith("<!--")) and (
            line.endswith("*/") or line.endswith("-->")
        )

    @staticmethod
    def is_json_line(line: str) -> bool:
        """Check if line follows JSON property format"""
        pattern = r"^[\w\"]*\s*:\s*[ `\'/\$\.\w\":,\|\(\)\{\}\[\]]+,*$"
        return bool(re.search(pattern, line))

    @staticmethod
    def is_only_marks(line: str) -> bool:
        """Check if line contains only symbols (no alphanumeric chars)"""
        return not re.search(r"[A-Za-z\d]", line)

    @staticmethod
    def is_event(line: str) -> bool:
        """Check if line contains an event marker"""
        return "::" in line

    @staticmethod
    def is_tag_span(line: str) -> bool:
        """Check if line contains a span tag with content"""
        return bool(re.search(r"<span.*?>[\"\w\.\-+\$]", line))

    @staticmethod
    def is_tag_label(line: str) -> bool:
        """Check if line contains a label tag with content"""
        return bool(
            re.search(r"<label>[\w\-+]", line) or re.search(r"\w</label>", line)
        )

    @staticmethod
    def is_tag_input(line: str) -> bool:
        """Check if line contains an input tag with value"""
        return bool(re.search(r"<input.*?value=\"", line))

    @staticmethod
    def is_widget_print(line: str) -> bool:
        """Check if line contains print widget"""
        pattern = r"<<(?:print|=|-)\s[^<]*[\"\'`\w]+[\-\?\s\w\.\$,\'\"<>\[\]\(\)/]+(?:\)>>|\">>|\'>>|`>>|\]>>|>>)"
        return bool(re.search(pattern, line))

    @staticmethod
    def is_widget_option(line: str) -> bool:
        """Check if line contains option widget"""
        return bool(re.search(r"<<option\s\"", line))

    @staticmethod
    def is_widget_button(line: str) -> bool:
        """Check if line contains button widget"""
        return bool(re.search(r"<<button ", line))

    @staticmethod
    def is_widget_link(line: str) -> bool:
        """Check if line contains link widget"""
        pattern = r"<<link\s*(\[\[|\"\w|`\w|\'\w|\"\(|`\(|\'\(|_\w|`)"
        return bool(re.search(pattern, line))

    @staticmethod
    def is_widget_high_rate_link(line: str) -> bool:
        """Check if line contains a high-frequency link widget"""
        pattern = r"<<link \[\[(Next\||Next\s\||Leave\||Refuse\||Return\||Resume\||Confirm\||Continue\||Stop\||Phase\|)"
        return bool(re.search(pattern, line))

    @staticmethod
    def is_only_widgets(line: str) -> bool:
        """Check if line contains only widgets, tags or variables (no text content)"""
        # Quick check for lines that definitely aren't just widgets
        if "<" not in line and "$" not in line and not line.startswith("_"):
            return False

        # Special cases that are known to be widgets-only
        special_widget_patterns = {
            "<<print either(",
            "<<= either(",
            "<<- either(",
            "<<print [",
            "<<= [",
            "<<- [",
        }
        if line in special_widget_patterns:
            return True

        # Remove all widget patterns
        cleaned_line = line
        for widget in re.findall(r"(<<(?:[^<>]*?|run.*?|for.*?)>>)", line):
            if widget:
                cleaned_line = cleaned_line.replace(widget, "", 1)

        # If all widgets removed and no other content remains
        if (
            "<" not in cleaned_line
            and "$" not in cleaned_line
            and not cleaned_line.startswith("_")
        ):
            return (
                not cleaned_line.strip()
                or ParseTwee.is_comment(cleaned_line.strip())
                or ParseTwee.is_only_marks(cleaned_line.strip())
            )

        # Remove all HTML tags
        for tag in re.findall(r"(<[/\s\w\"=\-@\$\+\'\.]*>)", cleaned_line):
            if tag:
                cleaned_line = cleaned_line.replace(tag, "", 1)

        # If all tags removed and no variables remain
        if "$" not in cleaned_line and not cleaned_line.startswith("_"):
            return (
                not cleaned_line.strip()
                or ParseTwee.is_comment(cleaned_line.strip())
                or ParseTwee.is_only_marks(cleaned_line.strip())
            )

        # Remove all variable references
        for var in re.findall(r"((?:\$|_)[^_][#;\w\.\(\)\[\]\"\'`]*)", cleaned_line):
            if var:
                cleaned_line = cleaned_line.replace(var, "", 1)

        # If what remains is empty or just marks, it's only widgets/vars
        return (
            not cleaned_line.strip()
            or ParseTwee.is_comment(cleaned_line.strip())
            or ParseTwee.is_only_marks(cleaned_line.strip())
        )
