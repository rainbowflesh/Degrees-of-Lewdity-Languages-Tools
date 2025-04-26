from asyncio.log import logger
import logging
import os
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger("asyncio:Translator")


class Translator:
    def __init__(self, use_local: bool = False, use_full: bool = False):
        self._use_local = use_local
        self._use_full = use_full

    def cursor(self):
        # implement cursor automaton
        logger.info(
            f"Using Cursor backend (implementation pending)")
        logger.debug("")
        pass

    def gemini(self):
        # implement api
        token = os.getenv("GEMINI_API_KEY")
        logger.info(
            f"Using Gemini backend (implementation pending)")
        if not token:
            raise ValueError(
                "API token required for Gemini provider but not provided.")
        logger.debug(
            f"Using API Token: {token[:4]}...{token[-4:]}")
        pass

    def gpt(self):
        # implement api
        token = os.getenv("OPENAI_API_KEY")
        logger.info(f"Using GPT backend (implementation pending)")
        if not token:
            raise ValueError(
                "API token required for GPT provider but not provided.")
        logger.info(
            f"Using API Token: {token[:4]}...{token[-4:]}")
        pass

    def x_alma(self):
        # implement ollama local host
        # X-ALMA is assumed local, token not typically needed
        logger.info(
            f"Using X_ALMA local backend (full={self._use_full}) (implementation pending)")
        if self._use_full:
            # Logic for full model
            pass
        else:
            # Logic for standard model
            pass

    def deepseek(self):
        logger.info(
            f"Using DEEPSEEK backend (local={self._use_local}, full={self._use_full}) (implementation pending)")
        if self._use_local:
            # implement ollama local host
            logger.info(f"Connecting to local Ollama for DEEPSEEK")
            if self._use_full:
                # model=""
                logger.info(f"Using full local DEEPSEEK model")
                pass
            else:
                logger.info(f"Using standard local DEEPSEEK model")
                pass
        else:
            # implement api
            token = os.getenv("DEEPSEEK_API_KEY")
            logger.info(f"Connecting to DEEPSEEK API")
            if not token:
                raise ValueError(
                    "API token required for remote DEEPSEEK API but not provided.")
            logger.info(
                f"Using API Token: {token[:4]}...{token[-4:]}")
            if self._use_full:
                logger.info(f"Using full remote DEEPSEEK model")
                # Use specific full model API endpoint/parameter
                pass
            else:
                logger.info(
                    f"Using standard remote DEEPSEEK model")
                # Use standard model API endpoint/parameter
                pass
