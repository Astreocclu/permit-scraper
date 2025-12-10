import asyncio
from playwright.async_api import async_playwright
import os

async def test_extraction():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Load local HTML
        cwd = os.getcwd()
        filepath = f'file://{cwd}/debug_html/fort_worth_p1.html'
        print(f"Loading {filepath}...")
        await page.goto(filepath)
        
        # Run extraction JS
        permits = await page.evaluate('''() => {
            const permits = [];
            // Look for the specific Accela data grid
            const tables = document.querySelectorAll('table[id*="gdvPermitList"], table[id*="gdvAppList"], table.aca_grid');
            
            console.log(`Found ${tables.length} candidate tables`);

            for (const table of tables) {
                const rows = table.querySelectorAll('tr.ACA_TabRow_Odd, tr.ACA_TabRow_Even, tr[class*="TabRow"]');
                console.log(`Table ${table.id} has ${rows.length} rows`);
                
                for (const row of rows) {
                    let permit_id = null;
                    let address = null;
                    let permit_type = null;
                    let status = null;
                    let date = null;
                    let description = null;

                    // Priority: Try to find specific span IDs which are standard in Accela
                    const idSpan = row.querySelector('span[id*="lblPermitNumber"], span[id*="lblAltId"]');
                    if (idSpan) permit_id = idSpan.innerText.trim();

                    const dateSpan = row.querySelector('span[id*="lblUpdatedTime"], span[id*="lblDate"], span[id*="lblFileDate"]');
                    if (dateSpan) date = dateSpan.innerText.trim();

                    const typeSpan = row.querySelector('span[id*="lblType"], span[id*="lblAppType"]');
                    if (typeSpan) permit_type = typeSpan.innerText.trim();

                    const statusSpan = row.querySelector('span[id*="lblStatus"]');
                    if (statusSpan) status = statusSpan.innerText.trim();
                    
                    const addressSpan = row.querySelector('span[id*="lblAddress"], span[id*="lblPermitAddress"]');
                    if (addressSpan) address = addressSpan.innerText.trim();
                    
                    const descSpan = row.querySelector('span[id*="lblShortNote"], span[id*="lblDescription"]');
                    if (descSpan) description = descSpan.innerText.trim();
                    
                    // console.log(`Row: ID=${permit_id}, Date=${date}`);

                    if (permit_id) {
                        permits.push({
                            permit_id: permit_id,
                            address: address || '',
                            type: permit_type || '',
                            status: status || '',
                            date: date || '',
                            description: description || ''
                        });
                    }
                }
            }
            return permits;
        }''')
        
        print(f"Extracted {len(permits)} permits")
        if len(permits) > 0:
            print("Sample:", permits[0])
            
        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_extraction())
