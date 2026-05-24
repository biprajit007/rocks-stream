import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db import Base, engine, SessionLocal
from app.routers import ads, auth, playback, social, streams
from app.services.main_stream import sync_main_stream_alias
from app.services.seed import seed_admin
from app.services.aes_key_store import current_key  # warm up key store

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    os.makedirs(settings.hls_root, exist_ok=True)
    os.makedirs(settings.logos_root, exist_ok=True)
    os.makedirs(settings.logs_root, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_admin(db)
        sync_main_stream_alias(db)
    finally:
        db.close()
    social.restore_scheduled_social_stops()
    # Warm up AES key store — generates the first rotating key immediately
    current_key()


@app.get("/health")
def health():
    return {"ok": True, "service": "backend"}


@app.get(f"{settings.api_v1_prefix}/health")
def api_health():
    return {"ok": True, "service": "backend", "scope": "api"}


app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(streams.router, prefix=settings.api_v1_prefix)
app.include_router(ads.router, prefix=settings.api_v1_prefix)
app.include_router(social.router, prefix=settings.api_v1_prefix)
app.include_router(playback.router)
