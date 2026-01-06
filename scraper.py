import pandas as pd
import requests
import os

URL = "https://friedas-berlin.de/en/wohnungsfinder/?etage=1,2,3,4,5&zimmer=2,3,4"
CSV_FILE = "friedas_data.csv"
CHANGES_FILE = "changes.txt"

def clean_currency(value):
    if isinstance(value, str):
        clean = value.replace('€', '').replace('.', '').replace(',', '.').strip()
        try:
            return float(clean)
        except ValueError:
            return 0.0
    return value

def get_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(URL, headers=headers)
    response.raise_for_status()
    
    dfs = pd.read_html(response.text)
    if not dfs:
        raise ValueError("No tables found")
    
    return dfs[0]

def compare_and_get_logs(new_df, old_df):
    logs = []
    
    id_col = new_df.columns[0]
    
    price_col = next((c for c in new_df.columns if 'Kaltmiete' in c), None)
    
    if not price_col:
        cols_str = ", ".join(new_df.columns)
        print(f"CRITICAL ERROR: Column 'Kaltmiete' not found. Available columns: {cols_str}")
        return []

    new_df = new_df.set_index(id_col)
    old_df = old_df.set_index(id_col)

    new_units = new_df.index.difference(old_df.index)
    for unit in new_units:
        msg = f"[NEW LISTING] {unit} added at {new_df.loc[unit, price_col]}"
        print(msg)
        logs.append(msg)

    removed_units = old_df.index.difference(new_df.index)
    for unit in removed_units:
        msg = f"[REMOVED] {unit} (was {old_df.loc[unit, price_col]})"
        print(msg)
        logs.append(msg)

    common_units = new_df.index.intersection(old_df.index)
    for unit in common_units:
        old_price_str = str(old_df.loc[unit, price_col])
        new_price_str = str(new_df.loc[unit, price_col])
        
        old_p = clean_currency(old_price_str)
        new_p = clean_currency(new_price_str)
        
        if old_p != new_p:
            diff = new_p - old_p
            direction = "[PRICE UP]" if diff > 0 else "[PRICE DOWN]"
            msg = f"{direction} {unit}: {old_price_str} -> {new_price_str} (Diff: {diff:+g})"
            print(msg)
            logs.append(msg)
            
    return logs

if __name__ == "__main__":
    try:
        current_df = get_data()
        all_logs = []
        
        if os.path.exists(CSV_FILE):
            try:
                old_df = pd.read_csv(CSV_FILE)
                all_logs = compare_and_get_logs(current_df, old_df)
            except Exception as e:
                print(f"Error reading history: {e}")
                
        current_df.to_csv(CSV_FILE, index=False)
        
        if all_logs:
            with open(CHANGES_FILE, "w") as f:
                f.write("\n".join(all_logs))
                
    except Exception as main_e:
        print(f"Script failed: {main_e}")
        exit(1)
