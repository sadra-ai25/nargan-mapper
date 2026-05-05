"""
CV Mapper - نگاشت دقیق و هوشمند بر اساس خروجی واقعی process_datasheet_final
"""
import pandas as pd
import re


def normalize_text(text):
    if pd.isna(text) or not text:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(text)).upper()


# ==================== نگاشت گسترده و واقعی ====================
CV_MAPPING_RULES = {
    # General
    ('GENERAL', 'TAGNO'): 'Tag Number',
    ('GENERAL', 'PIDNO'): 'PID No',
    ('GENERAL', 'SERVICE'): 'Service',
    ('GENERAL', 'FAILUREPOSITION'): 'Failure Position',
    ('GENERAL', 'NACEREQUIREMENT'): 'Nace Requirement',
    ('GENERAL', 'TIGHTSHUTOFF'): 'Tight Shut Off',
    ('GENERAL', 'ALLOWABLENOISELEVEL'): 'Allowable Noise Level',

    # Pipeline
    ('PIPELINE', 'LINESIZEINLET'): 'Line Size Inlet',
    ('PIPELINE', 'SCHEDULEINLET'): 'Schedule Inlet',
    ('PIPELINE', 'LINESIZEOUTLET'): 'Line Size Outlet',
    ('PIPELINE', 'SCHEDULEOUTLET'): 'Schedule Outlet',
    ('PIPELINE', 'PIPEMATERIAL'): 'Pipe Material',
    ('PIPELINE', 'PIPECLASS'): 'Pipe Class',

    # Process Conditions
    ('PROCESS CONDITIONS', 'FLUID'): 'Process Fluid',
    ('PROCESS CONDITIONS', 'STATUS'): 'Status',
    ('PROCESS CONDITIONS', 'MAXSHUTOFFDP'): 'Max Shut Off DP',
    ('PROCESS CONDITIONS', 'PRESSUREBARGDESIGN'): 'Design Pressure',
    ('PROCESS CONDITIONS', 'TEMPERATURECDESIGN'): 'Design Temperature',

    # Body and Trim - مهم‌ترین بخش
    ('BODY AND TRIM', 'BODYTYPE'): 'Body Type',
    ('BODY AND TRIM', 'VALVEBODYSIZE'): 'Body Size',
    ('BODY AND TRIM', 'BODYSIZE'): 'Body Size',
    ('BODY AND TRIM', 'VALVEBODYMATERIAL'): 'Body Material',
    ('BODY AND TRIM', 'BODYMATERIAL'): 'Body Material',
    ('BODY AND TRIM', 'BONNETTYPE'): 'Bonnet Type',
    ('BODY AND TRIM', 'BONNETMATERIAL'): 'Bonnet Material',
    ('BODY AND TRIM', 'CHARACTERISTIC'): 'Characteristic',
    ('BODY AND TRIM', 'ENDCONNECTIONANDRATING'): 'End Connection And Rating',

    # Trim
    ('BODY AND TRIM', 'TRIMSIZE'): 'Trim Size',

    # Positioner
    ('POSITIONER', 'POSITIONERTYPE'): 'Type Positioner',
    ('POSITIONER', 'TYPE'): 'Type Positioner',
    ('POSITIONER', 'SIGNALINLET'): 'Signal Inlet',
    ('POSITIONER', 'SIGNALOUTLET'): 'Signal Outlet',
    ('POSITIONER', 'EXPROTECTION'): 'Ex Protection Positioner',
    ('POSITIONER', 'IPPROTECTION'): 'IP Positioner',

    # Calculated Results
    ('CALCULATED RESULTS', 'CV'): 'Rated Cv',
    ('CALCULATED RESULTS', 'RATEDCV'): 'Rated Cv',
}

def map_to_aveva_cv(df_intermediate: pd.DataFrame) -> pd.DataFrame:
    """نگاشت نهایی - بهینه شده برای خروجی CVProcessor"""
    records = []
    current = {}

    for _, row in df_intermediate.iterrows():
        section = str(row.get('بخش (Section)', '')).strip()
        feature = str(row.get('ویژگی (Feature)', '')).strip()
        value = row.get('مقدار (Value)')

        if not feature or str(feature).lower().strip() in ['nan', 'none', '']:
            continue

        if section == 'HEADER' and feature == 'Sheet Name':
            if current:
                records.append(current)
            current = {'Sheet Name': str(value).strip()}
            continue

        norm_section = normalize_text(section)
        norm_feature = normalize_text(feature)

        # جستجوی مستقیم در rules
        lookup_key = (norm_section, norm_feature)
        target = None

        if lookup_key in CV_MAPPING_RULES:
            target = CV_MAPPING_RULES[lookup_key]
        else:
            # جستجوی هوشمندتر (برای مواردی که Feature کمی متفاوت تولید می‌شود)
            if 'BODY' in norm_section and ('SIZE' in norm_feature or 'BODYSIZE' in norm_feature):
                target = 'Body Size'
            elif 'TRIM' in norm_feature and 'SIZE' in norm_feature:
                target = 'Trim Size'
            elif 'CV' in norm_feature and ('CALCULATED' in norm_section or 'RESULT' in norm_section):
                target = 'Rated Cv'
            elif 'CHARACTERISTIC' in norm_feature:
                target = 'Characteristic'
            elif 'BONNET' in norm_feature:
                if 'TYPE' in norm_feature:
                    target = 'Bonnet Type'
                elif 'MATERIAL' in norm_feature:
                    target = 'Bonnet Material'

        if target:
            val = str(value).strip() if pd.notna(value) else ''
            clean_val = val if val.lower() not in ['nan', 'none', ''] else ''

            if isinstance(target, tuple):
                parts = [p.strip() for p in clean_val.split(' / ') if p.strip()]
                for i, col in enumerate(target):
                    if i < len(parts):
                        current[col] = parts[i]
            else:
                current[target] = clean_val

    if current:
        records.append(current)

    df_final = pd.DataFrame(records)
    df_final = df_final.replace(['none', 'None', 'nan', 'NaN'], '', regex=False).fillna('')

    # ترتیب ستون‌ها (مطابق فایل نمونه‌ای که فرستادی)
    desired_order = [
        'Sheet Name', 'Tag Number', 'Process Fluid', 'Status',
        'Design Pressure', 'Design Temperature',
        'Line Size Inlet', 'Schedule Inlet', 'Line Size Outlet', 'Schedule Outlet',
        'Body Type', 'Body Size', 'Trim Size', 'Rated Cv', 'Characteristic',
        'Body Material', 'Bonnet Type', 'Bonnet Material',
        'Type Positioner', 'Signal Inlet', 'Signal Outlet',
        'Failure Position', 'Nace Requirement', 'Tight Shut Off', 'Allowable Noise Level'
    ]

    existing = [col for col in desired_order if col in df_final.columns]
    remaining = [col for col in df_final.columns if col not in existing]
    df_final = df_final[existing + remaining]

    return df_final