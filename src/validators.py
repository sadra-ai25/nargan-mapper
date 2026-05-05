"""
Validators - اعتبارسنجی فایل‌ها
"""
import os
import warnings
import pandas as pd

warnings.filterwarnings('ignore')


def get_excel_engine(file_path: str) -> str:
    """تعیین engine مناسب بر اساس پسوند فایل"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.xls':
        return 'xlrd'
    return 'openpyxl'


def validate_excel_file(file_path: str) -> tuple:
    """
    اعتبارسنجی فایل اکسل - نسخه مقاوم در برابر شیت‌های با ستون کم
    """
    if not os.path.exists(file_path):
        return False, "فایل یافت نشد", None
    
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ['.xlsx', '.xlsm', '.xls']:
        return False, "فرمت فایل باید xlsx، xlsm یا xls باشد", None
    
    try:
        engine = get_excel_engine(file_path)
        xls = pd.ExcelFile(file_path, engine=engine)
        
        # بررسی تعداد شیت‌ها
        if len(xls.sheet_names) <= 4:
            return False, "فایل باید حداقل 5 شیت داشته باشد", None
        
        # تست خواندن امن شیت پنجم به بعد (بدون usecols ثابت)
        for sheet_name in xls.sheet_names[4:]:
            try:
                # اول بدون usecols بخوانیم تا تعداد ستون‌ها را بفهمیم
                test_df = pd.read_excel(
                    file_path,
                    sheet_name=sheet_name,
                    header=None,
                    nrows=5,
                    engine=engine,
                    dtype=str
                )
                
                # اگر شیت خیلی کم ستون داشت، باز هم قبول کنیم (فقط هشدار)
                if len(test_df.columns) < 10:
                    print(f"[WARNING] Sheet '{sheet_name}' has only {len(test_df.columns)} columns.")
                
            except Exception as e:
                return False, f"خطا در خواندن شیت '{sheet_name}': {str(e)}", None
        
        return True, None, None
    
    except Exception as e:
        return False, f"خطا در اعتبارسنجی فایل: {str(e)}", None