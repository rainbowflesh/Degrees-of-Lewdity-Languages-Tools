from enum import Enum
import os
import csv
from pathlib import Path
from loguru import logger
from ollama import ChatResponse, chat
from src.io_helper import IOHelper
from transformers import AutoTokenizer
import time


class Prompt(Enum):
    SYSTEM = ""
    ZH_HANS = """任务：将英文翻译成中文
规则：
1. 保留所有 HTML、Twee、JS 标签结构不变
2. 所有 HTML、Twee、JS 标签不参与翻译
3. 逐标签查找需要翻译的部分
4. 所有形如 <<...>>、<...>、`...` 的标签结构完整保留，不翻译里面的文字
5. 所有形如 [[...|...]] 的结构中，仅翻译左侧双括号内, 至管道标记符的部分到为中文, 不要混淆<<...>>
6. 如果[[...|...]]内左侧是网址, 不翻译
6. 专用名词对照表:  ["Degrees of Lewdity Plus", "dick", "penis", "vagina", "balls", "anus", "Next","Vanilla","moded", "Discord","plush"] => ["欲都孤儿威力加强版", "肉棒", "肉棒", "小穴", "蛋蛋", "菊穴","继续","原版","模组版","Discord","玩偶"]
7. 人名对照表, 请确保人名对照翻译一致: ["Avery","Bailey","Briar","Charlie","Darryl","Doren","Eden","Gwylan","Harper","Jordan","Kylar","Landry","Leighton","Mason","Morgan","River","Robin","Sam","Sirris","Whitney","Winter","Black Wolf","Niki","Quinn","Remy","Alex","Great Hawk","Wren","Sydney","Ivory Wraith","Zephyr","Nona","Lake couple","the witch"] => ["艾弗里","贝利","布莱尔","查里","达里尔","多伦","伊甸","格威岚","哈珀","约旦","凯拉尔","兰德里","礼顿","梅森","摩根","瑞沃","罗宾","萨姆","西里斯","惠特尼","温特","黑狼","尼奇","奎恩","雷米","艾利克斯","巨鹰","伦恩","悉尼","象牙怨灵","泽菲尔","诺娜","湖边情侣","巫女"]
9. 不要逐词逐句死板对照翻译，根据上下文选择恰当措辞搭配
10. 英语原文中还会使用各种抽象表达，翻译需要表达指代的具体内容
10. 在对原文词句之间、上下文逻辑上要连贯一致
12. 英语中过长的插入语导致的长难句，要结合中文常用的表达方式，把长难句的主体部分和修饰部分拆开成短句，让句子的主体部分表述清晰
13. 汉语表述中并不需要的语气词、抽象修饰不得出现，仅保留语句主体部分
14. 英语中常用"静态"的表述，如"xx是xx的"，而中文的表达习惯往往更加"动态"，需要翻译为中文的表述风格，禁止滥用"的"或滥用被动语态
15. 不要输出说明文字, 只需要翻译结果
16. 对于没有列出的规则，请按照中文的表达习惯与常识进行翻译
17. 情爱相关的描述可以信达雅一点, 但是不要过度

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
        self._io_helper = IOHelper()

        self._use_local = use_local
        self._model = model
        self._save_to_file = save
        self._input_files_path = input_path
        self._output_files_path = output_path

        self._tokenizer = AutoTokenizer.from_pretrained(
            "Qwen/Qwen3-8B", trust_remote_code=True, use_fast=False
        )
        self._qwen_token_limit = 40000
        self._total_translated_rows = 0
        self._token_limit_hit = False

        self._system_prompt = Prompt.SYSTEM.value
        self._zh_hans_prompt = Prompt.ZH_HANS.value
        self._prompt_token_length = len(
            self._tokenizer.tokenize(self._system_prompt + self._zh_hans_prompt)
        )

    def resume_translate(self):
        logger.info("Starting translation resume loop...")

        while True:
            self._token_limit_hit = False  # Reset before each scan
            translated_before = self._total_translated_rows

            self.search_and_translate()

            translated_after = self._total_translated_rows
            translated_this_round = translated_after - translated_before

            if translated_this_round == 0:
                logger.info("No new rows translated this round.")

                if not self._token_limit_hit:
                    logger.info("All translations complete.")
                    break
                else:
                    logger.info("Token limit hit immediately; pausing until next call.")
                    break
            else:
                logger.info(f"Translated {translated_this_round} rows this round.")

    def search_and_translate(self) -> None:
        if self._save_to_file:
            os.makedirs(self._output_files_path, exist_ok=True)

        for dirpath, _, filenames in os.walk(self._input_files_path):
            if not filenames:
                continue  # skip empty
            filenames.sort()
            for filename in filenames:
                if not filename.endswith(".csv"):
                    continue  # skip none csv

                padding_file = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(padding_file, self._input_files_path)
                translates_file = os.path.join(self._output_files_path, rel_path)

                if not os.path.exists(translates_file):
                    os.makedirs(os.path.dirname(translates_file), exist_ok=True)
                    logger.info(
                        f"No translates found in {padding_file}, starting new run"
                    )
                    self.do_batch_translate(padding_file, translates_file, 0, "w")
                    continue

                padding_rows = self._io_helper.count_csv_row_translations(
                    padding_file, check_translation=False
                )
                translated_rows = self._io_helper.count_csv_row_translations(
                    translates_file, check_translation=True
                )

                if translated_rows >= padding_rows:
                    logger.info(f"File {padding_file} translation complete, skipping")
                    continue

                logger.info(f"Resuming {padding_file} from line {translated_rows + 1}")
                self._io_helper.truncate_csv_newline(
                    translates_file, translated_rows
                )  # append to new line
                self.do_batch_translate(
                    padding_file, translates_file, translated_rows, "a"
                )

    def do_batch_translate(
        self,
        padding_file: str,
        translates_file: str,
        start_idx: int,
        mode: str,
    ) -> None:
        batch_token_count = 0

        with self._io_helper.safe_csv_writer(
            translates_file, mode, self._save_to_file
        ) as writer:
            try:
                with open(padding_file, "r", encoding="utf-8") as input_file:
                    reader = csv.reader(input_file)

                    for row_idx, row in enumerate(reader):
                        if row_idx < start_idx or len(row) < 2:
                            continue  # skip invalid row

                        input_text = row[1]
                        input_token_count = self.token_counter(input_text)

                        # estimate total token size
                        estimated_total = (
                            batch_token_count + input_token_count * 2
                        )  # assume output smaller 2 times than input
                        if estimated_total > self._qwen_token_limit:
                            logger.info("Estimated token limit reached, stopping batch")
                            self._token_limit_hit = True
                            return

                        translation = self.use_qwen(input_text)
                        output_token_count = self.token_counter(translation)

                        total_token_count = input_token_count + output_token_count
                        if (
                            batch_token_count + total_token_count
                            > self._qwen_token_limit
                        ):
                            logger.info("Token limit reached, stop this batch")
                            self._token_limit_hit = True
                            return

                        batch_token_count += total_token_count
                        self._total_translated_rows += 1

                        if writer:
                            row.append(translation)
                            writer.writerow(row)
                            logger.debug(
                                f"Translation {row_idx}: {translation} -> saved"
                            )
            except Exception as e:
                logger.error(f"Error in batch translation: {str(e)}")
                raise

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
            translated = self._extract_translation(full_response)

            logger.debug(f"Input: {input}")
            logger.debug(f"Output: {translated}")
            return translated

        except Exception as e:
            logger.error(f"Translation error: {e}")
            return input
        finally:
            end_time = time.time()
            duration = end_time - start_time
            logger.debug(f"use_qwen execution time: {duration:.4f} seconds")

    def token_counter(self, input: str) -> int:
        input_tokens = len(self._tokenizer.tokenize(input))
        return self._prompt_token_length + input_tokens

    def _extract_translation(self, full_response: str) -> str:
        """trim thinking block from full response"""
        if "<think>" in full_response and "</think>" in full_response:
            return full_response.split("</think>", 1)[1].strip()

        # leave last line as result
        paragraphs = [p.strip() for p in full_response.split("\n\n")]
        return next((p for p in reversed(paragraphs) if p), full_response)
