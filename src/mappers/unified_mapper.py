# src/mappers/unified_mapper.py
"""
Unified Mapper - نگاشت یکپارچه CV و PT
"""
import pandas as pd
from typing import Dict, Any

# تعریف ساختار استاندارد AVEVA
AVEVA_SCHEMA = {
    'Name': str,
    'PID No': str,
    'Service': str,
    'Fluid': str,
    'Design Pressure': str,
    'Operating Pressure': str,
    'Design Temperature': str,
    'Operating Temperature': str,
    'Valve Body Size': str,
    'Valve Body Material': str,
    'Plug Type': str,
    'Characteristic': str,
    'Actuator Type': str,
    'Positioner Type': str,
    'Cv Value': str,
}

def normalize_cv_output(df: pd.DataFrame) -> pd.DataFrame:
    """تبدیل خروجی CV به فرمت استاندارد"""
    # تغییر نام ستون‌ها به فرمت AVEVA
    column_mapping = {
        'Sheet Name': 'Name',
        'GENERAL | TAGNO': 'PID No',
        'GENERAL | SERVICE': 'Service',
        'PROCESS CONDITIONS | FLUID': 'Fluid',
        'PROCESS CONDITIONS | PRESSUREBARGDESIGN': 'Design Pressure',
        'PROCESS CONDITIONS | PRESSUREBARGOPERATING': 'Operating Pressure',
        'PROCESS CONDITIONS | TEMPERATURECDESIGN': 'Design Temperature',
        'PROCESS CONDITIONS | TEMPERATURECOPERATING': 'Operating Temperature',
        'BODY AND TRIM | VALVEBODYSIZE': 'Valve Body Size',
        'BODY AND TRIM | VALVEBODYMATERIAL': 'Valve Body Material',
        'BODY AND TRIM | PLUGTYPE': 'Plug Type',
        'BODY AND TRIM | CHARACTERISTIC': 'Characteristic',
        'ACTUATOR | ACTUATORTYPE': 'Actuator Type',
        'POSITIONER | POSITIONERTYPE': 'Positioner Type',
        'CALCULATED RESULTS | CV': 'Cv Value',
    }
    return df.rename(columns=column_mapping)

def normalize_pt_output(df: pd.DataFrame) -> pd.DataFrame:
    """تبدیل خروجی PT به فرمت استاندارد"""
    # PT ستون‌های خاص خودش رو داره
    # فقط ستون‌های مشترک رو نگاشت می‌کنیم
    common_columns = ['Name', 'PID No', 'Service', 'Fluid', 'Design Pressure', 
                      'Operating Pressure', 'Design Temperature', 'Operating Temperature']
    
    result = {}
    for col in common_columns:
        if col in df.columns:
            result[col] = df[col]
        else:
            result[col] = ''
    
    return pd.DataFrame([result])

def process_unified(file_path: str, file_type: str) -> pd.DataFrame:
    """
    پردازش یکپارچه - تشخیص نوع فایل و نگاشت به فرمت واحد
    """
    if file_type == 'CV':
        from .cv_processor import CVProcessor
        processor = CVProcessor(file_path)
        df_intermediate = processor.process()
        return normalize_cv_output(df_intermediate)
    
    elif file_type == 'PT':
        from .pt_processor import PTProcessor
        processor = PTProcessor(file_path)
        df_intermediate = processor.process()
        return normalize_pt_output(df_intermediate)
    
    else:
        raise ValueError(f"نوع فایل نامعتبر: {file_type}")