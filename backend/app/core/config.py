"""Central configuration: env loading + JWT fail-fast.

Imported first by every other app module; raises at import time if
JWT_SECRET is missing (same fail-fast behavior as the old server.py).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

# MongoDB connection (KeyError at import if unset — same as before)
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

# JWT Configuration — fail fast if the secret is not provided; a hardcoded
# fallback would give every deployment the same signing key.
JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET environment variable must be set. "
        'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
    )
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.environ.get("JWT_EXPIRATION_HOURS", "24"))

# Auth cookie settings (httpOnly so JS/XSS cannot steal the token)
COOKIE_NAME = "lims_token"
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"

# Reports directory
REPORTS_DIR = ROOT_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# Pagination
MAX_PAGE_SIZE = 200

# Login rate limiting (in-memory sliding window, per process)
LOGIN_RATE_LIMIT = 10          # max attempts
LOGIN_RATE_WINDOW_SECONDS = 60  # per this many seconds

# CORS
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").strip()
