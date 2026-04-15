from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import router
from backend.app.core.config import settings
from backend.app.services.assistant import NavigationAssistantService
from backend.app.services.storage import NavigationStore


app = FastAPI(
    title="Smart Blind Navigation API",
    description="Real-time AI-powered navigation assistant for visually impaired users.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = NavigationStore(settings.database_path)
store.initialize()
app.state.assistant = NavigationAssistantService(settings=settings, store=store)
app.include_router(router, prefix=settings.api_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health",
    }
