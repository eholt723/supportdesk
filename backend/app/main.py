from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import get_pool, close_pool
from app.routers import webhook, tickets, pipeline, events, kb


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    yield
    await close_pool()


app = FastAPI(title="SupportDesk API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook.router, prefix="/api/webhook")
app.include_router(tickets.router, prefix="/api/tickets")
app.include_router(pipeline.router, prefix="/api/pipeline")
app.include_router(events.router, prefix="/api/events")
app.include_router(kb.router, prefix="/api/kb")


@app.get("/health")
async def health():
    return {"status": "ok"}
