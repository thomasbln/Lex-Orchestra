"""
pytest configuration for Lex-Orchestra tests.

Ensures the project `.env` file is the single source of truth for test
settings — shell-exported env vars (e.g. from ~/.zshrc) must NOT silently
override the project config. Without override=True, a stale shell export
pointing at a decommissioned host would keep poisoning tests even after
.env has been updated.
"""
from pathlib import Path

from dotenv import load_dotenv


_PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_PROJECT_ROOT / ".env", override=True)
