import re


class AnonymizationService:
    PII_RULES = [
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL]"),
        (r"\b\d{2,3}-\d{3,4}-\d{4}\b", "[PHONE]"),
        (r"\b(19|20)\d{2}[./-](0[1-9]|1[0-2])[./-]([0-2][0-9]|3[0-1])\b", "[BIRTH_DATE]"),
        (r"\b\d{6}-\d{7}\b", "[RRN]"),
        (r"\b(?:서울|경기|인천|부산|대구|광주|대전|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주)[^\n,]{0,35}\b", "[ADDRESS]"),
        (r"\b(?:https?://|www\.)\S+\b", "[URL]"),
        (r"\b\d{2,6}-\d{2,6}-\d{2,6}\b", "[ACCOUNT]"),
        (r"\b(?:학번|사번|직번|employee id|student id)[:\s-]*[A-Za-z0-9-]{4,20}\b", "[ID]"),
        (r"\b(?:고려대학교|연세대학교|서울대학교|한양대학교|성균관대학교|중앙대학교|경희대학교|부산대학교|전남대학교|한국외국어대학교)\b", "[SCHOOL]"),
        (r"\b(?:삼성|LG|현대|카카오|네이버|쿠팡|토스|당근|라인|SK|CJ)[A-Za-z가-힣0-9\s]{0,12}\b", "[COMPANY]"),
        (r"\b[가-힣]{2,4}\s?(?:님|씨|학생|선생님)\b", "[NAME]"),
        (r"\bName\s*:\s*[A-Za-z\s]{2,30}\b", "Name: [NAME]"),
    ]
    RISK_PATTERNS = [
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", 35),
        (r"\b\d{2,3}-\d{3,4}-\d{4}\b", 30),
        (r"\b\d{6}-\d{7}\b", 40),
        (r"\b(?:서울|경기|인천|부산|대구|광주|대전|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주)[^\n,]{0,35}\b", 25),
        (r"\b(?:고려대학교|연세대학교|서울대학교|한양대학교|성균관대학교|중앙대학교|경희대학교|부산대학교|전남대학교|한국외국어대학교)\b", 15),
        (r"\b(?:삼성|LG|현대|카카오|네이버|쿠팡|토스|당근|라인|SK|CJ)[A-Za-z가-힣0-9\s]{0,12}\b", 15),
        (r"\b(?:https?://|www\.)\S+\b", 10),
        (r"\b(?:학번|사번|직번|employee id|student id)[:\s-]*[A-Za-z0-9-]{4,20}\b", 20),
    ]
    HIGH_RISK_THRESHOLD = 45

    def anonymize_text(self, text: str) -> str:
        sanitized = text or ""
        for pattern, replacement in self.PII_RULES:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        # NOTE: Production-grade privacy processing should combine NER, human review, and encrypted storage.
        return sanitized

    def build_anonymized_payload(
        self, resume_text: str, cover_letter_text: str, target_job_role: str, job_posting_text: str
    ) -> dict:
        return {
            "resume_text": self.anonymize_text(resume_text),
            "cover_letter_text": self.anonymize_text(cover_letter_text),
            "target_job_role": self.anonymize_text(target_job_role),
            "job_posting_text": self.anonymize_text(job_posting_text),
        }

    def detect_remaining_pii(self, text: str) -> list[str]:
        remaining: list[str] = []
        for pattern, _score in self.RISK_PATTERNS:
            if re.search(pattern, text or "", flags=re.IGNORECASE):
                remaining.append(pattern)
        return remaining

    def pii_risk_score(self, text: str) -> int:
        score = 0
        for pattern, weight in self.RISK_PATTERNS:
            matches = re.findall(pattern, text or "", flags=re.IGNORECASE)
            score += len(matches) * weight
        return score

    def should_reject(self, text: str) -> bool:
        return self.pii_risk_score(text) >= self.HIGH_RISK_THRESHOLD
