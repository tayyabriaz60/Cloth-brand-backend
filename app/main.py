from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.routers import (
    auth,
    bills,
    catalog,
    customers,
    dashboard,
    health,
    ledger,
    shop,
    stock,
    uploads,
    users,
)

settings = get_settings()

app = FastAPI(
    title="Cloth POS API",
    description="Backend for a bilingual (Urdu/English) POS for small cloth shops.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

register_error_handlers(app)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse("/docs")


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(customers.router)
app.include_router(bills.router)
app.include_router(stock.router)
app.include_router(ledger.router)
app.include_router(dashboard.router)
app.include_router(shop.router)
app.include_router(users.router)
app.include_router(uploads.router)
