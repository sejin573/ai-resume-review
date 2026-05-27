-- Safe ingestion pipeline schema migration
-- Apply with:
-- psql -U postgres -d ai_resume_review -f backend/migrations/20260520_ingestion_pipeline.sql

CREATE TABLE IF NOT EXISTS data_sources (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    license_status VARCHAR(50) NOT NULL DEFAULT 'unknown',
    license_note TEXT,
    source_url TEXT,
    permission_document_path TEXT,
    created_by_admin_id INTEGER REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

ALTER TABLE review_requests ADD COLUMN IF NOT EXISTS review_mode TEXT NOT NULL DEFAULT 'detailed';
ALTER TABLE review_requests ADD COLUMN IF NOT EXISTS job_category_preset TEXT;
ALTER TABLE review_results ADD COLUMN IF NOT EXISTS prompt_version TEXT NOT NULL DEFAULT 'coverfit-review-v1';
ALTER TABLE review_results ADD COLUMN IF NOT EXISTS pipeline_version TEXT NOT NULL DEFAULT 'coverfit-pipeline-v1';

CREATE TABLE IF NOT EXISTS review_refinements (
    id SERIAL PRIMARY KEY,
    review_request_id INTEGER NOT NULL REFERENCES review_requests(id),
    instruction TEXT NOT NULL,
    current_text TEXT NOT NULL,
    refined_text TEXT NOT NULL,
    change_summary TEXT NOT NULL,
    warnings_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS imported_documents (
    id SERIAL PRIMARY KEY,
    data_source_id INTEGER NOT NULL REFERENCES data_sources(id),
    original_title TEXT,
    original_text_encrypted_or_raw_for_review TEXT NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    job_role TEXT,
    company_name_masked TEXT,
    source_reference TEXT,
    import_status VARCHAR(50) NOT NULL DEFAULT 'imported',
    rejection_reason TEXT,
    anonymized_text TEXT,
    pii_risk_score INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE anonymized_training_samples ADD COLUMN IF NOT EXISTS imported_document_id INTEGER UNIQUE REFERENCES imported_documents(id);
ALTER TABLE anonymized_training_samples ADD COLUMN IF NOT EXISTS data_source_id INTEGER REFERENCES data_sources(id);
ALTER TABLE anonymized_training_samples ADD COLUMN IF NOT EXISTS training_record_json JSONB;
ALTER TABLE anonymized_training_samples ADD COLUMN IF NOT EXISTS sample_kind VARCHAR(50) NOT NULL DEFAULT 'user_review';
ALTER TABLE anonymized_training_samples ADD COLUMN IF NOT EXISTS quality_status VARCHAR(50) NOT NULL DEFAULT 'draft';
ALTER TABLE anonymized_training_samples ADD COLUMN IF NOT EXISTS reviewed_by_human BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE anonymized_training_samples ADD COLUMN IF NOT EXISTS contains_real_user_data BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE anonymized_training_samples ADD COLUMN IF NOT EXISTS pii_risk_score INTEGER NOT NULL DEFAULT 0;
ALTER TABLE anonymized_training_samples ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

CREATE TABLE IF NOT EXISTS training_sample_reviews (
    id SERIAL PRIMARY KEY,
    training_sample_id INTEGER NOT NULL REFERENCES anonymized_training_samples(id),
    reviewer_admin_id INTEGER NOT NULL REFERENCES users(id),
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    quality_score INTEGER,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS review_final_documents (
    id SERIAL PRIMARY KEY,
    review_request_id INTEGER NOT NULL UNIQUE REFERENCES review_requests(id),
    final_text TEXT NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'manual_edit',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS review_feedback (
    id SERIAL PRIMARY KEY,
    review_request_id INTEGER NOT NULL REFERENCES review_requests(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    rating VARCHAR(30) NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Usage limits / plan support
ALTER TABLE users ADD COLUMN IF NOT EXISTS plan VARCHAR(30) NOT NULL DEFAULT 'free';

CREATE TABLE IF NOT EXISTS usage_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    event_type VARCHAR(50) NOT NULL,
    review_request_id INTEGER REFERENCES review_requests(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_usage_events_user_type_created
ON usage_events (user_id, event_type, created_at);
