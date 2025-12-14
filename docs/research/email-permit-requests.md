# Email-Based Permit Data Requests

For cities without online search portals, Texas Public Information Act (TPIA) requests can be used to obtain permit data via email.

## Target Cities

| City | Population | Growth | Contact | Notes |
|------|------------|--------|---------|-------|
| **Highland Park** | 9,000 | 0% | Building.Permits@hptx.org | Ultra-wealthy (OpenGov - no public search) |
| **Anna** | 15,000 | 10% | Building@annatexas.gov | Ultra-high growth |
| **Fairview** | 10,000 | 3% | permits@fairviewtexas.org | Wealthy Collin suburb |

Note: Bedford was removed - now scrapable via opengov.py

## Template Email Request

Subject: `Public Information Request - Building Permits [CITY NAME]`

```
To Whom It May Concern,

Under the Texas Public Information Act (Government Code Chapter 552), I am requesting
the following public records:

A list of all building permits issued in [CITY NAME] from [START DATE] to [END DATE],
including:
- Permit number
- Property address
- Permit type (residential, commercial, etc.)
- Description of work
- Issue date
- Valuation (if available)
- Contractor name (if available)

I request this information in electronic format (Excel/CSV preferred) if available.

Please let me know if there are any fees associated with this request. I am willing to
pay reasonable costs for document production.

Thank you for your assistance.

[YOUR NAME]
[YOUR EMAIL]
[YOUR PHONE]
```

## Contact Information

### Highland Park, TX (Ultra-Wealthy)
- **Building Inspections**: 4700 Drexel Dr, Highland Park, TX 75205
- **Email**: Building.Permits@hptx.org
- **Phone**: 214-559-9308
- **Note**: OpenGov portal is application-only, no public permit search

### Anna, TX
- **Building Department**: 120 W. 7th St, Ste. #142, Anna, TX 75409
- **Email**: Building@annatexas.gov
- **Phone**: Contact via website

### Fairview, TX
- **Building Inspections**: 372 Town Place, Fairview, TX 75069
- **Email**: permits@fairviewtexas.org
- **Phone**: 972-562-0522
- **Hours**: 8:00 AM - 4:30 PM Mon-Fri

## Process

1. **Initial Request**: Send email template to city
2. **Response Time**: Cities have 10 business days to respond under TPIA
3. **Fee Estimate**: May receive cost estimate for large requests
4. **Data Delivery**: Usually Excel/CSV or PDF

## Frequency

For ongoing lead generation, consider:
- **Monthly requests**: "Permits issued in [MONTH YEAR]"
- **Quarterly batches**: Less overhead, still current data

## Automation Potential

Could create a script to:
1. Generate templated emails per city
2. Track request dates and responses
3. Parse incoming Excel attachments
4. Load into database

## Notes

- Anna is email-only for applications, likely same for data requests
- Fairview accepts email at permits@fairviewtexas.org
- Both cities are high-value (wealthy/growing) despite lack of online portal
- TPIA requests are free for public records (may charge for staff time on large requests)
