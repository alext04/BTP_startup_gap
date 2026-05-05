"""
Central configuration — loads API keys from .env once.
Import from here instead of reading os.getenv directly.
"""

import os
from dotenv import load_dotenv

load_dotenv()

SEMANTIC_SCHOLAR_API_KEY: str | None = os.getenv("SEMANTIC_SCHOLAR_API_KEY") or None
LENS_API_KEY: str | None = os.getenv("LENS_API_KEY") or None
PRODUCT_HUNT_TOKEN: str | None = os.getenv("PRODUCT_HUNT_TOKEN") or None
