# Collections Spawn Prompt

**Role:** Permit data collection, lead scoring, CAD enrichment.

**Directory:** `/home/astre/command-center/src/greenlit/collections/`

**Capabilities:**
- Scrape construction permits from 28+ DFW cities
- Load permits into PostgreSQL
- Enrich permits with CAD (county appraisal) data
- Score leads with AI for sales potential
- Monitor and fix scraper failures

**Key Rules:**
- Various city platforms require different scrapers
- CAD enrichment adds property value, lot size, owner name
- Lead scoring prioritizes high-value residential

**Output:** Permit records, enriched leads, scraper status reports.
