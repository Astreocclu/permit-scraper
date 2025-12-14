# Leads Inventory (Audited)

**Last Audit:** 2025-12-13

---

## EXECUTIVE SUMMARY

- **USABLE LEADS:** 1,398 (from 5,334 scraped)
- **Top Categories:** Plumbing (421), HVAC (329), Electrical (183)
- **Top Cities:** Fort Worth (436), DeSoto (251), Dallas (182)
- **Biggest Gap:** 2,527 permits with no type data (Sachse 1000, Flower Mound 797, Frisco 199)

---

## SELLABLE CATEGORIES

### NEW SINGLE FAMILY
- **Total:** 144
- **Cities:** DeSoto (105), Fort Worth (19), Dallas (11), Mesquite (9)
- **Sell to:** Home builders, GCs
- **Price:** $25-50/lead

### ADDITION/REMODEL
- **Total:** 110
- **Cities:** Fort Worth (51), DeSoto (14), Southlake (12), Dallas (10), Mesquite (8), McKinney (6), Grapevine (5), Westlake (2), Allen (1), Mansfield (1)
- **Sell to:** General contractors, remodelers
- **Price:** $15-30/lead

### ROOFING
- **Total:** 42
- **Cities:** McKinney (10), Southlake (10), Dallas (7), Grapevine (5), Fort Worth (3), Westlake (3), Allen (2), Plano (2)
- **Sell to:** Roofing contractors
- **Price:** $8-15/lead

### HVAC
- **Total:** 329
- **Cities:** Flower Mound (100), Fort Worth (98), Dallas (31), Carrollton (27), DeSoto (20), Grapevine (16), Mesquite (11), Southlake (10), McKinney (6), Plano (5), Westlake (3), Allen (2)
- **Sell to:** HVAC contractors
- **Price:** $10-20/lead

### PLUMBING
- **Total:** 421
- **Cities:** Fort Worth (145), Dallas (75), DeSoto (57), Carrollton (52), Grapevine (27), Mesquite (20), McKinney (11), Southlake (10), Plano (8), Westlake (7), Allen (6), Prosper (3)
- **Sell to:** Plumbers
- **Price:** $8-12/lead

### ELECTRICAL (RESIDENTIAL)
- **Total:** 65
- **Cities:** Dallas (41), Mesquite (12), Southlake (10), McKinney (2)
- **Sell to:** Electricians
- **Price:** $8-12/lead

### POOL/SPA
- **Total:** 34
- **Cities:** Carrollton (20), Southlake (8), DeSoto (2), Dallas (1), Grapevine (1), McKinney (1), Mesquite (1)
- **Sell to:** Pool contractors
- **Price:** $15-25/lead

### FOUNDATION REPAIR
- **Total:** 25
- **Cities:** Allen (6), Dallas (6), DeSoto (6), McKinney (4), Mesquite (3)
- **Sell to:** Foundation repair specialists
- **Price:** $20-35/lead

### FENCE/DECK
- **Total:** 45
- **Cities:** DeSoto (24), Carrollton (6), Grapevine (5), Southlake (5), Allen (3), Westlake (2)
- **Sell to:** Fence/deck contractors
- **Price:** $8-15/lead

---

## JUNK (NOT IN TOTALS)

| Category | Count |
|----------|------:|
| Uncategorized (no type) | 2,527 |
| Commercial | 404 |
| Solar (different buyer) | 352 |
| Signs | 233 |
| ROW/Utility | 193 |
| Certificate of Occupancy | 94 |
| Irrigation | 41 |
| Extensions | 36 |
| Demolition | 33 |
| Water Heater (low value) | 23 |
| **TOTAL JUNK** | **3,936** |

---

## CITY STATUS

### PRODUCING (50+ usable)

| City | Usable | Total | File | Last Scrape | Action |
|------|-------:|------:|------|-------------|--------|
| Fort Worth | 436 | 500 | `fort_worth_raw.json` | 2025-12-12 | None |
| DeSoto | 251 | 500 | `desoto_raw.json` | 2025-12-12 | None |
| Dallas | 182 | 500 | `dallas_raw.json` | 2025-12-12 | None |
| Carrollton | 112 | 258 | `carrollton_raw.json` | 2025-12-11 | None |
| Flower Mound | 100 | 897 | `flower_mound_raw.json` | 2025-12-11 | None |
| Grapevine | 76 | 100 | `grapevine_raw.json` | 2025-12-09 | Run 500 |
| Mesquite | 65 | 100 | `mesquite_raw.json` | 2025-12-13 | Run 500 |
| Southlake | 65 | 82 | `southlake_raw.json` | 2025-12-12 | None |

### LOW YIELD (20-49 usable)

| City | Usable | Total | File | Action |
|------|-------:|------:|------|--------|
| McKinney | 40 | 100 | `mckinney_raw.json` | Run 500 |
| Westlake | 28 | 180 | `westlake_raw.json` | None |
| Allen | 20 | 50 | `allen_raw.json` | Run 500 |

### NOT WORTH IT (<20 usable)

| City | Usable | Total | Issue |
|------|-------:|------:|-------|
| Plano | 18 | 50 | Auth required |
| Prosper | 3 | 100 | Wrong permit types |
| Frisco | 1 | 200 | No type extraction |
| Mansfield | 1 | 10 | Low volume |

### BROKEN (0 usable)

| City | Total | Issue |
|------|------:|-------|
| Sachse | 1,000 | No type field in SmartGov |
| Cedar Hill | 500 | All solar/commercial |
| Colleyville | 100 | All commercial |
| Denton | 5 | Too few scraped |
| Trophy Club | 5 | Too few scraped |
| Waxahachie | 5 | Too few scraped |
| Rowlett | 10 | Too few scraped |

---

## ACTION ITEMS

1. **Sachse:** Add type extraction to SmartGov scraper → +500 potential leads
2. **Frisco:** Add type inference from permit ID prefix → +100 potential leads
3. **McKinney:** Run `citizen_self_service.py mckinney 500` → +150 potential leads
4. **Grapevine:** Run `mygov_multi.py grapevine 500` → +300 potential leads
5. **Denton:** Run `etrakit.py denton 500` → +200 potential leads
