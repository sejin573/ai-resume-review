CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    plan VARCHAR(30) NOT NULL DEFAULT 'free',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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

CREATE TABLE IF NOT EXISTS review_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    resume_text TEXT NOT NULL,
    cover_letter_text TEXT NOT NULL,
    target_job_role TEXT NOT NULL,
    job_posting_text TEXT NOT NULL,
    source_file_type TEXT NOT NULL DEFAULT 'txt',
    review_mode TEXT NOT NULL DEFAULT 'detailed',
    job_category_preset TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS review_results (
    id SERIAL PRIMARY KEY,
    review_request_id INTEGER NOT NULL UNIQUE REFERENCES review_requests(id),
    result_json JSONB NOT NULL,
    provider_name TEXT NOT NULL DEFAULT 'mock',
    model_name TEXT NOT NULL DEFAULT 'mock-v1',
    prompt_version TEXT NOT NULL DEFAULT 'coverfit-review-v1',
    pipeline_version TEXT NOT NULL DEFAULT 'coverfit-pipeline-v1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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

CREATE TABLE IF NOT EXISTS training_consents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    review_request_id INTEGER NOT NULL UNIQUE REFERENCES review_requests(id),
    consent_given BOOLEAN NOT NULL,
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

CREATE TABLE IF NOT EXISTS anonymized_training_samples (
    id SERIAL PRIMARY KEY,
    training_consent_id INTEGER UNIQUE REFERENCES training_consents(id),
    imported_document_id INTEGER UNIQUE REFERENCES imported_documents(id),
    data_source_id INTEGER REFERENCES data_sources(id),
    input_payload JSONB NOT NULL,
    output_payload JSONB NOT NULL,
    training_record_json JSONB,
    sample_kind VARCHAR(50) NOT NULL DEFAULT 'user_review',
    quality_status VARCHAR(50) NOT NULL DEFAULT 'draft',
    reviewed_by_human BOOLEAN NOT NULL DEFAULT FALSE,
    contains_real_user_data BOOLEAN NOT NULL DEFAULT FALSE,
    pii_risk_score INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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

CREATE TABLE IF NOT EXISTS usage_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    event_type VARCHAR(50) NOT NULL,
    review_request_id INTEGER REFERENCES review_requests(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_usage_events_user_type_created
ON usage_events (user_id, event_type, created_at);
