#!/bin/bash
# Plano eTRAKiT Overnight Scraper
# Runs at 1 AM to scrape permits while server is idle
# Scheduled via crontab

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/logs/plano_overnight.log"

mkdir -p "$PROJECT_DIR/logs"

echo "========================================" >> "$LOG_FILE"
echo "Plano Overnight Scrape: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

cd "$PROJECT_DIR"

# Activate venv and load env
source venv/bin/activate
set -a
source .env
set +a

# Scrape 1000 permits (takes ~100 minutes at 30s/page)
echo "[1] Starting Plano eTRAKiT scraper for 1000 permits..." >> "$LOG_FILE"
PYTHONUNBUFFERED=1 python3 scrapers/etrakit_auth.py plano 1000 >> "$LOG_FILE" 2>&1

# Load to database
echo "[2] Loading permits to database..." >> "$LOG_FILE"
python3 scripts/load_permits.py --dir data/raw --file plano_raw.json >> "$LOG_FILE" 2>&1

echo "[3] Complete: $(date)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
