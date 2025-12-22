# Cities Requiring Authentication

**MANDATORY CHECK**: Before working on ANY city scraper, check this file first.

---

## Credentials Location

All credentials stored in `.env` file. Copy from `.env.example` if missing.

---

## Cities Needing Auth

| City | Platform | Credentials | Status | Env Vars |
|------|----------|-------------|--------|----------|
| **Irving** | MGO Connect | ✅ HAVE | ⚠️ PDF export broken | `MGO_EMAIL`, `MGO_PASSWORD` |
| **Denton** | MGO Connect | ✅ HAVE | ✅ Working (uses same creds) | `MGO_EMAIL`, `MGO_PASSWORD` |
| **Plano** | eTRAKiT | ✅ HAVE | ✅ Working | `PLANO_USERNAME`, `PLANO_PASSWORD` |
| **Lewisville** | Tyler eSuite | ❌ NEED | ❌ Blocked - no public search | Need Tyler eSuite login |
| **Richardson** | Citizenserve | ❌ NEED | ❌ 403 blocked | May need proxy + login |
| **Euless** | NewEdge Portal | ❌ TRY | ⚠️ Login required, has PDF reports | https://euless.newedgeservices.com/PermitPortal |
| **Forney** | MyGov Collaborator | ❌ NEED | ❌ No public portal | Need Collaborator login (no public access) |
| **Highland Village** | Custom | ❌ NEED | ❌ Contractor registration | Need contractor account |
| **Corinth** | Civic Access | ❌ NEED | ❌ Registration required | Need Civic Access account |
| **Carrollton** | CityView | ❌ TRY | ⚠️ Public data stale (July 2025) | May need login for fresh data |
| **Burleson** | MyGov | ❌ NEED? | ❌ No public permit search | Portal lacks permit module entirely |
| **North Richland Hills** | EnerGov CSS + Tyler SSO | ❌ NEED | ❌ Tyler Identity required | No anonymous access, internal error on SSO cancel |

---

## Current .env Credentials

```bash
# MGO Connect (Irving, Denton, potentially others)
MGO_EMAIL=resultsandgoaloriented@gmail.com
MGO_PASSWORD=SleepyPanda123!

# eTRAKiT (Plano)
PLANO_USERNAME=TrustedHearthandHome
PLANO_PASSWORD=SleepyPanda123!
```

## Which Scrapers Use Which Credentials

| Scraper | Env Vars Used | Cities |
|---------|---------------|--------|
| `mgo_connect.py` | `MGO_EMAIL`, `MGO_PASSWORD` | Irving, Denton |
| `irving_pdf_sampler.py` | `MGO_EMAIL`, `MGO_PASSWORD` | Irving |
| `etrakit_auth.py` | `PLANO_USERNAME`, `PLANO_PASSWORD` | Plano |
| `dfw_big4_socrata.py` | `SOCRATA_APP_TOKEN` (optional) | Arlington |

---

## How to Add New Credentials

1. Register on the portal (may need contractor license info)
2. Add to `.env`:
   ```
   CITYNAME_USERNAME=your_username
   CITYNAME_PASSWORD=your_password
   ```
3. Update this file with status
4. Update scraper to read from env

---

## Blockers Requiring Manual Action

### Need Credentials From Reid:
- [ ] **Lewisville Tyler eSuite** - https://etools.cityoflewisville.com/esuite.permits/
- [ ] **Forney MyGov Collaborator** - https://mygov.us/collaborator/forneytx
  - **Type:** MyGov Collaborator (requires contractor/city official login)
  - **Status:** BLOCKED - no public portal exists (public.mygov.us/forney_tx returns 404)
  - **Alternative:** Contact city directly for data access or look for permit reports published elsewhere
  - **Note:** Unlike Burleson/Westlake, Forney has NO public MyGov portal at all - only Collaborator
- [ ] **Highland Village** - Contractor registration required
- [ ] **Corinth Civic Access** - https://corinth.mycivicaccess.com/
- [ ] **Carrollton CityView** - https://cityserve.cityofcarrollton.com/CityViewPortal/Account/Register - Public data stops at July 2025, try registering to see if login reveals fresher data
- [ ] **Euless NewEdge** - https://euless.newedgeservices.com/PermitPortal - New portal requires login, city also publishes annual PDF reports
- [ ] **Burleson MyGov** - https://public.mygov.us/burleson_tx - Public portal only has Address Lookup, GIS Map, Knowledge Base, Code Violations. NO permit search module visible. May need Collaborator login or contact city directly.
- [ ] **North Richland Hills EnerGov** - https://selfservice.nrhtx.com/energov_prod/selfservice - Tyler Identity SSO enforced. Canceling SSO shows "internal error" and empty page. NO guest/public search option. See `docs/portal-analysis/north_richland_hills.md` for full analysis.

### Need Technical Fix (Have Credentials):
- [ ] **Irving** - PDF export opens about:blank, needs debugging

### Likely Unsolvable:
- **Richardson** - 403 IP block + may need proxy

---

## Public Access Cities (No Auth Needed)

These work without any login - 21 cities total:
- Dallas, Fort Worth, Arlington, Grand Prairie, Mesquite (Accela)
- Frisco, Flower Mound, Denton (eTRAKiT - public mode)
- McKinney, Allen, Southlake, Colleyville, Trophy Club, Hurst, Coppell, Waxahachie, Cedar Hill, DeSoto (EnerGov CSS)
- ~~Carrollton (CityView)~~ - **STALE DATA** - see above
- Westlake, Little Elm, Grapevine (MyGov)
- Sachse (SmartGov)

---

**Last Updated:** 2025-12-22
