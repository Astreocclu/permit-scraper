import json
import os
import re
import glob
from datetime import datetime

# Target fields mapping (Accela span IDs)
FIELDS = {
    'permit_id': ['lblPermitNumber', 'lblAltId'],
    'address': ['lblAddress', 'lblPermitAddress'],
    'type': ['lblType', 'lblAppType', 'lblPermitType'],
    'status': ['lblStatus'],
    'date': ['lblUpdatedTime', 'lblDate', 'lblFileDate'],
    'description': ['lblDescription', 'lblProjectDescription'],
    'contractor': ['lblLicensedProfessional']
}

def extract_from_html_regex(html_content):
    permits = []
    # Find all rows (tr) roughly. 
    # Actually, Regex on full table is hard.
    # But Accela IDs are unique-ish per row? 
    # No, they are `ctl00_..._ctl01_lblPermitNumber`, `ctl00_..._ctl02_lblPermitNumber`.
    # So we can capture ALL matches for each field, and assume they align by index?
    # This is risky if a field is missing in one row (HTML table should preserve cells though).
    # Better: Split by `</tr>`.
    
    rows = re.split(r'</tr>', html_content, flags=re.IGNORECASE)
    
    for row in rows:
        if 'lblPermitNumber' not in row and 'lblAltId' not in row:
            continue
            
        permit = {}
        found_data = False
        
        for field, ids in FIELDS.items():
            # Build regex for this field
            # <span ... id="...id..." ...>VALUE</span>
            # Handle potential unrelated attributes
            for eid in ids:
                # Pattern: id="..." containing eid
                pattern = f'<span[^>]+id=["\'][^"\']*{eid}[^"\']*["\'][^>]*>(.*?)</span>'
                match = re.search(pattern, row, re.IGNORECASE | re.DOTALL)
                if match:
                    val = match.group(1).strip()
                    # Clean HTML entities if needed?
                    val = val.replace('&amp;', '&').replace('&nbsp;', ' ')
                    permit[field] = val
                    found_data = True
                    break
        
        if found_data and permit.get('permit_id'):
            permits.append(permit)
            
    return permits

def main():
    html_files = glob.glob('debug_html/dallas_p*.html')
    # Sort numerically if possible, or by time
    # dallas_p1.html, dallas_p2.html ...
    try:
        html_files.sort(key=lambda x: int(re.search(r'p(\d+)', x).group(1)))
    except:
        html_files.sort(key=os.path.getmtime)
        
    print(f"Found {len(html_files)} HTML files to process.")
    
    all_permits = []
    
    for idx, fpath in enumerate(html_files):
        if idx % 10 == 0:
            print(f"Processing {idx}/{len(html_files)}: {fpath}...")
            
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                extracted = extract_from_html_regex(content)
                all_permits.extend(extracted)
        except Exception as e:
            print(f"Error parsing {fpath}: {e}")
            
    # Deduplicate by permit_id
    unique_permits = {p['permit_id']: p for p in all_permits}.values()
    
    output = {
        'source': 'dallas',
        'portal_type': 'Accela',
        'scraped_at': datetime.now().isoformat(),
        'target_count': 1000,
        'recovered_from_cache': True,
        'actual_count': len(unique_permits),
        'permits': list(unique_permits)
    }
    
    with open('dallas_raw.json', 'w') as f:
        json.dump(output, f, indent=2)
        
    print(f"Successfully recovered {len(unique_permits)} permits from {len(html_files)} pages.")
    print("Saved to dallas_raw.json")

if __name__ == '__main__':
    main()

