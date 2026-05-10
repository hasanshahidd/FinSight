"""FastAPI entrypoint for FinSight AI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api import admin, auth, budgets, chat, chat_stream, insights, transactions, users
from app.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware
from app.db.session import init_db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("startup", env=settings.env, llm=settings.llm_model)
    await init_db()
    yield
    logger.info("shutdown")


app = FastAPI(
    title="FinSight AI",
    description="AI-powered personal finance assistant.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["x-request-id"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["transactions"])
app.include_router(insights.router, prefix="/api/insights", tags=["insights"])
app.include_router(budgets.router, prefix="/api/budgets", tags=["budgets"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(chat_stream.router, tags=["chat"])  # WebSocket; no prefix
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "0.2.0"}


# Prometheus /metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
