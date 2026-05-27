from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_schema_updates(engine: Engine) -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    statements: list[str] = []

    if "users" in table_names:
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "plan" not in columns:
            statements.append("ALTER TABLE users ADD COLUMN plan VARCHAR(30) NOT NULL DEFAULT 'free'")
        if "is_active" not in columns:
            statements.append("ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1")

    if "review_requests" in table_names:
        columns = {column["name"] for column in inspector.get_columns("review_requests")}
        if "review_mode" not in columns:
            statements.append("ALTER TABLE review_requests ADD COLUMN review_mode TEXT NOT NULL DEFAULT 'detailed'")
        if "job_category_preset" not in columns:
            statements.append("ALTER TABLE review_requests ADD COLUMN job_category_preset TEXT")

    if "review_results" in table_names:
        columns = {column["name"] for column in inspector.get_columns("review_results")}
        if "prompt_version" not in columns:
            statements.append(
                "ALTER TABLE review_results ADD COLUMN prompt_version TEXT NOT NULL DEFAULT 'coverfit-review-v1'"
            )
        if "pipeline_version" not in columns:
            statements.append(
                "ALTER TABLE review_results ADD COLUMN pipeline_version TEXT NOT NULL DEFAULT 'coverfit-pipeline-v1'"
            )

    if "imported_documents" in table_names:
        columns = {column["name"] for column in inspector.get_columns("imported_documents")}
        if "anonymized_text" not in columns:
            statements.append("ALTER TABLE imported_documents ADD COLUMN anonymized_text TEXT")
        if "pii_risk_score" not in columns:
            statements.append("ALTER TABLE imported_documents ADD COLUMN pii_risk_score INTEGER NOT NULL DEFAULT 0")

    if "anonymized_training_samples" in table_names:
        sample_columns = inspector.get_columns("anonymized_training_samples")
        columns = {column["name"] for column in sample_columns}
        if "imported_document_id" not in columns:
            statements.append("ALTER TABLE anonymized_training_samples ADD COLUMN imported_document_id INTEGER")
        if "data_source_id" not in columns:
            statements.append("ALTER TABLE anonymized_training_samples ADD COLUMN data_source_id INTEGER")
        if "training_record_json" not in columns:
            statements.append("ALTER TABLE anonymized_training_samples ADD COLUMN training_record_json JSON")
        if "sample_kind" not in columns:
            statements.append("ALTER TABLE anonymized_training_samples ADD COLUMN sample_kind TEXT NOT NULL DEFAULT 'user_review'")
        if "quality_status" not in columns:
            statements.append("ALTER TABLE anonymized_training_samples ADD COLUMN quality_status TEXT NOT NULL DEFAULT 'draft'")
        if "reviewed_by_human" not in columns:
            statements.append("ALTER TABLE anonymized_training_samples ADD COLUMN reviewed_by_human BOOLEAN NOT NULL DEFAULT 0")
        if "contains_real_user_data" not in columns:
            statements.append("ALTER TABLE anonymized_training_samples ADD COLUMN contains_real_user_data BOOLEAN NOT NULL DEFAULT 0")
        if "pii_risk_score" not in columns:
            statements.append("ALTER TABLE anonymized_training_samples ADD COLUMN pii_risk_score INTEGER NOT NULL DEFAULT 0")
        if "updated_at" not in columns:
            statements.append("ALTER TABLE anonymized_training_samples ADD COLUMN updated_at TIMESTAMP")
        training_consent_column = next((column for column in sample_columns if column["name"] == "training_consent_id"), None)
        if training_consent_column and training_consent_column.get("nullable") is False:
            _relax_training_sample_consent_nullability(engine)

    if "review_final_documents" not in table_names:
        from app.models.review import ReviewFinalDocument

        ReviewFinalDocument.__table__.create(bind=engine, checkfirst=True)

    if "usage_events" not in table_names:
        from app.models.review import UsageEvent

        UsageEvent.__table__.create(bind=engine, checkfirst=True)

    if "review_feedback" not in table_names:
        from app.models.review import ReviewFeedback

        ReviewFeedback.__table__.create(bind=engine, checkfirst=True)

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def _relax_training_sample_consent_nullability(engine: Engine) -> None:
    if engine.dialect.name == "sqlite":
        with engine.begin() as connection:
            connection.execute(text("PRAGMA foreign_keys=OFF"))
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS anonymized_training_samples_new (
                        id INTEGER PRIMARY KEY,
                        training_consent_id INTEGER UNIQUE REFERENCES training_consents(id),
                        imported_document_id INTEGER UNIQUE REFERENCES imported_documents(id),
                        data_source_id INTEGER REFERENCES data_sources(id),
                        input_payload JSON NOT NULL,
                        output_payload JSON NOT NULL,
                        training_record_json JSON,
                        sample_kind TEXT NOT NULL DEFAULT 'user_review',
                        quality_status TEXT NOT NULL DEFAULT 'draft',
                        reviewed_by_human BOOLEAN NOT NULL DEFAULT 0,
                        contains_real_user_data BOOLEAN NOT NULL DEFAULT 0,
                        pii_risk_score INTEGER NOT NULL DEFAULT 0,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO anonymized_training_samples_new (
                        id,
                        training_consent_id,
                        imported_document_id,
                        data_source_id,
                        input_payload,
                        output_payload,
                        training_record_json,
                        sample_kind,
                        quality_status,
                        reviewed_by_human,
                        contains_real_user_data,
                        pii_risk_score,
                        created_at,
                        updated_at
                    )
                    SELECT
                        id,
                        training_consent_id,
                        imported_document_id,
                        data_source_id,
                        input_payload,
                        output_payload,
                        training_record_json,
                        sample_kind,
                        quality_status,
                        reviewed_by_human,
                        contains_real_user_data,
                        pii_risk_score,
                        created_at,
                        updated_at
                    FROM anonymized_training_samples
                    """
                )
            )
            connection.execute(text("DROP TABLE anonymized_training_samples"))
            connection.execute(text("ALTER TABLE anonymized_training_samples_new RENAME TO anonymized_training_samples"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_anonymized_training_samples_id ON anonymized_training_samples (id)"))
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_anonymized_training_samples_training_consent_id "
                    "ON anonymized_training_samples (training_consent_id)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_anonymized_training_samples_imported_document_id "
                    "ON anonymized_training_samples (imported_document_id)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_anonymized_training_samples_data_source_id "
                    "ON anonymized_training_samples (data_source_id)"
                )
            )
            connection.execute(text("PRAGMA foreign_keys=ON"))
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE anonymized_training_samples ALTER COLUMN training_consent_id DROP NOT NULL"))
