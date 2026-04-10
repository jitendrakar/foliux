import pandas as pd
import requests
import io
import math

url = "https://docs.google.com/spreadsheets/d/12eLJHTlHO1naQgJ-dzf-UTgUbasVv02tgwlHKofG2Y4/gviz/tq?tqx=out:csv&sheet=n2g"
print(f"Fetching {url}...")
try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    df = pd.read_csv(io.StringIO(response.text), skiprows=1)
    
    # Print columns to be sure
    print("Columns:", df.columns.tolist())
    
    targets = ['TCS', 'INFY', 'TATA CONSULTANCY', 'INFOSYS']
    for _, row in df.iterrows():
        try:
            symbol = str(row.iloc[2]).strip().upper()
            if any(t in symbol for t in targets):
                print(f"Match found: {symbol}")
                print(f"  Row data: {row.tolist()}")
                ltp_val = row.iloc[4]
                print(f"  LTP (index 4): {ltp_val}")
                change_val = row.iloc[5] if len(row) > 5 else "N/A"
                print(f"  Change (index 5): {change_val}")
        except Exception as e:
            print(f"Error processing row: {e}")

except Exception as e:
    print(f"Error: {e}")
