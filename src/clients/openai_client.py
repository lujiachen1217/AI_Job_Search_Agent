"""Shared OpenAI client initialization."""

from functools import lru_cache

from dotenv import load_dotenv
from openai import OpenAI


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    """Create and reuse one OpenAI client after loading environment variables."""
    load_dotenv()
    return OpenAI()
