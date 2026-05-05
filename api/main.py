"""
Main FastAPI Application
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os

from .routes import upload
from database.connection import init_db, get_db
from database.models import get_license_info

# ایجاد اپلیکیشن
app = FastAPI(
    title="Nargan Mapper API",
    description="API for mapping PT and CV datasheets to AVEVA format",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static & Templates
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_path = os.path.join(BASE_DIR, "static")
templates_path = os.path.join(BASE_DIR, "templates")

print(f"[DEBUG] Static path: {static_path}")   # این را ببین تا مطمئن شوی مسیر درست است
print(f"[DEBUG] Templates path: {templates_path}")

os.makedirs(static_path, exist_ok=True)
os.makedirs(templates_path, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_path), name="static")
templates = Jinja2Templates(directory=templates_path)

# Include Routes
app.include_router(upload.router)

# Startup Event
@app.on_event("startup")
async def startup_event():
    init_db()

# Health Check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "nargan-mapper"}

# Root Page - صفحه اصلی
@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    """صفحه اصلی"""
    ip_address = get_client_ip(request)
    
    db_gen = get_db()
    db = next(db_gen)
    try:
        license_info = get_license_info(db, ip_address)
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "license": license_info,
    })

def get_client_ip(request: Request) -> str:
    """دریافت IP کلاینت"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"