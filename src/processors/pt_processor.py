"""
PT Processor - پردازش فایل‌های Pressure Transmitter
"""
import pandas as pd
import re
from ..base_processor import BaseProcessor, clean_value, get_excel_engine


def get_k_slot(col_index):
    if col_index <= 4:
        return 0
    elif col_index <= 6:
        return 1
    else:
        return 2


def get_v_slot(col_index):
    if col_index <= 14:
        return 0
    elif col_index <= 17:
        return 1
    else:
        return 2


class PTProcessor(BaseProcessor):
    """پردازشگر فایل‌های PT (Pressure Transmitter)"""
    
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
        
        max_rows = min(15, len(df))
        
        for index in range(max_rows):
            row = df.iloc[index]
            for col_index, cell in enumerate(row):
                val = clean_value(cell)
                if not val:
                    continue
                val_upper = val.upper()
                
                if 'CON.NO.' in val_upper:
                    header_info['CON.NO.'] = val.split(':', 1)[-1].strip() if ':' in val else val
                elif 'DOC. NO.' in val_upper:
                    header_info['Doc. No.'] = val.split(':', 1)[-1].strip() if ':' in val else val
                elif 'PAGE' in val_upper and 'OF' in val_upper:
                    header_info['Page'] = val.split(':', 1)[-1].strip() if ':' in val else val
                elif 'UNIT' in val_upper and header_info['Unit Name'] is None:
                    header_info['Unit Name'] = val
                elif index in [4, 5, 6, 7] and col_index in [9, 10]:
                    if not any(k in val_upper for k in ['CON.NO.', 'DOC', 'PAGE', 'UNIT', 'GENERAL']):
                        header_info['Title'] = val
        
        return header_info
    
    def process_rows(self, df: pd.DataFrame, header_info: dict) -> list:
        all_data = []
        current_section = "GENERAL"
        current_prefix = None
        start_row = min(6, len(df))
        
        for index in range(start_row, len(df)):
            row = df.iloc[index]
            
            col0_val = clean_value(row[0]) if len(row) > 0 else None
            if col0_val and not col0_val.isnumeric() and col0_val.upper() != 'HEADER':
                current_section = col0_val
            
            raw_keys = []
            has_col3 = False
            col3_text = ""
            
            for c in range(3, 10):
                if c < len(row):
                    val = clean_value(row[c])
                    if val:
                        raw_keys.append((c, val))
                        if c == 3:
                            has_col3 = True
                            col3_text = val
            
            raw_values = []
            max_col = min(22, len(row))
            for c in range(11, max_col):
                if c < len(row):
                    val = clean_value(row[c])
                    if val:
                        raw_values.append((c, val))
            
            if not raw_keys:
                continue
            
            if has_col3:
                lower_text = col3_text.lower()
                is_prefix = (
                    col3_text.endswith(':') or
                    col3_text.endswith('-') or
                    'pipe / equipment' in lower_text or
                    'process connection' in lower_text or
                    'instrument connection' in lower_text or
                    'flushing ring' in lower_text or
                    'manifold' in lower_text or
                    'capillary' in lower_text or
                    'trim' in lower_text
                )
                
                if is_prefix:
                    current_prefix = col3_text.rstrip(':- ').strip()
                    if len(raw_keys) > 1:
                        raw_keys.pop(0)
                        raw_keys = [(c, f"{current_prefix} - {text.strip()}") for c, text in raw_keys]
                else:
                    raw_keys = [(c, col3_text.strip()) for c, text in raw_keys]
                    current_prefix = col3_text.rstrip(':- ').strip()
            else:
                if current_prefix:
                    raw_keys = [(c, f"{current_prefix} - {text.strip()}") for c, text in raw_keys]
            
            entries = []
            n_k = len(raw_keys)
            n_v = len(raw_values)
            
            if n_k == n_v:
                for k, v in zip(raw_keys, raw_values):
                    entries.append({'feature': k[1], 'value': v[1]})
            elif n_v > n_k:
                if n_k == 1:
                    joined_val = " / ".join([v[1] for v in raw_values])
                    entries.append({'feature': raw_keys[0][1], 'value': joined_val})
                else:
                    for i in range(n_k - 1):
                        entries.append({'feature': raw_keys[i][1], 'value': raw_values[i][1]})
                    joined_val = " / ".join([v[1] for v in raw_values[n_k - 1:]])
                    entries.append({'feature': raw_keys[-1][1], 'value': joined_val})
            else:
                v_by_slot = {}
                for v in raw_values:
                    s = get_v_slot(v[0])
                    if s not in v_by_slot:
                        v_by_slot[s] = []
                    v_by_slot[s].append(v[1])
                
                assigned = []
                for k in raw_keys:
                    s = get_k_slot(k[0])
                    if s in v_by_slot and v_by_slot[s]:
                        assigned.append({'key': k[1], 'val': v_by_slot[s].pop(0), 'matched': True})
                    else:
                        assigned.append({'key': k[1], 'val': "none", 'matched': False})
                
                leftovers = []
                for s in sorted(v_by_slot.keys()):
                    leftovers.extend(v_by_slot[s])
                
                for item in assigned:
                    if not item['matched'] and leftovers:
                        item['val'] = leftovers.pop(0)
                        item['matched'] = True
                
                for item in assigned:
                    entries.append({'feature': item['key'], 'value': item['val']})
            
            for entry in entries:
                all_data.append({
                    'بخش (Section)': current_section,
                    'ویژگی (Feature)': entry['feature'],
                    'مقدار (Value)': entry['value']
                })
        
        # اضافه کردن NOTES
        has_notes = any('note' in str(d['ویژگی (Feature)']).lower() for d in all_data)
        if not has_notes:
            all_data.append({
                'بخش (Section)': 'NOTES',
                'ویژگی (Feature)': 'Note',
                'مقدار (Value)': 'none'
            })
        
        return all_data