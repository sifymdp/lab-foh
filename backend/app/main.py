from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.yolo_models import load_models, unload_models
from app.config import settings
from app.database import Base, SessionLocal, engine, migrate_schema
from app.routers import ai, auth, floors, guest, menu, orders, reservations, sessions, stream, tables, users, ws
from app.seed import seed_database
from app.workers import camera_worker


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    migrate_schema()
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    models_loaded = load_models()
    if models_loaded:
        camera_worker.start_worker()
    yield
    stream.stop_all_stream_workers()
    await camera_worker.stop_worker()
    unload_models()


app = FastAPI(title="FOH Table Management API", version="1.0.0", lifespan=lifespan)

# Allow all localhost origins during development
cors_origins = settings.cors_origin_list + [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(floors.router)
app.include_router(tables.router)
app.include_router(sessions.router)
app.include_router(users.router)
app.include_router(menu.router)
app.include_router(reservations.router)
app.include_router(orders.router)
app.include_router(guest.router)
app.include_router(ai.router)
app.include_router(ws.router)
app.include_router(stream.router)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}
