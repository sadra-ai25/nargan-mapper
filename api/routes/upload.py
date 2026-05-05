"""
Upload Routes - مسیرهای آپلود و پردازش فایل
"""
import os
import uuid
import tempfile
import pandas as pd
from datetime import datetime, timedelta

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from src.detectors import detect_file_type
from src.validators import validate_excel_file
from database.connection import get_db
from database.models import (
    get_or_create_license,
    check_license_and_update,
    add_usage_log,
    get_license_info,
)

from src.mappers.cv_mapper import process_cv_ui
from src.mappers.pt_mapper import process_pt_ui


# جدید: mapperهای بدون Processor

router = APIRouter(prefix="/api", tags=["upload"])

TEMP_DIR = tempfile.gettempdir()
CACHE_DIR = os.path.join(TEMP_DIR, "nargan_cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def cleanup_old_files():
    try:
        now = datetime.now()
        for filename in os.listdir(CACHE_DIR):
            filepath = os.path.join(CACHE_DIR, filename)
            if os.path.isfile(filepath):
                file_age = now - datetime.fromtimestamp(os.path.getmtime(filepath))
                if file_age > timedelta(hours=2):
                    os.remove(filepath)
    except Exception:
        pass


@router.get("/download/{session_id}")
async def download_file(session_id: str):
    for filename in os.listdir(CACHE_DIR):
        # فقط بر اساس session_id جستجو کن تا تداخل ایجاد نشود
        if session_id in filename: 
            filepath = os.path.join(CACHE_DIR, filename)
            if os.path.isfile(filepath):
                return FileResponse(
                    filepath,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    filename=filename,
                )
    raise HTTPException(status_code=404, detail="فایل مورد نظر یافت نشد")



@router.get("/license")
async def get_license(request: Request):
    ip_address = get_client_ip(request)
    db_gen = get_db()
    db = next(db_gen)
    try:
        license_info = get_license_info(db, ip_address)
    finally:
        try: next(db_gen)
        except StopIteration:
            pass
    return JSONResponse(license_info)


@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    save_path: str = Form(default=""),
):
    ip_address = get_client_ip(request)

    if not file.filename.lower().endswith(('.xlsx', '.xlsm', '.xls')):
        raise HTTPException(status_code=400, detail="فرمت فایل باید xlsx، xlsm یا xls باشد")

    session_id = str(uuid.uuid4())
    temp_path = os.path.join(CACHE_DIR, f"{session_id}_{file.filename}")

    try:
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        # ۱) اعتبارسنجی
        is_valid, error_msg, _ = validate_excel_file(temp_path)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg or "فایل نامعتبر است")

        # ۲) تشخیص CV یا PT
        file_type = detect_file_type(temp_path)
        
        if file_type == "CV":
            df_final = process_cv_ui(temp_path)
            
        elif file_type == "PT":
            
            df_final = process_pt_ui(temp_path)
 # if file_type == "UNKNOWN":
        #     raise HTTPException(status_code=400, detail="نوع فایل قابل تشخیص نیست. باید CV یا PT باشد.")
        # ۳) محاسبه تعداد شیت‌ها
        engine = 'xlrd' if file.filename.lower().endswith('.xls') else 'openpyxl'
        xls = pd.ExcelFile(temp_path, engine=engine)
        sheets_processed = max(0, len(xls.sheet_names) - 4)

        if sheets_processed <= 0:
            raise HTTPException(status_code=400, detail="فایل باید حداقل ۵ شیت داشته باشد")

        # ۴) چک لایسنس
        db_gen = get_db()
        db = next(db_gen)
        try:
            success, message, remaining = check_license_and_update(db, ip_address, sheets_processed)
            if not success:
                return JSONResponse({
                    "success": False,
                    "error": message,
                    "remaining": remaining,
                    "license_expired": True
                })
        finally:
            try: next(db_gen)
            except StopIteration:
                pass

        # ۵) پردازش بدون Processor
        if file_type == "CV":
            df_final = process_cv_ui(temp_path)

        elif file_type == "PT":
            df_final = process_pt_ui(temp_path)

        else:
            raise HTTPException(status_code=400, detail="نوع فایل پشتیبانی نمی‌شود")

        records_count = len(df_final)

        # ۶) ثبت لاگ
        db_gen = get_db()
        db = next(db_gen)
        try:
            add_usage_log(db, ip_address, file.filename, file_type, sheets_processed, records_count)
        finally:
            try: next(db_gen)
            except StopIteration:
                pass

        # ۷) ذخیره خروجی
        base_name = os.path.splitext(file.filename)[0]
        output_filename = f"{base_name}_{session_id}_AVEVA_Final.xlsx"
        output_path = os.path.join(CACHE_DIR, output_filename)

        df_final.to_excel(output_path, index=False)

        cleanup_old_files()

        # لایسنس نهایی
        db_gen = get_db()
        db = next(db_gen)
        try:
            license_info = get_license_info(db, ip_address)
            remaining = license_info.get("remaining", 0)
        finally:
            try: next(db_gen)
            except StopIteration:
                pass

        return {
            "success": True,
            "message": "فایل با موفقیت پردازش شد",
            "session_id": session_id,
            "file_type": file_type,
            "sheets_processed": sheets_processed,
            "records_count": records_count,
            "filename": output_filename,
            "license": license_info,
            "remaining": remaining
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=1000, detail=f"خطا در پردازش فایل: {str(e)}")

    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass


@router.post("/license/reset")
async def reset_license(request: Request):
    ip_address = get_client_ip(request)
    db_gen = get_db()
    db = next(db_gen)
    try:
        license_record = get_or_create_license(db, ip_address)
        license_record.used_count = 0
        db.commit()
        license_info = get_license_info(db, ip_address)
    finally:
        try: next(db_gen)
        except StopIteration:
            pass

    return JSONResponse({
        "success": True,
        "message": "لایسنس با موفقیت ریست شد",
        "license": license_info,
    })
