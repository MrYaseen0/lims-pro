"""Thin compatibility shim.

The application now lives in the :mod:`app` package; this module keeps
``uvicorn server:app`` working and re-exports the names the test harness
(and any external tooling) imports from ``server``.
"""
from app.main import app
from app.core.database import db, init_db, ensure_indexes, reset_db, audit_logger, get_client
from app.core.security import hash_password
from app.core.deps import _login_attempts
from app.core.config import JWT_SECRET, COOKIE_NAME
from app.services.ranges import parse_range_bounds, compute_result_flags, to_float, check_critical_values


def __getattr__(name):
    # ``client`` stays live: it is None before init_db() and the real
    # Motor client afterwards.
    if name == "client":
        return get_client()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "app",
    "db",
    "client",
    "init_db",
    "ensure_indexes",
    "reset_db",
    "audit_logger",
    "hash_password",
    "_login_attempts",
    "JWT_SECRET",
    "COOKIE_NAME",
    "parse_range_bounds",
    "compute_result_flags",
    "to_float",
]
