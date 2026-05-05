# src/cv_mapper_final.py
import pandas as pd
import re

def normalize_text(text):
    if pd.isna(text) or not text:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(text)).upper()

def get_val(v_dict, section, feature, default=""):
    key = f"{section} | {feature}" if section else feature
    return v_dict.get(key, default)

def get_split_val(v_dict, section, feature, index=0, delimiter='/', default=""):
    val = get_val(v_dict, section, feature)
    if not val:
        return default
    parts = [p.strip() for p in val.split(delimiter)]
    return parts[index] if index < len(parts) else default

def map_to_aveva_cv(df_intermediate: pd.DataFrame) -> pd.DataFrame:
    """
    نگاشت نهایی به فرمت استاندارد AVEVA برای Control Valve
    """
    all_valves = []
    current_valve = {}

    for _, row in df_intermediate.iterrows():
        section = str(row.get('بخش (Section)', '')).strip()
        feature = str(row.get('ویژگی (Feature)', '')).strip()
        value = str(row.get('مقدار (Value)', '')).strip()

        if not feature or feature.lower() in ['nan', 'none']:
            continue

        if section == 'HEADER' and feature == 'Sheet Name':
            if current_valve:
                all_valves.append(current_valve)
            current_valve = {}
            current_valve['Sheet Name'] = value
            continue

        key = f"{section} | {feature}" if section else feature
        current_valve[key] = value if value.lower() not in ['nan', 'none', ''] else ''

    if current_valve:
        all_valves.append(current_valve)

    # نگاشت به ستون‌های نهایی AVEVA
    mapped_list = []
    for v in all_valves:
        mapped = {}

        # General & Header
        mapped['Name'] = get_val(v, 'GENERAL', 'TAGNO') or get_val(v, 'HEADER', 'Sheet Name')
        mapped['PID No'] = get_val(v, 'GENERAL', 'PIDNO')
        mapped['Service'] = get_val(v, 'GENERAL', 'SERVICE')

        # Process Conditions
        mapped['Fluid'] = get_val(v, 'PROCESS CONDITIONS', 'FLUID')
        mapped['Design Pressure'] = get_val(v, 'PROCESS CONDITIONS', 'PRESSUREBARGDESIGN')
        mapped['Operating Pressure'] = get_val(v, 'PROCESS CONDITIONS', 'PRESSUREBARGOPERATING')
        mapped['Design Temperature'] = get_val(v, 'PROCESS CONDITIONS', 'TEMPERATURECDESIGN')
        mapped['Operating Temperature'] = get_val(v, 'PROCESS CONDITIONS', 'TEMPERATURECOPERATING')

        # Body & Trim
        mapped['Valve Body Size'] = get_val(v, 'BODY AND TRIM', 'VALVEBODYSIZE')
        mapped['Valve Body Material'] = get_val(v, 'BODY AND TRIM', 'VALVEBODYMATERIAL')
        mapped['Plug Type'] = get_val(v, 'BODY AND TRIM', 'PLUGTYPE')
        mapped['Seat Material'] = get_val(v, 'BODY AND TRIM', 'SEATMATERIAL')
        mapped['Characteristic'] = get_val(v, 'BODY AND TRIM', 'CHARACTERISTIC')

        # Actuator & Positioner
        mapped['Actuator Type'] = get_val(v, 'ACTUATOR', 'ACTUATORTYPE')
        mapped['Positioner Type'] = get_val(v, 'POSITIONER', 'POSITIONERTYPE')
        mapped['Signal Type'] = get_val(v, 'POSITIONER', 'SIGNALTYPE')

        # Calculated
        mapped['Cv Value'] = get_val(v, 'CALCULATED RESULTS', 'CV')

        # اضافه کردن فیلدهای بیشتر اگر نیاز بود (از notebook خودتان)

        mapped_list.append(mapped)

    df_final = pd.DataFrame(mapped_list)
    df_final = df_final.replace(['none', 'None', 'nan', 'NaN'], '', regex=False).fillna('')
    
    # مرتب‌سازی ستون‌ها (اولویت)
    priority = ['Name', 'PID No', 'Service', 'Valve Body Size', 'Cv Value']
    cols = priority + [c for c in df_final.columns if c not in priority]
    return df_final[cols]