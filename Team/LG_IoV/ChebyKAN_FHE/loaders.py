import pandas as pd
import numpy as np
import os
import glob
from pathlib import Path

def parse_can_log(filepath, label):
    """Fast vectorized parsing for CAN logs (Car-Hacking and CAN-VTC)."""
    # Read as single string column by using a separator not present in the data
    df = pd.read_csv(filepath, sep='\\t', header=None, names=['raw'], skip_blank_lines=True, engine='python')
    if len(df) == 0:
        raise ValueError(f"Zero rows loaded from {filepath}")
        
    # Example line: "ID: 0350    000    DLC: 8    05 28 84 66 6d 00 00 a2"
    # Extract ID, DLC, and payload (payload is optional)
    extracted = df['raw'].str.extract(r'ID:\s*([0-9a-fA-F]+)\s+\d+\s+DLC:\s*(\d+)(?:\s+(.*))?')
    
    parsed_df = pd.DataFrame()
    parsed_df['can_id'] = extracted[0]
    parsed_df['dlc'] = pd.to_numeric(extracted[1], errors='coerce').fillna(0).astype(int)
    
    # Payload bytes
    payload_str = extracted[2].str.split(expand=True)
    for i in range(8):
        if i < payload_str.shape[1]:
            parsed_df[f'b{i}'] = payload_str[i].apply(lambda x: int(x, 16) if pd.notna(x) else 0)
        else:
            parsed_df[f'b{i}'] = 0
            
    parsed_df['label'] = label
    return parsed_df

def load_car_hacking(base_dir):
    print(f"[car_hack] loading from {base_dir}")
    files = glob.glob(os.path.join(base_dir, '**', '*.csv'), recursive=True)
    if not files:
        raise FileNotFoundError(f"[car_hack] No CSV files found in {base_dir}")
        
    dfs = []
    for f in files:
        fname = os.path.basename(f).lower()
        if 'normal' in fname:
            label = 'Normal'
        elif 'dos' in fname:
            label = 'DoS'
        elif 'fuzzy' in fname:
            label = 'Fuzzy'
        elif 'rpm' in fname:
            label = 'RPM'
        elif 'gear' in fname:
            label = 'Gear'
        else:
            label = 'Unknown'
            
        print(f"[car_hack] parsing {fname} as {label}")
        df = parse_can_log(f, label)
        # Assign session id based on file
        df['session_id'] = f"car_hack_{os.path.basename(f)}"
        dfs.append(df)
        
    final_df = pd.concat(dfs, ignore_index=True)
    print(f"[car_hack] loaded {len(final_df)} rows.")
    if len(final_df) == 0:
        raise ValueError(f"[car_hack] Zero rows loaded in total from {base_dir}")
    return final_df

def load_vtc_can(base_dir):
    print(f"[vtc_can] loading from {base_dir}")
    files = glob.glob(os.path.join(base_dir, '**', '*.csv'), recursive=True)
    if not files:
        raise FileNotFoundError(f"[vtc_can] No CSV files found in {base_dir}")
        
    dfs = []
    for f in files:
        fname = os.path.basename(f).lower()
        if 'attack_free' in fname:
            label = 'Attack_free'
        elif 'dos' in fname:
            label = 'DoS_attack'
        elif 'fuzzy' in fname:
            label = 'Fuzzy_attack'
        elif 'impersonation' in fname:
            label = 'Impersonation_attack'
        else:
            label = 'Unknown'
            
        print(f"[vtc_can] parsing {fname} as {label}")
        df = parse_can_log(f, label)
        df['session_id'] = f"vtc_{os.path.basename(f)}"
        dfs.append(df)
        
    final_df = pd.concat(dfs, ignore_index=True)
    print(f"[vtc_can] loaded {len(final_df)} rows.")
    if len(final_df) == 0:
        raise ValueError(f"[vtc_can] Zero rows loaded in total from {base_dir}")
    return final_df

def load_veremi(base_dir):
    print(f"[veremi] loading from {base_dir}")
    files = glob.glob(os.path.join(base_dir, '**', '*.csv'), recursive=True)
    if not files:
        raise FileNotFoundError(f"[veremi] No CSV files found in {base_dir}")
        
    dfs = []
    for f in files:
        print(f"[veremi] parsing {os.path.basename(f)}")
        df = pd.read_csv(f)
        if len(df) == 0:
            raise ValueError(f"Zero rows loaded from {f}")
        df['session_id'] = f"veremi_{os.path.basename(f)}"
        dfs.append(df)
        
    final_df = pd.concat(dfs, ignore_index=True)
    
    # The prompt says VeReMi classes: BENIGN, ATTACK
    if 'attack' in final_df.columns:
        final_df['label'] = final_df['attack'].apply(lambda x: 'ATTACK' if x == 1 else 'BENIGN')
    else:
        final_df['label'] = 'BENIGN'
        
    print(f"[veremi] loaded {len(final_df)} rows.")
    if len(final_df) == 0:
        raise ValueError(f"[veremi] Zero rows loaded in total from {base_dir}")
    return final_df

def load_cicids(base_dir):
    print(f"[cicids] loading from {base_dir}")
    files = glob.glob(os.path.join(base_dir, '**', '*.csv'), recursive=True)
    if not files:
        raise FileNotFoundError(f"[cicids] No CSV files found in {base_dir}")
        
    dfs = []
    for f in files:
        print(f"[cicids] parsing {os.path.basename(f)}")
        # Handle leading spaces in columns
        df = pd.read_csv(f, skipinitialspace=True)
        if len(df) == 0:
            raise ValueError(f"Zero rows loaded from {f}")
        df['session_id'] = f"cicids_{os.path.basename(f)}"
        
        # Ensure 'Label' column exists
        if 'Label' in df.columns:
            df.rename(columns={'Label': 'label'}, inplace=True)
        else:
            # Fallback if case is different
            for col in df.columns:
                if col.lower() == 'label':
                    df.rename(columns={col: 'label'}, inplace=True)
                    break
                    
        dfs.append(df)
        
    final_df = pd.concat(dfs, ignore_index=True)
    # Simplify classes to Benign vs Attack
    final_df['label'] = final_df['label'].apply(lambda x: 'Benign' if x == 'BENIGN' else 'Attack')
    
    print(f"[cicids] loaded {len(final_df)} rows.")
    if len(final_df) == 0:
        raise ValueError(f"[cicids] Zero rows loaded in total from {base_dir}")
    return final_df
