# Permit Scraper (Signal Engine)

## STATUS: FUTURE WORK - NOT ACTIVE

This repo contains permit portal scrapers for the DFW Signal Engine.
These are NOT integrated with the contractor audit system yet.

## What This Is
Puppeteer scrapers for city permit portals → extract homeowner leads (called "clients")

## Isolation
- Completely separate from contractor-auditor
- No shared database
- No shared services

## Portals (Planned)
- Southlake (EnerGov)
- Fort Worth
- McKinney
- Frisco (eTRAKiT)
- [Others TBD]

## DO NOT
- Import anything from contractor-auditor
- Share database connections
- Mix permit logic with audit logic
