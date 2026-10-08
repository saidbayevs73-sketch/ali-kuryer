
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import Base, engine
import app.models

from app.bootstrap import ensure_admin
from app.config import settings

from app import auth
from app.routers import (
    customer,
    panels,
    restaurant,
    orders,
    admin,
    courier,
)

app = FastAPI(
    title="Ali Kuryer NEW",
    docs_url=(
        None
        if settings.environment == "production"
        else "/api/docs"
    ),
    redoc_url=None,
)

# Ma'lumotlar bazasi
Base.metadata.create_all(bind=engine)
ensure_admin()

# Statik fayllar va HTML sahifalar
app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)

templates = Jinja2Templates(directory="app/templates")

# API routerlar
app.include_router(auth.router)
app.include_router(customer.router)
app.include_router(panels.router)
app.include_router(restaurant.router)
app.include_router(orders.router)
app.include_router(admin.router)
app.include_router(courier.router)


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request},
    )


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "Ali Kuryer NEW",
    }


@app.get("/admin")
def admin_panel(request: Request):
    return templates.TemplateResponse(
        "panel.html",
        {"request": request},
    )


@app.get("/restaurant")
def restaurant_panel(request: Request):
    return templates.TemplateResponse(
        "panel.html",
        {"request": request},
    )


@app.get("/courier")
def courier_panel(request: Request):
    return templates.TemplateResponse(
        "panel.html",
        {"request": request},
    )


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = (
        "strict-origin-when-cross-origin"
    )
    response.headers["Permissions-Policy"] = (
        "camera=(self), geolocation=(self)"
    )

    return response
