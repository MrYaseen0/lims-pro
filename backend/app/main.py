"""FastAPI application factory: lifespan, routers, CORS."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core import config
from app.core.database import init_db, ensure_indexes, get_client
from app.routers import auth, patients, orders, results, reports, billing, analytics

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await ensure_indexes()
    logger.info("MongoDB indexes ensured")
    yield
    client = get_client()
    if client is not None:
        client.close()


app = FastAPI(title="Laboratory Information System API", lifespan=lifespan)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Defense-in-depth headers for API responses (no new dependencies)."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app.add_middleware(SecurityHeadersMiddleware)

app.include_router(auth.router, prefix="/api")
app.include_router(patients.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(results.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")


@app.get("/api/")
async def root():
    return {"message": "Laboratory Information System API", "version": "1.0.0"}


# CORS: when credentials (httpOnly auth cookie) are used, browsers reject
# `Access-Control-Allow-Origin: *`, so a wildcard is expressed as an origin
# regex (which echoes the request origin) instead of a literal "*".
if config.CORS_ORIGINS == "*":
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in config.CORS_ORIGINS.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
