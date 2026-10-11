"""Ali Kuryer FastAPI entrypoint.

Do not require optional template/static directories on startup. The public
landing page lives at the repository root in index.html.
"""
import os
from pathlib import Path
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
import app.models  # Register SQLAlchemy tables before create_all

from app.bootstrap import ensure_admin
from app.config import settings
from app import auth, telegram_login
from app.routers import support_bot
from app.routers import customer, panels, restaurant, orders, admin, courier, customer_experience, commerce, customer_profile

ROOT_DIR = Path(__file__).resolve().parent
STATIC_DIR = ROOT_DIR / "app" / "static"
TEMPLATE_DIR = ROOT_DIR / "app" / "templates"

@asynccontextmanager
async def support_lifespan(app: FastAPI):
    await asyncio.to_thread(support_bot.register_support_webhook)
    yield


app = FastAPI(
    title="Ali Kuryer",
    docs_url=None if settings.ENVIRONMENT == "production" else "/api/docs",
    redoc_url=None,
    lifespan=support_lifespan,
)

Base.metadata.create_all(bind=engine)
ensure_admin()

# A missing optional directory must not crash the whole service.
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

ASSET_DIR = ROOT_DIR / "site-assets"
if ASSET_DIR.is_dir():
    app.mount("/site-assets", StaticFiles(directory=str(ASSET_DIR)), name="site-assets")
LEGAL_DIR = ROOT_DIR / "legal"
if LEGAL_DIR.is_dir():
    app.mount("/legal", StaticFiles(directory=str(LEGAL_DIR)), name="legal")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR)) if TEMPLATE_DIR.is_dir() else None

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ali-kuryer.uz",
        "https://www.ali-kuryer.uz",
        "https://saidbayevs73-sketch.github.io",
        "https://ali-kuryer.onrender.com",
        "https://ali-kuryer-1.onrender.com",
    ],
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth.router)
app.include_router(telegram_login.router)
app.include_router(customer_experience.router)
app.include_router(customer.router)
app.include_router(customer_profile.router)
app.include_router(panels.router)
app.include_router(restaurant.router)
app.include_router(orders.router)
app.include_router(commerce.router)
app.include_router(admin.router)
app.include_router(courier.router)
app.include_router(support_bot.router)


@app.get("/", include_in_schema=False)
def home():
    index = ROOT_DIR / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=503, detail="Bosh sahifa topilmadi")
    return FileResponse(str(index), media_type="text/html")


@app.get("/api/health")
def health():
    return {"ok": True, "service": "Ali Kuryer"}


def _panel(request: Request):
    if os.getenv("ENABLE_STAFF_WEB_PANELS", "0") != "1":
        raise HTTPException(status_code=404, detail="Topilmadi")
    # Existing deployments do not include the panel template yet.
    # Do not return a false-success page or crash with TemplateNotFound.
    if templates is None or not (TEMPLATE_DIR / "panel.html").is_file():
        raise HTTPException(status_code=404, detail="Panel hozircha mavjud emas")
    return templates.TemplateResponse(request=request, name="panel.html")


@app.get("/admin", include_in_schema=False)
def admin_panel(request: Request):
    return _panel(request)


@app.get("/restaurant", include_in_schema=False)
def restaurant_panel(request: Request):
    return RedirectResponse("https://ali-kuryer-1.onrender.com/restaurant", status_code=303)


@app.get("/courier", include_in_schema=False)
def courier_panel(request: Request):
    return RedirectResponse("https://ali-kuryer-1.onrender.com/courier", status_code=303)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(self), geolocation=(self)"
    return response
