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

from src.translator import Translator


load_dotenv()
logger = logging.getLogger("Test Translator Resume")


def test_translator_resume():
    t = Translator(input_path=r"tests/test_data/diff/dolp", save=True, use_local=True)
    t.resume_translate()
