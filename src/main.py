from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from core.deps import engine
from models import Base
from routers.auth import router as auth_router
from routers.customers import router as customers_router
from routers.notes import router as notes_router
from routers.health import router as health_router
from routers.subscriptions import router as subscriptions_router
from routers.appointments import router as appointments_router
from routers.products import router as products_router
from routers.payments import router as payments_router
from routers.communications import router as communications_router
from routers.reports import router as reports_router

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
app.include_router(health_router)
app.include_router(subscriptions_router)
app.include_router(appointments_router)
app.include_router(products_router)
app.include_router(payments_router)
app.include_router(communications_router)
app.include_router(reports_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "Wellness Clinic API v1.0.0"}