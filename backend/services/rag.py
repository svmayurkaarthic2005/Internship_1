"""
RAG (Retrieval-Augmented Generation) pipeline for SIS Chatbot

Jurisdiction hierarchy: District → Taluk → Town → Ward → Block → Survey Number → Sub-Division

Components:
  detect_language()             — Tamil / Tanglish / English detection
  get_rag_context()             — ChromaDB semantic retrieval
  format_structured_data_for_llm() — Plain-text DB summary for LLM fallback
  build_html_response()         — Direct HTML builder (bypasses LLM for table queries)
  build_prompt()                — LLM prompt assembly (only when HTML path returns "")
  call_llama()                  — Synchronous Ollama LLM call
  call_llama_stream()           — Async streaming Ollama LLM call
  parse_intent()                — Keyword + fuzzy intent routing
  clean_message()               — Strip list prefixes
  extract_*()                   — Entity extraction helpers
"""

from langchain_ollama import ChatOllama
from typing import Dict, Any, Optional
from html import escape
from difflib import SequenceMatcher
import re

from backend.config import settings
from backend.services.chroma import similarity_search
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Initialize Ollama LLM
llm = ChatOllama(
    model=settings.LLM_MODEL,
    base_url=settings.OLLAMA_BASE_URL,
    temperature=0.1
)


# ─────────────────────────────────────────────────────────────────────────────
# detect_language
#   - Default to "tanglish" (no ChromaDB filter) when content is mixed.
#   - Pure-Tamil threshold at 50% so "Survey 145 எங்கே உள்ளது?"
#     is correctly classified as tanglish, not ta.
# ─────────────────────────────────────────────────────────────────────────────
def detect_language(text: str) -> str:
    """
    Detect language of input text using heuristics.

    Returns:
        "ta"        — predominantly Tamil (>50 % Tamil chars)
        "tanglish"  — mixed Tamil + English, or any Tamil present
        "en"        — pure English / no Tamil
    """
    if not text:
        return "en"

    tamil_chars = len(re.findall(r'[\u0B80-\u0BFF]', text))
    total_chars = len(text.strip())

    if total_chars == 0:
        return "en"

    tamil_pct = (tamil_chars / total_chars) * 100
    has_english = bool(re.search(r'[a-zA-Z]', text))

    if tamil_pct > 50:
        return "ta"
    elif tamil_chars > 0:
        # Any Tamil present alongside English → tanglish (no filter)
        return "tanglish"
    else:
        return "en"


# ─────────────────────────────────────────────────────────────────────────────
# get_rag_context — improved filter-failure logging
# ─────────────────────────────────────────────────────────────────────────────
def get_rag_context(query: str, language: str = "en", n_results: int = 5) -> str:
    """
    Retrieve relevant context from ChromaDB based on query.

    Language filter is applied for pure "en" or "ta"; tanglish searches
    both collections (no filter).
    """
    try:
        where_filter = None
        if language == "ta":
            where_filter = {"language": "tamil"}
        elif language == "en":
            where_filter = {"language": "english"}
        # tanglish → no filter (retrieves from both language documents)

        results = []
        if where_filter:
            try:
                results = similarity_search(query, n_results=n_results, where_filter=where_filter)
                if not results:
                    logger.warning(
                        f"Language filter {where_filter} returned 0 results for query "
                        f"'{query[:60]}'. ChromaDB may be missing '{language}' metadata on "
                        f"some documents. Retrying without filter."
                    )
                    results = similarity_search(query, n_results=n_results)
            except Exception as filter_err:
                logger.warning(
                    f"Similarity search with filter {where_filter} raised an error: {filter_err}. "
                    f"Retrying without filter."
                )
                results = similarity_search(query, n_results=n_results)
        else:
            results = similarity_search(query, n_results=n_results)

        if not results:
            logger.warning(f"No RAG context found (even without filter) for query: '{query[:60]}'")
            return ""

        context_parts = []
        for i, result in enumerate(results, 1):
            content = result["content"]
            metadata = result.get("metadata", {})
            doc_name = metadata.get("document_name", "Unknown")
            context_parts.append(f"[Source {i}: {doc_name}]\n{content}\n")

        context = "\n---\n".join(context_parts)
        logger.info(f"Retrieved {len(results)} context chunks for query")
        return context

    except Exception as e:
        logger.error(f"Error retrieving RAG context: {e}")
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# format_structured_data_for_llm
#   Simplified plain-text summary used ONLY when the LLM fallback is needed
#   (i.e. build_html_response returned "").
# ─────────────────────────────────────────────────────────────────────────────
def format_structured_data_for_llm(structured_data: Dict[str, Any]) -> str:
    """
    Produce a compact plain-text summary of structured_data for the LLM.
    Only used in the LLM fallback path. Does NOT reproduce full table logic —
    that lives exclusively in build_html_response.
    """
    if not structured_data:
        return ""

    lines = ["\n\nSTRUCTURED DATA FROM DATABASE:"]

    query_type = structured_data.get("query_type", "")
    if query_type:
        lines.append(f"Query Type: {query_type}")

    count = structured_data.get("count", 0)
    found = structured_data.get("found", True)

    if not found:
        lines.append("Result: No records found.")
        return "\n".join(lines)

    if count:
        lines.append(f"Total records: {count}")

    skip = {"query_type", "count", "found", "message", "surveys", "applications",
            "surveys_by_block", "sub_divisions", "visits", "workload"}

    for key, value in structured_data.items():
        if key not in skip and not isinstance(value, (list, dict)):
            lines.append(f"{key}: {value}")

    if structured_data.get("message"):
        lines.append(f"Note: {structured_data['message']}")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# build_html_response — HTML escaping on all DB values
# ─────────────────────────────────────────────────────────────────────────────
def _e(value) -> str:
    """Escape a value for safe HTML insertion."""
    return escape(str(value)) if value is not None else "-"


# Human-readable labels for DB status values
_STATUS_LABELS = {
    "pending":     "Pending",
    "in_progress": "In Progress",
    "approved":    "Approved",
    "rejected":    "Rejected",
    "escalated":   "Escalated",
    # field visit statuses
    "unscheduled": "Unscheduled",
    "scheduled":   "Scheduled",
    "completed":   "Completed",
    "overdue":     "Overdue",
    "rescheduled": "Rescheduled",
    "cancelled":   "Cancelled",
}


def _status(value) -> str:
    """Return a human-readable, HTML-escaped status label."""
    raw = str(value).lower() if value is not None else ""
    return escape(_STATUS_LABELS.get(raw, str(value) if value is not None else "-"))


def build_html_response(structured_data: Dict[str, Any], language: str = "en") -> str:
    """
    Build a clean HTML response directly from structured DB data,
    bypassing the LLM entirely for table-based queries.

    All DB values are HTML-escaped to prevent XSS / broken markup.
    Intro text uses <div> (not <p>) — browsers auto-close <p> before
    block-level elements like <table>, which hides the <thead>.

    Args:
        structured_data: Database query results
        language: Detected language ("en", "ta", or "tanglish") for table labels

    Returns an HTML string, or "" if no structured data to display
    (caller should then fall back to the LLM).
    """
    if not structured_data or not structured_data.get("found", True):
        return ""

    # Tamil translations for table headers and labels
    labels = {
        "en": {
            "survey_no": "Survey No.", "subdivisions": "Sub-Divisions",
            "district": "District", "taluk": "Taluk", "town": "Town",
            "ward": "Ward", "block": "Block", "area_sqm": "Area (sq.m)",
            "application_no": "Application No.", "type": "Type",
            "status": "Status", "stage": "Stage", "submitted": "Submitted",
            "submission_date": "Submission Date", "days_pending": "Days Pending",
            "field": "Field", "value": "Value",
            "applicant_name": "Applicant Name", "mobile": "Mobile",
            "email": "Email", "address": "Address",
            "survey_number": "Survey Number", "submitted_via": "Submitted Via",
            "sale_deed_number": "Sale Deed Number",
            "sale_deed_registered": "Sale Deed Registered",
            "declared_reason": "Declared Reason",
            "subdivisions_being_merged": "Subdivisions Being Merged",
            "total_merge_area": "Total Merge Area",
            "number_of_subdivisions": "Number of Subdivisions",
            "field_visit_status": "Field Visit Status",
            "scheduled_date": "Scheduled Date",
            "actual_visit_date": "Actual Visit Date",
            "encroachment_found": "Encroachment Found",
            "area_verified": "Area Verified",
            "yes": "Yes", "no": "No", "found": "Found",
            "merge_applications": "merge application(s)",
            "applications": "application(s)",
            "surveys": "survey number(s) in your jurisdiction",
            "no_records_found": "No records found",
            "application_details": "Application Details",
            "here_are": "Here are the",
            "total_area": "Total Area", "land_type": "Land Type",
            "patta_number": "Patta Number", "jurisdiction": "Jurisdiction",
            "CSC": "Common Service Center (CSC)",
            "citizen": "Citizen (Direct)",
            "sub_registrar": "Sub-Registrar Referral",
            "workload_summary": "Your Workload Summary",
            "metric": "Metric", "count": "Count",
            "total_applications": "Total Applications",
            "pending_count": "Pending", "overdue_count": "Overdue",
            "unscheduled_visits": "Field Visits Unscheduled",
            "unscheduled_field_visits": "application(s) with no field visit scheduled",
        },
        "ta": {
            "survey_no": "கணக்கெண்", "subdivisions": "உட்பிரிவுகள்",
            "district": "மாவட்டம்", "taluk": "தாலுகா", "town": "நகரம்",
            "ward": "வார்டு", "block": "தொகுதி", "area_sqm": "பரப்பளவு (சதுர மீ)",
            "application_no": "விண்ணப்ப எண்", "type": "வகை",
            "status": "நிலை", "stage": "நிலை", "submitted": "சமர்ப்பிக்கப்பட்டது",
            "submission_date": "சமர்ப்பித்த தேதி",
            "days_pending": "நிலுவையில் உள்ள நாட்கள்",
            "field": "புலம்", "value": "மதிப்பு",
            "applicant_name": "விண்ணப்பதாரரின் பெயர்",
            "mobile": "தொலைபேசி", "email": "மின்னஞ்சல்",
            "address": "முகவரி", "survey_number": "கணக்கெண்",
            "submitted_via": "சமர்ப்பிக்கப்பட்ட முறை",
            "sale_deed_number": "விற்பனை பத்திர எண்",
            "sale_deed_registered": "விற்பனை பத்திரம் பதிவு செய்யப்பட்டது",
            "declared_reason": "அறிவிக்கப்பட்ட காரணம்",
            "subdivisions_being_merged": "இணைக்கப்படும் உட்பிரிவுகள்",
            "total_merge_area": "மொத்த இணைப்பு பரப்பளவு",
            "number_of_subdivisions": "உட்பிரிவுகளின் எண்ணிக்கை",
            "field_visit_status": "கள ஆய்வு நிலை",
            "scheduled_date": "திட்டமிடப்பட்ட தேதி",
            "actual_visit_date": "உண்மையான பார்வை தேதி",
            "encroachment_found": "ஆக்கிரமிப்பு கண்டறியப்பட்டது",
            "area_verified": "பரப்பளவு சரிபார்க்கப்பட்டது",
            "yes": "ஆம்", "no": "இல்லை", "found": "கண்டறியப்பட்டது",
            "merge_applications": "இணைப்பு விண்ணப்பங்கள்",
            "applications": "விண்ணப்பங்கள்",
            "surveys": "உங்கள் அதிகார வரம்பில் உள்ள கணக்கெண்கள்",
            "no_records_found": "பதிவுகள் எதுவும் இல்லை",
            "application_details": "விண்ணப்ப விவரங்கள்",
            "here_are": "இதோ",
            "total_area": "மொத்த பரப்பளவு", "land_type": "நில வகை",
            "patta_number": "பட்டா எண்", "jurisdiction": "அதிகார வரம்பு",
            "CSC": "பொது சேவை மையம் (CSC)",
            "citizen": "குடிமகன் (நேரடி)",
            "sub_registrar": "துணை பதிவாளர் பரிந்துரை",
            "workload_summary": "உங்கள் பணிச்சுமை சுருக்கம்",
            "metric": "அளவீடு", "count": "எண்ணிக்கை",
            "total_applications": "மொத்த விண்ணப்பங்கள்",
            "pending_count": "நிலுவையில்", "overdue_count": "தாமதமானது",
            "unscheduled_visits": "கள ஆய்வு திட்டமிடப்படவில்லை",
            "unscheduled_field_visits": "கள ஆய்வு திட்டமிடப்படாத விண்ணப்பங்கள்",
        },
    }

    # For tanglish, use English labels
    lang = "ta" if language == "ta" else "en"
    t = labels[lang]

    # ── Surveys in jurisdiction ──────────────────────────────────────
    if "surveys" in structured_data and isinstance(structured_data["surveys"], list):
        surveys = structured_data["surveys"]
        count = structured_data.get("count", len(surveys))

        if not surveys:
            msg = _e(structured_data.get("message", t["no_records_found"]))
            return f"<div>{msg}</div>"

        rows = "".join(
            f"<tr>"
            f"<td>{_e(s.get('survey_no'))}</td>"
            f"<td>{_e(s.get('subdivisions') or '-')}</td>"
            f"<td>{_e(s.get('district'))}</td>"
            f"<td>{_e(s.get('taluk'))}</td>"
            f"<td>{_e(s.get('town'))}</td>"
            f"<td>{_e(s.get('ward'))}</td>"
            f"<td>{_e(s.get('block'))}</td>"
            f"</tr>"
            for s in surveys
        )
        return (
            f"<div class='table-intro'>{t['here_are']} <strong>{count}</strong> "
            f"{t['surveys']}:</div>"
            f"<table class='data-table'>"
            f"<thead><tr>"
            f"<th>{t['survey_no']}</th><th>{t['subdivisions']}</th>"
            f"<th>{t['district']}</th><th>{t['taluk']}</th>"
            f"<th>{t['town']}</th><th>{t['ward']}</th><th>{t['block']}</th>"
            f"</tr></thead>"
            f"<tbody>{rows}</tbody>"
            f"</table>"
        )

    # ── Applications (regular + merge) ──────────────────────────────
    if "applications" in structured_data and isinstance(structured_data["applications"], list):
        applications = structured_data["applications"]
        count = structured_data.get("count", len(applications))

        if not applications:
            return f"<div>{t['no_records_found']}</div>"

        is_merge = bool(applications) and "subdivisions_being_merged" in applications[0]

        if is_merge:
            rows = ""
            for app in applications:
                jur = app.get("jurisdiction", {})
                subdivisions = app.get("subdivisions_being_merged", [])
                logger.debug(f"App {app.get('application_number')}: {len(subdivisions)} subdivisions")

                subdiv_list = ", ".join(sd["sub_division_no"] for sd in subdivisions) if subdivisions else "-"
                subdiv_list = _e(subdiv_list)

                rows += (
                    f"<tr>"
                    f"<td>{_e(app.get('application_number'))}</td>"
                    f"<td>{_e(app.get('survey_no'))}</td>"
                    f"<td>{subdiv_list}</td>"
                    f"<td>{ f\"{app['total_merge_area_sqm']:.2f}\" if app.get('total_merge_area_sqm') else 'N/A' }</td>"
                    f"<td>{_status(app.get('status'))}</td>"
                    f"<td>{_e(app.get('stage'))}</td>"
                    f"<td>{_e(app.get('submission_date'))}</td>"
                    f"<td>{_e(jur.get('district'))}</td>"
                    f"<td>{_e(jur.get('taluk'))}</td>"
                    f"<td>{_e(jur.get('town'))}</td>"
                    f"</tr>"
                )
            return (
                f"<div class='table-intro'>{t['found']} <strong>{count}</strong> {t['merge_applications']}:</div>"
                f"<table class='data-table'>"
                f"<thead><tr>"
                f"<th>{t['application_no']}</th><th>{t['survey_no']}</th><th>{t['subdivisions']}</th>"
                f"<th>{t['area_sqm']}</th><th>{t['status']}</th><th>{t['stage']}</th><th>{t['submitted']}</th>"
                f"<th>{t['district']}</th><th>{t['taluk']}</th><th>{t['town']}</th>"
                f"</tr></thead>"
                f"<tbody>{rows}</tbody>"
                f"</table>"
            )
        else:
            rows = ""
            for app in applications:
                overdue = " ⚠️" if app.get("is_overdue") else ""
                rows += (
                    f"<tr>"
                    f"<td>{_e(app.get('application_number'))}</td>"
                    f"<td>{_e(app.get('type'))}</td>"
                    f"<td>{_status(app.get('status'))}{overdue}</td>"
                    f"<td>{_e(app.get('stage'))}</td>"
                    f"<td>{_e(app.get('submission_date'))}</td>"
                    f"</tr>"
                )
            return (
                f"<div class='table-intro'>{t['found']} <strong>{count}</strong> {t['applications']}:</div>"
                f"<table class='data-table'>"
                f"<thead><tr>"
                f"<th>{t['application_no']}</th><th>{t['type']}</th>"
                f"<th>{t['status']}</th><th>{t['stage']}</th><th>{t['submitted']}</th>"
                f"</tr></thead>"
                f"<tbody>{rows}</tbody>"
                f"</table>"
            )

    # ── Ward/Block surveys ───────────────────────────────────────────
    if "surveys_by_block" in structured_data:
        jur = structured_data.get("jurisdiction", {})
        rows = ""
        for block_name, surveys in structured_data["surveys_by_block"].items():
            for s in surveys:
                subdiv = _e(", ".join(s.get("subdivisions", [])) or "-")
                rows += (
                    f"<tr>"
                    f"<td>{_e(s.get('survey_no'))}</td>"
                    f"<td>{subdiv}</td>"
                    f"<td>{_e(block_name)}</td>"
                    f"<td>{_e(jur.get('ward'))}</td>"
                    f"<td>{_e(jur.get('town'))}</td>"
                    f"<td>{_e(jur.get('taluk'))}</td>"
                    f"<td>{_e(jur.get('district'))}</td>"
                    f"</tr>"
                )
        if not rows:
            return f"<div>{t['no_records_found']}</div>"
        return (
            f"<div class='table-intro'>{t['surveys']}:</div>"
            f"<table class='data-table'>"
            f"<thead><tr>"
            f"<th>{t['survey_no']}</th><th>{t['subdivisions']}</th><th>{t['block']}</th>"
            f"<th>{t['ward']}</th><th>{t['town']}</th><th>{t['taluk']}</th><th>{t['district']}</th>"
            f"</tr></thead>"
            f"<tbody>{rows}</tbody>"
            f"</table>"
        )

    # ── Single survey detail ─────────────────────────────────────────
    if "survey_no" in structured_data and "sub_divisions" in structured_data:
        jur = structured_data.get("jurisdiction", {})
        rows = "".join(
            f"<tr>"
            f"<td>{_e(sd.get('sub_division_no'))}</td>"
            f"<td>{sd.get('area_sqm', 0):.2f}</td>"
            f"</tr>"
            for sd in structured_data.get("sub_divisions", [])
        )
        subdiv_table = (
            f"<table class='data-table'>"
            f"<thead><tr><th>{t['subdivisions']}</th><th>{t['area_sqm']}</th></tr></thead>"
            f"<tbody>{rows}</tbody>"
            f"</table>"
            if rows else f"<div>{t['no_records_found']}</div>"
        )
        return (
            f"<div class='table-intro'><strong>{t['survey_no']} {_e(structured_data['survey_no'])}</strong></div>"
            f"<ul>"
            f"<li>{t['total_area']}: <strong>{structured_data.get('total_area_sqm', 0):.2f} sq.m</strong></li>"
            f"<li>{t['land_type']}: {_e(structured_data.get('land_type'))}</li>"
            f"<li>{t['patta_number']}: {_e(structured_data.get('patta_number'))}</li>"
            f"<li>{t['jurisdiction']}: {_e(jur.get('district'))} &rarr; {_e(jur.get('taluk'))} &rarr; "
            f"{_e(jur.get('town'))} &rarr; {_e(jur.get('ward'))} &rarr; {_e(jur.get('block'))}</li>"
            f"</ul>"
            f"<div class='table-intro'>{t['subdivisions']} ({structured_data.get('sub_divisions_count', 0)}):</div>"
            f"{subdiv_table}"
        )

    # ── Single application detail ────────────────────────────────────
    if "application_number" in structured_data and structured_data.get("found", False) and "type" in structured_data:
        app = structured_data
        overdue_flag = " ⚠️ OVERDUE" if app.get("is_overdue") else ""
        priority_flag = " 🔴 PRIORITY" if app.get("priority_flag") else ""

        applicant_rows = ""
        if "applicant" in app and app["applicant"]:
            applicant = app["applicant"]
            applicant_rows = (
                f"<tr><td><strong>{t['applicant_name']}</strong></td><td>{_e(applicant.get('name'))}</td></tr>"
                f"<tr><td><strong>{t['mobile']}</strong></td><td>{_e(applicant.get('mobile'))}</td></tr>"
                f"<tr><td><strong>{t['email']}</strong></td><td>{_e(applicant.get('email') or 'N/A')}</td></tr>"
                f"<tr><td><strong>{t['address']}</strong></td><td>{_e(applicant.get('address') or 'N/A')}</td></tr>"
            )

        submission_channel = app.get("submission_channel")
        if submission_channel:
            submission_channel_display = t.get(submission_channel, _e(submission_channel))
        else:
            submission_channel_display = "Not specified" if lang == "en" else "குறிப்பிடப்படவில்லை"

        optional_rows = ""
        if app.get("survey_no"):
            optional_rows += f"<tr><td><strong>{t['survey_number']}</strong></td><td>{_e(app.get('survey_no'))}</td></tr>"
        if submission_channel:
            optional_rows += f"<tr><td><strong>{t['submitted_via']}</strong></td><td>{submission_channel_display}</td></tr>"
        if app.get("sale_deed_number"):
            optional_rows += f"<tr><td><strong>{t['sale_deed_number']}</strong></td><td>{_e(app.get('sale_deed_number'))}</td></tr>"
            optional_rows += f"<tr><td><strong>{t['sale_deed_registered']}</strong></td><td>{t['yes'] if app.get('sale_deed_registered') else t['no']}</td></tr>"
        if app.get("declared_reason"):
            optional_rows += f"<tr><td><strong>{t['declared_reason']}</strong></td><td>{_e(app.get('declared_reason'))}</td></tr>"

        merge_info_html = ""
        if app.get("type") == "MERGE" and "subdivisions_being_merged" in app:
            subdivisions = app["subdivisions_being_merged"]
            if subdivisions:
                total_area = app.get("total_merge_area_sqm", 0)
                subdiv_details = [
                    f"{_e(sd['sub_division_no'])} ({sd['area_sqm']:.2f} sq.m)"
                    if sd.get('area_sqm') else _e(sd['sub_division_no'])
                    for sd in subdivisions
                ]
                subdiv_list = ", ".join(subdiv_details)
                merge_info_html = (
                    f"<tr><td colspan='2' style='background-color: #f0f8ff; padding: 10px; border-left: 4px solid #0066cc;'>"
                    f"<strong>📋 {t['subdivisions_being_merged']}:</strong><br>"
                    f"<div style='margin: 5px 0;'>{subdiv_list}</div>"
                    f"<strong>📊 {t['total_merge_area']}:</strong> "
                    f"{ f'{total_area:.2f} sq.m' if total_area else '-' }<br>"
                    f"<strong>🔢 {t['number_of_subdivisions']}:</strong> {len(subdivisions)}"
                    f"</td></tr>"
                )

        field_visit_rows = ""
        if "field_visit" in app and app["field_visit"]:
            fv = app["field_visit"]
            fv_status = _status(fv.get("status"))
            field_visit_rows = f"<tr><td><strong>{t['field_visit_status']}</strong></td><td>{fv_status}</td></tr>"
            if fv.get("scheduled_date"):
                field_visit_rows += f"<tr><td><strong>{t['scheduled_date']}</strong></td><td>{_e(fv.get('scheduled_date'))}</td></tr>"
            if fv.get("actual_date"):
                field_visit_rows += f"<tr><td><strong>{t['actual_visit_date']}</strong></td><td>{_e(fv.get('actual_date'))}</td></tr>"
            if fv.get("status") == "completed":
                field_visit_rows += f"<tr><td><strong>{t['encroachment_found']}</strong></td><td>{t['yes'] if fv.get('encroachment_found') else t['no']}</td></tr>"
                field_visit_rows += f"<tr><td><strong>{t['area_verified']}</strong></td><td>{t['yes'] if fv.get('area_verified') else t['no']}</td></tr>"

        return (
            f"<div class='table-intro'><strong>{t['application_details']}: {_e(app['application_number'])}</strong>{overdue_flag}{priority_flag}</div>"
            f"<table class='data-table'>"
            f"<thead><tr><th>{t['field']}</th><th>{t['value']}</th></tr></thead>"
            f"<tbody>"
            f"{applicant_rows}"
            f"<tr><td><strong>{t['type']}</strong></td><td>{_e(app.get('type'))}</td></tr>"
            f"<tr><td><strong>{t['status']}</strong></td><td>{_status(app.get('status'))}</td></tr>"
            f"<tr><td><strong>{t['stage']}</strong></td><td>{_e(app.get('stage'))}</td></tr>"
            f"<tr><td><strong>{t['submission_date']}</strong></td><td>{_e(app.get('submission_date'))}</td></tr>"
            f"{optional_rows}"
            f"{merge_info_html}"
            f"{field_visit_rows}"
            f"</tbody>"
            f"</table>"
        )

    # ── Officer workload ─────────────────────────────────────────────
    if "workload" in structured_data or "total_applications" in structured_data:
        d = structured_data
        return (
            f"<div class='table-intro'><strong>{t['workload_summary']}</strong></div>"
            f"<table class='data-table'>"
            f"<thead><tr><th>{t['metric']}</th><th>{t['count']}</th></tr></thead>"
            f"<tbody>"
            f"<tr><td>{t['total_applications']}</td><td>{_e(d.get('total_applications'))}</td></tr>"
            f"<tr><td>{t['pending_count']}</td><td>{_e(d.get('pending_count'))}</td></tr>"
            f"<tr><td>{t['overdue_count']}</td><td>{_e(d.get('overdue_count'))}</td></tr>"
            f"<tr><td>{t['unscheduled_visits']}</td><td>{_e(d.get('unscheduled_visits'))}</td></tr>"
            f"</tbody>"
            f"</table>"
        )

    # ── Unscheduled field visits ─────────────────────────────────────
    if "visits" in structured_data and isinstance(structured_data["visits"], list):
        visits = structured_data["visits"]
        if not visits:
            return f"<div>{t['no_records_found']}</div>"
        rows = "".join(
            f"<tr>"
            f"<td>{_e(v.get('application_number'))}</td>"
            f"<td>{_e(v.get('type'))}</td>"
            f"<td>{_status(v.get('status'))}</td>"
            f"<td>{_e(v.get('stage'))}</td>"
            f"<td>{_e(v.get('submission_date'))}</td>"
            f"<td>{_e(v.get('days_since_submission'))} {'days' if lang == 'en' else 'நாட்கள்'}</td>"
            f"</tr>"
            for v in visits
        )
        return (
            f"<div class='table-intro'>{t['found']} <strong>{len(visits)}</strong> "
            f"{t['unscheduled_field_visits']}:</div>"
            f"<table class='data-table'>"
            f"<thead><tr>"
            f"<th>{t['application_no']}</th><th>{t['type']}</th><th>{t['status']}</th>"
            f"<th>{t['stage']}</th><th>{t['submitted']}</th><th>{t['days_pending']}</th>"
            f"</tr></thead>"
            f"<tbody>{rows}</tbody>"
            f"</table>"
        )

    # No matching handler — caller falls back to LLM
    return ""


def build_prompt(
    query: str,
    context: str,
    structured_data: Dict[str, Any],
    language: str,
    chat_history: list = None
) -> str:
    """
    Build the LLM prompt. Only called when build_html_response returned "".
    structured_data is summarised as plain text (no duplicate table logic).

    Args:
        query: User's question
        context: Retrieved RAG context
        structured_data: Structured data from database queries
        language: Detected language ("en", "ta", or "tanglish")
        chat_history: List of previous messages for conversation context
    """
    language_instruction = {
        "en": "CRITICAL: You MUST respond in English language only.",
        "ta": "CRITICAL: You MUST respond in Tamil language only.",
        "tanglish": "CRITICAL: You MUST respond in the same mixed Tamil-English style (Tanglish) that the user used."
    }.get(language, "CRITICAL: You MUST respond in English language only.")

    system_instruction = f"""{language_instruction}

You are a friendly AI assistant for Sub Inspector Surveyor (SIS) officers of Tamil Nadu.

Your responsibilities:
- Help SIS officers with surveys, applications, field visits, and workflow procedures.
- Provide accurate information using ONLY the structured database data or RAG context provided.
- NEVER invent, assume, or generate any data that is not explicitly provided.
- Be conversational and helpful, but stay focused on SIS work.

CONVERSATION CONTEXT:
- You have access to previous messages in this conversation.
- Use the conversation history to understand context and answer follow-up questions.
- If the user refers to something from a previous message (like "that application" or "the survey I mentioned"),
  use the conversation history to identify what they're referring to.
- Maintain conversation continuity while staying within SIS domain.

HANDLING DIFFERENT TYPES OF QUERIES:
1. **Greetings and casual conversation** (hi, hello, how are you, thanks, etc.):
   - Respond warmly and briefly
   - Remind them of what you can help with
2. **General questions about your capabilities**:
   - Explain what you can do clearly
   - Mention surveys, applications (ISD/NISD/MERGE), field visits, workflow procedures
3. **SIS-specific queries with no data found**:
   - Explain that you don't have that specific information
   - Suggest what they can ask about instead
4. **SIS-specific queries with data**:
   - Present the data clearly using HTML tables for structured information
   - Be concise and professional

STRICT DATA RULES:
1. DO NOT generate example tables, field descriptions, or placeholder data.
2. DO NOT explain what an ISD/NISD/MERGE application "contains" unless RAG context says so.
3. DO NOT say "the following information is available for..." — only show actual data.
4. DO NOT use markdown tables (| --- |) — only plain text or HTML <table> tags.
5. If specific data is not available, acknowledge it and suggest alternatives.

When RAG context IS provided:
- Answer questions about procedures, rules, and workflow from the context only.
- Quote or summarise from the context — do not add information beyond it.

When structured data IS provided:
- Present it as-is in a clear, concise response.
- Use an HTML table only if the data has multiple rows or columns."""

    # Build conversation history section
    history_section = ""
    if chat_history and len(chat_history) > 0:
        history_lines = ["\n\nCONVERSATION HISTORY (for context):"]
        for msg in chat_history[-10:]:  # Last 10 messages max
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if len(content) > 500:
                content = content[:500] + "... [truncated]"
            history_lines.append(f"{role.upper()}: {content}")
        history_section = "\n".join(history_lines)

    structured_section = format_structured_data_for_llm(structured_data)
    context_section = f"\n\nRELEVANT DOCUMENT CONTEXT:\n{context}" if context else ""

    return (
        f"{system_instruction}"
        f"{history_section}"
        f"{structured_section}"
        f"{context_section}"
        f"\n\nUSER QUESTION:\n{query}"
        f"\n\nASSISTANT RESPONSE:"
    )


async def call_llama(prompt: str) -> str:
    """Call Llama model via Ollama (non-streaming)."""
    try:
        logger.info("Calling Ollama LLM...")
        response = llm.invoke(prompt)
        response_text = response.content if hasattr(response, "content") else str(response)
        response_text = response_text.strip()
        logger.info(f"LLM response generated ({len(response_text)} chars)")
        return response_text
    except Exception as e:
        logger.error(f"Error calling LLM: {e}")
        return "I apologize, but I encountered an error processing your request. Please try again."


async def call_llama_stream(prompt: str):
    """Call Llama model via Ollama with streaming."""
    try:
        logger.info("Calling Ollama LLM with streaming...")
        chunk_count = 0
        total_content = ""
        async for chunk in llm.astream(prompt):
            chunk_count += 1
            content = chunk.content if hasattr(chunk, "content") else str(chunk)
            if content:
                total_content += content
                yield content
            if chunk_count % 10 == 0:
                logger.debug(f"Streamed {chunk_count} chunks, {len(total_content)} chars so far")
        logger.info(f"LLM streaming complete: {chunk_count} chunks, {len(total_content)} total chars")
        if not total_content:
            logger.error("WARNING: LLM returned empty response!")
            yield "I apologize, but I received an empty response. Please try again."
    except Exception as e:
        logger.error(f"Error in LLM stream: {e}", exc_info=True)
        yield "I apologize, but I encountered an error processing your request. Please try again."


# ─────────────────────────────────────────────────────────────────────────────
# parse_intent — specific patterns before broad ones
#   "show me survey 145"  → survey_detail  (not all_surveys_in_jurisdiction)
#   "show all surveys"    → all_surveys_in_jurisdiction
# ─────────────────────────────────────────────────────────────────────────────
def parse_intent(message: str) -> str:
    """
    Parse user intent from message using keyword + fuzzy matching.
    Supports English, Tamil, and Tanglish. Tolerates minor typos.
    Order matters — most specific checks first.
    """
    # Strip leading list-item prefixes like "1.", "2)", "a-" etc.
    message = re.sub(r'^\s*\d+[\.\)\-]\s*', '', message)
    message = re.sub(r'^\s*[a-zA-Z][\.\)\-]\s*', '', message)

    msg = message.lower()
    words = re.findall(r'[\w\u0B80-\u0BFF]+', msg)

    def fuzzy_match(keyword: str, threshold: float = 0.82) -> bool:
        """
        True if keyword is an exact substring OR close enough to any word.
        Tamil/Unicode keywords and short tokens use exact-only to avoid false positives.
        """
        if keyword in msg:
            return True
        if len(keyword) <= 3 or any('\u0B80' <= c <= '\u0BFF' for c in keyword):
            return False
        for word in words:
            if SequenceMatcher(None, keyword, word).ratio() >= threshold:
                return True
        return False

    def has(keywords: list) -> bool:
        return any(fuzzy_match(kw) for kw in keywords)

    # ── keyword sets (English + Tamil) ───────────────────────────────
    ta_survey      = ["கணக்கெண்", "கணக்கு", "survey", "surveys", "survay", "suvery"]
    ta_subdivision = ["உட்பிரிவு", "உட்பிரிவுகள்", "subdivision", "subdivisions",
                      "sub-division", "sub-divisions", "subdiv"]
    ta_show        = ["காட்டு", "காண்பி", "பட்டியல்", "அனைத்தும்",
                      "show", "list", "all", "my", "display", "get"]
    ta_owner       = ["உரிமையாளர்", "சொந்தக்காரர்", "owner", "owners",
                      "ownership", "patta", "pattadar"]
    ta_pending     = ["நிலுவை", "நிலுவையில்", "காத்திருக்கும்",
                      "pending", "waiting", "pendig", "pendng"]
    ta_overdue     = ["காலதாமத", "காலதாமதமான", "தாமதம்",
                      "overdue", "late", "delayed", "overdew", "overdu"]
    ta_field_visit = ["கள ஆய்வு", "களஆய்வு", "வருகை",
                      "field", "visit", "visits", "scheduling", "schedule", "feild"]
    ta_workload    = ["பணிச்சுமை", "workload", "worklod", "work load"]
    ta_application = ["விண்ணப்பம்", "விண்ணப்பங்கள்",
                      "application", "applications", "aplications", "aplication"]
    ta_merge       = ["இணைப்பு", "இணைக்க",
                      "merge", "merging", "merged", "merg"]
    ta_status      = ["நிலை", "status", "statuss", "staus"]
    ta_area        = ["பரப்பளவு", "பரப்பு", "area", "arrea"]
    ta_ward        = ["வார்டு", "ward", "wards"]
    ta_block       = ["தொகுதி", "block", "blocks"]
    ta_next        = ["அடுத்த", "கிடைக்கும்", "next", "available", "nxt"]
    ta_detail      = ["விவரம்", "விவரங்கள்", "detail", "details", "info",
                      "contain", "included", "which", "what", "how", "land"]

    # SD-specific workflow intents
    if "sd" in msg:
        if any(w in msg for w in ["additional", "asking for", "requested", "information", "missing"]):
            return "sd_additional_info"
        if any(w in msg for w in ["encroachment", "flag", "receive", "noted"]):
            return "sd_encroachment_check"
        if any(w in msg for w in ["complete", "sketch", "field data", "readiness"]):
            return "sd_sketch_readiness"
        if any(w in msg for w in ["forward", "forwarded", "sent to"]):
            return "sd_forward_check"
        if any(w in msg for w in ["remark", "remarks", "comment", "recorded"]):
            return "sd_remarks"

    # Field visit specific workflow intents (check before general field_visits)
    if any(w in msg for w in ["field visit", "inspection", "schedule", "calendar", "visit date"]):
        if any(w in msg for w in ["date did i select", "select for this", "what date", "which date"]):
            return "fv_date_select"
        if any(w in msg for w in ["nearby", "same ward", "close by", "location", "neighborhood"]):
            return "fv_nearby_pending"
        if any(w in msg for w in ["already have scheduled", "scheduled in this", "scheduled this week", "scheduled"]):
            if "conflict" not in msg and "reschedule" not in msg and "overdue" not in msg and "unassigned" not in msg:
                return "fv_scheduled_this_week"
        if any(w in msg for w in ["recently rescheduled", "last 7 days", "rescheduled during"]):
            return "fv_recently_rescheduled"
        if any(w in msg for w in ["reschedule", "availability", "rescheduling"]):
            return "fv_reschedule_availability"
        if any(w in msg for w in ["deadline", "15-working-day", "15 working day"]):
            return "fv_deadline_check"
        if any(w in msg for w in ["overdue field visits", "exceeded the scheduled", "overdue"]):
            return "fv_overdue_inspections"
        if any(w in msg for w in ["unassigned", "not yet been assigned"]):
            return "fv_unassigned_awaiting"
        if any(w in msg for w in ["conflict", "conflicts", "overlap"]):
            return "fv_scheduling_conflicts"

    # 1. Application number pattern → application_status
    if re.search(r'\b(?:ISD|NISD|MERGE)/\w+/\d+/\d+\b|\bAPP-\d+-\d+\b', message, re.IGNORECASE):
        return "application_status"

    # 2. Overdue
    if has(ta_overdue):
        return "overdue_applications"

    # 3. Escalation
    if any(w in msg for w in ["escalat", "threshold", "approaching deadline", "deadline this week", "எஸ்கலேஷன்"]):
        return "escalation_check"

    # 4. Litigation
    if any(w in msg for w in ["litigation", "court", "legal", "flagged", "case flag", "வழக்கு", "நீதிமன்றம்"]):
        return "litigation_check"

    # 5. Sale deed
    if any(w in msg for w in ["sale deed", "deed number", "registered deed", "sub-registrar", "sub registrar", "deed verified"]):
        return "sale_deed_check"

    # 6. Joint owners
    if any(w in msg for w in ["joint owner", "joint owners", "co-owner", "co owner", "multiple owner", "shared ownership", "கூட்டு உரிமையாளர்"]):
        return "joint_owner_check"

    # 7. Active applications by taluk
    if "active" in msg and "taluk" in msg:
        return "active_applications_taluks"

    # 8. Highest priority
    if "priority" in msg and ("week" in msg or "highest" in msg):
        return "highest_priority_applications"

    # 9. Assigned today
    if "assigned" in msg and "today" in msg:
        return "assigned_today"

    # 10. Immediate action
    for kw1, kw2 in [
        ("immediate", "action"), ("urgent", ""), ("need attention", ""),
        ("action today", ""), ("critical", "application"),
        ("require action", ""), ("requires action", ""), ("deadline today", ""),
    ]:
        if kw1 in msg and (not kw2 or kw2 in msg):
            return "immediate_action"

    # 11. Awaiting field visit
    if "awaiting" in msg and ("visit" in msg or "inspection" in msg):
        return "awaiting_field_visit"

    # 12. Completion rate
    if "completion rate" in msg:
        return "completion_rate"

    # 13. Pending longest
    if "pending" in msg and "longest" in msg:
        return "pending_longest"

    # 14. Workload by type
    if "workload" in msg and "type" in msg:
        return "workload_by_type"

    # 15. Officer workload
    if has(ta_workload) or ("how many" in msg and "assigned" in msg):
        return "officer_workload"

    # 16. NISD vs ISD
    if "nisd" in msg and "isd" in msg:
        return "is_nisd_or_isd"

    # 17. Check documents
    if "document" in msg and any(w in msg for w in ["missing", "required", "all", "have"]):
        return "check_documents"

    # 18. Check sale deed (broader)
    if "deed" in msg or "sub-registrar" in msg:
        return "check_sale_deed"

    # 19. Town applications
    if "town" in msg and any(w in msg for w in ["pending", "applications", "show", "list"]):
        return "town_applications"

    # 20. Block applications (not ward surveys)
    if has(ta_block) and any(w in msg for w in ["pending", "applications", "show", "list"]):
        is_ward_surveys = has(ta_survey) and any(w in msg for w in ["show", "list", "all"])
        if not is_ward_surveys:
            return "block_applications"

    # 21. Jurisdiction summary
    if any(w in msg for w in ["jurisdiction", "my area", "assigned area", "coverage",
                               "my jurisdiction", "எனது பகுதி"]) and \
       not has(ta_survey) and not has(ta_application):
        return "jurisdiction_summary"

    # ── ISD Processing queries (before survey_owners / pending_applications) ──
    _sd_kws = ["sub-division", "subdivision", "sub division"]
    if any(w in msg for w in _sd_kws) or "patta transfer" in msg:
        if any(w in msg for w in ["patta transfer", "transfer order"]):
            return "isd_processing"
        if any(w in msg for w in ["latest action", "action taken", "each sub-division", "each subdivision"]):
            return "isd_processing"
        if "proposed" in msg:
            return "isd_processing"
        if "assigned" in msg and any(w in msg for w in ["number", "numbers"]):
            return "isd_processing"
        if "status" in msg and ("retrieve" in msg or "by sub" in msg):
            return "isd_processing"
        if any(w in msg for w in ["compare", "original"]) and "area" in msg:
            return "isd_processing"

    # 22. Specific survey number + keyword ← after merge/isd checks
    if re.search(r'\b\d{1,4}(?:/\d{1,4}[A-Za-z]*)?\b', msg) and (
        has(ta_survey) or has(ta_area) or has(ta_subdivision)
    ):
        if has(ta_owner):   return "survey_owners"
        if has(ta_next):    return "next_subdivision"
        return "survey_detail"

    # 23. Survey owners
    if has(ta_owner):
        return "survey_owners"

    # 24. Ward / block scoped surveys
    if has(ta_survey) and has(ta_ward)  and has(ta_show): return "ward_surveys"
    if has(ta_survey) and has(ta_block) and has(ta_show): return "block_surveys"

    # 25. All surveys in jurisdiction
    if has(ta_survey) and has(ta_show) and not has(ta_ward) and not has(ta_block) and not has(ta_owner):
        return "all_surveys_in_jurisdiction"

    # 26. Pending applications
    is_workflow_query = any(w in msg for w in ["workflow", "step", "guide", "procedure",
                                                "process", "work flow", "mean", "stand for",
                                                "difference", "explain"])
    if not is_workflow_query:
        is_type_query   = any(w in msg for w in ["isd", "nisd", "merge"])
        is_app_query    = has(ta_application)
        is_action_query = any(w in msg for w in ["how many", "howmuch", "show", "list",
                                                   "display", "view", "pending", "active",
                                                   "assigned", "count", "are there", "there are"])
        if is_type_query and is_action_query:
            return "pending_applications"
        if is_app_query and (is_action_query or is_type_query):
            return "pending_applications"
        if ("show" in msg or "list" in msg or "display" in msg) and "all" in msg and "application" in msg:
            return "pending_applications"
        if has(ta_pending) and not has(ta_ward):
            return "pending_applications"

    # 27. Typed application lists — nisd before isd (substring trap)
    if fuzzy_match("nisd") and has(ta_show + ta_application):
        return "nisd_applications"
    if fuzzy_match("isd") and has(ta_show + ta_application):
        return "isd_applications"

    # 28. Field visits
    if has(ta_field_visit) and not has(ta_application):
        return "field_visits"

    # 29. Survey detail (keyword, no number)
    if has(ta_survey) and any(w in msg for w in ["number", "no", "detail"]) \
       and not has(ta_show):
        return "survey_detail"

    # 30. Next subdivision
    if has(ta_subdivision) and has(ta_next):
        return "next_subdivision"

    # 31. Subdivision detail
    if has(ta_subdivision):
        if has(ta_survey) or any(c.isdigit() for c in msg):
            return "survey_detail"
        return "subdivision_detail"

    # 32. MERGE
    if has(ta_merge) and (has(ta_survey + ta_subdivision + ta_detail) or has(ta_area)):
        return "merge_info"
    if has(ta_merge) and has(ta_show + ta_application):
        return "merge_applications"
    if has(ta_merge):
        return "merge_info"

    # 33. Rejection
    if fuzzy_match("reject") or "நிராகரிப்பு" in msg:
        return "rejection_info"

    # 34. Taluk summary
    if "taluk" in msg and any(w in msg for w in ["summary", "all", "total", "how many"]) \
       and not has(ta_application):
        return "taluk_summary"

    return "general_query"


# ─────────────────────────────────────────────────────────────────────────────
# Entity extraction helpers (from current production version)
# ─────────────────────────────────────────────────────────────────────────────

def clean_message(message: str) -> str:
    """Remove list prefixes (like '1. ', '2) ', 'a- ') at the beginning of the message."""
    if not message:
        return ""
    cleaned = re.sub(r'^\s*\d+[\.\)\-]\s*', '', message)
    cleaned = re.sub(r'^\s*[a-zA-Z][\.\)\-]\s*', '', cleaned)
    return cleaned.strip()


def extract_survey_number(message: str) -> Optional[str]:
    """
    Extract survey number from message, handling list prefixes and survey keywords.
    Supports formats: "145", "145/1A", "survey no 145", "survey 145/2B".
    """
    cleaned = clean_message(message)

    # Keyword match first (e.g. "survey 145", "survey no 145/1A")
    keyword_match = re.search(
        r'\bsurvey(?:\s+(?:no|num|number|nos|numbers)(?:\.|\b)?)?(?:\s*[:\-#])?\s*(\d{1,4}(?:/\d{1,2}[A-Z]?)?)\b',
        cleaned, re.IGNORECASE
    )
    if keyword_match:
        return keyword_match.group(1)

    # Survey number with subdivision pattern (e.g. 145/1A)
    slash_match = re.search(r'\b\d{1,4}/\d{1,2}[A-Z]?\b', cleaned)
    if slash_match:
        return slash_match.group(0)

    # Fallback to any 1-4 digit number
    fallback_match = re.search(r'\b\d{1,4}\b', cleaned)
    if fallback_match:
        return fallback_match.group(0)

    return None


def extract_application_number(message: str) -> Optional[str]:
    """Extract application number (e.g. ISD/W1/2024/0001 or APP-2024-000015)."""
    cleaned = clean_message(message)
    app_match = re.search(
        r'\b(?:ISD|NISD|MERGE)/\w+/\d+/\d+\b|\bAPP-\d+-\d+\b',
        cleaned, re.IGNORECASE
    )
    if app_match:
        return app_match.group(0).upper()
    return None


def extract_ward_number(message: str) -> Optional[str]:
    """
    Extract ward number from message.
    Hierarchy: District → Taluk → Town → Ward → Block
    """
    cleaned = clean_message(message)

    match = re.search(
        r'\bward\s*(?:no(?:\.|\b)?)?\s*[:\-#]?\s*(\d+)\b',
        cleaned, re.IGNORECASE
    )
    if match:
        return match.group(1)

    skip_keywords = r'\b(?:block|survey|district|taluk|town)\s*(?:no(?:\.|\b)?)?\s*[:\-#]?\s*$'
    for m in re.finditer(r'\b\d+\b', cleaned):
        preceding = cleaned[:m.start()].lower()
        if not re.search(skip_keywords, preceding):
            return m.group(0)
    return None


def extract_block_number(message: str) -> Optional[str]:
    """
    Extract block number from message.
    Block is BELOW Ward in hierarchy. May be alphanumeric (e.g. "3", "B4").
    """
    cleaned = clean_message(message)

    match = re.search(
        r'\bblock\s*(?:no(?:\.|\b)?)?\s*[:\-#]?\s*([A-Z]?\d+)\b',
        cleaned, re.IGNORECASE
    )
    if match:
        return match.group(1).upper()

    skip_keywords = r'\b(?:ward|survey|district|taluk|town)\s*(?:no(?:\.|\b)?)?\s*[:\-#]?\s*$'
    for m in re.finditer(r'\b([A-Z]?\d+)\b', cleaned, re.IGNORECASE):
        preceding = cleaned[:m.start()].lower()
        if not re.search(skip_keywords, preceding):
            return m.group(1).upper()
    return None


def extract_town_name(message: str) -> Optional[str]:
    """
    Extract town name from message.
    Town is between Taluk and Ward in hierarchy.
    """
    cleaned = clean_message(message)

    match = re.search(
        r'\btown\s+(?:of\s+)?([A-Za-z\s]+?)(?:\s+town)?\b',
        cleaned, re.IGNORECASE
    )
    if match:
        return match.group(1).strip()

    match = re.search(r'([A-Za-z\s]+?)\s+town\b', cleaned, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return None


def extract_taluk_name(message: str) -> Optional[str]:
    """
    Extract taluk name from message.
    Taluk is directly below District in hierarchy.
    """
    cleaned = clean_message(message)

    match = re.search(
        r'\btaluk\s+(?:of\s+)?([A-Za-z\s]+?)(?:\s+taluk)?\b',
        cleaned, re.IGNORECASE
    )
    if match:
        return match.group(1).strip()

    match = re.search(r'([A-Za-z\s]+?)\s+taluk\b', cleaned, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return None


def extract_district_name(message: str) -> Optional[str]:
    """
    Extract district name from message.
    District is the top of the jurisdiction hierarchy.
    """
    cleaned = clean_message(message)

    match = re.search(
        r'\bdistrict\s+(?:of\s+)?([A-Za-z\s]+?)(?:\s+district)?\b',
        cleaned, re.IGNORECASE
    )
    if match:
        return match.group(1).strip()

    match = re.search(r'([A-Za-z\s]+?)\s+district\b', cleaned, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return None
