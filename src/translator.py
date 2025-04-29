from asyncio.log import logger
from datetime import datetime
from enum import Enum
import json
import logging
import os
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from deprecated import deprecated
from dotenv import load_dotenv
from huggingface_hub import Padding
from ollama import ChatResponse, Client, chat
from src.io_helper import IOHelper
from transformers import AutoTokenizer
import time


load_dotenv()
logger = logging.getLogger("Translator")


class Prompt(Enum):
    SYSTEM = ""
    ZH_HANS = """任务：将英文翻译成中文
规则：
1. 保留所有 HTML、Twee、JS 标签结构不变
2. 所有 HTML、Twee、JS 标签不参与翻译
3. 逐标签查找需要翻译的部分
4. 所有形如 <<...>>、<...>、`...` 的标签结构完整保留，不翻译里面的文字
5. 所有形如 [[文本|文本]], [[...|...]], [[test|test]], [[Text|TEXT]] 的结构中，仅翻译左侧双括号内, 至管道标记符的部分到为中文, 不要混淆<<...>>
6. 专用名词对照表:  ["Degrees of Lewdity Plus", "dick", "penis", "vagina", "balls", "anus", "Next","Vanilla","moded", "Discord"] => ["欲都孤儿威力加强版", "肉棒", "肉棒", "小穴", "蛋蛋", "菊穴","继续","原版","模组版","Discord"]
7. 人名对照表, 请确保人名对照翻译一致: ["Avery","Bailey","Briar","Charlie","Darryl","Doren","Eden","Gwylan","Harper","Jordan","Kylar","Landry","Leighton","Mason","Morgan","River","Robin","Sam","Sirris","Whitney","Winter","Black Wolf","Niki","Quinn","Remy","Alex","Great Hawk","Wren","Sydney","Ivory Wraith","Zephyr","Nona","Lake couple","the witch"] => ["艾弗里","贝利","布莱尔","查里","达里尔","多伦","伊甸","格威岚","哈珀","约旦","凯拉尔","兰德里","礼顿","梅森","摩根","瑞沃","罗宾","萨姆","西里斯","惠特尼","温特","黑狼","尼奇","奎恩","雷米","艾利克斯","巨鹰","伦恩","悉尼","象牙怨灵","泽菲尔","诺娜","湖边情侣","巫女"]
9. 不要逐词逐句死板对照翻译，根据上下文选择恰当措辞搭配
10. 英语原文中还会使用各种抽象表达，翻译需要表达指代的具体内容
10. 在对原文词句之间、上下文逻辑上要连贯一致
12. 英语中过长的插入语导致的长难句，要结合中文常用的表达方式，把长难句的主体部分和修饰部分拆开成短句，让句子的主体部分表述清晰
13. 汉语表述中并不需要的语气词、抽象修饰不得出现，仅保留语句主体部分
14. 英语中常用"静态"的表述，如"xx是xx的"，而中文的表达习惯往往更加"动态"，需要翻译为中文的表述风格，禁止滥用"的"或滥用被动语态
15. 不要输出说明文字, 只需要翻译结果
16. 对于没有列出的规则，请按照中文的表达习惯与常识进行翻译

翻译:
"""


class Translator:
    def __init__(
        self,
        use_local: bool = False,
        model: str = "qwen3:8b",
        save: bool = False,
        input_path: Path = None,
        output_path: Path = Path("tests/test_data/mt_translates"),
    ):
        self._use_local = use_local
        self._model = model
        self._io_helper = IOHelper()
        self._save_to_file = save
        self._input_files_path = input_path
        self._output_files_path = output_path
        self._state_file = Path(self._output_files_path) / "state.json"

    def create_translates(self) -> None:
        state = self.load_state()
        state_file = state["last_file"] if state else None
        state_row = state["last_row"] if state else -1

        if self._save_to_file:
            os.makedirs(self._output_files_path, exist_ok=True)

        token_limit = 32000
        batch_token_count = 0
        total_rows = 0
        tokenizer = AutoTokenizer.from_pretrained(
            "Qwen/Qwen3-8B", trust_remote_code=True, use_fast=False
        )

        for dirpath, _, filenames in os.walk(self._input_files_path):
            for filename in filenames:
                if not filename.endswith(".csv"):
                    continue

                padding = os.path.join(dirpath, filename)
                padding_path = os.path.relpath(padding, self._input_files_path)
                if state_file and padding_path < state_file:
                    logger.info(f"Skip processed files {padding_path}")
                    continue

                translates_dist = os.path.join(self._output_files_path, padding_path)
                os.makedirs(os.path.dirname(translates_dist), exist_ok=True)

                mode = "a" if state_file == padding_path else "w"
                with (
                    open(padding, "r", encoding="utf-8") as input_file,
                    open(
                        translates_dist, mode, encoding="utf-8", newline=""
                    ) as output_file,
                ):

                    reader = csv.reader(input_file)
                    writer = csv.writer(output_file)

                    for row_idx, row in enumerate(reader):
                        if state_file == padding_path and row_idx <= state_row:
                            continue  # skip processed rows

                        if len(row) < 2:
                            continue  # skip invalid row

                        input_text = row[1]
                        token_count = self.token_counter(input_text, tokenizer)
                        logger.info(
                            f"Translate {padding} id {row[0]} token will use: {token_count}"
                        )

                        if batch_token_count + token_count > token_limit:
                            self.save_state(padding_path, row_idx, batch_token_count)
                            logger.warning(
                                f"Batch token count exceeded ({batch_token_count} + {token_count} > {token_limit}), restarting from next row"
                            )
                            return

                        translation = self.use_qwen(input_text)
                        batch_token_count += token_count
                        total_rows += 1

                        if self._save_to_file:
                            try:
                                row.append(translation)
                                writer.writerow(row)
                                self.save_state(
                                    padding_path, row_idx, batch_token_count
                                )
                                logger.debug(
                                    f"Wrote translated row to: {translates_dist}"
                                )
                            except Exception as e:
                                logger.error(
                                    f"Error writing to file {translates_dist}: {e}"
                                )
                        else:
                            logger.info(f"Translated: {input_text} → {translation}")

        self.reset_state()
        logger.info(
            f"Finished batch. Total rows translated: {total_rows}, total tokens used: {batch_token_count}"
        )

    def scan_for_translation(self, padding_path, translated_path):
        for dirpath, _, filenames in os.walk(padding_path):
            for filename in filenames:
                if not filename.endswith(".csv"):
                    continue

                padding_file = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(padding_file, padding_path)
                translated_file = os.path.join(translated_path, rel_path)

                padding_total_rows = self.get_valid_row_count(padding_file)
                if not os.path.exists(translated_file):
                    logger.info(f"{padding_file} → do tr (no translated file)")
                    # TODO: send file to use_qwen

                translated_total_rows = self.get_valid_row_count(translated_file)
                last_tr_id = self.get_last_translated_row_id(translated_file)

                if translated_total_rows < padding_total_rows:
                    # TODO: send line id = last_tr_id col2 to use_qwen
                    logger.info(
                        "Translated file <",
                        translated_file,
                        "> missing translation lines idx: ",
                        last_tr_id,
                        " Total missing lines: ",
                        padding_total_rows - translated_total_rows,
                    )

    def use_qwen(self, input: str) -> str:
        start_time = time.time()
        model = self._model
        content = Prompt.ZH_HANS.value + input

        try:
            response: ChatResponse = chat(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": content,
                    },
                ],
            )

            full_response = response["message"]["content"]

            # trim useless thinking block, leave last line as response
            if "<think>" in full_response and "</think>" in full_response:
                translated = full_response.split("</think>", 1)[1].strip()
            else:
                paragraphs = [p.strip() for p in full_response.split("\n\n")]
                translated = next((p for p in reversed(paragraphs) if p), full_response)

            logger.debug(f"Input: {input}")
            logger.debug(f"Output: {full_response}")
            return translated

        except Exception as e:
            logger.error(f"Translation error: {e}")
            return input
        finally:
            end_time = time.time()
            duration = end_time - start_time
            logger.debug(f"use_qwen execution time: {duration:.4f} seconds")

    def token_counter(self, input: str, tokenizer) -> int:
        content = Prompt.SYSTEM.value + Prompt.ZH_HANS.value + input
        return len(tokenizer.tokenize(content))

    def get_valid_row_count(self, file_path):
        count = 0
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2 and row[1].strip():
                    count += 1
        return count

    def get_last_translated_row_id(self, file_path):
        last_valid_row_id = -1
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3 and row[2].strip():
                    try:
                        last_valid_row_id = int(row[0])
                    except ValueError:
                        continue
        return last_valid_row_id

    @deprecated()
    def reset_state(self):
        state_path = Path(self._output_files_path) / "state.json"
        if state_path.exists():
            os.remove(state_path)

    @deprecated()
    def load_state(self):
        if not os.path.exists(self._state_file):
            logger.info("No state file found, starting new translation")
            return None
        with open(self._state_file, "r", encoding="utf-8") as f:
            return json.load(f)

    @deprecated()
    def save_state(self, file: str, row_idx: int, token_used: int):
        state = {
            "last_file": file,
            "last_row": row_idx,
            "token_used": token_used,
            "last_model": self._model,
            "timestamp": datetime.now().isoformat(),
        }
        with open(self._state_file, "w") as f:
            # fcntl.flock(f, fcntl.LOCK_EX)
            json.dump(state, f, indent=2)
            # fcntl.flock(f, fcntl.LOCK_UN)
