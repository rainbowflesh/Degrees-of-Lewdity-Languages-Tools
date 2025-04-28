from enum import Enum
from pathlib import Path
from typing import List, Dict, Set, Optional, Any, Callable, Tuple, Union
from .consts import *
from .parse_twee import ParseTwee

# File name patterns for special handling
SPECIAL_FILES = {
    # 01-setup
    "weather-descriptions.js": {"'", '"', "`"},

    # 02-Helpers
    "macros.js": {"return `", "either(", "return '", 'return "'},

    # 04-Variables
    "feats.js": {"title: ", "desc: ", "hint: ", ".html"},
    "colours.js": {'name_cap: "', 'name: "'},
    "shop.js": {'"'},
    "plant-setup.js": {"plural:", "singular:", "seed_name:"},

    # special-masturbation
    "macros-masturbation.js": {"namecap", "name : name"},

    # 04-Pregnancy
    "children-story-functions.js": {"const wordList", "wordList.push"},
    "pregnancy.js": {"names = ['", "names.pushUnique", "spermOwner.name +", "spermOwner.fullDescription +", ".replace(/[^a-zA-Z"},
    "story-functions.js": {"name = (caps ?", "name = caps ?", "name = name[0]"},
    "pregnancy-types.js": {'return "tiny";', 'return "small";', 'return "normal";', 'return "large";', 'return ["tiny",'},

    # 03-Templates
    "t-actions.js": {"either("},
    "t-bodyparts.js": {"either("},

    # external
    "color-namer.js": None,  # Special handling

    # base-system
    "widgets.js": {".name_cap,", "addfemininityfromfactor(", "playerAwareTheyArePregnant()", "function formatList("},
    "text.js": {".statChange", 'return "', "targetName"},
    "stat-changes.js": {"return '", 'return "', ".statChange"},

    # 01-main
    "02-tooltips.js": {'"', '`', "Description", "Output", "<span", "<br>"},

    # 05-renderer
    "30-canvasmodel-editor.js": {'CombatEditor.create', 'CombatEditor.Create', 'textContent'},
}

class ParseJS:
    """Parser for JavaScript files in Degrees of Lewdity codebase"""

    def __init__(self, lines: List[str], filepath: Path):
        self._lines = lines
        self._filepath = filepath
        self._filename = filepath.name
        self._filedir = filepath.parent

    def parse(self) -> List[bool]:
        """Entry point for parsing files based on directory location"""
        match self._filedir.name:
            case "01-setup" | "02-Helpers" | "04-Variables" | "special-masturbation" | \
                 "04-Pregnancy" | "03-Templates" | "external" | "01-main" | "05-renderer":
                return self._parse_with_special_handling()
            case "03-JavaScript":
                return self._parse_javascript_file()
            case "base-clothing":
                return self._parse_clothing_file()
            case "base-system":
                return self._parse_system_file()
            case _:
                return self._parse_normal()

    def _parse_with_special_handling(self) -> List[bool]:
        """Handle files that have known patterns in SPECIAL_FILES dictionary"""
        if self._filename in SPECIAL_FILES:
            patterns = SPECIAL_FILES[self._filename]
            if patterns is None:
                # Special case for color-namer.js
                if self._filename == "color-namer.js":
                    return self.parse_type_between(starts=["var colors = {"], ends=["}"])
            else:
                return self.parse_type_only(patterns)

        # Specific file parsers for complex files
        match self._filename:
            case "t-misc.js":
                return self._parse_t_misc()
            case "effect.js":
                return self._parse_effect()
            case _:
                return self._parse_normal()

    def _parse_javascript_file(self) -> List[bool]:
        """Handle files in the 03-JavaScript directory"""
        match self._filename:
            case "bedroom-pills.js":
                return self._parse_bedroom_pills()
            case "base.js":
                return self._parse_base()
            case "debug-menu.js":
                return self._parse_debug_menu()
            case "eyes-related.js":
                return self.parse_type_only({"sentence += ", '"."'})
            case "furniture.js":
                return self.parse_type_only({"nameCap: ", "description: "})
            case "sexShopMenu.js":
                return self._parse_sexshop_menu()
            case "sexToysInventory.js":
                return self._parse_sextoy_inventory()
            case "ingame.js":
                return self.parse_type_only({'return i + "st";', 'return i + "nd";', 'return i + "rd";', 'return i + "th";', 'names', 'Wikifier.wikifyEval'})
            case "ui.js":
                return self._parse_ui()
            case "npc-compressor.js":
                return self._parse_npc_compressor()
            case "colour-namer.js":
                return self._parse_colour_namer()
            case "clothing-shop-v2.js":
                return self.parse_type_only({"const options", ".replace(/[^a-zA-Z", "prompt(", "message:"})
            case "time.js":
                return self.parse_type_only({"const monthNames", "const daysOfWeek"})
            case "time-macros.js":
                return self.parse_type_only({"School term ", "nextDate", '"', "ampm = hour", "<span"})
            case "save.js":
                return self._parse_save()
            case _:
                return self._parse_normal()

    def _parse_clothing_file(self) -> List[bool]:
        """Handle files in the base-clothing directory"""
        match self._filename:
            case "update-clothes.js":
                return self._parse_update_clothes()
            case _ if self._filename.startswith("clothing-"):
                return self.parse_type_only({"name_cap:", "description:", "<<link `", "altDamage:", "name_simple:", "pattern_options:"})
            case _:
                return self._parse_normal()

    def _parse_system_file(self) -> List[bool]:
        """Handle files in the base-system directory"""
        match self._filename:
            case "widgets.js" | "text.js" | "stat-changes.js":
                if self._filename in SPECIAL_FILES:
                    return self.parse_type_only(SPECIAL_FILES[self._filename])
                return self._parse_normal()
            case "effect.js":
                return self._parse_effect()
            case _:
                return self._parse_normal()

    def _parse_bedroom_pills(self):
        """Optimized parse method for bedroom-pills.js using pattern matching"""
        results = []
        next_line_needs_processing = False

        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            match (next_line_needs_processing, line):
                # Handle case where previous line indicated this line needs processing
                case (True, _):
                    next_line_needs_processing = False
                    results.append(True)

                # Handle special key patterns that need translation
                case (_, s) if any(key in s for key in ["name:", "description:", "onTakeMessage:", "warning_label:"]) and not s.startswith("*"):
                    if s.endswith(":"):
                        next_line_needs_processing = True
                        results.append(False)
                    else:
                        results.append(True)

                # Handle HTML and UI elements
                case (_, s) if any(pattern in s for pattern in [
                    '<span class="hpi_auto_label">',
                    "<span class='hpi_auto_label'>",
                    "hpi_name_",
                    "<span id",
                    'class="hpi_take_pills"',
                    "item.autoTake() ?",
                    "item.hpi_take_pills ?",
                    "</a>",
                    '"Effective for "',
                    'return "',
                    "return this.autoTake()",
                    "const itemName",
                    "${itemName}",
                    "<span"
                ]):
                    results.append(True)

                # Default case
                case _:
                    results.append(False)

        return results

    def _parse_base(self):
        """Optimized parse method for base.js using pattern matching and simplified condition checks"""
        # Use list comprehension with pattern-based filtering for cleaner code
        return [
            bool(line.strip() and any(pattern in line.strip() for pattern in [
                "T.text_output",
                "return '",
                'return "',
                "return `"
            ]))
            for line in self._lines
        ]

    def _parse_debug_menu(self):
        """Optimized parse method for debug-menu.js using state pattern matching"""
        results = []
        state = None

        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            match (state, line):
                # Inner HTML state
                case (None, s) if 'document.getElementById("debugEventsAdd").innerHTML' in s:
                    state = "inner_html"
                    results.append(False)
                case ("inner_html", "`;"):
                    state = None
                    results.append(False)
                case ("inner_html", s) if any(pattern in s for pattern in [
                    "<abbr>", "<span>", "<option", "<button", "<h3>", "<<swarminit"
                ]):
                    results.append(True)
                case ("inner_html", _):
                    results.append(False)

                # Link patterns
                case (_, s) if any(pattern in s for pattern in [
                    "link: [`", 'link: ["', "link: [(", "text_only: "
                ]):
                    results.append(True)

                # Default case
                case _:
                    results.append(False)

        return results

    def _parse_sexshop_menu(self):
        """Optimized method for parsing sexShopMenu.js"""
        results = []
        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            match line:
                case s if any(p in s for p in ["namecap: ", "description: ", "${item.owned()", "<span ", "<option "]):
                    results.append(True)
                case s if "Buy it" in s and "/*" not in s:
                    results.append(True)
                case s if "Make a gift for :" in s:
                    results.append(True)
                case _:
                    results.append(False)

        return results

    def _parse_sextoy_inventory(self):
        """Optimized method for parsing sexToysInventory.js"""
        results = []
        state = None

        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            # State machine with pattern matching
            match (state, line):
                # <a> tag state
                case (None, s) if "<a id=" in s:
                    state = "a_tag"
                    results.append(False)
                case ("a_tag", "</a>"):
                    state = None
                    results.append(False)
                case ("a_tag", _):
                    results.append(True)

                # Cursed text state
                case (None, 'document.getElementById("stiCursedText").outerHTML ='):
                    state = "cursed"
                    results.append(False)
                case ("cursed", "return;"):
                    state = None
                    results.append(False)
                case ("cursed", _):
                    results.append(True)

                # Carry count state
                case (None, s) if 'document.getElementById("carryCount")' in s:
                    state = "carry"
                    results.append(False)
                case ("carry", "</div>`;"):
                    state = None
                    results.append(False)
                case ("carry", _):
                    results.append(True)

                # Other patterns
                case _ if any(pattern in line for pattern in [
                    ".textContent", "(elem !== null)", "invItem.worn",
                    "<span class=", "const itemStatus"
                ]):
                    results.append(True)
                case _:
                    results.append(False)

        return results

    def _parse_ui(self):
        """Optimized method for parsing ui.js"""
        results = []
        text_flag = False

        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            match (text_flag, line):
                # Text state management
                case (False, "text ="):
                    text_flag = True
                    results.append(False)
                case (True, "break;"):
                    text_flag = False
                    results.append(False)
                case (True, s) if not ParseTwee.is_only_marks(s):
                    results.append(True)

                # Text assignment patterns
                case (_, s) if "text =" in s and "let text" not in s and "const text" not in s:
                    results.append(True)

                # Various text patterns
                case (_, s) if any(pattern in s for pattern in [
                    "<span", "npc.breastdesc =", "npc.breastsdesc =", "const breastSizes =",
                    'women = "', "men = ", ".replace(/[^a-zA-Z", 'return "'
                ]):
                    results.append(True)

                # Default case
                case _:
                    results.append(False)

        return results

    def _parse_npc_compressor(self):
        """Optimized method for parsing npc-compressor.js"""
        results = []
        multiconst_flag = False

        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            match (multiconst_flag, line):
                # Multi-const state handling
                case (False, s) if ("DescList" in s or "descList" in s) and not s.endswith(";"):
                    multiconst_flag = True
                    results.append(False)
                case (True, s) if s.endswith(";"):
                    multiconst_flag = False
                    results.append("fullDescription =" in s)
                case (True, s) if s.endswith('",') or s.endswith('"'):
                    results.append(True)
                case (True, _):
                    results.append(False)

                # Other text patterns
                case (_, s) if any(pattern in s for pattern in [
                    "const breastdesc", "const breastsdesc",
                    "const plant =", "const man =", "const sizeList"
                ]):
                    results.append(True)
                case (_, s) if ("descList" in s and "]" in s) or ("DescList" in s and "]" in s):
                    results.append(True)
                case _:
                    results.append(False)

        return results

    def _parse_colour_namer(self):
        """Optimized method for parsing colour-namer.js"""
        return [
            bool(line.strip() and any(pattern in line.strip() for pattern in [
                'return "', 'main = "', 'main === "', 'colour = "',
                "`rgb", "aux = ", "= aux"
            ]))
            for line in self._lines
        ]

    def _parse_save(self):
        """Optimized method for parsing save.js"""
        results = []
        state = None

        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            match (state, line):
                # Multi-line strings state
                case (None, s) if s.startswith("strings:") and "]" not in s:
                    state = "strings"
                    results.append(False)
                case ("strings", s) if s.endswith("],"):
                    state = None
                    results.append(False)
                case ("strings", _):
                    results.append(True)

                # Text map state
                case (None, s) if s.startswith("textMap:") and "}" not in s:
                    state = "textmap"
                    results.append(False)
                case ("textmap", s) if s.endswith("},"):
                    state = None
                    results.append(False)
                case ("textmap", _):
                    results.append(True)

                # Other translatable patterns
                case (_, s) if any(pattern in s for pattern in [
                    "Wikifier.wikifyEval", "Degrees of Lewdity.",
                    "displayName:", "textMap:", "strings:"
                ]):
                    results.append(True)
                case _:
                    results.append(False)

        return results

    def _parse_actions(self):
        """Optimized parse method for actions.js using state pattern matching"""
        results = []
        state = None

        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            match (state, line):
                # Multi-line text state
                case (None, s) if (s.startswith("result.text") and (s.endswith("{") or s.endswith("="))):
                    state = "multirow_text"
                    results.append(True)
                case ("multirow_text", s) if s.endswith("`;"):
                    state = None
                    results.append(True)
                case ("multirow_text", _):
                    results.append(True)

                # JSON object state
                case (None, s) if s.endswith("{"):
                    state = "json"
                    results.append(False)
                case ("json", s) if any(s.endswith(end) for end in ["};", ")};"]):
                    state = None
                    results.append(False)
                case ("json", s) if ParseTwee.is_json_line(line) and "text:" in s:
                    results.append(True)
                case ("json", _):
                    results.append(False)

                # Text and option patterns
                case (_, s) if any(pattern in s for pattern in [
                    "result.text", "text:", "result.options.push", ".name;", '" : "'
                ]):
                    results.append(True)
                case (_, s) if (s.startswith("? '") or s.startswith('? "') or
                              s.startswith(': "') or s.startswith(": '")):
                    results.append(True)

                # Default case
                case _:
                    results.append(False)

        return results

    def _parse_effects(self):
        """Optimized method for parsing effects.js"""
        results = []
        state = None

        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            match (state, line):
                # Fragment append state
                case (None, "fragment.append("):
                    state = "fragment"
                    results.append(False)
                case ("fragment", ");"):
                    state = None
                    results.append(False)
                case ("fragment", s) if not ParseTwee.is_only_marks(s) and s not in {
                    "Wikifier.wikifyEval(", "span(", "altText.selectedToy",
                    "altText.toys =", "toy1.name"
                }:
                    results.append(True)
                case ("fragment", _):
                    results.append(False)

                # sWikifier state
                case (None, s) if s.startswith("sWikifier(") and ")" not in s:
                    state = "swikifier"
                    results.append(False)
                case ("swikifier", s) if s.endswith(");"):
                    state = None
                    results.append(False)
                case ("swikifier", _):
                    results.append(True)

                # Other text patterns
                case (_, s) if any(pattern in s for pattern in [
                    "sWikifier", "`You", '"You', "fragment.append(wikifier(",
                    "altText.toys = ", "altText.start = ", "<span class",
                    "toy1.name", '? "', ': "', "altText.", "T.text_output",
                    "altText.lubricated", '? " semen-lubricated"', ")}. <<gpain>>`",
                    "}.</span>`", '" : "'
                ]):
                    results.append(True)
                case (_, s) if "fragment.append(" in s and not any(
                    empty in s for empty in {"''", "' '", '""', '" "', "``", "` `", "br()"}
                ):
                    results.append(True)
                case _:
                    results.append(False)

        return results

    def _parse_t_misc(self):
        """Optimized method for parsing t-misc.js"""
        results = []
        either_state = False

        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            match (either_state, line):
                case (False, "either("):
                    either_state = True
                    results.append(True)
                case (True, ")"):
                    either_state = False
                    results.append(False)
                case (True, _):
                    results.append(True)
                case (_, s) if 'Template.add("' in s and s.endswith(";"):
                    results.append(True)
                case _:
                    results.append(False)

        return results

    def _parse_update_clothes(self):
        """Optimized method for parsing update-clothes.js"""
        return [
            bool(line.strip() and ((line.strip().startswith("V") and ".name =" in line.strip()) or
                                  "name: " in line.strip()))
            for line in self._lines
        ]

    def _parse_effect(self):
        """Optimized method for parsing effect.js"""
        results = []
        state = None

        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            match (state, line):
                # Element state
                case (None, "element("):
                    state = "element"
                    results.append(False)
                case ("element", ");"):
                    state = None
                    results.append(False)
                case ("element", _):
                    results.append(True)

                # sWikifier state
                case (None, "sWikifier("):
                    state = "swikifier"
                    results.append(False)
                case ("swikifier", ");"):
                    state = None
                    results.append(False)
                case ("swikifier", _):
                    results.append(True)

                # Text content
                case (_, s) if any(quote in s for quote in ['"', "'", "`"]):
                    results.append(True)
                case _:
                    results.append(False)

        return results

    def _parse_normal(self) -> List[bool]:
        """Default parsing method for files without specific handling"""
        results = []
        state = None

        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            match (state, line):
                # sWikifier state
                case (None, "sWikifier("):
                    state = "sWikifier"
                    results.append(False)
                case ("sWikifier", ");"):
                    state = None
                    results.append(False)
                case ("sWikifier", _):
                    results.append(True)

                # fragment.append state
                case (None, "fragment.append("):
                    state = "fragment_append"
                    results.append(False)
                case ("fragment_append", ");"):
                    state = None
                    results.append(False)
                case ("fragment_append", _) if not ParseTwee.is_only_marks(line) and line not in {"Wikifier.wikifyEval(", "span(", "altText.selectedToy"}:
                    results.append(True)
                case ("fragment_append", _):
                    results.append(False)

                # resultArray.push state
                case (None, "resultArray.push("):
                    state = "result_array"
                    results.append(False)
                case ("result_array", ");"):
                    state = None
                    results.append(False)
                case ("result_array", _):
                    results.append(True)

                # return state
                case (None, "return ["):
                    state = "return_array"
                    results.append(False)
                case ("return_array", line_end) if line_end.endswith(".random());") or line_end.endswith(".random())"):
                    state = None
                    results.append(False)
                case ("return_array", _):
                    results.append(True)

                # Default case for pattern matching against specific lines
                case _:
                    if "fragment.append(" in line and any(_ not in line for _ in {"''", "' '", '""', '" "', "``", "` `", "br()"}):
                        results.append(True)
                    elif ("addfemininityfromfactor(" in line and line.endswith(");")) or '"Pregnant Looking Belly"' in line:
                        results.append(True)
                    elif any(marker in line for marker in [
                        "altText.toys = ", "altText.start = ", "<span", "sWikifier(", "span(",
                        "resultArray.push", "statChange", "reasons.push", "displayName:", "textMap:",
                        'const output = month', 'createElement("span"'
                    ]):
                        results.append(True)
                    else:
                        results.append(False)

        return results

    def parse_type_only(self, pattern: Union[str, Set[str]]) -> List[bool]:
        """Parse file extracting only lines containing specified patterns"""
        if isinstance(pattern, str):
            return [bool(line.strip() and pattern in line.strip()) for line in self._lines]

        return [bool(line.strip() and any(p in line.strip() for p in pattern)) for line in self._lines]

    def parse_type_between(self, starts: List[str], ends: List[str], contain: bool = False) -> List[bool]:
        """Parse extracting only content between start and end markers"""
        results = []
        active = False

        for line in self._lines:
            line = line.strip()
            if not line:
                results.append(False)
                continue

            if line in starts:
                active = True
                results.append(contain)
            elif line in ends:
                active = False
                results.append(contain)
            elif active:
                results.append(True)
            else:
                results.append(False)

        return results

__all__ = ["ParseJS"]
