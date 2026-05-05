import pandas as pd
import re
import os

def clean_value(val):
    if pd.isna(val):
        return None
    s = str(val).strip()
    if s.lower() in ['nan', 'none', '', '<na>']:
        return None
    s = re.sub(r'\s+', ' ', s)
    return s

def read_any_file(file_input):
    """
    می‌تواند مسیر فایل (String) یا فایل آپلود شده (File-like object) را دریافت کند.
    """
    # تشخیص پسوند فایل
    if isinstance(file_input, str):
        ext = os.path.splitext(file_input)[1].lower()
    else:
        # برای فایل‌های آپلود شده در Streamlit یا Django
        name = getattr(file_input, 'name', '')
        ext = os.path.splitext(name)[1].lower()

    if ext in ['.xlsx', '.xls', '.xlsm']:
        return pd.ExcelFile(file_input), 'excel'
    elif ext in ['.csv', '.txt']:
        # فرض بر این است که فایل متنی/CSV با کاما یا تب جدا شده است
        df = pd.read_csv(file_input, sep=None, engine='python')
        return {"sheet1": df}, 'csv'
    else:
        raise Exception(f"Unsupported file format: {ext}")


def generate_intermediate_data(file_input):
    """
    این تابع دیتای ۳ ستونه میانی را فقط در حافظه تولید می‌کند.
    """
    file_obj, file_type = read_any_file(file_input)

    if file_type == 'excel':
        # از شیت پنجم به بعد
        sheet_names = file_obj.sheet_names[4:] if len(file_obj.sheet_names) > 4 else file_obj.sheet_names
    else:
        sheet_names = list(file_obj.keys())

    all_data = []

    for sheet_name in sheet_names:
        if file_type == 'excel':
            df = pd.read_excel(file_input, sheet_name=sheet_name, header=None)
        else:
            df = file_obj[sheet_name]

        header_info = {'CON.NO.': None, 'Doc. No.': None, 'Unit Name': None, 'Page': None, 'Title': None}

        for index, row in df.iloc[:15].iterrows():
            for col_index, cell in enumerate(row):
                val = clean_value(cell)
                if not val: 
                    continue

                val_upper = val.upper()
                if col_index == 9 and 'CON.NO.' in val_upper:
                    header_info['CON.NO.'] = val.split(':', 1)[-1].strip() if ':' in val else val
                elif col_index == 16 and 'DOC. NO.' in val_upper:
                    header_info['Doc. No.'] = val.split(':', 1)[-1].strip() if ':' in val else val
                if 'PAGE' in val_upper and 'OF' in val_upper:
                    header_info['Page'] = val.split(':', 1)[-1].strip() if ':' in val else val
                elif 'UNIT' in val_upper and header_info['Unit Name'] is None:
                    header_info['Unit Name'] = val
                elif index in range(1, 10) and col_index in range(7, 12):
                    if not any(k in val_upper for k in ['CON.NO.', 'DOC', 'PAGE', 'UNIT', 'GENERAL', 'PIPELINE']):
                        header_info['Title'] = val

        all_data.append({'بخش (Section)': 'HEADER', 'ویژگی (Feature)': 'Sheet Name', 'مقدار (Value)': sheet_name})

        for key in ['CON.NO.', 'Doc. No.', 'Unit Name', 'Page', 'Title']:
            if header_info.get(key):
                all_data.append({'بخش (Section)': 'HEADER', 'ویژگی (Feature)': key, 'مقدار (Value)': header_info[key]})

        current_section_left = "GENERAL"
        current_section_right = "POSITIONER"
        is_split_mode = False
        is_matrix_mode = False
        matrix_headers = {}

        for index, row in df.iterrows():
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
                    11: clean_value(row[11]) or 'Units',
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
                    r_candidate = clean_value(row[c]) if c < len(row) else None
                    if r_candidate and r_candidate.isupper() and len(r_candidate) > 2 and not r_candidate.isdigit():
                        current_section_right = r_candidate
                        break

                l_keys = [clean_value(row[c]) for c in range(3, 6) if c < len(row) and clean_value(row[c])]
                l_values = [clean_value(row[c]) for c in range(6, 11) if c < len(row) and clean_value(row[c])]

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

                r_keys = [clean_value(row[c]) for c in range(14, 18) if c < len(row) and clean_value(row[c])]
                r_values = [clean_value(row[c]) for c in range(18, 22) if c < len(row) and clean_value(row[c])]

                if r_keys:
                    if len(r_keys) == 2 and len(r_values) >= 4:
                        all_data.append({'بخش (Section)': current_section_right,'ویژگی (Feature)': r_keys[0],'مقدار (Value)': f"{r_values[0]} / {r_values[1]}"})
                        all_data.append({'بخش (Section)': current_section_right,'ویژگی (Feature)': r_keys[1],'مقدار (Value)': f"{r_values[2]} / {r_values[3]}"})
                    else:
                        for i in range(len(r_keys)):
                            all_data.append({
                                'بخش (Section)': current_section_right,
                                'ویژگی (Feature)': r_keys[i],
                                'مقدار (Value)': r_values[i] if i < len(r_values) else 'none'
                            })

            elif is_matrix_mode:
                raw_keys = [clean_value(row[c]) for c in range(3, 11) if c < len(row) and clean_value(row[c])]
                if not raw_keys: continue
                base_key = " / ".join(raw_keys)

                for col_idx, suffix in matrix_headers.items():
                    val = clean_value(row[col_idx]) if col_idx < len(row) else None
                    all_data.append({
                        'بخش (Section)': current_section_left,
                        'ویژگی (Feature)': f"{base_key} [{suffix}]",
                        'مقدار (Value)': val if val else 'none'
                    })

            else:
                # این بخش در کد ثانویه شما مشکل داشت که با بازگردانی منطق اولیه اصلاح شد
                raw_keys = [clean_value(row[c]) for c in range(3, 11) if c < len(row) and clean_value(row[c])]
                raw_values = [clean_value(row[c]) for c in range(11, min(22, len(row))) if c < len(row) and clean_value(row[c])]

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

    return pd.DataFrame(all_data)


def map_to_final_format(df_three_col):
    """
    این تابع فایل میانی را دریافت کرده و فرمت خروجی نهایی را تولید می‌کند.
    """
    all_valves = []
    current_valve = {}

    for index, row in df_three_col.iterrows():
        section = str(row['بخش (Section)']).strip()
        feature = str(row['ویژگی (Feature)']).strip()
        value = str(row['مقدار (Value)']).strip()

        if section == 'HEADER' and feature == 'Sheet Name':
            if current_valve:
                all_valves.append(current_valve)
            current_valve = {}

        if feature and feature != 'nan':
            key = f"{section} | {feature}"
            current_valve[key] = value

    if current_valve:
        all_valves.append(current_valve)

    def get_val(v_dict, section, feature, index=None):
        val = v_dict.get(f"{section} | {feature}", "")
        if index is None:
            return val
        if not val:
            return ""
        parts = [p.strip() for p in str(val).split("/")]
        if index < len(parts):
            return parts[index]
        return ""

    mapped_data_list = []

    for v in all_valves:
        mapped_data = {}
        
        # --- HEADER & GENERAL ---
        mapped_data['Sheet Name'] = get_val(v, 'HEADER', 'Sheet Name')
        mapped_data['Tag Number'] = get_val(v, 'GENERAL', 'Tag No.') or mapped_data['Sheet Name']
        mapped_data['Ambient Temperature Min'] = get_val(v, 'GENERAL', 'Ambient Temperature (°C): / Min. / Max.', 0)
        mapped_data['Ambient Temperature Max'] = get_val(v, 'GENERAL', 'Ambient Temperature (°C): / Min. / Max.', 1)
        mapped_data['Allowable Noise Level'] = get_val(v, 'GENERAL', 'Allowable Noise Level (dBA)')
        mapped_data['Tightness Requirements'] = get_val(v, 'GENERAL', 'Tightness Requirements')
        mapped_data['Tight Shut Off'] = get_val(v, 'GENERAL', 'Tight Shut-off')
        mapped_data['Available Air Supply Pressure Min'] = get_val(v, 'GENERAL', 'Available Air Supply Pressure (barg): / Min. / Nor. / Max.', 0)
        mapped_data['Available Air Supply Pressure Norm'] = get_val(v, 'GENERAL', 'Available Air Supply Pressure (barg): / Min. / Nor. / Max.', 1)
        mapped_data['Available Air Supply Pressure Max'] = get_val(v, 'GENERAL', 'Available Air Supply Pressure (barg): / Min. / Nor. / Max.', 2)
        mapped_data['Failure Position'] = get_val(v, 'GENERAL', 'Failure Position')
        mapped_data['Nace Requirement'] = get_val(v, 'GENERAL', 'Nace Requirement')
        
        # --- PIPELINE ---
        mapped_data['Line Size Inlet'] = get_val(v, 'PIPELINE', 'Line Size and Schedule (in): / Inlet / Outlet', 0)
        mapped_data['Schedule Inlet'] = get_val(v, 'PIPELINE', 'Line Size and Schedule (in): / Inlet / Outlet', 1)
        mapped_data['Line Size Outlet'] = get_val(v, 'PIPELINE', 'Line Size and Schedule (in): / Inlet / Outlet', 2)
        mapped_data['Schedule Outlet'] = get_val(v, 'PIPELINE', 'Line Size and Schedule (in): / Inlet / Outlet', 3)
        mapped_data['Pipe Material'] = get_val(v, 'PIPELINE', 'Pipe Material')
        mapped_data['Pipe Class'] = get_val(v, 'PIPELINE', 'Pipe Class')
        
        # --- PROCESS CONDITIONS ---
        mapped_data['Process Fluid'] = get_val(v, 'PROCESS CONDITIONS', 'Process Fluid')
        mapped_data['Status'] = get_val(v, 'PROCESS CONDITIONS', 'Status')
        mapped_data['Max Shut Off DP'] = get_val(v, 'PROCESS CONDITIONS', 'Max . Shut-Off d/P (bar)')
        mapped_data['Critical Pressure'] = get_val(v, 'PROCESS CONDITIONS', 'Critical Pressure (bara)')
        mapped_data['Design Pressure'] = get_val(v, 'PROCESS CONDITIONS', 'Design Pressure')
        mapped_data['Design Temperature'] = get_val(v, 'PROCESS CONDITIONS', 'Design Temperature')
        
        mapped_data['Flow Rate Unit'] = get_val(v, 'PROCESS CONDITIONS', 'Flow Rate [Units]')
        mapped_data['Flow Rate Min Flow'] = get_val(v, 'PROCESS CONDITIONS', 'Flow Rate [@ Min. Flow]')
        mapped_data['Flow Rate Norm Flow'] = get_val(v, 'PROCESS CONDITIONS', 'Flow Rate [@ Norm. Flow]')
        mapped_data['Flow Rate Max Flow'] = get_val(v, 'PROCESS CONDITIONS', 'Flow Rate [@ Max. Flow]')
        
        mapped_data['Pressure Unit'] = get_val(v, 'PROCESS CONDITIONS', 'Pressure [Units]')
        mapped_data['Pressure Min Flow'] = get_val(v, 'PROCESS CONDITIONS', 'Pressure [@ Min. Flow]')
        mapped_data['Pressure Norm Flow'] = get_val(v, 'PROCESS CONDITIONS', 'Pressure [@ Norm. Flow]')
        mapped_data['Pressure Max Flow'] = get_val(v, 'PROCESS CONDITIONS', 'Pressure [@ Max. Flow]')
        
        mapped_data['Pressure Drop Unit'] = get_val(v, 'PROCESS CONDITIONS', 'Pressure Drop [Units]')
        mapped_data['Pressure Drop Min Flow'] = get_val(v, 'PROCESS CONDITIONS', 'Pressure Drop [@ Min. Flow]')
        mapped_data['Pressure Drop Norm Flow'] = get_val(v, 'PROCESS CONDITIONS', 'Pressure Drop [@ Norm. Flow]')
        mapped_data['Pressure Drop Max Flow'] = get_val(v, 'PROCESS CONDITIONS', 'Pressure Drop [@ Max. Flow]')
        
        mapped_data['Temperature Unit'] = get_val(v, 'PROCESS CONDITIONS', 'Temperature [Units]')
        mapped_data['Temperature Min Flow'] = get_val(v, 'PROCESS CONDITIONS', 'Temperature [@ Min. Flow]')
        mapped_data['Temperature Norm Flow'] = get_val(v, 'PROCESS CONDITIONS', 'Temperature [@ Norm. Flow]')
        mapped_data['Temperature Max Flow'] = get_val(v, 'PROCESS CONDITIONS', 'Temperature [@ Max. Flow]')

        mapped_data['Viscosity Unit'] = get_val(v, 'PROCESS CONDITIONS', 'Viscosity [Units]')
        mapped_data['Viscosity Min Flow'] = get_val(v, 'PROCESS CONDITIONS', 'Viscosity [@ Min. Flow]')
        mapped_data['Viscosity Norm Flow'] = get_val(v, 'PROCESS CONDITIONS', 'Viscosity [@ Norm. Flow]')
        mapped_data['Viscosity Max Flow'] = get_val(v, 'PROCESS CONDITIONS', 'Viscosity [@ Max. Flow]')
        
        mapped_data['Flash Unit'] = get_val(v, 'PROCESS CONDITIONS', 'Flash [Units]')
        mapped_data['Flash Min Flow'] = get_val(v, 'PROCESS CONDITIONS', 'Flash [@ Min. Flow]')
        mapped_data['Flash Norm Flow'] = get_val(v, 'PROCESS CONDITIONS', 'Flash [@ Norm. Flow]')
        mapped_data['Flash Max Flow'] = get_val(v, 'PROCESS CONDITIONS', 'Flash [@ Max. Flow]')
        
        # --- BODY AND TRIM ---
        mapped_data['Manufacturer Body AndTrim'] = get_val(v, 'BODY AND TRIM', 'MFR')
        mapped_data['Model Body And Trim'] = get_val(v, 'BODY AND TRIM', 'Model')
        mapped_data['Body Type'] = get_val(v, 'BODY AND TRIM', 'Body Type')
        mapped_data['Body Size'] = get_val(v, 'BODY AND TRIM', 'Body Size')
        mapped_data['Trim Size'] = get_val(v, 'BODY AND TRIM', 'Trim Size')
        mapped_data['Rated Cv'] = get_val(v, 'BODY AND TRIM', 'Rated Cv')
        mapped_data['Characteristic'] = get_val(v, 'BODY AND TRIM', 'Characteris.')
        mapped_data['End Connection And Rating'] = get_val(v, 'BODY AND TRIM', 'End Connec. & Rating')
        mapped_data['Body Material'] = get_val(v, 'BODY AND TRIM', 'Body Material')
        mapped_data['Bonnet Type'] = get_val(v, 'BODY AND TRIM', 'Bonnet Type')
        mapped_data['Bonnet Material'] = get_val(v, 'BODY AND TRIM', 'Material')

        # --- POSITIONER ---
        mapped_data['Manufacturer Positioner'] = get_val(v, 'POSITIONER', 'MFR')
        mapped_data['Model Positioner'] = get_val(v, 'POSITIONER', 'Model')
        mapped_data['Type Positioner'] = get_val(v, 'POSITIONER', 'Type')
        mapped_data['Signal Inlet'] = get_val(v, 'POSITIONER', 'Signal: Inlet')
        mapped_data['Signal Outlet'] = get_val(v, 'POSITIONER', 'Outlet')
        mapped_data['Positioner Bypass'] = get_val(v, 'POSITIONER', 'Bypass')
        mapped_data['Positioner Gauges'] = get_val(v, 'POSITIONER', 'Gauges')
        mapped_data['Ex Protection Positioner'] = get_val(v, 'POSITIONER', 'Ex. Protection')
        mapped_data['IP Positioner'] = get_val(v, 'POSITIONER', 'IP')

        # --- SOLENOID VALVE ---
        mapped_data['Manufacturer Solenoid Valve'] = get_val(v, 'SOLENOID VALVE', 'MFR')
        mapped_data['Model Solenoid Valve'] = get_val(v, 'SOLENOID VALVE', 'Model')
        mapped_data['Type Solenoid Valve'] = get_val(v, 'SOLENOID VALVE', 'Type')
        mapped_data['Tag Number Solenoid Valve'] = get_val(v, 'SOLENOID VALVE', 'Tag. Number')
        mapped_data['Ex Protection Solenoid Valve'] = get_val(v, 'SOLENOID VALVE', 'Ex. Protection')
        mapped_data['IP Solenoid Valve'] = get_val(v, 'SOLENOID VALVE', 'IP')
        
        # --- LIMIT SWITCHES ---
        mapped_data['Manufacturer Limit Switches'] = get_val(v, 'LIMIT SWITCHES', 'MFR')
        mapped_data['Model Limit Switches'] = get_val(v, 'LIMIT SWITCHES', 'Model')
        mapped_data['Type Limit Switches'] = get_val(v, 'LIMIT SWITCHES', 'Type')
        mapped_data['Quantity'] = get_val(v, 'LIMIT SWITCHES', 'Quantity')

        mapped_data_list.append(mapped_data)

    df_final = pd.DataFrame(mapped_data_list)
    df_final = df_final.replace(['none', 'None', 'NONE', 'nan', 'NaN', 'null'], '', regex=False)
    df_final = df_final.fillna('')
    return df_final


def process_cv_ui(file_input, output_path=None):
    """
    تابع اصلی که صفر تا صد پروسه را برای رابط کاربری (آپلود) یا کد عادی هندل می‌کند.
    """
    # ۱. تولید دیتای ۳ ستونه درون رم (بدون ذخیره در فایل)
    print("Generating intermediate mapping in memory...")
    intermediate_df = generate_intermediate_data(file_input)
    
    # ۲. تولید دیتای نهایی AVEVA
    print("Processing final mapping...")
    final_df = map_to_final_format(intermediate_df)
    
    # اگر مسیر خروجی داده شده بود، ذخیره کن (برای حالت کد معمولی)
    if output_path:
        final_df.to_excel(output_path, index=False)
        print(f"✅ Final AVEVA file created at: {output_path}")
        
    return final_df


# ==========================================
# نحوه اجرای تست
# ==========================================
if __name__ == "__main__":
    
    INPUT_FILE = "CV - 3607-32-74-ED-IN-DS-7401-A3g.xlsm" # یا هر فرمت دیگری
    OUTPUT_FILE = "AVEVA_OUTPUT.xlsx"

    # اجرای کامل و ذخیره مستقیم فایل خروجی
    process_cv_ui(INPUT_FILE, OUTPUT_FILE)
