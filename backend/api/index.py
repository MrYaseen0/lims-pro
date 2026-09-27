"""Vercel serverless entry point.

Re-exports the FastAPI ASGI application from ``app.main`` so Vercel's
Python runtime can serve it. Local development is unchanged:
``uvicorn server:app`` from ``backend/`` still works.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: E402,F401  (re-exported for Vercel)
