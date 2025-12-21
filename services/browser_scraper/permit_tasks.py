
# Generic Templates

# Efficiency directive - prepended to all templates
EFFICIENCY_DIRECTIVE = """GUIDELINES:
1. Use browser actions only (navigate, click, input, scroll, extract) - avoid file operations like write_file
2. Explore the portal to understand its structure when needed
3. When you find what works, note it in your final output
4. If an element is stuck after 3 attempts, try alternative approaches or selectors
5. Return JSON with your findings - include an "observations" field if the portal behaves unexpectedly
"""

ENERGOV_TEMPLATE = EFFICIENCY_DIRECTIVE + """
Go to the {city_name} EnerGov portal at {url}
Click on "Search" or "Public Search".
Select "Permit" from the search dropdown if available.
Search for address: {{address}}
Find the most recent permit for: {{permit_type}}
Extract these fields as JSON:
- permit_number
- issue_date
- permit_type
- valuation
- status
- contractor_name

Return ONLY the JSON object.
"""

ETRAKIT_TEMPLATE = EFFICIENCY_DIRECTIVE + """
Go to the {city_name} eTRAKiT portal at {url}
Select "Public Search" or "Search Permits".
In the dropdown select "Building" or "Permit".
Search for address: {{address}}
Find the most recent permit for: {{permit_type}}
Extract these fields as JSON:
- permit_number
- issue_date
- permit_type
- valuation
- status
- contractor_name

Return ONLY the JSON object.
"""

MYGOV_TEMPLATE = EFFICIENCY_DIRECTIVE + """
Go to the {city_name} MyGov portal at {url}
Search for address: {{address}}
If forced to login, try searching for "Public Search" or "Collaborator" guest access.
Find the most recent permit for: {{permit_type}}
Extract these fields as JSON:
- permit_number
- issue_date
- permit_type
- valuation
- status
- contractor_name

Return ONLY the JSON object.
"""

MGO_TEMPLATE = EFFICIENCY_DIRECTIVE + """
Go to the MGO Connect portal at https://www.mgoconnect.org/cp/home
1. Login first (REQUIRED):
   - Click "Login".
   - Use Username: "{{mgo_email}}"
   - Use Password: "{{mgo_password}}"
   - Submit.
2. Select Jurisdiction:
   - Select State: "Texas".
   - Click the Jurisdiction dropdown.
   - IMPORTANT: Type "{jurisdiction}" into the search box.
   - Select "{jurisdiction}".
   - Click "Go" or "Continue".
3. Search:
   - Click "Search Permits".
   - Search for address: {{address}}
   - Find the most recent permit for: {{permit_type}}
   - Extract these fields as JSON:
     - permit_number
     - issue_date
     - permit_type
     - valuation
     - status
     - contractor_name

Return ONLY the JSON object.
"""

# Bulk Templates
BULK_ENERGOV_TEMPLATE = EFFICIENCY_DIRECTIVE + """
Go to the {city_name} EnerGov portal at {url}
Click on "Search" or "Public Search".
Select "Permit" from the search dropdown if available.
Search for permits issued between {start_date} and {end_date}.
- If there is an "Advanced Search", use it.
- Filter by Status: "Issued" or "Active" if possible.
- Filter by Work Class/Type: "Building" or "Commercial" or "Residential".

Scrape the results table.
For each permit in the list (up to 20 per page), extract:
- permit_number
- issue_date
- permit_type
- status
- address
- description (if available)

If there are multiple pages, go to the next page and continue scraping until you have 50 permits or run out of pages.
Return the data as a valid JSON list of objects.
"""

SOUTHLAKE_BULK_TASK = EFFICIENCY_DIRECTIVE + """
Go to the Southlake EnerGov portal at https://energov.cityofsouthlake.com/EnerGov_Prod/SelfService#/search

1. Select "Permit" from the Module dropdown.

2. Click "Advanced" to open advanced search.

3. Set date filters:
   - Find "Issued Date" fields
   - Set start date: {start_date}
   - Set end date: {end_date}

4. Click "Search" button.

5. CRITICAL: After results load, the portal may show old permits despite date filter.
   - Find the "Issued Date" column header in the results table
   - Click it TWICE to sort DESCENDING (newest first)
   - Verify the top results show dates within your search range

6. If "Export" button is available, click it to download Excel file.
   Otherwise, scrape the first page of results.

7. Extract up to 50 permits with these fields:
   - permit_number (Case Number column)
   - issue_date (Issued Date column)
   - permit_type (Type column)
   - status (Status column)
   - address (Address column)
   - description (Description column if available)

Return the data as a valid JSON list of objects.
"""

BULK_ETRAKIT_TEMPLATE = EFFICIENCY_DIRECTIVE + """
Go to the {city_name} eTRAKiT portal at {url}
Select "Public Search" or "Search Permits".
Select "Permit" search type.
Search criteria:
- Date Range: {start_date} to {end_date}
- Permit Type: "Building" (or leaving blank for all)

Click Search.
From the results list, extract the following for all rows (handle pagination if needed, aim for 50 items max per run):
- permit_number
- issue_date
- permit_type
- status
- address
- valuation

Return the data as a valid JSON list of objects.
"""

BULK_MYGOV_TEMPLATE = EFFICIENCY_DIRECTIVE + """
Go to the {city_name} MyGov portal at {url}
Use the "Reports" or "Search" module if available.
Search for permits Issued between {start_date} and {end_date}.
If "Reports" is not available, try the main search bar with just the year (e.g., "2024") and filter manually if possible.

Extract all visible permits (limit to 50) as a JSON list:
- permit_number
- issue_date
- permit_type
- status
- address
- contractor

Return ONLY the JSON list.
"""

BULK_MGO_TEMPLATE = EFFICIENCY_DIRECTIVE + """
Go to the MGO Connect portal at https://www.mgoconnect.org/cp/home
1. Login first (REQUIRED):
   - Click "Login".
   - Use Username: "{mgo_email}"
   - Use Password: "{mgo_password}"
2. Select State and Jurisdiction:
   - First, click State dropdown and select "Texas".
   - Then click Jurisdiction dropdown and select "{jurisdiction}".
   - Click "Go" or the button to enter the jurisdiction.
3. Search Permits:
   - Select "Search Permits" (look for "Search Residential Permits" link).
   - Set Date Range: type "{start_date}" in "Created After" field, "{end_date}" in "Created Before" field.
   - Skip status filtering (default "9 items selected" is fine).
   - Click the "Search" button to execute the query.

Extract the results table (limit 50 items) as a JSON list:
- permit_number
- issue_date
- permit_type
- status
- address
- contractor

Return ONLY the JSON list.
"""

BULK_CITYVIEW_TEMPLATE = EFFICIENCY_DIRECTIVE + """
Go to the Carrollton CityView Portal at https://cityserve.cityofcarrollton.com/CityViewPortal/Permit/Locator

1. Explore the portal to find a search interface:
   - Look for "Search", "Permit Search", "Permit Locator", or similar
   - Note what search options are available (address, permit number, date range, etc.)

2. Try to filter for recent permits:
   - If there is a date range filter, use: {start_date} to {end_date}
   - If no date filter, search for permit numbers starting with "PR2512" (Dec 2025) or "PR2511" (Nov 2025)
   - Alternatively, search for common 2025 permit prefixes: "PRBD2025", "PRPL2025", "PREL2025"

3. From the results, extract permits as JSON:
   - permit_number (e.g., "PRBD202512001")
   - address
   - permit_type (Building, Plumbing, Electrical, etc.)
   - status
   - issue_date (if visible, otherwise leave empty and we'll parse from permit_number)
   - valuation (if visible)

4. Click on individual permit links if needed to get more details.

Return a JSON list of all permits found (aim for 50+ if available).
Important: Focus on permits from the last 30-60 days.
"""

# ... (Specific tasks preserved)

# ... (Lower down)

def get_task_for_city(city: str, address: str = "", permit_type: str = "Building", mgo_email: str = "", mgo_password: str = "", mode: str = "single", start_date: str = "", end_date: str = "") -> str:
    """
    Format the task template for a given city.
    Mode: 'single' or 'bulk'.
    """
    normalized_city = city.lower().replace(" ", "_").replace("north_richland_hills", "nrh")
    
    # Base templates map (Logic to swap to BULK if mode='bulk')
    template = CITY_TASKS.get(normalized_city)
    
    if not template:
         raise ValueError(f"No task specific for city: {city} (normalized: {normalized_city})")

    # Dynamic Template Swapping for Bulk
    if mode == "bulk":
        if "energov" in template.lower() or "energov_prod" in template.lower():
            import re
            url_match = re.search(r'https?://[^\s]+', template)
            if url_match:
                url = url_match.group(0)
                if "etrakit" in url.lower() or "etrakit" in template.lower():
                     return BULK_ETRAKIT_TEMPLATE.format(city_name=city, url=url, start_date=start_date, end_date=end_date)
                elif "mygov" in url.lower():
                     return BULK_MYGOV_TEMPLATE.format(city_name=city, url=url, start_date=start_date, end_date=end_date)
                elif "energov" in url.lower() or "tylerhost" in url.lower() or "tylerportico" in url.lower():
                     return BULK_ENERGOV_TEMPLATE.format(city_name=city, url=url, start_date=start_date, end_date=end_date)
                elif "mgoconnect" in url.lower() or "mgo" in normalized_city:
                     jurisdiction = city.title()
                     if "Irving" in template: jurisdiction = "Irving"
                     if "Garland" in template: jurisdiction = "Garland"
                     if "Lewisville" in template: jurisdiction = "Lewisville"
                     if "Denton" in template: jurisdiction = "Denton"
                     if "Celina" in template: jurisdiction = "Celina"
                     if "Fate" in template: jurisdiction = "Fate"
                     return BULK_MGO_TEMPLATE.format(jurisdiction=jurisdiction, mgo_email=mgo_email, mgo_password=mgo_password, start_date=start_date, end_date=end_date)
        
        # Fallback for custom tasks
        return template.replace("{address}", f"permits from {start_date} to {end_date}").replace("most recent permit", "list of permits")

        
    # Format with all available variables (safe if template doesn't use them all)
    return template.format(
        address=address, 
        permit_type=permit_type,
        mgo_email=mgo_email,
        mgo_password=mgo_password
    )

# Specific existing tasks (preserved for custom logic)
FORT_WORTH_PERMIT_TASK = """
Go to the Fort Worth permit portal at https://aca-prod.accela.com/CFW/Cap/CapHome.aspx?module=Building&TabName=Building
Search for property address: {address}
First, you may need to enter the address in the search bar or navigate to a search form.
Specifically look for "Search Applications" or input field for address.
Find the latest permit matching type: {permit_type}
If multiple permits are found, prioritize "Active" or "Issued" status and the most recent date.

Extract the following fields into a valid JSON object:
- permit_number: The permit ID/Number
- issue_date: Date emitted
- permit_type: The type or description
- valuation: Job value or cost
- status: Current status (e.g. Issued, Finaled)
- contractor: Contractor name if available
- description: Brief work description

Return ONLY the JSON object.
"""

ARLINGTON_PERMIT_TASK = """
Go to the Arlington permit portal at https://webapps.arlingtontx.gov/CitizenAccess/Cap/CapHome.aspx
Search for address: {address}
First, you may need to register or continue as guest if allowed.
Find the search bar for permits.
Find the most recent permit for: {permit_type}
Extract these fields as JSON:
- permit_number
- issue_date
- permit_type
- valuation
- status
- contractor_name

Return ONLY the JSON object.
"""

# Map of cities to tasks
CITY_TASKS = {
    # Existing / Custom
    "fort_worth": FORT_WORTH_PERMIT_TASK,
    "arlington": ARLINGTON_PERMIT_TASK,
    
    # MGO Connect
    "garland": MGO_TEMPLATE.format(jurisdiction="Garland"),
    "irving": MGO_TEMPLATE.format(jurisdiction="Irving"),
    "lewisville": MGO_TEMPLATE.format(jurisdiction="Lewisville"),
    "denton": ETRAKIT_TEMPLATE.format(city_name="Denton", url="https://dntn-trk.aspgov.com/eTRAKiT"),
    "celina": MYGOV_TEMPLATE.format(city_name="Celina", url="https://public.mygov.us/celina_tx/module?module=pi"),
    "fate": MYGOV_TEMPLATE.format(city_name="Fate", url="https://public.mygov.us/fate_tx/module?module=pi"),
    
    # EnerGov
    "southlake": ENERGOV_TEMPLATE.format(city_name="Southlake", url="https://energov.cityofsouthlake.com/EnerGov_Prod/SelfService"),
    "colleyville": ENERGOV_TEMPLATE.format(city_name="Colleyville", url="https://selfservice.colleyville.com/energov_prod/selfservice"),
    "north_richland_hills": ENERGOV_TEMPLATE.format(city_name="North Richland Hills", url="https://selfservice.nrhtx.com/energov_prod/selfservice"),
    "nrh": ENERGOV_TEMPLATE.format(city_name="North Richland Hills", url="https://selfservice.nrhtx.com/energov_prod/selfservice"),
    "mckinney": ENERGOV_TEMPLATE.format(city_name="McKinney", url="https://www.mckinneytexas.org/CSS"),
    "allen": ENERGOV_TEMPLATE.format(city_name="Allen", url="https://energovweb.cityofallen.org/energov/selfservice/home"),
    "princeton": ENERGOV_TEMPLATE.format(city_name="Princeton", url="https://princetontx-energov.tylerhost.net/apps/SelfService"), # Correct EnerGov URL
    "grand_prairie": ENERGOV_TEMPLATE.format(city_name="Grand Prairie", url="https://egov.gptx.org/EnerGov_Prod/SelfService#/home"),
    "mesquite": ENERGOV_TEMPLATE.format(city_name="Mesquite", url="https://energov.cityofmesquite.com/EnerGov_Prod/SelfService"),
    "desoto": ENERGOV_TEMPLATE.format(city_name="DeSoto", url="https://cityofdesototx-energovweb.tylerhost.net/apps/selfservice#/home"),
    "cedar_hill": ENERGOV_TEMPLATE.format(city_name="Cedar Hill", url="https://cedarhilltx-energovpub.tylerhost.net/Apps/SelfService#/home"),
    "coppell": ENERGOV_TEMPLATE.format(city_name="Coppell", url="https://energov.coppelltx.gov/EnerGov_Prod/SelfService"),
    "hurst": ENERGOV_TEMPLATE.format(city_name="Hurst", url="https://www.hursttx.gov/CSS"),
    "trophy_club": ENERGOV_TEMPLATE.format(city_name="Trophy Club", url="https://energovweb.trophyclub.org/energovprod/selfservice"),
    "duncanville": ENERGOV_TEMPLATE.format(city_name="Duncanville", url="https://duncanvilletx.gov"),
    
    # MyGov
    "grapevine": """
    Go to the Grapevine MyGov portal.
    Try URL: https://public.mygov.us/tx_grapevine/templates?module=reports (Reports view often works better)
    Or: https://public.mygov.us/tx_grapevine/lookup
    If using Reports: Select "Permits" module, filtered by date/address.
    If using Lookup: Search for address: {address}
    
    Extract these fields as JSON:
    - permit_number
    - issue_date
    - permit_type
    - valuation
    - status
    - contractor_name
    
    Return ONLY the JSON object.
    """,
    "forney": MYGOV_TEMPLATE.format(city_name="Forney", url="https://mygov.us/collaborator/forneytx"),
    "mansfield": MYGOV_TEMPLATE.format(city_name="Mansfield", url="https://public.mygov.us/mansfield_tx/module?module=pi"),
    "little_elm": MYGOV_TEMPLATE.format(city_name="Little Elm", url="https://public.mygov.us/little_elm_tx/module?module=pi"),
    "rowlett": MYGOV_TEMPLATE.format(city_name="Rowlett", url="https://public.mygov.us/rowlett_tx/module?module=pi"),
    "midlothian": MYGOV_TEMPLATE.format(city_name="Midlothian", url="https://public.mygov.us/midlothian_tx/module?module=pi"),
    "royse_city": MYGOV_TEMPLATE.format(city_name="Royse City", url="https://public.mygov.us/roysecity_tx/module?module=pi"),
    "lancaster": MYGOV_TEMPLATE.format(city_name="Lancaster", url="https://public.mygov.us/lancaster_tx/module?module=pi"),
    "weatherford": MYGOV_TEMPLATE.format(city_name="Weatherford", url="https://permits.weatherfordtx.gov/"), 

    # eTRAKiT
    "plano": ETRAKIT_TEMPLATE.format(city_name="Plano", url="https://ecop.plano.gov/eTRAKiT"),
    "frisco": ETRAKIT_TEMPLATE.format(city_name="Frisco", url="https://etrakit.friscotexas.gov/eTRAKiT"),
    "burleson": MYGOV_TEMPLATE.format(city_name="Burleson", url="https://public.mygov.us/burleson_tx"),
    "the_colony": ETRAKIT_TEMPLATE.format(city_name="The Colony", url="https://tcol-trk.aspgov.com/eTrakit/"),
    "keller": ETRAKIT_TEMPLATE.format(city_name="Keller", url="https://etrakit.cityofkeller.com/eTRAKiT"),
    "flower_mound": ETRAKIT_TEMPLATE.format(city_name="Flower Mound", url="https://etrakit.flower-mound.com/etrakit"),
    
    # Others
    "bedford": """
    Go to the Bedford OpenGov portal at https://bedfordtx.portal.opengov.com/
    Click on "Search Public Records" or look for a search bar.
    Search for address: {address}
    Filter by Record Type: "Building Permit" if possible.
    Find the most recent permit for: {permit_type}
    Extract these fields as JSON:
    - permit_number
    - issue_date
    - permit_type
    - valuation
    - status
    - contractor_name
    
    Return ONLY the JSON object.
    """,
    "sachse": """
    Go to the Sachse SmartGov portal at https://ci-sachse-tx.smartgovcommunity.com/ApplicationPublic/ApplicationSearch
    Enter search term: {address}
    Click "Search".
    Find the most recent permit for: {permit_type}
    Extract these fields as JSON:
    - permit_number
    - issue_date
    - permit_type
    - valuation
    - status
    - contractor_name
    
    Return ONLY the JSON object.
    """,
    "anna": """
    Go to the Anna SmartGov portal at https://ci-anna-tx.smartgovcommunity.com/ApplicationPublic/ApplicationSearch
    Enter search term: {address}
    Click "Search".
    Find the most recent permit for: {permit_type}
    Extract these fields as JSON:
    - permit_number
    - issue_date
    - permit_type
    - valuation
    - status
    - contractor_name
    
    Return ONLY the JSON object.
    """,
    "euless": """
    Go to the Euless online portal at https://www.eulesstx.gov/departments/planning-and-development/building-inspections/permits
    Search for "Check Permit Status" or login.
    Search for address: {address}
    Find the most recent permit for: {permit_type}
    Extract these fields as JSON:
    - permit_number
    - issue_date
    - permit_type
    - valuation
    - status
    - contractor_name
    
    Return ONLY the JSON object.
    """,
    "richardson": """
    Go to the Richardson website: https://www.cor.net
    Navigate to "Online Permits" (or search for it).
    Search for address: {address}
    Find the most recent permit for: {permit_type}
    Extract these fields as JSON:
    - permit_number
    - issue_date
    - permit_type
    - valuation
    - status
    - contractor_name
    
    Return ONLY the JSON object.
    """,
    "carrollton": """
    Go to the Carrollton CityView Portal at https://cityserve.cityofcarrollton.com/CityViewPortal
    Click "Search" or "Permit Search".
    Search for address: {address}
    Find the most recent permit for: {permit_type}
    Extract these fields as JSON:
    - permit_number
    - issue_date
    - permit_type
    - valuation
    - status
    - contractor_name
    
    Return ONLY the JSON object.
    """,
    "rockwall": """
    Go to the Rockwall public portal.
    Search for "City of Rockwall Permits" or similar.
    Search for address: {address}
    Find the most recent permit for: {permit_type}
    Extract these fields as JSON:
    - permit_number
    - issue_date
    - permit_type
    - valuation
    - status
    - contractor_name
    
    Return ONLY the JSON object.
    """,
    "wylie": """
    Go to the Wylie Citizenserve portal.
    URL: https://www.citizenserve.com/wylie
    Search for address: {address}
    Find the most recent permit for: {permit_type}
    Extract these fields as JSON:
    - permit_number
    - issue_date
    - permit_type
    - valuation
    - status
    - contractor_name
    
    Return ONLY the JSON object.
    """,
    "cleburne": """
    Go to the Cleburne Cityworks portal.
    Search for address: {address}
    Find the most recent permit for: {permit_type}
    Extract these fields as JSON:
    - permit_number
    - issue_date
    - permit_type
    - valuation
    - status
    - contractor_name
    
    Return ONLY the JSON object.
    """,
    "azle": """
    Go to the Azle online permits portal at https://www.cityofazle.org (navigate to Departments -> Building Inspection).
    Search for address: {address}
    Find the most recent permit for: {permit_type}
    Extract these fields as JSON:
    - permit_number
    - issue_date
    - permit_type
    - valuation
    - status
    - contractor_name
    
    Return ONLY the JSON object.
    """,
    "melissa": """
    Go to the Melissa Camino portal.
    URL: https://app.caminopermits.com/search?jurisdiction=melissa-tx (or navigate from cityofmelissa.com)
    Search for address: {address}
    Find the most recent permit for: {permit_type}
    Extract these fields as JSON:
    - permit_number
    - issue_date
    - permit_type
    - valuation
    - status
    - contractor_name
    
    Return ONLY the JSON object.
    """,
    # Added missing cities
    "prosper": ETRAKIT_TEMPLATE.format(city_name="Prosper", url="http://etrakit.prospertx.gov/eTRAKIT"),
    "dallas": """
    Go to the Dallas Accela portal (Build) at https://developdallas.dallascityhall.com/
    Note: This system is migrating soon.
    Search for address: {address}
    Find the most recent permit for: {permit_type}
    Extract these fields as JSON:
    - permit_number
    - issue_date
    - permit_type
    - valuation
    - status
    - contractor_name
    
    Return ONLY the JSON object.
    """,
    "saginaw": """
    Go to the Saginaw TX Online Portal.
    URL: http://www.ci.saginaw.tx.us/departments/building_inspections___permits/index.php
    Look for "Permits & Forms" or online search.
    Search for address: {address}
    Find the most recent permit for: {permit_type}
    Extract these fields as JSON:
    - permit_number
    - issue_date
    - permit_type
    - valuation
    - status
    - contractor_name
    
    Return ONLY the JSON object.
    """,
    "haltom_city": """
    Go to the Haltom City Online Action Center.
    URL: https://www.haltomcitytx.com/departments/planning-community-development/online-permit-portal
    Search for address: {address}
    Find the most recent permit for: {permit_type}
    Extract these fields as JSON:
    - permit_number
    - issue_date
    - permit_type
    - valuation
    - status
    - contractor_name
    
    Return ONLY the JSON object.
    """
}

def get_task_for_city(city: str, address: str = "", permit_type: str = "Building", mgo_email: str = "", mgo_password: str = "", mode: str = "single", start_date: str = "", end_date: str = "") -> str:
    """
    Format the task template for a given city.
    Mode: 'single' or 'bulk'.
    """
    normalized_city = city.lower().replace(" ", "_").replace("north_richland_hills", "nrh")
    
    # Base templates map (Logic to swap to BULK if mode='bulk')
    template = CITY_TASKS.get(normalized_city)
    
    if not template:
         raise ValueError(f"No task specific for city: {city} (normalized: {normalized_city})")

    # Dynamic Template Swapping for Bulk
    if mode == "bulk":
        # Special handling for Southlake (portal ignores date filters)
        if normalized_city == "southlake":
            return SOUTHLAKE_BULK_TASK.format(start_date=start_date, end_date=end_date)

        # CityView (Carrollton) - special handling
        if normalized_city == "carrollton" or "cityview" in template.lower():
            return BULK_CITYVIEW_TEMPLATE.format(start_date=start_date, end_date=end_date)

        if "energov" in template.lower() or "energov_prod" in template.lower() or "mgoconnect" in template.lower() or "mgo" in normalized_city or "etrakit" in template.lower() or "mygov" in template.lower():
            import re
            url_match = re.search(r'https?://[^\s]+', template)
            if url_match:
                url = url_match.group(0)
                if "etrakit" in url.lower() or "etrakit" in template.lower():
                     return BULK_ETRAKIT_TEMPLATE.format(city_name=city, url=url, start_date=start_date, end_date=end_date)
                elif "mygov" in url.lower():
                     return BULK_MYGOV_TEMPLATE.format(city_name=city, url=url, start_date=start_date, end_date=end_date)
                elif "energov" in url.lower() or "tylerhost" in url.lower() or "tylerportico" in url.lower() or "selfservice" in url.lower():
                     return BULK_ENERGOV_TEMPLATE.format(city_name=city, url=url, start_date=start_date, end_date=end_date)
                elif "mgoconnect" in url.lower() or "mgo" in normalized_city:
                     jurisdiction = city.title()
                     if "Irving" in template: jurisdiction = "Irving"
                     if "Garland" in template: jurisdiction = "Garland"
                     if "Lewisville" in template: jurisdiction = "Lewisville"
                     if "Denton" in template: jurisdiction = "Denton"
                     if "Celina" in template: jurisdiction = "Celina"
                     if "Fate" in template: jurisdiction = "Fate"
                     return BULK_MGO_TEMPLATE.format(jurisdiction=jurisdiction, mgo_email=mgo_email, mgo_password=mgo_password, start_date=start_date, end_date=end_date)
        
        # Fallback for custom tasks
        return template.replace("{address}", f"permits from {start_date} to {end_date}").replace("most recent permit", "list of permits")

        
    # Format with all available variables (safe if template doesn't use them all)
    return template.format(
        address=address, 
        permit_type=permit_type,
        mgo_email=mgo_email,
        mgo_password=mgo_password
    )
