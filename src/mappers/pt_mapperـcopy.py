"""
PT Mapper - نگاشت دقیق Pressure Transmitter به فرمت AVEVA
"""
import pandas as pd
import re


def normalize_text(text):
    """حذف فاصله‌ها و کاراکترهای ویژه برای تطابق"""
    if pd.isna(text) or text == '' or text is None:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(text)).upper()


PT_MAPPING_RULES = {
    # --- GENERAL ---
    ('GENERAL', 'TAGNO'): 'Name',
    ('GENERAL', 'PIDNO'): 'PID No',
    ('GENERAL', 'SERVICE'): 'Service',
    ('GENERAL', 'LINEEQUIPMENTNUMBER'): 'Line Equipment Number',
    ('GENERAL', 'PIPEEQUIPMENTMATERIALSIZE'): ('Material', 'Size'),
    ('GENERAL', 'PIPEEQUIPMENTSCHEDULECLASS'): ('Schedule', 'Pipe Class'),
    ('GENERAL', 'HAZARDOUSAREACLASSIFICATION'): 'Area Classification',
    ('GENERAL', 'NACEREQUIREMENTSTANDARD'): 'Nace Requirement',

    # --- PROCESS DATA ---
    ('PROCESSDATA', 'FLUID'): 'Fluid',
    ('PROCESSDATA', 'STATE'): 'State',
    ('PROCESSDATA', 'PRESSUREBARGDESIGN'): 'Design Pressure',
    ('PROCESSDATA', 'PRESSUREBARGOPERATING'): 'Operating Pressure',
    ('PROCESSDATA', 'TEMPERATURECDESIGN'): 'Design Temperature',
    ('PROCESSDATA', 'TEMPERATURECOPERATING'): 'Operating Temperature',
    ('PROCESSDATA', 'SPECGRAVITYOPERCONDITION'): 'Density Specific Gravity Molecular Mass',
    ('PROCESSDATA', 'VISCOSITYCPOPERCONDITION'): 'Viscosity',

    # --- TRANSMITTER ---
    ('TRANSMITTER', 'TYPE'): 'Type Item',
    ('TRANSMITTER', 'INSTRUMENTRANGE'): 'Instrument Range',
    ('TRANSMITTER', 'INSTRUMENTRANGEBARG'): 'Instrument Range',
    ('TRANSMITTER', 'INSTRUMENTRANGEMBAR'): 'Instrument Range',
    ('TRANSMITTER', 'INSTRUMENTRANGEMMH2O'): 'Instrument Range',
    ('TRANSMITTER', 'CALIBRATIONRANGE'): 'Calibration Range',
    ('TRANSMITTER', 'CALIBRATIONRANGEBARG'): 'Calibration Range',
    ('TRANSMITTER', 'CALIBRATIONRANGEMBAR'): 'Calibration Range',
    ('TRANSMITTER', 'CALIBRATIONRANGEMMH2O'): 'Calibration Range',
    ('TRANSMITTER', 'CALIBRATIONRANGEKPA'): 'Calibration Range',
    ('TRANSMITTER', 'POWERSUPPLY'): 'Power Supply',
    ('TRANSMITTER', 'ELECTRICALCONNECTION'): 'Electrical Connection',
    ('TRANSMITTER', 'ACCURACY'): 'Accuracy',
    ('TRANSMITTER', 'ELEMENTTYPE'): 'Element Type',
    ('TRANSMITTER', 'BODYMATERIAL'): 'Body Material',
    ('TRANSMITTER', 'FILLFLUID'): 'Fill Fluid Transmitter',
    ('TRANSMITTER', 'PROCESSCONNECTION'): 'Process Connection',
    ('TRANSMITTER', 'INGRESSPROTECTION'): 'Ingress Protection',
    ('TRANSMITTER', 'ELECEXPROTECTION'): 'Elec Ex Protection',

    # --- DIAPHRAGM SEAL ---
    ('DIAPHRAGMSEAL', 'DIAPHRAGMTYPE'): 'Diaphragm Type',
    ('DIAPHRAGMSEAL', 'DIAPHRAGMMATERIAL'): 'Diaphragm Material',
    ('DIAPHRAGMSEAL', 'CAPILLARYLENGTH'): 'Capillary Length',
    ('DIAPHRAGMSEAL', 'FILLFLUID'): 'Fill Fluid Diaphragm Seal',

    # --- MANIFOLD ---
    ('MANIFOLD', 'MANIFOLDTYPE'): 'Manifold Type',
    ('MANIFOLD', 'MANIFOLDBODYMATERIAL'): 'Manifold Body Material',
    ('MANIFOLD', 'MANIFOLDRATING'): 'Manifold Rating',

    # --- OPTIONS ---
    ('OPTIONS', 'INTEGRALINDICATOR'): 'Integral Indicator',
}


def map_to_aveva_pt(df_intermediate: pd.DataFrame) -> pd.DataFrame:
    """تابع اصلی نگاشت PT"""
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
        key = (norm_section, norm_feature)

        if key in PT_MAPPING_RULES:
            target = PT_MAPPING_RULES[key]

            val_str = str(value).strip() if value is not None else ''
            clean_val = val_str if val_str.lower() not in ['nan', 'none', ''] else ''

            if isinstance(target, tuple):
                parts = [p.strip() for p in clean_val.split(' / ') if p.strip()]
                for i, col_name in enumerate(target):
                    if i < len(parts):
                        current[col_name] = parts[i]
                    else:
                        current[col_name] = ''
            else:
                current[target] = clean_val

    if current:
        records.append(current)

    df_final = pd.DataFrame(records)
    df_final = df_final.replace(['none', 'None', 'nan', 'NaN'], '', regex=False).fillna('')

    # مرتب‌سازی ستون‌ها
    priority = ['Name', 'PID No', 'Service', 'Fluid', 'Design Pressure', 'Design Temperature', 'Type Item']
    other_cols = [c for c in df_final.columns if c not in priority]
    df_final = df_final[priority + other_cols]

    return df_final