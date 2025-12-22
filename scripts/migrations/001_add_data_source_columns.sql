-- scripts/migrations/001_add_data_source_columns.sql
-- Add columns for tracking data source and CAD account linkage

ALTER TABLE leads_permit
ADD COLUMN IF NOT EXISTS data_source VARCHAR(50);

ALTER TABLE leads_permit
ADD COLUMN IF NOT EXISTS cad_account_number VARCHAR(50);

ALTER TABLE leads_permit
ADD COLUMN IF NOT EXISTS year_built INTEGER;

ALTER TABLE leads_permit
ADD COLUMN IF NOT EXISTS property_value DECIMAL(12,2);

-- Index for deduplication queries
CREATE INDEX IF NOT EXISTS idx_leads_permit_cad_account
ON leads_permit(cad_account_number) WHERE cad_account_number IS NOT NULL;

-- Index for data source filtering
CREATE INDEX IF NOT EXISTS idx_leads_permit_data_source
ON leads_permit(data_source) WHERE data_source IS NOT NULL;

COMMENT ON COLUMN leads_permit.data_source IS 'Source identifier (e.g., dallas_accela, dcad_taxroll, denton_socrata)';
COMMENT ON COLUMN leads_permit.cad_account_number IS 'CAD property account ID for cross-referencing';
