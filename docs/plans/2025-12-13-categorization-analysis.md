# Categorization Fix Analysis - 2025-12-13

## Rule-Based Fix Results (No AI)

944 leads recategorized using 3-layer logic:
1. permit_type priority
2. Word boundary matching for "deck"/"demo"
3. Category order (roof before outdoor_living, etc.)

### Top Changes by Volume
| Change | Count | Why |
|--------|-------|-----|
| other → hvac | 220 | "Mechanical" permit types now caught |
| roof → solar | 39 | "Solar/Photovoltaic" types prioritized |
| concrete → foundation | 33 | "Foundation Repair" types prioritized |
| pool → electrical | 30 | Electrical work for pools → electrical |
| outdoor_living → roof | 24 | "decking" no longer matches "deck" |
| electrical → solar | 18 | Solar permit types |
| pool → plumbing | 15 | Plumbing work for pools |
| plumbing → electrical | 8 | |
| electrical → hvac | 6 | |
| pool → hvac | 5 | |
| pool → demolition | 5 | |
| hvac → plumbing | 5 | |
| roof → hvac | 5 | |

### Net Category Movement
| Category | Net Change | Gained | Lost |
|----------|------------|--------|------|
| hvac | +240 | 245 | 5 |
| solar | +59 | 59 | 0 |
| foundation | +31 | 33 | 2 |
| plumbing | +23 | 31 | 8 |
| electrical | +18 | 42 | 24 |
| demolition | +16 | 16 | 0 |
| new_construction | +8 | 10 | 2 |
| remodel | -6 | 0 | 6 |
| addition | -11 | 0 | 11 |
| roof | -22 | 24 | 46 |
| outdoor_living | -33 | 4 | 37 |
| concrete | -42 | 0 | 42 |
| pool | -58 | 0 | 58 |
| other | -223 | 0 | 223 |

## Cost Estimate for Full Rescore
- Leads: 6,117
- Input tokens: ~3.7M
- Output tokens: ~0.9M
- **Total: $0.77** (DeepSeek pricing)

## Next Step
Running AI rescore on the 944 changed leads to compare rule-based vs AI categorization.
