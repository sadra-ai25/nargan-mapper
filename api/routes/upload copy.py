"""
Upload Routes - مسیرهای آپلود و پردازش فایل
"""
import os
import uuid
import tempfile
import pandas as pd
import re
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from src.detectors import detect_file_type
from src.processors import CVProcessor, PTProcessor

from src.validators import validate_excel_file
from database.connection import get_db
from database.models import (
    get_or_create_license,
    check_license_and_update,
    add_usage_log,
    get_license_info,
)

router = APIRouter(prefix="/api", tags=["upload"])

# مسیرهای موقت
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


# ==================== نگاشت نهایی CV - کامل و دقیق ====================
def map_to_aveva_cv(df_intermediate: pd.DataFrame) -> pd.DataFrame:
    """نگاشت کامل به فرمت AVEVA Vertical CV (78 ستون)"""
    records = []
    current_record = {}

    for _, row in df_intermediate.iterrows():
        section = str(row.get('بخش (Section)', '')).strip()
        feature = str(row.get('ویژگی (Feature)', '')).strip()
        value = str(row.get('مقدار (Value)', '')).strip()

        if section == 'HEADER' and feature == 'Sheet Name':
            if current_record:
                records.append(current_record)
            current_record = {'Sheet Name': value}
            continue

        if section and feature:
            key = f"{section} | {feature}"
            current_record[key] = value if value.lower() not in ['nan', 'none', ''] else ''

    if current_record:
        records.append(current_record)

    final_data = []
    for r in records:
        item = {
            'Sheet Name': r.get('Sheet Name', ''),
            'Tag Number': r.get('GENERAL | TAGNO') or r.get('Sheet Name', ''),

            # General
            'Ambient Temperature Min': r.get('GENERAL | AMBIENTTEMPERATUREMIN', ''),
            'Ambient Temperature Max': r.get('GENERAL | AMBIENTTEMPERATUREMAX', ''),
            'Allowable Noise Level': r.get('GENERAL | ALLOWABLENOISELEVEL', ''),
            'Tightness Requirements': r.get('GENERAL | TIGHTNESSREQUIREMENTS', ''),
            'Tight Shut Off': r.get('GENERAL | TIGHTSHUTOFF', ''),
            'Available Air Supply Pressure Min': r.get('GENERAL | AVAILABLEAIRSUPPLYPRESSUREMIN', ''),
            'Available Air Supply Pressure Norm': r.get('GENERAL | AVAILABLEAIRSUPPLYPRESSURENORM', ''),
            'Available Air Supply Pressure Max': r.get('GENERAL | AVAILABLEAIRSUPPLYPRESSUREMAX', ''),
            'Failure Position': r.get('GENERAL | FAILUREPOSITION', ''),
            'Nace Requirement': r.get('GENERAL | NACEREQUIREMENT', ''),

            # Pipeline / Line
            'Line Size Inlet': r.get('PIPELINE | LINESIZEINLET', '') or r.get('GENERAL | LINESIZEINLET', ''),
            'Schedule Inlet': r.get('PIPELINE | SCHEDULEINLET', ''),
            'Line Size Outlet': r.get('PIPELINE | LINESIZEOUTLET', ''),
            'Schedule Outlet': r.get('PIPELINE | SCHEDULEOUTLET', ''),
            'Pipe Material': r.get('PIPELINE | PIPEMATERIAL', ''),
            'Pipe Class': r.get('PIPELINE | PIPECLASS', ''),

            # Process Conditions
            'Process Fluid': r.get('PROCESS CONDITIONS | FLUID', '') or r.get('PROCESSDATA | FLUID', ''),
            'Status': r.get('PROCESS CONDITIONS | STATUS', ''),
            'Max Shut Off DP': r.get('PROCESS CONDITIONS | MAXSHUTOFFDP', ''),
            'Critical Pressure': r.get('PROCESS CONDITIONS | CRITICALPRESSURE', ''),
            'Design Pressure': r.get('PROCESS CONDITIONS | PRESSUREBARGDESIGN', '') or r.get('PROCESSDATA | PRESSUREBARGDESIGN', ''),
            'Design Temperature': r.get('PROCESS CONDITIONS | TEMPERATURECDESIGN', '') or r.get('PROCESSDATA | TEMPERATURECDESIGN', ''),

            # Calculated Results / Flow Matrix
            'Flow Rate Unit': r.get('CALCULATED RESULTS | FLOWRATEUNIT', ''),
            'Flow Rate Min Flow': r.get('CALCULATED RESULTS | FLOWRATEMINFLOW', ''),
            'Flow Rate Norm Flow': r.get('CALCULATED RESULTS | FLOWRATENORMFLOW', ''),
            'Flow Rate Max Flow': r.get('CALCULATED RESULTS | FLOWRATEMAXFLOW', ''),

            'Pressure Unit': r.get('CALCULATED RESULTS | PRESSUREUNIT', ''),
            'Pressure Min Flow': r.get('CALCULATED RESULTS | PRESSUREMINFLOW', ''),
            'Pressure Norm Flow': r.get('CALCULATED RESULTS | PRESSURENORMFLOW', ''),
            'Pressure Max Flow': r.get('CALCULATED RESULTS | PRESSUREMAXFLOW', ''),

            'Pressure Drop Unit': r.get('CALCULATED RESULTS | PRESSUREDROPUNIT', ''),
            'Pressure Drop Min Flow': r.get('CALCULATED RESULTS | PRESSUREDROPMINFLOW', ''),
            'Pressure Drop Norm Flow': r.get('CALCULATED RESULTS | PRESSUREDROPNORMFLOW', ''),
            'Pressure Drop Max Flow': r.get('CALCULATED RESULTS | PRESSUREDROPMAXFLOW', ''),

            'Temperature Unit': r.get('CALCULATED RESULTS | TEMPERATUREUNIT', ''),
            'Temperature Min Flow': r.get('CALCULATED RESULTS | TEMPERATUREMINFLOW', ''),
            'Temperature Norm Flow': r.get('CALCULATED RESULTS | TEMPERATURENORMFLOW', ''),
            'Temperature Max Flow': r.get('CALCULATED RESULTS | TEMPERATUREMAXFLOW', ''),

            'Viscosity Unit': r.get('CALCULATED RESULTS | VISCOSITYUNIT', ''),
            'Viscosity Min Flow': r.get('CALCULATED RESULTS | VISCOSITYMINFLOW', ''),
            'Viscosity Norm Flow': r.get('CALCULATED RESULTS | VISCOSITYNORMFLOW', ''),
            'Viscosity Max Flow': r.get('CALCULATED RESULTS | VISCOSITYMAXFLOW', ''),

            'Flash Unit': r.get('CALCULATED RESULTS | FLASHUNIT', ''),
            'Flash Min Flow': r.get('CALCULATED RESULTS | FLASHMINFLOW', ''),
            'Flash Norm Flow': r.get('CALCULATED RESULTS | FLASHNORMFLOW', ''),
            'Flash Max Flow': r.get('CALCULATED RESULTS | FLASHMAXFLOW', ''),

            # Body and Trim
            'Manufacturer Body AndTrim': r.get('BODY AND TRIM | MANUFACTURER', ''),
            'Model Body And Trim': r.get('BODY AND TRIM | MODEL', ''),
            'Body Type': r.get('BODY AND TRIM | BODYTYPE', ''),
            'Body Size': r.get('BODY AND TRIM | VALVEBODYSIZE', '') or r.get('BODY AND TRIM | BODYSIZE', ''),
            'Trim Size': r.get('BODY AND TRIM | TRIMSIZE', ''),
            'Rated Cv': r.get('CALCULATED RESULTS | CV', '') or r.get('CALCULATED RESULTS | RATEDCV', ''),
            'Characteristic': r.get('BODY AND TRIM | CHARACTERISTIC', ''),
            'End Connection And Rating': r.get('BODY AND TRIM | ENDCONNECTIONANDRATING', ''),
            'Body Material': r.get('BODY AND TRIM | VALVEBODYMATERIAL', '') or r.get('BODY AND TRIM | BODYMATERIAL', ''),
            'Bonnet Type': r.get('BODY AND TRIM | BONNETTYPE', ''),
            'Bonnet Material': r.get('BODY AND TRIM | BONNETMATERIAL', ''),

            # Positioner
            'Manufacturer Positioner': r.get('POSITIONER | MANUFACTURER', ''),
            'Model Positioner': r.get('POSITIONER | MODEL', ''),
            'Type Positioner': r.get('POSITIONER | TYPE', '') or r.get('POSITIONER | POSITIONERTYPE', ''),
            'Signal Inlet': r.get('POSITIONER | SIGNALINLET', ''),
            'Signal Outlet': r.get('POSITIONER | SIGNALOUTLET', ''),
            'Positioner Bypass': r.get('POSITIONER | POSITIONERBYPASS', ''),
            'Positioner Gauges': r.get('POSITIONER | POSITIONERGAUGES', ''),
            'Ex Protection Positioner': r.get('POSITIONER | EXPROTECTION', ''),
            'IP Positioner': r.get('POSITIONER | IPPROTECTION', ''),

            # Solenoid Valve
            'Manufacturer Solenoid Valve': r.get('SOLENOID VALVE | MANUFACTURER', ''),
            'Model Solenoid Valve': r.get('SOLENOID VALVE | MODEL', ''),
            'Type Solenoid Valve': r.get('SOLENOID VALVE | TYPE', ''),
            'Tag Number Solenoid Valve': r.get('SOLENOID VALVE | TAGNUMBER', ''),
            'Ex Protection Solenoid Valve': r.get('SOLENOID VALVE | EXPROTECTION', ''),
            'IP Solenoid Valve': r.get('SOLENOID VALVE | IPPROTECTION', ''),

            # Limit Switches
            'Manufacturer Limit Switches': r.get('LIMIT SWITCHES | MANUFACTURER', ''),
            'Model Limit Switches': r.get('LIMIT SWITCHES | MODEL', ''),
            'Type Limit Switches': r.get('LIMIT SWITCHES | TYPE', ''),
            'Quantity': r.get('LIMIT SWITCHES | QUANTITY', ''),
        }
        final_data.append(item)

    df_final = pd.DataFrame(final_data)
    df_final = df_final.replace(['none', 'None', 'nan', 'NaN', ''], '', regex=False).fillna('')
    return df_final


# ==================== نگاشت نهایی PT - کامل ====================
def map_to_aveva_pt(df_intermediate: pd.DataFrame) -> pd.DataFrame:
    """نگاشت کامل PT به فرمت AVEVA (بر اساس فایل نمونه)"""
    all_records = []
    current_record = {}

    for _, row in df_intermediate.iterrows():
        section = str(row.get('بخش (Section)', '')).strip()
        feature = str(row.get('ویژگی (Feature)', '')).strip()
        value = str(row.get('مقدار (Value)', '')).strip()

        if not feature or feature.lower() in ['nan', 'none']:
            continue

        if section == 'HEADER' and feature == 'Sheet Name':
            if current_record:
                all_records.append(current_record)
            current_record = {'Sheet Name': value}
            continue

        key = f"{section} | {feature}" if section else feature
        current_record[key] = value if value.lower() not in ['nan', 'none', ''] else ''

    if current_record:
        all_records.append(current_record)

    mapped_list = []
    for v in all_records:
        mapped = {
            'Name': v.get('GENERAL | TAGNO') or v.get('HEADER | TAGNO') or v.get('Sheet Name', ''),
            'PID No': v.get('GENERAL | PIDNO', '') or v.get('HEADER | PIDNO', ''),
            'Service': v.get('GENERAL | SERVICE', ''),
            'Line Equipment Number': v.get('GENERAL | LINEEQUIPMENTNUMBER', ''),
            'Fluid': v.get('PROCESS DATA | FLUID', '') or v.get('PROCESSDATA | FLUID', ''),
            'Design Pressure': v.get('PROCESS DATA | PRESSUREBARGDESIGN', '') or v.get('PROCESSDATA | PRESSUREBARGDESIGN', ''),
            'Operating Pressure': v.get('PROCESS DATA | PRESSUREBARGOPERATING', '') or v.get('PROCESSDATA | PRESSUREBARGOPERATING', ''),
            'Design Temperature': v.get('PROCESS DATA | TEMPERATURECDESIGN', '') or v.get('PROCESSDATA | TEMPERATURECDESIGN', ''),
            'Operating Temperature': v.get('PROCESS DATA | TEMPERATURECOPERATING', '') or v.get('PROCESSDATA | TEMPERATURECOPERATING', ''),
            'Density Specific Gravity Molecular Mass': v.get('PROCESS DATA | SPECGRAVITYOPERCONDITION', ''),
            'Viscosity': v.get('PROCESS DATA | VISCOSITYCPOPERCONDITION', ''),

            'Type Item': v.get('TRANSMITTER | TYPE', ''),
            'Instrument Range': (v.get('TRANSMITTER | INSTRUMENTRANGE', '') or 
                                v.get('TRANSMITTER | INSTRUMENTRANGEBARG', '') or 
                                v.get('TRANSMITTER | INSTRUMENTRANGEMBAR', '') or
                                v.get('TRANSMITTER | INSTRUMENTRANGEMMH2O', '')),
            'Calibration Range': (v.get('TRANSMITTER | CALIBRATIONRANGE', '') or 
                                 v.get('TRANSMITTER | CALIBRATIONRANGEBARG', '') or 
                                 v.get('TRANSMITTER | CALIBRATIONRANGEMBAR', '') or
                                 v.get('TRANSMITTER | CALIBRATIONRANGEMMH2O', '') or
                                 v.get('TRANSMITTER | CALIBRATIONRANGEKPA', '')),
            'Power Supply': v.get('TRANSMITTER | POWERSUPPLY', ''),
            'Electrical Connection': v.get('TRANSMITTER | ELECTRICALCONNECTION', ''),
            'Accuracy': v.get('TRANSMITTER | ACCURACY', ''),
            'Element Type': v.get('TRANSMITTER | ELEMENTTYPE', ''),
            'Body Material': v.get('TRANSMITTER | BODYMATERIAL', ''),
            'Fill Fluid Transmitter': v.get('TRANSMITTER | FILLFLUID', ''),
            'Process Connection': v.get('TRANSMITTER | PROCESSCONNECTION', ''),

            # Diaphragm Seal
            'Diaphragm Type': v.get('DIAPHRAGMSEAL | DIAPHRAGMTYPE', '') or v.get('DIAPHRAGM SEAL | DIAPHRAGMTYPE', ''),
            'Diaphragm Material': v.get('DIAPHRAGMSEAL | DIAPHRAGMMATERIAL', '') or v.get('DIAPHRAGM SEAL | DIAPHRAGMMATERIAL', ''),
            'Capillary Length': v.get('DIAPHRAGMSEAL | CAPILLARYLENGTH', ''),
            'Capillary Material': v.get('DIAPHRAGMSEAL | CAPILLARYMATERIAL', ''),
            'Fill Fluid Diaphragm Seal': v.get('DIAPHRAGMSEAL | FILLFLUID', '') or v.get('DIAPHRAGM SEAL | FILLFLUID', ''),

            # Manifold
            'Manifold Type': v.get('MANIFOLD | MANIFOLDTYPE', ''),
            'Manifold Body Material': v.get('MANIFOLD | MANIFOLDBODYMATERIAL', ''),
            'Manifold Rating': v.get('MANIFOLD | MANIFOLDRATING', ''),

            # Options
            'Integral Indicator': v.get('OPTIONS | INTEGRALINDICATOR', ''),
            'Ingress Protection': v.get('TRANSMITTER | INGRESSPROTECTION', ''),
            'Elec Ex Protection': v.get('TRANSMITTER | ELECEXPROTECTION', ''),
            'Nace Requirement': v.get('GENERAL | NACEREQUIREMENTSTANDARD', ''),
        }
        mapped_list.append(mapped)

    df_final = pd.DataFrame(mapped_list)
    df_final = df_final.replace(['none', 'None', 'nan', 'NaN', ''], '', regex=False).fillna('')

    # حذف ردیف‌های خالی
    df_final = df_final[df_final['Name'] != '']

    # مرتب‌سازی ستون‌ها (اولویت)
    priority = ['Name', 'PID No', 'Service', 'Fluid', 'Design Pressure', 'Design Temperature', 'Type Item']
    other_cols = [c for c in df_final.columns if c not in priority]
    df_final = df_final[priority + other_cols]

    return df_final

@router.get("/download/{session_id}")
async def download_file(session_id: str):
    for filename in os.listdir(CACHE_DIR):
        if session_id in filename or filename.endswith("_AVEVA_Final.xlsx"):
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
    print(f"[DEBUG] Received file: {file.filename} | Size: {file.size} bytes")

    if not file.filename.lower().endswith(('.xlsx', '.xlsm', '.xls')):
        raise HTTPException(status_code=400, detail="فرمت فایل باید xlsx، xlsm یا xls باشد")

    session_id = str(uuid.uuid4())
    temp_path = os.path.join(CACHE_DIR, f"{session_id}_{file.filename}")

    try:
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        # اعتبارسنجی فایل
        is_valid, error_msg, _ = validate_excel_file(temp_path)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg or "فایل نامعتبر است")

        # تشخیص نوع فایل (PT یا CV)
        file_type = detect_file_type(temp_path)
        if file_type == "UNKNOWN":
            raise HTTPException(status_code=400, detail="نوع فایل قابل تشخیص نیست. لطفاً فایل PT یا CV آپلود کنید.")

        # باز کردن فایل برای شمارش شیت‌ها
        engine = 'xlrd' if file.filename.lower().endswith('.xls') else 'openpyxl'
        xls = pd.ExcelFile(temp_path, engine=engine)
        sheets_processed = max(0, len(xls.sheet_names) - 4)

        if sheets_processed <= 0:
            raise HTTPException(status_code=400, detail="فایل باید حداقل ۵ شیت داشته باشد")

        # چک لایسنس
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
            try:
                next(db_gen)
            except StopIteration:
                pass


        if file_type == "CV":
            processor = CVProcessor(temp_path)
            df_intermediate = processor.process()
            df_final = map_to_aveva_cv(df_intermediate)
        else:  # PT
            processor = PTProcessor(temp_path)
            df_intermediate = processor.process()
            df_final = map_to_aveva_pt(df_intermediate)

        records_count = len(df_final)

        # ثبت لاگ استفاده
        db_gen = get_db()
        db = next(db_gen)
        try:
            add_usage_log(db, ip_address, file.filename, file_type, sheets_processed, records_count)
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

        # ذخیره فایل نهایی
        base_name = os.path.splitext(file.filename)[0]
        output_filename = f"{base_name}_AVEVA_Final.xlsx"
        output_path = os.path.join(CACHE_DIR, output_filename)

        df_final.to_excel(output_path, index=False)

        print(f"[SUCCESS] Processed {sheets_processed} sheets → {records_count} records | File: {output_filename}")

        cleanup_old_files()

        # دریافت اطلاعات لایسنس به‌روز
        db_gen = get_db()
        db = next(db_gen)
        try:
            license_info = get_license_info(db, ip_address)
            remaining = license_info.get("remaining", 0)
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

        # بازگشت پاسخ به فرانت‌اند (وب)
        return {
            "success": True,
            "message": "فایل با موفقیت پردازش و نگاشت شد",
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
        print(f"[ERROR] Processing failed: {type(e).__name__} - {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"خطا در پردازش فایل: {str(e)}")
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
