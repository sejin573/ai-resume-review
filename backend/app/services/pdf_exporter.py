from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

BODY_FONT_NAME = "CoverFitBody"
HEADING_FONT_NAME = "CoverFitHeading"
WINDOWS_FONT_DIR = Path("C:/Windows/Fonts")
BODY_FONT_PATH = WINDOWS_FONT_DIR / "malgun.ttf"
HEADING_FONT_PATH = WINDOWS_FONT_DIR / "malgunbd.ttf"


def _escape_html(value: str) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def _score_rows(scores: dict[str, Any]) -> list[list[str]]:
    labels = {
        "job_fit": "직무 적합도",
        "specificity": "구체성",
        "achievement": "성과 표현",
        "writing_quality": "문장력",
        "uniqueness": "차별성",
        "structure": "논리 구조",
        "keyword_match": "키워드 반영",
    }
    rows = [["평가 항목", "점수"]]
    for key, label in labels.items():
        rows.append([label, f"{scores.get(key, '-')}"])
    return rows


def _sanitize_pdf_text(value: str) -> str:
    safe = []
    for char in str(value or ""):
        codepoint = ord(char)
        if char in {"\\", "(", ")"}:
            safe.append(f"\\{char}")
        elif 32 <= codepoint <= 126:
            safe.append(char)
        elif char in {"\n", "\r", "\t"}:
            safe.append(" ")
        else:
            safe.append("?")
    return "".join(safe)


def _basic_pdf_lines(*lines: str) -> bytes:
    """Minimal PDF fallback when ReportLab or system fonts are unavailable.

    This fallback preserves the export flow, but it cannot render Korean text
    correctly because it relies on a Latin-only built-in font. Production and
    local development should keep ReportLab installed and Windows Korean fonts
    available so `_build_reportlab_pdf` can be used.
    """

    content_parts = ["BT", "/F1 12 Tf", "50 780 Td", "14 TL"]
    first = True
    for line in lines:
        text = _sanitize_pdf_text(line)
        if not first:
            content_parts.append("T*")
        content_parts.append(f"({text}) Tj")
        first = False
    content_parts.append("ET")
    content = "\n".join(content_parts).encode("latin-1", errors="replace")

    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
        f"5 0 obj << /Length {len(content)} >> stream\n".encode("latin-1") + content + b"\nendstream endobj",
    ]

    output = BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(output.tell())
        output.write(obj)
        output.write(b"\n")

    xref_start = output.tell()
    output.write(f"xref\n0 {len(offsets)}\n".encode("latin-1"))
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode("latin-1"))
    output.write(
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode("latin-1")
    )
    return output.getvalue()


def _register_korean_fonts() -> None:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    registered_fonts = pdfmetrics.getRegisteredFontNames()
    if BODY_FONT_NAME not in registered_fonts:
      pdfmetrics.registerFont(TTFont(BODY_FONT_NAME, str(BODY_FONT_PATH)))
    if HEADING_FONT_NAME not in registered_fonts:
      pdfmetrics.registerFont(TTFont(HEADING_FONT_NAME, str(HEADING_FONT_PATH)))


def _build_reportlab_pdf(
    *,
    job_role: str,
    review_created_at: datetime,
    review_mode: str,
    final_text: str,
    ai_summary: str,
    scores: dict[str, Any],
    strengths: list[str],
    problems: list[str],
    interview_questions: list[str],
) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    _register_korean_fonts()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        title=f"CoverFit AI - {job_role or '자기소개서'}",
        author="CoverFit AI",
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="PdfTitle",
            parent=styles["Title"],
            fontName=HEADING_FONT_NAME,
            fontSize=21,
            leading=28,
            textColor=colors.HexColor("#183a31"),
            alignment=TA_LEFT,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="PdfMeta",
            parent=styles["Normal"],
            fontName=BODY_FONT_NAME,
            fontSize=9.2,
            leading=13.5,
            textColor=colors.HexColor("#62706d"),
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="PdfSection",
            parent=styles["Heading2"],
            fontName=HEADING_FONT_NAME,
            fontSize=12.6,
            leading=17,
            textColor=colors.HexColor("#183a31"),
            spaceBefore=10,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="PdfBody",
            parent=styles["BodyText"],
            fontName=BODY_FONT_NAME,
            fontSize=10.4,
            leading=19,
            textColor=colors.HexColor("#202722"),
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            name="PdfFooter",
            parent=styles["Normal"],
            fontName=BODY_FONT_NAME,
            fontSize=8,
            leading=12,
            textColor=colors.HexColor("#7c8783"),
            alignment=TA_LEFT,
        )
    )

    role_label = job_role or "지원 직무 미입력"
    mode_label = review_mode or "detailed"
    final_text = final_text.strip() or "최종 문안이 비어 있습니다."

    story = [
        Paragraph("CoverFit AI 제출용 자기소개서", styles["PdfTitle"]),
        Paragraph(
            f"지원 직무: {_escape_html(role_label)} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"첨삭 모드: {_escape_html(mode_label)} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"작성일: {review_created_at.strftime('%Y-%m-%d')}",
            styles["PdfMeta"],
        ),
        Paragraph("최종 제출 문안", styles["PdfSection"]),
        Paragraph(_escape_html(final_text), styles["PdfBody"]),
        Spacer(1, 4 * mm),
        Paragraph("검토 요약", styles["PdfSection"]),
        Paragraph(_escape_html(ai_summary), styles["PdfBody"]),
    ]

    score_table = Table(_score_rows(scores), colWidths=[118 * mm, 34 * mm])
    score_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), HEADING_FONT_NAME),
                ("FONTNAME", (0, 1), (-1, -1), BODY_FONT_NAME),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf1eb")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#183a31")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d3d9d4")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 1), (1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend([Paragraph("평가 점수", styles["PdfSection"]), score_table])

    def bullet_section(title: str, items: list[str]) -> None:
        story.append(Paragraph(title, styles["PdfSection"]))
        for item in items[:6]:
            story.append(Paragraph(f"• {_escape_html(item)}", styles["PdfBody"]))

    bullet_section("강점", strengths)
    bullet_section("보완 포인트", problems)
    bullet_section("면접 예상 질문", interview_questions)
    story.extend(
        [
            Spacer(1, 6 * mm),
            Paragraph(
                "이 문서는 CoverFit AI의 첨삭 결과를 바탕으로 사용자가 검토한 제출용 문안입니다.",
                styles["PdfFooter"],
            ),
        ]
    )

    doc.build(story)
    return buffer.getvalue()


def build_review_pdf(
    *,
    job_role: str,
    review_created_at: datetime,
    review_mode: str,
    final_text: str,
    ai_summary: str,
    scores: dict[str, Any],
    strengths: list[str],
    problems: list[str],
    interview_questions: list[str],
) -> bytes:
    try:
        if BODY_FONT_PATH.exists() and HEADING_FONT_PATH.exists():
            return _build_reportlab_pdf(
                job_role=job_role,
                review_created_at=review_created_at,
                review_mode=review_mode,
                final_text=final_text,
                ai_summary=ai_summary,
                scores=scores,
                strengths=strengths,
                problems=problems,
                interview_questions=interview_questions,
            )
    except ModuleNotFoundError:
        pass
    except Exception:
        # The export flow should remain available even if the richer layout fails.
        pass

    return _basic_pdf_lines(
        "CoverFit AI Final Cover Letter",
        f"Role: {job_role}",
        f"Review mode: {review_mode}",
        f"Date: {review_created_at.strftime('%Y-%m-%d')}",
        "",
        "Final text:",
        final_text[:1200],
        "",
        "AI summary:",
        ai_summary[:600],
    )
