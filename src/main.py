from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from core.deps import engine
from models import Base
from routers.auth import router as auth_router
from routers.customers import router as customers_router
from routers.notes import router as notes_router

# Create all tables on startup (only if alembic hasn't migrated)
# We catch the error gracefully in case tables already exist
try:
    Base.metadata.create_all(bind=engine)
except Exception:
    pass

app = FastAPI(title="Wellness Clinic API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(customers_router)
app.include_router(notes_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "Wellness Clinic API v1.0.0"}