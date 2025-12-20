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
| **Euless** | Cityworks PLL | ❌ NEED | ❌ reCAPTCHA | Likely not scriptable |
| **Forney** | MyGov | ❌ NEED | ❌ Login required | Need MyGov Collaborator login |
| **Highland Village** | Custom | ❌ NEED | ❌ Contractor registration | Need contractor account |
| **Corinth** | Civic Access | ❌ NEED | ❌ Registration required | Need Civic Access account |

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
- [ ] **Forney MyGov** - https://mygov.us/collaborator/forneytx
- [ ] **Highland Village** - Contractor registration required
- [ ] **Corinth Civic Access** - https://corinth.mycivicaccess.com/

### Need Technical Fix (Have Credentials):
- [ ] **Irving** - PDF export opens about:blank, needs debugging

### Likely Unsolvable:
- **Euless** - reCAPTCHA on login
- **Richardson** - 403 IP block + may need proxy

---

## Public Access Cities (No Auth Needed)

These work without any login - 21 cities total:
- Dallas, Fort Worth, Arlington, Grand Prairie, Mesquite (Accela)
- Frisco, Flower Mound, Denton (eTRAKiT - public mode)
- McKinney, Allen, Southlake, Colleyville, Trophy Club, Hurst, Coppell, Waxahachie, Cedar Hill, DeSoto (EnerGov CSS)
- Carrollton (CityView)
- Westlake, Little Elm, Grapevine (MyGov)
- Sachse (SmartGov)

---

**Last Updated:** 2024-12-20
