import pandas as pd
import json
import os
import re

# ==========================================
# File Reader (supports upload & multiple formats)
# ==========================================
def read_any_file(file_input):

    if isinstance(file_input, str):
        ext = os.path.splitext(file_input)[1].lower()
    else:
        name = getattr(file_input, 'name', '')
        ext = os.path.splitext(name)[1].lower()

    if ext in ['.xlsx', '.xls', '.xlsm']:
        return pd.ExcelFile(file_input), 'excel'

    elif ext in ['.csv', '.txt']:
        df = pd.read_csv(file_input, sep=None, engine='python')
        return {"sheet1": df}, 'csv'

    else:
        raise Exception(f"Unsupported file format: {ext}")


# ==========================================
# Clean Value
# ==========================================
def clean_value(val):
    s = str(val).strip()
    if s.lower() in ['nan', 'none', '', '<na>']:
        return None
    return s


def get_k_slot(col_index):
    if col_index <= 4: return 0
    elif col_index <= 6: return 1
    else: return 2


def get_v_slot(col_index):
    if col_index <= 14: return 0
    elif col_index <= 17: return 1
    else: return 2


# ==========================================
# 1️⃣ Generate Intermediate 3 Column Data (IN MEMORY)
# ==========================================
def generate_intermediate_data(file_input):

    file_obj, file_type = read_any_file(file_input)

    if file_type == 'excel':
        sheet_names = file_obj.sheet_names[4:]
    else:
        sheet_names = list(file_obj.keys())

    all_data = []

    for sheet_name in sheet_names:

        if file_type == 'excel':
            df = pd.read_excel(file_input, sheet_name=sheet_name, header=None)
        else:
            df = file_obj[sheet_name]

        header_info = {
            'CON.NO.': None,
            'Doc. No.': None,
            'Unit Name': None,
            'Page': None,
            'Title': None
        }

        for index, row in df.iloc[:10].iterrows():
            for col_index, cell in enumerate(row):

                val = clean_value(cell)
                if not val:
                    continue

                val_upper = val.upper()

                if 'CON.NO.' in val_upper:
                    header_info['CON.NO.'] = val.split(':',1)[-1].strip() if ':' in val else val

                elif 'DOC. NO.' in val_upper:
                    header_info['Doc. No.'] = val.split(':',1)[-1].strip() if ':' in val else val

                elif 'PAGE' in val_upper and 'OF' in val_upper:
                    header_info['Page'] = val.split(':',1)[-1].strip() if ':' in val else val

                elif 'UNIT' in val_upper and header_info['Unit Name'] is None:
                    header_info['Unit Name'] = val

                elif index in [4,5,6,7] and col_index in [9,10]:
                    if not any(k in val_upper for k in ['CON.NO.','DOC','PAGE','UNIT','GENERAL']):
                        header_info['Title'] = val

        all_data.append({
            'Section':'HEADER',
            'Feature':'Sheet Name',
            'Value':sheet_name
        })

        for key in ['CON.NO.','Doc. No.','Unit Name','Page','Title']:
            if header_info.get(key):
                all_data.append({
                    'Section':'HEADER',
                    'Feature':key,
                    'Value':header_info[key]
                })

        current_section = "GENERAL"
        current_prefix = None

        for index,row in df.iterrows():

            if index < 6:
                continue

            col0_val = clean_value(row[0])

            if col0_val and not col0_val.isnumeric() and col0_val.upper() != 'HEADER':
                current_section = col0_val

            raw_keys = []
            has_col3 = False
            col3_text = ""

            for c in range(3,10):
                if c < len(row):
                    val = clean_value(row[c])
                    if val:
                        raw_keys.append((c,val))
                        if c == 3:
                            has_col3 = True
                            col3_text = val

            raw_values = []

            for c in range(11,min(22,len(row))):
                if c < len(row):
                    val = clean_value(row[c])
                    if val:
                        raw_values.append((c,val))

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
                        raw_keys = [(c,f"{current_prefix} - {text.strip()}") for c,text in raw_keys]

                    else:
                        raw_keys = [(c,col3_text.strip()) for c,text in raw_keys]

                else:
                    current_prefix = col3_text.rstrip(':- ').strip()

            else:

                if current_prefix:
                    raw_keys = [(c,f"{current_prefix} - {text.strip()}") for c,text in raw_keys]


            entries = []

            n_k = len(raw_keys)
            n_v = len(raw_values)

            if n_k == n_v:

                for k,v in zip(raw_keys,raw_values):
                    entries.append({'feature':k[1],'value':v[1]})

            elif n_v > n_k:

                if n_k == 1:

                    joined_val = " / ".join([v[1] for v in raw_values])

                    entries.append({
                        'feature':raw_keys[0][1],
                        'value':joined_val
                    })

                else:

                    for i in range(n_k-1):
                        entries.append({
                            'feature':raw_keys[i][1],
                            'value':raw_values[i][1]
                        })

                    joined_val = " / ".join([v[1] for v in raw_values[n_k-1:]])

                    entries.append({
                        'feature':raw_keys[-1][1],
                        'value':joined_val
                    })

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

                        assigned.append({
                            'key':k[1],
                            'val':v_by_slot[s].pop(0),
                            'matched':True
                        })

                    else:

                        assigned.append({
                            'key':k[1],
                            'val':"",
                            'matched':False
                        })

                leftovers = []

                for s in sorted(v_by_slot.keys()):
                    leftovers.extend(v_by_slot[s])

                for item in assigned:

                    if not item['matched'] and leftovers:

                        item['val'] = leftovers.pop(0)
                        item['matched'] = True

                for item in assigned:

                    entries.append({
                        'feature':item['key'],
                        'value':item['val']
                    })

            for entry in entries:

                all_data.append({
                    'Section':current_section,
                    'Feature':entry['feature'],
                    'Value':entry['value']
                })

    result_df = pd.DataFrame(all_data)

    return result_df


# ==========================================
# Text Normalization
# ==========================================
def normalize_text(text):

    if pd.isna(text) or text == '':
        return ""

    return re.sub(r'[^a-zA-Z0-9]', '', str(text)).upper()


# ==========================================
# Mapping Rules (FULL)
# ==========================================
mapping_rules = {

('GENERAL','TAGNO'):'Name',
('GENERAL','PIDNO'):'PID No',
('GENERAL','SERVICE'):'Service',
('GENERAL','LINEEQUIPMENTNUMBER'):'Line Equipment Number',

('GENERAL','PIPEEQUIPMENTMATERIALSIZE'):('Material','Size'),

('GENERAL','PIPEEQUIPMENTSCHEDULECLASS'):('Schedule','Pipe Class'),

('GENERAL','HAZARDOUSAREACLASSIFICATION'):'Area Classification',

('GENERAL','NACEREQUIREMENTSTANDARD'):'Nace Requirement',


('PROCESSDATA','FLUID'):'Fluid',
('PROCESSDATA','STATE'):'State',
('PROCESSDATA','PRESSUREBARGDESIGN'):'Design Pressure',
('PROCESSDATA','PRESSUREBARGOPERATING'):'Operating Pressure',

('PROCESSDATA','TEMPERATURECDESIGN'):'Design Temperature',
('PROCESSDATA','TEMPERATURECOPERATING'):'Operating Temperature',

('PROCESSDATA','SPECGRAVITYOPERCONDITION'):
'Density Specific Gravity Molecular Mass',

('PROCESSDATA','VISCOSITYCPOPERCONDITION'):
'Viscosity',


('TRANSMITTER','TYPE'):'Type Item',

('TRANSMITTER','INSTRUMENTRANGE'):'Instrument Range',
('TRANSMITTER','INSTRUMENTRANGEBARG'):'Instrument Range',
('TRANSMITTER','INSTRUMENTRANGEMBAR'):'Instrument Range',
('TRANSMITTER','INSTRUMENTRANGEMMH2O'):'Instrument Range',

('TRANSMITTER','CALIBRATIONRANGEBARG'):'Calibration Range',
('TRANSMITTER','CALIBRATIONRANGEMBAR'):'Calibration Range',
('TRANSMITTER','CALIBRATIONRANGEMMH2O'):'Calibration Range',
('TRANSMITTER','CALIBRATIONRANGEKPA'):'Calibration Range',
('TRANSMITTER','CALIBRATIONRANGE'):'Calibration Range',

('TRANSMITTER','POWERSUPPLY'):'Power Supply',
('TRANSMITTER','ELECTRICALCONNECTION'):'Electrical Connection',
('TRANSMITTER','LOOPRESISTANCE'):'Loop Resistance',

('TRANSMITTER','ELECEXPROTECTION'):'Elec Ex Protection',

('TRANSMITTER','INGRESSPROTECTION'):'Ingress Protection',

('TRANSMITTER','ACCURACY'):'Accuracy',
('TRANSMITTER','ELEVATION'):'Elevation',
('TRANSMITTER','SUPPRESSION'):'Suppression',

('TRANSMITTER','FAILSAFEDIRECTION'):'Failsafe Direction',

('TRANSMITTER','OUTPUTSIGNAL'):'Signal Outlet',

('TRANSMITTER','FORM'):'Form',

('TRANSMITTER','DAMPINGTIME'):'Damping Time',

('TRANSMITTER','ELEMENTTYPE'):'Element Type',
('TRANSMITTER','ELEMENTMATERIAL'):'Element Material',

('TRANSMITTER','BODYRATING'):'Body Rating',
('TRANSMITTER','BODYMATERIAL'):'Body Material',

('TRANSMITTER','PROCESSFLANGESMATERIAL'):
'Process Flanges Material',

('TRANSMITTER','WETTEDPARTSMATERIAL'):
'Wetted Parts Material',

('TRANSMITTER','BOLTSMATERIAL'):'Bolts Material',

('TRANSMITTER','HOUSINGMATERIAL'):'Housing Material',

('TRANSMITTER','FILLFLUID'):'Fill Fluid Transmitter',

('TRANSMITTER','VENTORDRAINSIZEMATERIAL'):
'Vent Or Drain Size Material',

('TRANSMITTER','PROCESSCONNECTION'):
'Process Connection',

('TRANSMITTER','ALLOWOPERATINGTEMPERATURE'):
'Allow Operating Temperature',

('TRANSMITTER','PROCESSCONNECTIONALLOWOPERATINGTEMPERATURE'):
('Process Connection','Allow Operating Temperature'),


('DIAPHRAGMSEAL','DIAPHRAGMTYPE'):'Diaphragm Type',
('DIAPHRAGMSEAL','DIAPHRAGMMATERIAL'):'Diaphragm Material',

('DIAPHRAGMSEAL','CAPILLARYLENGTH'):'Capillary Length',
('DIAPHRAGMSEAL','CAPILLARYMATERIAL'):'Capillary Material',

('DIAPHRAGMSEAL','PROCESSCONNECTIONTYPE'):
'Process Connection Type Diaphragm Seal',

('DIAPHRAGMSEAL','PROCESSCONNECTIONMATERIAL'):
'Process Connection Material',

('DIAPHRAGMSEAL','PROCESSCONNECTIONSIZE'):
'Process Connection Size Diaphragm Seal',

('DIAPHRAGMSEAL','PROCESSCONNECTIONRATING'):
'Process Connection Rating Diaphragm Seal',

('DIAPHRAGMSEAL','INSTRUMENTCONNECTIONTYPE'):
'Instrument Connection Type',

('DIAPHRAGMSEAL','INSTRUMENTCONNECTIONMATERIAL'):
'Instrument Connection Material',

('DIAPHRAGMSEAL','FILLFLUID'):
'Fill Fluid Diaphragm Seal',

('DIAPHRAGMSEAL','FLUSHINGRINGRATING'):
'Flushing Ring Rating',

('DIAPHRAGMSEAL','FLUSHINGRINGPROCESSCONNECTION'):
'Flushing Ring Process Connection',


('MANIFOLD','MANIFOLDTYPE'):'Manifold Type',
('MANIFOLD','MANIFOLDRATING'):'Manifold Rating',

('MANIFOLD','MANIFOLDBODYMATERIAL'):
'Manifold Body Material',

('MANIFOLD','PROCESSCONNECTIONTYPE'):
'Process Connection Type Manifold',

('MANIFOLD','PROCESSCONNECTIONSIZE'):
'Process Connection Size Manifold',

('MANIFOLD','PROCESSCONNECTIONRATING'):
'Process Connection Rating Manifold',

('MANIFOLD','MAXIMUMRATINGPRESSURE'):
'Maximum Rating Pressure',

('MANIFOLD','MAXIMUMRATINGTEMPERATURE'):
'Maximum Rating Temperature',

('MANIFOLD','INSTRUMENTCONNECTION'):
'Instrument Connection',

('MANIFOLD','TRIM'):'Trim',
('MANIFOLD','PACKING'):'Packing',

('MANIFOLD','TRIMPACKING'):('Trim','Packing'),


('OPTIONS','INTEGRALINDICATOR'):'Integral Indicator',
('OPTIONS','INDICATIONSCALE'):'Indication Scale',

('OPTIONS','HANDHELDCOMMUNICATOR'):
'Hand Held Communicator',

('OPTIONS','CABLEGLAND'):'Cable Gland',

('OPTIONS','HYDROSTATICTESTING'):
'Hydrostatic Testing',

('OPTIONS','CLEANING'):'Cleaning',

('OPTIONS','MOUNTINGACCESSORIESBRACKET'):
'Mounting Accessories Bracket',

('OPTIONS','CERTIFICATION'):'Certification'

}


# ==========================================
# Final Mapping Function
# ==========================================
def map_to_final_format(df_three_col,template_file):

    df_template = pd.read_excel(template_file)

    aveva_columns = df_template.columns.tolist()

    df_input = df_three_col.copy()

    df_input.columns = ['Section','Feature','Value']

    df_input['Section'] = df_input['Section'].replace(r'^\s*$',pd.NA,regex=True).ffill()

    all_records = []

    current_record = {col:None for col in aveva_columns}

    has_data = False

    for index,row in df_input.iterrows():

        section_raw = row['Section']
        feature_raw = row['Feature']
        value_raw = row['Value']

        if pd.isna(feature_raw) or str(feature_raw).strip()=='':
            continue

        norm_section = normalize_text(section_raw)
        norm_feature = normalize_text(feature_raw)

        if norm_section=='HEADER' and norm_feature=='SHEETNAME':

            if has_data:

                all_records.append(current_record)

                current_record = {col:None for col in aveva_columns}

                has_data = False

            continue

        lookup_key = (norm_section,norm_feature)

        if lookup_key in mapping_rules:

            target = mapping_rules[lookup_key]

            if isinstance(target,tuple):

                if value_raw:

                    parts = [p.strip() for p in str(value_raw).split('/')]

                    for i,target_col in enumerate(target):

                        if i < len(parts):

                            current_record[target_col] = parts[i]

                            has_data = True

            else:

                current_record[target] = value_raw

                has_data = True

    if has_data:

        all_records.append(current_record)

    df_output = pd.DataFrame(all_records)

    return df_output


# ==========================================
# MAIN PIPELINE
# ==========================================
def process_pt_ui(file_input, output_path=None):

    TEMPLATE = "/mnt/storage-1/home/sadra/AISadra/user-4/nargan-mapping/src/mappers/PT Template Headers.xlsx"

    print("Generating intermediate 3-column structure in memory...")

    intermediate_df = generate_intermediate_data(file_input)

    print("Running AVEVA mapping...")

    final_df = map_to_final_format(intermediate_df, TEMPLATE)

    if output_path:
        final_df.to_excel(output_path, index=False)

    return final_df



# ==========================================
# Example Run
# ==========================================
if __name__ == "__main__":

    INPUT_FILE = "PT - 3607-32-74-ED-IN-DS-7301-A4 (2).xlsm"

    TEMPLATE = "/mnt/storage-1/home/sadra/AISadra/user-4/nargan-mapping/src/mappers/PT Template Headers.xlsx"

    OUTPUT_FILE = "AVEVA_PT_OUTPUT.xlsx"

    process_pt_ui(INPUT_FILE,TEMPLATE,OUTPUT_FILE)
