from app.services.anonymization_service import AnonymizationService

_service = AnonymizationService()


def anonymize_text(text: str) -> str:
    return _service.anonymize_text(text)


def build_anonymized_payload(resume_text: str, cover_letter_text: str, target_job_role: str, job_posting_text: str) -> dict:
    return _service.build_anonymized_payload(
        resume_text=resume_text,
        cover_letter_text=cover_letter_text,
        target_job_role=target_job_role,
        job_posting_text=job_posting_text,
    )
