"""
Detector module - تشخیص نوع فایل (PT یا CV)
نسخه بهبودیافته و مقاوم
"""
import os
import warnings
import pandas as pd

warnings.filterwarnings('ignore')


def get_excel_engine(file_path: str) -> str:
    """تعیین engine مناسب"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.xls':
        return 'xlrd'
    return 'openpyxl'


def detect_file_type(file_path: str) -> str:
    """
    تشخیص نوع فایل PT یا CV با روش‌های چندلایه
    """
    try:
        engine = get_excel_engine(file_path)
        xls = pd.ExcelFile(file_path, engine=engine)
        
        print(f"[DEBUG] Total sheets: {len(xls.sheet_names)} | Names: {xls.sheet_names[:10]}...")  # برای دیباگ

        # اگر کمتر از ۵ شیت داشت → UNKNOWN
        if len(xls.sheet_names) <= 4:
            print("[DEBUG] Not enough sheets")
            return 'UNKNOWN'

        # --- روش ۱: جستجو در تمام شیت‌ها از شیت پنجم به بعد ---
        sheet_list = xls.sheet_names[4:]
        
        cv_indicators = [
            'BODY AND TRIM', 'POSITIONER', 'ACTUATOR', 'NORMAL FLOW', 'MIN. FLOW', 
            'MAX. FLOW', 'TRIM TYPE', 'VALVE CHARACTERISTIC', 'Cv VALUE', 
            'VALVE BODY', 'PLUG TYPE', 'SEAT LEAKAGE', 'CONTROL VALVE', 'Cv'
        ]
        
        pt_indicators = [
            'TRANSMITTER', 'DIAPHRAGM SEAL', 'MANIFOLD', 'PROCESS DATA', 
            'CALIBRATION RANGE', 'INSTRUMENT RANGE', 'FILL FLUID', 
            'ELEMENT TYPE', 'PRESSURE TRANSMITTER'
        ]

        for sheet_name in sheet_list:
            try:
                # خواندن امن (بدون usecols ثابت)
                df = pd.read_excel(
                    file_path,
                    sheet_name=sheet_name,
                    header=None,
                    nrows=30,           # بیشتر ردیف بررسی شود
                    engine=engine,
                    dtype=str
                )
                
                # محدود کردن ستون اگر خیلی زیاد بود
                if len(df.columns) > 50:
                    df = df.iloc[:, :50]
                
                content_str = ' '.join(df.fillna('').astype(str).values.flatten()).upper()
                
                # جستجوی CV
                for ind in cv_indicators:
                    if ind in content_str:
                        print(f"[DEBUG] CV detected in sheet: {sheet_name} | Indicator: {ind}")
                        return 'CV'
                
                # جستجوی PT
                for ind in pt_indicators:
                    if ind in content_str:
                        print(f"[DEBUG] PT detected in sheet: {sheet_name} | Indicator: {ind}")
                        return 'PT'
                        
            except Exception as e:
                print(f"[WARNING] Error reading sheet '{sheet_name}': {e}")
                continue

        # --- روش ۲: بررسی نام شیت‌ها (fallback) ---
        for sheet_name in xls.sheet_names:
            sheet_upper = sheet_name.upper()
            if any(k in sheet_upper for k in ['CV', 'CONTROL VALVE', 'VALVE']):
                print(f"[DEBUG] CV detected by sheet name: {sheet_name}")
                return 'CV'
            if any(k in sheet_upper for k in ['PT', 'PRESSURE', 'TRANSMITTER']):
                print(f"[DEBUG] PT detected by sheet name: {sheet_name}")
                return 'PT'

        # --- روش ۳: اگر هیچی پیدا نشد، بر اساس نام فایل حدس بزن ---
        filename_upper = os.path.basename(file_path).upper()
        if 'CV' in filename_upper or 'CONTROL' in filename_upper or 'VALVE' in filename_upper:
            print("[DEBUG] CV detected by filename")
            return 'CV'
        if 'PT' in filename_upper or 'PRESSURE' in filename_upper or 'TRANSMITTER' in filename_upper:
            print("[DEBUG] PT detected by filename")
            return 'PT'

        print("[DEBUG] No indicators found → UNKNOWN")
        return 'UNKNOWN'
    
    except Exception as e:
        print(f"[ERROR] detect_file_type failed: {e}")
        return 'UNKNOWN'