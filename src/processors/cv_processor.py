"""
CV Processor - پردازش فایل‌های Control Valve
"""
import pandas as pd
import re
from ..base_processor import BaseProcessor, clean_value, get_excel_engine
import os


class CVProcessor(BaseProcessor):
    """پردازشگر فایل‌های CV (Control Valve)"""
    
    def __init__(self, file_path: str):
        super().__init__(file_path)
        self.engine = get_excel_engine(file_path)
    
    def extract_header(self, df: pd.DataFrame, sheet_name: str) -> dict:
        header_info = {
            'CON.NO.': None,
            'Doc. No.': None,
            'Unit Name': None,
            'Page': None,
            'Title': None
        }
        
        # فقط 20 ردیف اول را بررسی کن
        max_rows = min(20, len(df))
        
        for index in range(max_rows):
            row = df.iloc[index]
            for col_index, cell in enumerate(row):
                val = clean_value(cell)
                if not val:
                    continue
                val_upper = val.upper()
                
                if col_index == 9 and 'CON.NO.' in val_upper:
                    header_info['CON.NO.'] = val.split(':', 1)[-1].strip() if ':' in val else val
                elif col_index == 16 and 'DOC. NO.' in val_upper:
                    header_info['Doc. No.'] = val.split(':', 1)[-1].strip() if ':' in val else val
                elif 'PAGE' in val_upper and 'OF' in val_upper:
                    header_info['Page'] = val.split(':', 1)[-1].strip() if ':' in val else val
                elif 'UNIT' in val_upper and header_info['Unit Name'] is None:
                    header_info['Unit Name'] = val
                elif index in range(1, 10) and col_index in range(7, 12):
                    if not any(k in val_upper for k in ['CON.NO.', 'DOC', 'PAGE', 'UNIT', 'GENERAL', 'PIPELINE']):
                        header_info['Title'] = val
        
        return header_info
    
    def process_rows(self, df: pd.DataFrame, header_info: dict) -> list:
        all_data = []
        
        current_section_left = "GENERAL"
        current_section_right = "POSITIONER"
        is_split_mode = False
        is_matrix_mode = False
        matrix_headers = {}
        
        # فقط از ردیف 6 به بعد را پردازش کن
        start_row = min(6, len(df))
        
        for index in range(start_row, len(df)):
            row = df.iloc[index]
            
            col0_val = clean_value(row[0]) if len(row) > 0 else None
            if col0_val and not col0_val.isnumeric():
                current_section_left = col0_val.upper()
                current_section_right = "POSITIONER"
            
            val_12 = clean_value(row[12]) if len(row) > 12 else None
            val_17 = clean_value(row[17]) if len(row) > 17 else None
            
            if (val_12 and 'MIN' in str(val_12).upper() and 'FLOW' in str(val_12).upper()) or \
               (val_17 and 'NORM' in str(val_17).upper() and 'FLOW' in str(val_17).upper()):
                is_matrix_mode = True
                is_split_mode = False
                matrix_headers = {
                    11: clean_value(row[11]) or 'Units' if len(row) > 11 else 'Units',
                    12: val_12 or '@ Min. Flow',
                    17: val_17 or '@ Norm. Flow',
                    20: clean_value(row[20]) if len(row) > 20 and clean_value(row[20]) else '@ Max. Flow'
                }
                continue
            
            split_triggers = ["BODY AND TRIM", "ACTUATOR", "POSITIONER", "AIR SET", "ACCESSORIES", "TEST", "OTHERS", "PURCHASE"]
            full_width_triggers = ["GENERAL", "PROCESS CONDITIONS", "PIPELINE", "CALCULATED RESULTS"]
            
            if current_section_left in split_triggers:
                is_split_mode = True
                is_matrix_mode = False
            elif current_section_left in full_width_triggers:
                is_split_mode = False
            else:
                val_14 = clean_value(row[14]) if len(row) > 14 else None
                if val_14 and not str(val_14).replace('.', '', 1).isdigit():
                    is_split_mode = True
                    is_matrix_mode = False
            
            if is_split_mode:
                for c in [11, 12, 13, 14]:
                    if c >= len(row):
                        continue
                    r_candidate = clean_value(row[c])
                    if r_candidate and r_candidate.isupper() and len(r_candidate) > 2 and not r_candidate.isdigit():
                        current_section_right = r_candidate
                        break
                
                l_keys = []
                l_values = []
                for c in range(3, 6):
                    if c < len(row):
                        key = clean_value(row[c])
                        if key:
                            l_keys.append(key)
                
                for c in range(6, 11):
                    if c < len(row):
                        val = clean_value(row[c])
                        if val:
                            l_values.append(val)
                
                if l_keys:
                    if len(l_keys) > 1 and l_keys[0].endswith('Type') and l_keys[1].startswith('Trim'):
                        l_keys = [f"{l_keys[0]} / {l_keys[1]}"]
                        l_values = [f"{l_values[0] if len(l_values) > 0 else 'none'} / {l_values[1] if len(l_values) > 1 else 'none'}"]
                    elif len(l_keys) == 1 and len(l_values) >= 2:
                        l_keys = [l_keys[0]]
                        l_values = [f"{l_values[0]} / {l_values[1]}"]
                    
                    for i in range(len(l_keys)):
                        all_data.append({
                            'بخش (Section)': current_section_left,
                            'ویژگی (Feature)': l_keys[i],
                            'مقدار (Value)': l_values[i] if i < len(l_values) else 'none'
                        })
                
                r_keys = []
                r_values = []
                for c in range(14, 18):
                    if c < len(row):
                        key = clean_value(row[c])
                        if key:
                            r_keys.append(key)
                
                for c in range(18, 22):
                    if c < len(row):
                        val = clean_value(row[c])
                        if val:
                            r_values.append(val)
                
                if r_keys:
                    if len(r_keys) == 2 and len(r_values) >= 4:
                        all_data.append({
                            'بخش (Section)': current_section_right,
                            'ویژگی (Feature)': r_keys[0],
                            'مقدار (Value)': f"{r_values[0]} / {r_values[1]}"
                        })
                        all_data.append({
                            'بخش (Section)': current_section_right,
                            'ویژگی (Feature)': r_keys[1],
                            'مقدار (Value)': f"{r_values[2]} / {r_values[3]}"
                        })
                    else:
                        for i in range(len(r_keys)):
                            all_data.append({
                                'بخش (Section)': current_section_right,
                                'ویژگی (Feature)': r_keys[i],
                                'مقدار (Value)': r_values[i] if i < len(r_values) else 'none'
                            })
            
            elif is_matrix_mode:
                raw_keys = []
                for c in range(3, 11):
                    if c < len(row):
                        val = clean_value(row[c])
                        if val:
                            raw_keys.append(val)
                
                if not raw_keys:
                    continue
                
                base_key = " / ".join(raw_keys)
                
                for col_idx, suffix in matrix_headers.items():
                    val = None
                    if col_idx < len(row):
                        val = clean_value(row[col_idx])
                    all_data.append({
                        'بخش (Section)': current_section_left,
                        'ویژگی (Feature)': f"{base_key} [{suffix}]",
                        'مقدار (Value)': val if val else 'none'
                    })
            
            else:
                raw_keys = []
                for c in range(3, 11):
                    if c < len(row):
                        val = clean_value(row[c])
                        if val:
                            raw_keys.append(val)
                
                raw_values = []
                max_col = min(22, len(row))
                for c in range(11, max_col):
                    val = clean_value(row[c])
                    if val:
                        raw_values.append(val)
                
                if not raw_keys:
                    continue
                
                entries = []
                n_k = len(raw_keys)
                n_v = len(raw_values)
                
                if n_k == n_v:
                    for k, v in zip(raw_keys, raw_values):
                        entries.append({'feature': k, 'value': v})
                elif n_k == 1 and n_v > 1:
                    joined_val = " / ".join(raw_values)
                    entries.append({'feature': raw_keys[0], 'value': joined_val})
                elif n_k == 2 and n_v == 4:
                    entries.append({'feature': raw_keys[0], 'value': f'{raw_values[0]} / {raw_values[1]}'})
                    entries.append({'feature': raw_keys[1], 'value': f'{raw_values[2]} / {raw_values[3]}'})
                else:
                    key_str = " / ".join(raw_keys)
                    val_str = " / ".join(raw_values) if raw_values else "none"
                    entries.append({'feature': key_str, 'value': val_str})
                
                for entry in entries:
                    all_data.append({
                        'بخش (Section)': current_section_left,
                        'ویژگی (Feature)': entry['feature'],
                        'مقدار (Value)': entry['value'] if entry['value'] else 'none'
                    })
        
        return all_data
    


