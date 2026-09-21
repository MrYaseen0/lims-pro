"""Pagination helper (clamps page_size to MAX_PAGE_SIZE)."""
from app.core.config import MAX_PAGE_SIZE


def paginate(page: int = 1, page_size: int = 20):
    page = max(1, page)
    page_size = min(max(1, page_size), MAX_PAGE_SIZE)
    return (page - 1) * page_size, page_size
