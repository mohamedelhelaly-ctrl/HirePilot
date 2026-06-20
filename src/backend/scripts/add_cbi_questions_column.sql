-- Add cbi_questions column to applications (run once against your DB)
ALTER TABLE applications
ADD COLUMN IF NOT EXISTS cbi_questions JSONB DEFAULT '[]'::jsonb;
