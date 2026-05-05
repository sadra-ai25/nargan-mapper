"""
Base Processor - کلاس پایه برای پردازش فایل‌ها
پشتیبانی کامل از xlsx, xlsm, xls
"""
import pandas as pd
import re
import os
import warnings
from abc import ABC, abstractmethod

# غیرفعال کردن هشدارها
warnings.filterwarnings('ignore')


def clean_value(val):
    """پاکسازی مقدار"""
    if pd.isna(val):
        return None
    s = str(val).strip()
    if s.lower() in ['nan', 'none', '', '‐', '–', '#n/a', '#ref!']:
        return None
    s = re.sub(r'\s+', ' ', s)
    return s


def get_excel_engine(file_path: str) -> str:
    """تعیین engine مناسب بر اساس پسوند فایل"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.xls':
        return 'xlrd'
    return 'openpyxl'


class BaseProcessor(ABC):
    """کلاس پایه پردازشگر"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.xls = None
        self.sheet_names = []
        self.all_data = []
        self.engine = get_excel_engine(file_path)
    
    def load_file(self, start_sheet: int = 4):
        """بارگذاری فایل و دریافت لیست شیت‌ها"""
        self.xls = pd.ExcelFile(self.file_path, engine=self.engine)
        self.sheet_names = self.xls.sheet_names[start_sheet:]
        return self.sheet_names
    
    @abstractmethod
    def extract_header(self, df: pd.DataFrame, sheet_name: str) -> dict:
        """استخراج اطلاعات هدر شیت"""
        pass
    
    @abstractmethod
    def process_rows(self, df: pd.DataFrame, header_info: dict) -> list:
        """پردازش ردیف‌ها"""
        pass
    
    def read_sheet_safe(self, sheet_name: str) -> pd.DataFrame:
        """خواندن امن شیت با مدیریت خطاها"""
        try:
            df = pd.read_excel(
                self.file_path,
                sheet_name=sheet_name,
                header=None,
                engine=self.engine,
                dtype=str,  # همه ستون‌ها را به رشته تبدیل کن
            )
            return df
        except Exception as e:
            print(f"Warning: Error reading sheet '{sheet_name}': {e}")
            # تلاش با محدودیت ستون
            try:
                df = pd.read_excel(
                    self.file_path,
                    sheet_name=sheet_name,
                    header=None,
                    engine=self.engine,
                    dtype=str,
                    usecols=range(25),  # فقط 25 ستون اول
                )
                return df
            except Exception:
                return pd.DataFrame()
    
    def process(self) -> pd.DataFrame:
        """پردازش کامل فایل"""
        sheet_list = self.load_file()
        
        for sheet_name in sheet_list:
            try:
                df = self.read_sheet_safe(sheet_name)
                
                if df.empty:
                    print(f"Warning: Empty sheet '{sheet_name}', skipping...")
                    continue
                
                header_info = self.extract_header(df, sheet_name)
                
                # ثبت نام شیت در هدر
                self.all_data.append({
                    'بخش (Section)': 'HEADER',
                    'ویژگی (Feature)': 'Sheet Name',
                    'مقدار (Value)': sheet_name
                })
                
                for key, val in header_info.items():
                    if val:
                        self.all_data.append({
                            'بخش (Section)': 'HEADER',
                            'ویژگی (Feature)': key,
                            'مقدار (Value)': val
                        })
                
                # پردازش ردیف‌ها
                sheet_data = self.process_rows(df, header_info)
                self.all_data.extend(sheet_data)
                
            except Exception as e:
                print(f"Error processing sheet '{sheet_name}': {e}")
                continue
        
        return pd.DataFrame(self.all_data)