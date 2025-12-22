-- scripts/migrations/002_create_scrapers_metadata.sql
-- Track scraper runs and file hashes for change detection

CREATE TABLE IF NOT EXISTS scrapers_metadata (
    id SERIAL PRIMARY KEY,
    scraper_name VARCHAR(100) UNIQUE NOT NULL,
    last_run TIMESTAMP WITH TIME ZONE,
    last_file_hash VARCHAR(64),
    last_file_url TEXT,
    records_processed INTEGER DEFAULT 0,
    records_loaded INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'idle',  -- idle, running, success, error
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_scrapers_metadata_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER scrapers_metadata_updated
    BEFORE UPDATE ON scrapers_metadata
    FOR EACH ROW
    EXECUTE FUNCTION update_scrapers_metadata_timestamp();

COMMENT ON TABLE scrapers_metadata IS 'Tracks scraper run history and file hashes for change detection';
