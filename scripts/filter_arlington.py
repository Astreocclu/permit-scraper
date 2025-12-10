import pandas as pd
import sys

# Load the CSV
input_file = 'dfw_big4_contractor_leads.csv'
output_file = 'arlington_filtered.csv'

try:
    print(f"Loading {input_file}...")
    df = pd.read_csv(input_file)
    print(f"Total rows: {len(df)}")

    # Filter for Arlington
    arlington_df = df[df['City'].str.lower() == 'arlington'].copy()
    print(f"Arlington rows: {len(arlington_df)}")

    # Filter out unwanted types
    # Exclude: 'No Building Permit', 'Certificate of Occupancy', 'Sign', 'Face Change'
    # We want Residential: 'New Construction', 'Foundation', 'Window/Door Replacement', 'Addition', 'Remodel'
    
    # Let's see unique types
    # print(arlington_df['Permit_Type'].unique())
    
    unwanted_types = [
        'No Building Permit', 
        'Certificate of Occupancy', 
        'Sign', 
        'Face Change',
        'Wireless Facilities',
        'Demolition',
        'Retail Trade',
        'Other Services', 
        'Health Care', 
        'Finance and Insurance',
        'Accommodation and Food Services',
        'Transportation and Warehousing',
        'Real Estate and Rental',
        'Administrative and Support',
        'Construction' # Vague, but often commercial reg
    ]
    
    # Filter
    # Use str.contains approach or exact match.
    # The 'Permit_Type' in CSV seems to be codes like 'RP', 'CP', 'CO'.
    # But 'Description' has the text like 'Foundation', 'New Construction'.
    # Actually looking at the CSV sample:
    # Permit_Type: FE, SI, CO, RP, CP
    # Description: 'Repair / Replacement', 'New', 'Real Estate...', 'Foundation', 'Window/Door Replacement'
    
    # Logic:
    # RP = Residential Permit?
    # CP = Commercial Permit?
    # FE = Fence/Electrical?
    # CO = Certificate of Occupancy
    # SI = Sign
    
    # Let's keep RP and maybe FE if useful (Fence?). Actually value > $5000 is good heuristic.
    
    # Filter by Permit Type Code first
    valid_codes = ['RP'] # Residential Permit seems best target
    # Maybe check 'FE' (Fence/Electrical) if value is high?
    
    filtered_df = arlington_df[arlington_df['Permit_Type'].isin(['RP', 'FE', 'SW'])] # SW = Swimming Pool?
    
    # Also filter by Description to remove minor stuff
    # We want "New Construction", "Addition", "Remodel", "Foundation", "Window", "Roof"
    
    print(f"Rows after Code filter (RP, FE, SW): {len(filtered_df)}")
    
    # Filter unwanted descriptions if any (e.g. small repairs)
    # Filter by Value > 1000 to remove tiny jobs
    filtered_df = filtered_df[pd.to_numeric(filtered_df['Value'], errors='coerce').fillna(0) > 1000]
    
    print(f"Rows after Value > 1000 filter: {len(filtered_df)}")
    
    # Save
    filtered_df.to_csv(output_file, index=False)
    print(f"Saved filtered data to {output_file}")
    
except Exception as e:
    print(f"Error: {e}")
