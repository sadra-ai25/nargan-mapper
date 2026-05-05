"""
License Middleware - میان‌افزار بررسی لایسنس
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from database.connection import get_db
from database.models import get_or_create_license


class LicenseMiddleware(BaseHTTPMiddleware):
    """میان‌افزار بررسی لایسنس برای همه درخواست‌ها"""
    
    EXEMPT_PATHS = [
        "/",
        "/health",
        "/api/",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/static",
    ]
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # exempt paths
        if any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS):
            return await call_next(request)
        
        # get client IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip_address = forwarded.split(",")[0].strip()
        else:
            ip_address = request.client.host if request.client else "unknown"
        
        # check license
        db_gen = get_db()
        db = next(db_gen)
        try:
            license_record = get_or_create_license(db, ip_address)
            
            if not license_record.is_active:
                return JSONResponse({
                    "success": False,
                    "error": "حساب شما غیرفعال شده است",
                    "license_expired": True,
                    "remaining": 0,
                })
            
            if license_record.is_expired:
                return JSONResponse({
                    "success": False,
                    "error": "لایسنس شما به پایان رسیده است",
                    "license_expired": True,
                    "remaining": 0,
                    "total_limit": license_record.total_limit,
                    "used_count": license_record.used_count,
                })
        
        except Exception as e:
            return JSONResponse({
                "success": False,
                "error": f"خطا در بررسی لایسنس: {str(e)}",
            })
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
        
        response = await call_next(request)
        return response