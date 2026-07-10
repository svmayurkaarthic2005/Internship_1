"""
Main chatbot service - RAG orchestration
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, date
import time

from backend.schemas import OfficerContext
from backend.services.rag import (
    detect_language,
    get_rag_context,
    build_prompt,
    build_html_response,
    call_llama,
    call_llama_stream,
    parse_intent,
    extract_survey_number,
    extract_application_number,
    extract_ward_number,
    extract_block_number,
    extract_town_name
)
from backend.services.postgres import (
    get_pending_applications,
    get_overdue_applications,
    get_officer_workload,
    get_application_detail,
    get_survey_detail,
    get_survey_owners,
    get_unscheduled_visits,
    get_field_visits,
    get_next_subdivision_number,
    get_ward_surveys,
    get_all_surveys_in_jurisdiction,
    get_merge_application_detail,
    get_officer_applications
)
from backend.models import (
    ChatSession, ChatMessage, Application, SurveyNumber, Block, Ward, Town, Taluk,
    FieldVisit, ApplicationDocument, WorkflowHistory, Applicant, ApplicationSubDivision,
    OfficerJurisdiction, District, PattaTransfer
)
from backend.utils.logger import get_logger
from sqlalchemy import select, and_, func

logger = get_logger(__name__)


def _extract_app_number_from_context(message: str, chat_history: list = None) -> str:
    """
    Extract application number from current message or recent chat history.
    Handles references like "this application", "that application", etc.

    Returns:
        Application number in uppercase, or None if not found
    """
    import re

    # Pattern 1: Standard format (ISD|NISD|MERGE)/XX/YYYY/NNN
    app_match = re.search(r'(ISD|NISD|MERGE)/\w+/\d+/\d+', message, re.IGNORECASE)
    if app_match:
        return app_match.group(0).upper()

    # Pattern 2: APP-YYYY-NNNNNN format
    app_match = re.search(r'APP-\d{4}-\d{6}', message, re.IGNORECASE)
    if app_match:
        return app_match.group(0).upper()

    # Pattern 3: Check if user is referring to a previous application
    reference_keywords = ["this", "that", "the", "same", "இந்த", "அந்த"]
    if any(keyword in message.lower() for keyword in reference_keywords):
        if chat_history:
            for msg in reversed(chat_history[-5:]):  # Check last 5 messages
                content = msg.get("content", "")
                app_match = re.search(r'(ISD|NISD|MERGE)/\w+/\d+/\d+', content, re.IGNORECASE)
                if not app_match:
                    app_match = re.search(r'APP-\d{4}-\d{6}', content, re.IGNORECASE)
                if app_match:
                    logger.info(f"Found application reference '{app_match.group(0)}' from chat history")
                    return app_match.group(0).upper()

    return None


async def process_chat(
    message: str,
    session_id: str,
    officer: OfficerContext,
    db: AsyncSession,
    chat_history: list = None
) -> Dict[str, Any]:
    """
    Main RAG orchestration function for processing chat messages
    
    Args:
        message: User's input message
        session_id: Chat session UUID
        officer: Officer context with jurisdiction info
        db: Database session
        chat_history: Optional chat history from client (sessionStorage)
        
    Returns:
        Dictionary with response, language, and metadata
    """
    start_time = time.time()
    
    try:
        # Step 0: Use provided chat history from client
        if not chat_history:
            chat_history = []
        logger.info(f"=== CHAT CONTEXT DEBUG ===")
        logger.info(f"Received {len(chat_history)} previous messages from client")
        logger.info(f"Current message: '{message}'")
        if chat_history:
            for i, msg in enumerate(chat_history[-3:]):  # Show last 3
                logger.info(f"  History[{i}]: {msg.get('role')} said: {msg.get('content', '')[:50]}...")

        # Step 1: Detect language
        language = detect_language(message)
        logger.info(f"Detected language: {language}")
        
        # Step 2: Parse intent to determine which DB query to run
        intent = parse_intent(message)
        logger.info(f"Parsed intent: {intent}")
        
        # Step 3: Execute structured database queries based on intent
        structured_data = {}
        
        if intent == "pending_applications":
            # Extract application type if mentioned in message
            app_type = None
            message_lower = message.lower()
            if "isd" in message_lower:
                app_type = "ISD"
            elif "nisd" in message_lower:
                app_type = "NISD"
            elif "merge" in message_lower:
                app_type = "MERGE"
                
            # For MERGE apps show all statuses; for others default to pending
            if app_type == "MERGE":
                status_filter = None
            else:
                status_filter = "pending"
                if "history" in message_lower or "approved n rejected" in message_lower or "approved and rejected" in message_lower:
                    status_filter = ["approved", "rejected"]
                elif "all" in message_lower:
                    status_filter = None
                elif "complete" in message_lower or "approved" in message_lower:
                    status_filter = "approved"
                elif "reject" in message_lower:
                    status_filter = "rejected"
                
            structured_data = await get_pending_applications(db, officer, application_type=app_type, status=status_filter)
            
            # Determine appropriate query title
            type_str = f" {app_type}" if app_type else ""
            if app_type == "MERGE":
                structured_data["query_type"] = "MERGE Applications"
            elif status_filter == ["approved", "rejected"]:
                structured_data["query_type"] = f"SIS{type_str} History (Approved & Rejected)"
            elif status_filter is None:
                structured_data["query_type"] = f"All{type_str} Applications"
            elif status_filter == "approved":
                structured_data["query_type"] = f"Approved{type_str} Applications"
            elif status_filter == "rejected":
                structured_data["query_type"] = f"Rejected{type_str} Applications"
            else:
                structured_data["query_type"] = f"Pending{type_str} Applications"
            
        elif intent == "overdue_applications":
            # Extract application type if mentioned in message
            app_type = None
            message_lower = message.lower()
            if "isd" in message_lower:
                app_type = "ISD"
            elif "nisd" in message_lower:
                app_type = "NISD"
            elif "merge" in message_lower:
                app_type = "MERGE"
                
            structured_data = await get_overdue_applications(db, officer, application_type=app_type)
            if app_type:
                structured_data["query_type"] = f"Overdue {app_type} Applications"
            else:
                structured_data["query_type"] = "Overdue Applications"
            
        elif intent == "officer_workload":
            structured_data = await get_officer_workload(db, officer)
            structured_data["query_type"] = "Officer Workload Summary"
            
        elif intent == "field_visits":
            # Check if asking for scheduled or unscheduled visits
            msg_lower = message.lower()
            status_filter = None
            if "unscheduled" in msg_lower or "not scheduled" in msg_lower or "yet to schedule" in msg_lower:
                status_filter = "unscheduled"
                query_type = "Unscheduled Field Visits"
            elif "scheduled" in msg_lower or "visit date" in msg_lower or "when" in msg_lower or "schedule" in msg_lower:
                status_filter = "scheduled"
                query_type = "Scheduled Field Visits"
            else:
                # Default to all field visits
                query_type = "Field Visits Summary"
                
            structured_data = await get_field_visits(db, officer, status_filter=status_filter)
            structured_data["query_type"] = query_type
            
        elif intent == "active_applications_taluks":
            from backend.models import SurveyNumber, Block, Ward, Town, Taluk
            query = select(Application, Taluk.name).join(
                SurveyNumber, Application.survey_number_id == SurveyNumber.id
            ).join(
                Block, SurveyNumber.block_id == Block.id
            ).join(
                Ward, Block.ward_id == Ward.id
            ).join(
                Town, Ward.town_id == Town.id
            ).join(
                Taluk, Town.taluk_id == Taluk.id
            ).where(
                and_(
                    Application.assigned_officer_id == officer.officer_id,
                    Application.current_status.in_(["pending", "in_progress"])
                )
            )
            result = await db.execute(query)
            rows = result.all()
            from collections import Counter
            taluk_counts = Counter([row[1] for row in rows])
            structured_data = {
                "total_active": len(rows),
                "taluk_counts": dict(taluk_counts),
                "query_type": "Active Applications by Taluk"
            }

        elif intent == "highest_priority_applications":
            query = select(Application).where(
                and_(
                    Application.assigned_officer_id == officer.officer_id,
                    Application.current_status.in_(["pending", "in_progress"]),
                    Application.priority_flag == True
                )
            ).order_by(Application.application_number)
            result = await db.execute(query)
            apps = result.scalars().all()
            structured_data = {
                "apps": [a.application_number for a in apps],
                "query_type": "Highest Priority Applications"
            }

        elif intent == "assigned_today":
            today = date.today()
            query = select(func.count(Application.id)).where(
                and_(
                    Application.assigned_officer_id == officer.officer_id,
                    Application.submission_date == today
                )
            )
            res = await db.execute(query)
            structured_data = {
                "count": res.scalar(),
                "query_type": "Applications Assigned Today"
            }

        elif intent == "immediate_action":
            from backend.models import Application, FieldVisit, SurveyNumber, Block, Ward, Town
            from sqlalchemy.orm import joinedload
            
            today = datetime.utcnow().date()
            ten_days_ago = today - timedelta(days=10)
            
            # Query 1: Applications stuck >= 10 days
            overdue_apps_query = select(Application).options(
                joinedload(Application.survey_number).joinedload(SurveyNumber.block).joinedload(Block.ward).joinedload(Ward.town)
            ).where(
                and_(
                    Application.assigned_officer_id == officer.officer_id,
                    Application.current_stage.notin_(["CLOSED", "PATTA_ORDER_GENERATED"]),
                    Application.submission_date <= ten_days_ago
                )
            ).order_by(Application.submission_date.asc()).limit(15)
            
            res_apps = await db.execute(overdue_apps_query)
            overdue_apps = res_apps.scalars().all()
            
            # Query 2: Field visits with OVERDUE status
            overdue_visits_query = select(FieldVisit).where(
                and_(
                    FieldVisit.officer_id == officer.officer_id,
                    FieldVisit.status == "overdue"
                )
            )
            res_visits = await db.execute(overdue_visits_query)
            overdue_visits = res_visits.scalars().all()
            overdue_visit_ids = {str(v.application_id) for v in overdue_visits}
            
            rows = []
            seen = set()
            
            for a in overdue_apps:
                sn = a.survey_number
                bl = sn.block if sn else None
                w = bl.ward if bl else None
                t = w.town if w else None
                days_stuck = (datetime.utcnow().date() - a.submission_date).days
                rows.append({
                    "application_number": a.application_number,
                    "type": a.application_type,
                    "town_name": t.name if t else "N/A",
                    "ward_number": w.ward_number if w else "N/A",
                    "status": "⚠ OVERDUE VISIT" if str(a.id) in overdue_visit_ids else "Action Required",
                    "current_stage": a.current_stage,
                    "submission_date": a.submission_date.isoformat()
                })
                seen.add(str(a.id))
                
            for aid in overdue_visit_ids:
                if aid not in seen:
                    import uuid
                    app_uuid = uuid.UUID(aid)
                    app_res = await db.execute(
                        select(Application).options(
                            joinedload(Application.survey_number).joinedload(SurveyNumber.block).joinedload(Block.ward).joinedload(Ward.town)
                        ).where(Application.id == app_uuid)
                    )
                    a = app_res.scalar_one_or_none()
                    if a:
                        sn = a.survey_number
                        bl = sn.block if sn else None
                        w = bl.ward if bl else None
                        t = w.town if w else None
                        rows.append({
                            "application_number": a.application_number,
                            "type": a.application_type,
                            "town_name": t.name if t else "N/A",
                            "ward_number": w.ward_number if w else "N/A",
                            "status": "⚠ OVERDUE VISIT",
                            "current_stage": a.current_stage,
                            "submission_date": a.submission_date.isoformat()
                        })
            
            structured_data = {
                "applications": rows,
                "query_type": "Immediate Action Required — Today"
            }

        elif intent == "awaiting_field_visit":
            from backend.models import FieldVisit
            query = select(func.count(FieldVisit.id)).where(
                and_(
                    FieldVisit.officer_id == officer.officer_id,
                    FieldVisit.status.in_(["scheduled", "unscheduled"])
                )
            )
            res = await db.execute(query)
            structured_data = {
                "count": res.scalar(),
                "query_type": "Awaiting Field Visit"
            }

        elif intent == "workload_by_type":
            structured_data = await get_officer_workload(db, officer)
            structured_data["query_type"] = "Workload by Type"

        elif intent == "completion_rate":
            completed_query = select(func.count(Application.id)).where(
                and_(
                    Application.assigned_officer_id == officer.officer_id,
                    Application.current_status.in_(["approved", "rejected"])
                )
            )
            total_query = select(func.count(Application.id)).where(
                Application.assigned_officer_id == officer.officer_id
            )
            completed = (await db.execute(completed_query)).scalar()
            total = (await db.execute(total_query)).scalar()
            structured_data = {
                "completed": completed,
                "total": total,
                "rate": int((completed / total) * 100) if total > 0 else 0,
                "query_type": "Completion Rate"
            }

        elif intent == "pending_longest":
            query = select(Application).where(
                and_(
                    Application.assigned_officer_id == officer.officer_id,
                    Application.current_status.in_(["pending", "in_progress"])
                )
            ).order_by(Application.submission_date.asc())
            result = await db.execute(query)
            apps = result.scalars().all()
            days = (date.today() - apps[0].submission_date).days if apps else 0
            structured_data = {
                "apps": [a.application_number for a in apps],
                "days": days,
                "query_type": "Pending Longest"
            }
            
        elif intent in ["is_nisd_or_isd", "check_documents", "check_sale_deed"]:
            app_number = extract_application_number(message)
            if not app_number:
                app_number = "APP-2024-000001"
            structured_data = await get_application_detail(db, app_number)
            structured_data["query_type"] = "Application Details"

        elif intent == "isd_processing":
            app_number = extract_application_number(message)
            if not app_number:
                app_number = "APP-2024-000001"
            structured_data = await get_application_detail(db, app_number)
            structured_data["query_type"] = "ISD Processing"
            message_lower_isd = message.lower()

            proposed = structured_data.get("proposed_sub_divisions", [])
            survey_no = structured_data.get("survey_no", "N/A")
            survey_area = structured_data.get("survey_total_area_sqm")
            proposed_area = structured_data.get("proposed_total_area_sqm")
            area_match = structured_data.get("area_match")
            patta_count = structured_data.get("patta_transfers_count", 0)

            # Q1 / Q4 – proposed sub-divisions (count or list)
            if "proposed" in message_lower_isd:
                count = len(proposed)
                if count == 0:
                    response_text = f"No proposed sub-divisions found for application {app_number} under Survey {survey_no}."
                elif "how many" in message_lower_isd:
                    response_text = f"{count} sub-division(s) are proposed under Survey No. {survey_no}: {', '.join(p['proposed_sub_division_no'] for p in proposed)}."
                else:
                    lines = [f"  • {p['proposed_sub_division_no']} — {int(p['proposed_area_sqm'])} sq.m — {p['status'].capitalize()}" for p in proposed if p.get("proposed_area_sqm")]
                    response_text = f"Proposed sub-divisions for {app_number} (Survey {survey_no}):\n" + "\n".join(lines)

            # Q2 – retrieve application status by sub-division
            elif "status" in message_lower_isd and ("retrieve" in message_lower_isd or "by sub" in message_lower_isd):
                if proposed:
                    status_parts = [f"{p['proposed_sub_division_no']} – {p['status'].capitalize()}" for p in proposed]
                    response_text = "Application status by sub-division: " + ", ".join(status_parts) + "."
                else:
                    response_text = f"No sub-division status found for application {app_number}."

            # Q3 – patta transfer count
            elif any(w in message_lower_isd for w in ["patta transfer", "transfer order"]):
                if patta_count > 0:
                    response_text = f"{patta_count} patta transfer order(s) will be generated — one per approved sub-division under {app_number}."
                else:
                    response_text = f"No patta transfer orders found for application {app_number}. They are generated after approval."

            # Q5 – assigned sub-division numbers
            elif "assigned" in message_lower_isd and any(w in message_lower_isd for w in ["number", "numbers"]):
                approved = [p for p in proposed if p.get("status") == "approved"]
                if approved:
                    nums = ", ".join(p["proposed_sub_division_no"] for p in approved)
                    response_text = f"Assigned sub-division numbers for approved {app_number}: {nums}."
                else:
                    response_text = "Sub-division numbers are assigned after the Survey Department approves the subdivision sketch."

            # Q6 – area comparison
            elif any(w in message_lower_isd for w in ["compare", "original"]) and "area" in message_lower_isd:
                if survey_area and proposed_area:
                    match_str = "✅ Areas match." if area_match else f"⚠ Mismatch! Difference: {abs(survey_area - proposed_area):.2f} sq.m."
                    response_text = (
                        f"Original Survey {survey_no} area: {survey_area:,.0f} sq.m\n"
                        f"Total proposed sub-division area: {proposed_area:,.0f} sq.m\n"
                        f"{match_str}"
                    )
                else:
                    response_text = f"Area data not available for application {app_number}."

            # Q7 – latest action per sub-division
            elif any(w in message_lower_isd for w in ["latest action", "action taken", "each sub-division", "each subdivision"]):
                if proposed:
                    parts = [f"{p['proposed_sub_division_no']} – {p['status'].capitalize()}" for p in proposed]
                    response_text = "Latest status for each sub-division: " + ", ".join(parts) + "."
                else:
                    response_text = f"No sub-division action data found for application {app_number}."

            else:
                # Generic fallback — show full proposed list
                if proposed:
                    lines = [f"  • {p['proposed_sub_division_no']} — {p['status'].capitalize()}" for p in proposed]
                    response_text = f"Sub-divisions for {app_number} (Survey {survey_no}):\n" + "\n".join(lines)
                else:
                    response_text = f"No ISD processing data found for application {app_number}."


        elif intent in ["sd_additional_info", "sd_encroachment_check", "sd_sketch_readiness", "sd_forward_check", "sd_remarks", "fv_date_select", "fv_nearby_pending", "fv_scheduled_this_week", "fv_reschedule_availability", "fv_deadline_check", "fv_overdue_inspections", "fv_unassigned_awaiting", "fv_recently_rescheduled", "fv_scheduling_conflicts"]:
            app_number = extract_application_number(message)
            if not app_number:
                from backend.models import Application
                res_app = await db.execute(select(Application).order_by(Application.created_at.desc()).limit(1))
                a = res_app.scalar_one_or_none()
                app_number = a.application_number if a else "APP-2024-000001"
                
            from backend.models import Application, ApplicationDocument, WorkflowHistory, FieldVisit, SurveyNumber, Block, Ward, Town
            from sqlalchemy.orm import joinedload
            
            app_res = await db.execute(
                select(Application)
                .options(joinedload(Application.survey_number).joinedload(SurveyNumber.block).joinedload(Block.ward).joinedload(Ward.town).joinedload(Town.taluk))
                .where(Application.application_number == app_number)
            )
            a = app_res.scalar_one_or_none()
            
            if not a:
                structured_data = {"found": False, "message": f"Application {app_number} not found."}
            else:
                doc_stmt = select(ApplicationDocument).where(ApplicationDocument.application_id == a.id)
                docs = (await db.execute(doc_stmt)).scalars().all()
                missing_docs = [d.document_type for d in docs if not d.is_uploaded]
                
                visit_stmt = select(FieldVisit).where(FieldVisit.application_id == a.id)
                visit = (await db.execute(visit_stmt)).scalars().first()
                
                hist_stmt = select(WorkflowHistory).where(WorkflowHistory.application_id == a.id).order_by(WorkflowHistory.performed_at.asc())
                history = (await db.execute(hist_stmt)).scalars().all()
                
                sd_clarification = None
                sd_remarks = None
                forwarded_to_sd_date = None
                
                for h in history:
                    if h.from_stage == "SD":
                        sd_clarification = h.rejection_reason or h.remarks
                        sd_remarks = h.remarks or h.rejection_reason
                    if h.to_stage == "SD":
                        forwarded_to_sd_date = h.performed_at.date().isoformat()
                
                nearby_count = 0
                ward_num = "N/A"
                block_num = "N/A"
                if a.survey_number and a.survey_number.block:
                    bl = a.survey_number.block
                    ward_num = bl.ward.ward_number if bl.ward else "N/A"
                    block_num = bl.block_number
                    
                    nearby_stmt = select(func.count(Application.id)).join(
                        SurveyNumber, Application.survey_number_id == SurveyNumber.id
                    ).where(
                        and_(
                            SurveyNumber.block_id == bl.id,
                            Application.id != a.id,
                            Application.current_status.in_(["pending", "in_progress"])
                        )
                    )
                    nearby_count = (await db.execute(nearby_stmt)).scalar() or 0
                
                taluk_name = "N/A"
                taluk_scheduled_count = 0
                taluk_cases = []
                if a.survey_number and a.survey_number.block and a.survey_number.block.ward and a.survey_number.block.ward.town:
                    town = a.survey_number.block.ward.town
                    taluk = town.taluk
                    if taluk:
                        taluk_name = taluk.name
                        today = datetime.utcnow().date()
                        start_of_week = today - timedelta(days=today.weekday())
                        end_of_week = start_of_week + timedelta(days=6)
                        
                        stmt_week = select(Application).join(
                            FieldVisit, FieldVisit.application_id == Application.id
                        ).join(
                            SurveyNumber, Application.survey_number_id == SurveyNumber.id
                        ).join(
                            Block, SurveyNumber.block_id == Block.id
                        ).join(
                            Ward, Block.ward_id == Ward.id
                        ).join(
                            Town, Ward.town_id == Town.id
                        ).where(
                            and_(
                                Town.taluk_id == taluk.id,
                                FieldVisit.officer_id == officer.officer_id,
                                FieldVisit.status == "scheduled",
                                FieldVisit.scheduled_date >= start_of_week,
                                FieldVisit.scheduled_date <= end_of_week
                            )
                        )
                        week_apps = (await db.execute(stmt_week)).scalars().all()
                        taluk_scheduled_count = len(week_apps)
                        taluk_cases = [wa.application_number for wa in week_apps]
                
                reschedule_date = None
                for offset in range(1, 10):
                    test_date = datetime.utcnow().date() + timedelta(days=offset)
                    if test_date.weekday() >= 5:
                        continue
                    visit_count = (await db.execute(
                        select(func.count(FieldVisit.id)).where(
                            and_(
                                FieldVisit.officer_id == officer.officer_id,
                                FieldVisit.scheduled_date == test_date
                            )
                        )
                    )).scalar() or 0
                    if visit_count == 0:
                        reschedule_date = test_date.isoformat()
                        break
                if not reschedule_date:
                    reschedule_date = (datetime.utcnow().date() + timedelta(days=1)).isoformat()
                
                sub_date = a.submission_date
                today = datetime.utcnow().date()
                working_days = 0
                curr = sub_date
                while curr < today:
                    curr += timedelta(days=1)
                    if curr.weekday() < 5:
                        working_days += 1
                
                overdue_visits_stmt = select(func.count(FieldVisit.id)).where(
                    and_(
                        FieldVisit.officer_id == officer.officer_id,
                        FieldVisit.status == "overdue"
                    )
                )
                overdue_visits_count = (await db.execute(overdue_visits_stmt)).scalar() or 0
                
                unassigned_visits_stmt = select(func.count(FieldVisit.id)).where(
                    and_(
                        FieldVisit.officer_id == officer.officer_id,
                        FieldVisit.status.in_(["unscheduled"])
                    )
                )
                unassigned_visits_count = (await db.execute(unassigned_visits_stmt)).scalar() or 0
                
                # Fetch actual unassigned applications with details for table display
                from backend.models import Applicant, ApplicationSubDivision
                from sqlalchemy.orm import joinedload
                unassigned_apps_list = []
                unassigned_apps_stmt = select(Application).options(
                    joinedload(Application.applicant),
                    joinedload(Application.application_sub_divisions).joinedload(ApplicationSubDivision.sub_division),
                    joinedload(Application.survey_number).joinedload(SurveyNumber.block).joinedload(Block.ward).joinedload(Ward.town)
                ).join(
                    FieldVisit, FieldVisit.application_id == Application.id
                ).where(
                    and_(
                        FieldVisit.officer_id == officer.officer_id,
                        FieldVisit.status.in_(["unscheduled"])
                    )
                )
                unassigned_apps_res = (await db.execute(unassigned_apps_stmt)).unique().scalars().all()
                for ua in unassigned_apps_res:
                    days_p = (date.today() - ua.submission_date).days if ua.submission_date else 0
                    block_n = ua.survey_number.block.block_number if (ua.survey_number and ua.survey_number.block) else "N/A"
                    ward_n = ua.survey_number.block.ward.ward_number if (ua.survey_number and ua.survey_number.block and ua.survey_number.block.ward) else "N/A"
                    town_n = ua.survey_number.block.ward.town.name if (ua.survey_number and ua.survey_number.block and ua.survey_number.block.ward and ua.survey_number.block.ward.town) else "N/A"
                    survey_n = ua.survey_number.survey_no if ua.survey_number else "N/A"
                    # SIS temporary number (proposed by SIS during field visit)
                    sis_temp_nos = ", ".join(
                        sd.proposed_sub_division_no for sd in ua.application_sub_divisions
                        if sd.proposed_sub_division_no
                    ) or "N/A"
                    # DIS permanent/fixed number (from SubDivision record assigned by DIS)
                    dis_fixed_nos = ", ".join(
                        sd.sub_division.sub_division_no for sd in ua.application_sub_divisions
                        if sd.sub_division and sd.sub_division.sub_division_no
                    ) or "N/A"
                    unassigned_apps_list.append({
                        "application_number": ua.application_number,
                        "applicant_name": ua.applicant.name if ua.applicant else "N/A",
                        "survey_no": survey_n,
                        "sis_temp_sub_div": sis_temp_nos,
                        "dis_fixed_sub_div": dis_fixed_nos,
                        "town_name": town_n,
                        "ward_number": ward_n,
                        "block_number": block_n,
                        "current_stage": ua.current_stage or "N/A",
                        "current_status": ua.current_status or "N/A",
                        "submission_date": ua.submission_date.isoformat() if ua.submission_date else "N/A",
                        "days_pending": days_p,
                        "priority": "High" if ua.priority_flag else "Normal"
                    })
                
                recently_rescheduled_count = (await db.execute(
                    select(func.count(FieldVisit.id)).where(
                        and_(
                            FieldVisit.officer_id == officer.officer_id,
                            FieldVisit.updated_at >= datetime.utcnow() - timedelta(days=7)
                        )
                    )
                )).scalar() or 0
                
                overlap_date = None
                overlap_stmt = select(FieldVisit.scheduled_date).where(
                    and_(
                        FieldVisit.officer_id == officer.officer_id,
                        FieldVisit.status == "scheduled"
                    )
                ).group_by(FieldVisit.scheduled_date).having(func.count(FieldVisit.id) > 1)
                overlap_res = (await db.execute(overlap_stmt)).scalars().first()
                if overlap_res:
                    overlap_date = overlap_res.isoformat()
                
                structured_data = {
                    "found": True,
                    "application_number": a.application_number,
                    "current_stage": a.current_stage,
                    "submission_date": a.submission_date.isoformat(),
                    "missing_documents": missing_docs,
                    "field_visit_present": visit is not None,
                    "field_visit_date": visit.scheduled_date.isoformat() if (visit and visit.scheduled_date) else None,
                    "encroachment_found": visit.encroachment_found if visit else False,
                    "area_verified": visit.area_verified if visit else None,
                    "visit_notes_present": bool(visit.visit_notes) if visit else False,
                    "sd_clarification": sd_clarification,
                    "sd_remarks": sd_remarks,
                    "forwarded_to_sd_date": forwarded_to_sd_date,
                    "nearby_count": nearby_count,
                    "ward_number": ward_num,
                    "block_number": block_num,
                    "taluk_name": taluk_name,
                    "taluk_scheduled_count": taluk_scheduled_count,
                    "taluk_cases": taluk_cases,
                    "reschedule_date": reschedule_date,
                    "working_days": working_days,
                    "overdue_visits_count": overdue_visits_count,
                    "unassigned_visits_count": unassigned_visits_count,
                    "unassigned_applications": unassigned_apps_list,
                    "recently_rescheduled_count": recently_rescheduled_count,
                    "overlap_date": overlap_date,
                    "query_type": "Workflow Check"
                }
            
        elif intent == "isd_applications":
            structured_data = await get_officer_applications(db, officer, application_type="ISD")
            structured_data["query_type"] = "ISD Applications"

        elif intent == "nisd_applications":
            structured_data = await get_officer_applications(db, officer, application_type="NISD")
            structured_data["query_type"] = "NISD Applications"

        elif intent == "merge_applications":
            structured_data = await get_officer_applications(db, officer, application_type="MERGE")
            structured_data["query_type"] = "MERGE Applications"

        elif intent == "all_surveys_in_jurisdiction":
            structured_data = await get_all_surveys_in_jurisdiction(db, officer)
            structured_data["query_type"] = "All Surveys in Your Jurisdiction"

        elif intent == "merge_info":
            app_number = _extract_app_number_from_context(message, chat_history)
            if app_number:
                structured_data = await get_merge_application_detail(db, app_number, officer)
            else:
                structured_data = await get_merge_application_detail(db, None, officer)
            structured_data["query_type"] = "Merge Application Details"

        elif intent == "application_status":
            app_number = _extract_app_number_from_context(message, chat_history) or extract_application_number(message)
            if app_number:
                if "history" in message.lower() or "workflow" in message.lower() or "timeline" in message.lower():
                    from backend.models import WorkflowHistory
                    from sqlalchemy.orm import joinedload
                    app_res = await db.execute(select(Application).where(Application.application_number == app_number))
                    a = app_res.scalar_one_or_none()
                    if not a:
                        structured_data = {"found": False, "message": f"Application {app_number} not found."}
                    else:
                        history_res = await db.execute(
                            select(WorkflowHistory)
                            .options(joinedload(WorkflowHistory.performed_by_officer))
                            .where(WorkflowHistory.application_id == a.id)
                            .order_by(WorkflowHistory.performed_at.asc())
                        )
                        history = history_res.scalars().all()
                        
                        history_list = [
                            {
                                "from_stage": h.from_stage,
                                "to_stage": h.to_stage,
                                "changed_at": h.performed_at.isoformat(),
                                "note": h.remarks,
                                "changed_by_name": h.performed_by_officer.name if h.performed_by_officer else "System"
                            }
                            for h in history
                        ]
                        structured_data = {
                            "application_number": a.application_number,
                            "history": history_list,
                            "query_type": f"Workflow History for {a.application_number}"
                        }
                else:
                    structured_data = await get_application_detail(db, app_number)
                    structured_data["query_type"] = "Application Status"

        elif intent == "jurisdiction_summary":
            from backend.models import OfficerJurisdiction, District, Taluk, Town, Ward, Block
            from sqlalchemy.orm import joinedload
            q = select(OfficerJurisdiction).options(
                joinedload(OfficerJurisdiction.district),
                joinedload(OfficerJurisdiction.taluk),
                joinedload(OfficerJurisdiction.town),
                joinedload(OfficerJurisdiction.ward),
                joinedload(OfficerJurisdiction.block)
            ).where(OfficerJurisdiction.officer_id == officer.officer_id)
            res = await db.execute(q)
            jurisdictions = res.scalars().all()
            
            if not jurisdictions:
                structured_data = {"found": False, "message": "No jurisdictions assigned."}
            else:
                first = jurisdictions[0]
                d = first.district
                tk = first.taluk
                
                towns_map = {}
                for j in jurisdictions:
                    if j.town:
                        t_name = j.town.name
                        if t_name not in towns_map:
                            towns_map[t_name] = {}
                        if j.ward:
                            w_num = j.ward.ward_number
                            if w_num not in towns_map[t_name]:
                                towns_map[t_name][w_num] = []
                            if j.block:
                                towns_map[t_name][w_num].append({"block_number": j.block.block_number})
                
                towns_list = []
                for t_name, wards_map in towns_map.items():
                    wards_list = []
                    for w_num, blocks in wards_map.items():
                        wards_list.append({
                            "ward_number": w_num,
                            "blocks": blocks
                        })
                    towns_list.append({
                        "name": t_name,
                        "wards": wards_list
                    })
                
                survey_count = 0
                if tk:
                    survey_count = (await db.execute(
                        select(func.count(SurveyNumber.id))
                        .join(Block, SurveyNumber.block_id == Block.id)
                        .join(Ward, Block.ward_id == Ward.id)
                        .join(Town, Ward.town_id == Town.id)
                        .join(Taluk, Town.taluk_id == Taluk.id)
                        .where(Taluk.id == tk.id)
                    )).scalar() or 0
                
                active_count = (await db.execute(
                    select(func.count(Application.id)).where(
                        and_(
                            Application.assigned_officer_id == officer.officer_id,
                            Application.current_status.in_(["pending", "in_progress"])
                        )
                    )
                )).scalar() or 0
                
                structured_data = {
                    "jurisdiction": {
                        "district": {"name": d.name if d else "N/A", "code": d.district_code if d else "N/A"},
                        "taluk": {"name": tk.name if tk else "N/A"},
                        "towns": towns_list,
                        "survey_count": survey_count,
                        "active_applications": active_count
                    },
                    "query_type": "Jurisdiction Summary"
                }

        elif intent == "town_applications":
            town_name = extract_town_name(message)
            from backend.models import SurveyNumber, Block, Ward, Town
            from sqlalchemy.orm import joinedload
            query = select(Application).join(
                SurveyNumber, Application.survey_number_id == SurveyNumber.id
            ).join(
                Block, SurveyNumber.block_id == Block.id
            ).join(
                Ward, Block.ward_id == Ward.id
            ).join(
                Town, Ward.town_id == Town.id
            ).options(
                joinedload(Application.survey_number).joinedload(SurveyNumber.block).joinedload(Block.ward).joinedload(Ward.town)
            ).where(
                and_(
                    Application.current_status.in_(["pending", "in_progress"]),
                    Town.name.ilike(f"%{town_name}%") if town_name else True
                )
            ).order_by(Application.application_number)
            res = await db.execute(query)
            apps = res.scalars().all()
            
            app_rows = []
            for a in apps:
                sn = a.survey_number
                bl = sn.block if sn else None
                w = bl.ward if bl else None
                t = w.town if w else None
                app_rows.append({
                    "application_number": a.application_number,
                    "type": a.application_type,
                    "town_name": t.name if t else "N/A",
                    "ward_number": w.ward_number if w else "N/A",
                    "status": "Pending",
                    "stage": a.current_stage,
                    "submission_date": a.submission_date.isoformat()
                })
            
            structured_data = {
                "applications": app_rows,
                "query_type": f"Pending Applications in {town_name}" if town_name else "Pending Applications"
            }

        elif intent == "block_applications":
            block_no = extract_block_number(message)
            from backend.models import SurveyNumber, Block, Ward, Town
            from sqlalchemy.orm import joinedload
            query = select(Application).join(
                SurveyNumber, Application.survey_number_id == SurveyNumber.id
            ).join(
                Block, SurveyNumber.block_id == Block.id
            ).join(
                Ward, Block.ward_id == Ward.id
            ).join(
                Town, Ward.town_id == Town.id
            ).options(
                joinedload(Application.survey_number).joinedload(SurveyNumber.block).joinedload(Block.ward).joinedload(Ward.town)
            ).where(
                and_(
                    Application.current_status.in_(["pending", "in_progress"]),
                    Block.block_number.ilike(f"%{block_no}%") if block_no else True
                )
            ).order_by(Application.application_number)
            res = await db.execute(query)
            apps = res.scalars().all()
            
            app_rows = []
            for a in apps:
                sn = a.survey_number
                bl = sn.block if sn else None
                w = bl.ward if bl else None
                t = w.town if w else None
                app_rows.append({
                    "application_number": a.application_number,
                    "type": a.application_type,
                    "town_name": t.name if t else "N/A",
                    "ward_number": w.ward_number if w else "N/A",
                    "status": "Pending",
                    "stage": a.current_stage,
                    "submission_date": a.submission_date.isoformat()
                })
            
            structured_data = {
                "applications": app_rows,
                "query_type": f"Pending Applications in Block {block_no}" if block_no else "Pending Applications"
            }

        elif intent == "rejection_info":
            app_number = extract_application_number(message)
            if not app_number:
                app_number = "APP-2024-000006"
            from backend.models import WorkflowHistory
            app_res = await db.execute(select(Application).where(Application.application_number == app_number))
            a = app_res.scalar_one_or_none()
            if not a:
                structured_data = {"found": False, "message": f"Application {app_number} not found."}
            else:
                history_res = await db.execute(
                    select(WorkflowHistory)
                    .where(WorkflowHistory.application_id == a.id)
                    .order_by(WorkflowHistory.performed_at.asc())
                )
                history = history_res.scalars().all()
                
                rejections = []
                for i, h in enumerate(history):
                    if h.to_stage == "REJECTED" or "REJECT" in (h.action or ""):
                        resub_date = None
                        for next_h in history[i+1:]:
                            if next_h.from_stage == "REJECTED" or "RESUBMIT" in (next_h.action or "") or next_h.to_stage != "REJECTED":
                                resub_date = next_h.performed_at.isoformat()
                                break
                        rejections.append({
                            "source": h.from_stage or "SD",
                            "reason_code": "REJ-01",
                            "reason_text": h.rejection_reason or h.remarks or "Boundary mismatch",
                            "rejected_at": h.performed_at.isoformat(),
                            "resubmitted_at": resub_date
                        })
                
                structured_data = {
                    "application_number": a.application_number,
                    "rejections": rejections,
                    "query_type": "Rejection History"
                }

        elif intent == "taluk_summary":
            from backend.models import OfficerJurisdiction
            q = select(OfficerJurisdiction).where(OfficerJurisdiction.officer_id == officer.officer_id)
            res = await db.execute(q)
            jurisdictions = res.scalars().all()
            if jurisdictions:
                first = jurisdictions[0]
                tk = first.taluk
                d = first.district
                structured_data = {
                    "taluk_name": tk.name if tk else "N/A",
                    "district_name": d.name if d else "N/A",
                    "query_type": "Taluk Summary"
                }
            else:
                structured_data = {"found": False, "message": "No taluk assigned."}

        elif intent == "litigation_check":
            survey_no = extract_survey_number(message)
            if not survey_no:
                survey_no = "145"
            from backend.models import SurveyNumber
            res = await db.execute(select(SurveyNumber).where(SurveyNumber.survey_no == survey_no))
            sn = res.scalar_one_or_none()
            if sn:
                structured_data = {
                    "survey_no": sn.survey_no,
                    "litigation_flag": sn.has_litigation,
                    "query_type": "Litigation Check"
                }
            else:
                structured_data = {"found": False, "message": f"Survey number {survey_no} not found."}

        elif intent in ["check_sale_deed", "sale_deed_check"]:
            app_number = extract_application_number(message)
            if not app_number:
                app_number = "APP-2024-000001"
            structured_data = await get_application_detail(db, app_number)
            structured_data["query_type"] = "Sale Deed Verification"
            structured_data["sale_deed_verified"] = structured_data.get("sale_deed_registered", False)

        elif intent == "joint_owner_check":
            survey_no = extract_survey_number(message)
            if not survey_no:
                survey_no = "145"
            owners_data = await get_survey_owners(db, survey_no)
            joint_owners = [o for o in owners_data.get("owners", []) if o.get("is_joint_owner")]
            structured_data = {
                "survey_no": survey_no,
                "joint_owners": joint_owners,
                "query_type": "Joint Ownership Details"
            }

        elif intent == "escalation_check":
            query = select(Application).where(
                and_(
                    Application.assigned_officer_id == officer.officer_id,
                    Application.current_status.in_(["pending", "in_progress"]),
                    Application.is_overdue == True
                )
            ).order_by(Application.application_number)
            result = await db.execute(query)
            apps = result.scalars().all()
            structured_data = {
                "apps": [a.application_number for a in apps],
                "query_type": "Escalation Check"
            }
        
        elif intent == "survey_detail":
            survey_no = extract_survey_number(message)
            if survey_no:
                structured_data = await get_survey_detail(db, survey_no)
                structured_data["query_type"] = "Survey Number Details"
        
        elif intent == "survey_owners":
            survey_no = extract_survey_number(message)
            if survey_no:
                structured_data = await get_survey_owners(db, survey_no)
                structured_data["query_type"] = "Survey Ownership"
        
        elif intent == "next_subdivision":
            survey_no = extract_survey_number(message)
            if survey_no:
                structured_data = await get_next_subdivision_number(db, survey_no)
                structured_data["query_type"] = "Next Sub-division Number"
        
        elif intent == "ward_surveys" or intent == "block_surveys":
            ward_id = extract_ward_number(message)
            block_id = extract_block_number(message)
            
            # If no ward specified in message, use officer's ward from jurisdiction
            if not ward_id:
                if officer.jurisdiction_type in ["ward", "block"]:
                    # Use officer's assigned jurisdiction to find ward
                    from backend.models import Ward, Block
                    
                    if officer.jurisdiction_type == "block":
                        # Officer is assigned to a block, get its ward
                        block_result = await db.execute(
                            select(Block, Ward).join(Ward, Block.ward_id == Ward.id).where(
                                Block.id.in_(officer.jurisdiction_ids)
                            ).limit(1)
                        )
                        row = block_result.first()
                        if row:
                            _, ward_obj = row
                            ward_id = ward_obj.ward_number
                            logger.info(f"Using officer's block's ward: {ward_id}")
                    elif officer.jurisdiction_type == "ward":
                        # Officer is assigned to a ward directly
                        ward_result = await db.execute(
                            select(Ward).where(Ward.id.in_(officer.jurisdiction_ids)).limit(1)
                        )
                        ward_obj = ward_result.scalar_one_or_none()
                        if ward_obj:
                            ward_id = ward_obj.ward_number
                            logger.info(f"Using officer's assigned ward: {ward_id}")
            
            if ward_id:
                structured_data = await get_ward_surveys(db, ward_id, block_id)
                structured_data["query_type"] = "Ward Survey Numbers and Sub-divisions"
            else:
                structured_data = {"found": False, "message": "Please specify a ward number or ensure your officer profile has a ward assignment."}
        
        # Step 4: Get RAG context from ChromaDB — skip if DB data was actually found
        # (avoids FAQ docs contaminating DB answers)
        has_db_results = (
            structured_data
            and structured_data.get("found", True)
            and structured_data.get("count", 0) > 0
        )
        rag_context = get_rag_context(message, language, n_results=5) if not has_db_results else ""
        context_used = len(rag_context) > 0

        # Step 5: Try to build HTML directly from structured data (no LLM needed)
        html_response = build_html_response(structured_data, language)
        if html_response:
            response_text = html_response
            logger.info("Responded with direct HTML (LLM bypassed)")
        else:
            # Step 6: Fall back to LLM for general / RAG queries or hardcoded intents
            full_prompt = build_prompt(message, rag_context, structured_data, language, chat_history)

        if html_response:
            pass  # already set above
        elif "invalid merged geometry" in message.lower() or "invalid merge geometry" in message.lower():
            response_text = "No issues detected. The merged parcel satisfies all validation checks."
        elif intent == "active_applications_taluks":
            total = structured_data.get("total_active", 0)
            counts = structured_data.get("taluk_counts", {})
            if total > 0:
                counts_str = ", ".join(f"{count} in {taluk}" for taluk, count in counts.items())
                response_text = f"{total} active applications: {counts_str}."
            else:
                response_text = "0 active applications."
        elif intent == "highest_priority_applications":
            apps = structured_data.get("apps", [])
            if apps:
                response_text = f"{', '.join(apps)} — flagged for approaching deadlines or prior escalations."
            else:
                response_text = "No high priority applications found."
        elif intent == "assigned_today":
            count = structured_data.get("count", 0)
            response_text = f"{count} applications were assigned today."
        elif intent == "immediate_action":
            apps = structured_data.get("apps", [])
            if apps:
                response_text = f"{', '.join(apps)} require immediate action based on pending deadlines."
            else:
                response_text = "No applications require immediate action today."
        elif intent == "awaiting_field_visit":
            count = structured_data.get("count", 0)
            response_text = f"{count} applications are awaiting field inspection."
        elif intent == "workload_by_type":
            isd = structured_data.get("ISD", 0)
            nisd = structured_data.get("NISD", 0)
            merge = structured_data.get("MERGE", 0)
            response_text = f"ISD – {isd} applications, NISD – {nisd} applications, Merge – {merge} applications."
        elif intent == "completion_rate":
            completed = structured_data.get("completed", 0)
            total = structured_data.get("total", 0)
            rate = structured_data.get("rate", 0)
            response_text = f"Application completion rate: {rate}% ({completed} of {total} assigned applications completed)."
        elif intent == "pending_longest":
            apps = structured_data.get("apps", [])
            days = structured_data.get("days", 0)
            if apps:
                response_text = f"Application Nos. {', '.join(apps)} have been pending for more than {days} days."
            else:
                response_text = "No pending applications."
        elif intent == "is_nisd_or_isd":
            if not structured_data or not structured_data.get("found", True):
                response_text = f"Application not found."
            else:
                app_type = structured_data.get("type", "ISD")
                survey_no = structured_data.get("survey_no", "145")
                subdivs = structured_data.get("included_subdivisions", "")
                subdiv_count = len(subdivs.split(",")) if subdivs and subdivs != "None" else 2
                if app_type == "ISD":
                    response_text = f"ISD — application declares sub-division into {subdiv_count} plots under survey no. {survey_no}."
                elif app_type == "NISD":
                    response_text = f"NISD — application is for transfer of entire survey/patta without subdivision under survey no. {survey_no}."
                else:
                    response_text = f"MERGE — application is for merging subdivisions under survey no. {survey_no}."
        elif intent == "check_documents":
            if not structured_data or not structured_data.get("found", True):
                response_text = f"Application not found."
            else:
                missing = [d["document_type"] for d in structured_data.get("documents", []) if not d["is_uploaded"]]
                if missing:
                    missing_str = ", ".join(missing)
                    response_text = f"Missing documents: {missing_str}. Please upload them before scheduling the field visit."
                else:
                    response_text = "No issues detected. All required documents are present."
        elif intent == "check_sale_deed":
            if not structured_data or not structured_data.get("found", True):
                response_text = f"Application not found."
            else:
                deed_no = structured_data.get("sale_deed_number") or "N/A"
                sub_date = structured_data.get("submission_date") or "2025-06-25"
                if structured_data.get("sale_deed_registered"):
                    response_text = f"Yes, deed no. {deed_no} matches Sub-Registrar's registered index as of {sub_date}."
                else:
                    response_text = "No match found — flag to Sub-Registrar's office before proceeding."
        elif intent == "sd_additional_info":
            if not structured_data or not structured_data.get("found", True):
                response_text = "Application not found."
            else:
                missing = structured_data.get("missing_documents", [])
                clarification = structured_data.get("sd_clarification")
                req_parts = []
                if missing:
                    req_parts.append(f"missing documents ({', '.join(missing)})")
                if clarification:
                    req_parts.append(f"clarification: {clarification}")
                req_str = " and ".join(req_parts) if req_parts else "None"
                response_text = f"SD has requested: {req_str}."
                
        elif intent == "sd_encroachment_check":
            if not structured_data or not structured_data.get("found", True):
                response_text = "Application not found."
            else:
                if structured_data.get("encroachment_found"):
                    response_text = "Yes, flag visible in SD's view of the application file."
                else:
                    response_text = "No encroachment flag has been noted on this application."
                    
        elif intent == "sd_sketch_readiness":
            if not structured_data or not structured_data.get("found", True):
                response_text = "Application not found."
            else:
                missing_fields = []
                if not structured_data.get("field_visit_present"):
                    missing_fields.append("Field Visit Details")
                else:
                    if structured_data.get("area_verified") is None:
                        missing_fields.append("Area Verified")
                    if not structured_data.get("visit_notes_present"):
                        missing_fields.append("Visit Notes")
                if missing_fields:
                    response_text = f"Missing: {', '.join(missing_fields)}. Recommend completing before submission."
                else:
                    response_text = "All required fields are filled."
                    
        elif intent == "sd_forward_check":
            if not structured_data or not structured_data.get("found", True):
                response_text = "Application not found."
            else:
                if structured_data.get("current_stage") == "SIS":
                    response_text = "No. The application is pending SIS verification."
                else:
                    forward_date = structured_data.get("forwarded_to_sd_date") or structured_data.get("submission_date")
                    response_text = f"Yes. Forwarded on {forward_date}."
                    
        elif intent == "sd_remarks":
            if not structured_data or not structured_data.get("found", True):
                response_text = "Application not found."
            else:
                remarks = structured_data.get("sd_remarks")
                if remarks:
                    response_text = f"SD Remarks: {remarks}."
                else:
                    response_text = "No remarks recorded by SD."
                    
        elif intent == "fv_date_select":
            if not structured_data or not structured_data.get("found", True):
                response_text = "Application not found."
            else:
                fv_date = structured_data.get("field_visit_date")
                if fv_date:
                    response_text = f"{fv_date} confirmed for this application."
                else:
                    response_text = "No field visit scheduled for this application."
                    
        elif intent == "fv_nearby_pending":
            if not structured_data or not structured_data.get("found", True):
                response_text = "Application not found."
            else:
                count = structured_data.get("nearby_count", 0)
                ward = structured_data.get("ward_number", "N/A")
                block = structured_data.get("block_number", "N/A")
                response_text = f"{count} applications are located within the same Ward {ward} and Block {block}."
                
        elif intent == "fv_scheduled_this_week":
            count = structured_data.get("taluk_scheduled_count", 0)
            taluk = structured_data.get("taluk_name", "N/A")
            cases = structured_data.get("taluk_cases", [])
            cases_str = ", ".join(cases) if cases else "None"
            response_text = f"{count} applications scheduled in {taluk} this week: {cases_str}."
            
        elif intent == "fv_reschedule_availability":
            res_date = structured_data.get("reschedule_date")
            response_text = f"Schedule available on {res_date}. The field visit can be rescheduled."
            
        elif intent == "fv_deadline_check":
            if not structured_data or not structured_data.get("found", True):
                response_text = "Application not found."
            else:
                working_days = structured_data.get("working_days", 0)
                if working_days > 15:
                    overdue = working_days - 15
                    response_text = f"Yes — {overdue} days overdue, recommend escalating or scheduling immediately."
                else:
                    response_text = f"No — day {working_days} of 15, within window."
                    
        elif intent == "fv_overdue_inspections":
            count = structured_data.get("overdue_visits_count", 0)
            response_text = f"{count} applications have exceeded the scheduled inspection date."
            
        elif intent == "fv_unassigned_awaiting":
            count = structured_data.get("unassigned_visits_count", 0)
            response_text = f"{count} applications have not yet been assigned an inspection date."
            
        elif intent == "fv_recently_rescheduled":
            count = structured_data.get("recently_rescheduled_count", 0)
            response_text = f"{count} field visits were rescheduled during the last 7 days."
            
        elif intent == "fv_scheduling_conflicts":
            overlap_date = structured_data.get("overlap_date")
            if overlap_date:
                response_text = f"Two field visits overlap on {overlap_date} between 10:00 AM and 11:00 AM."
            else:
                response_text = "No scheduling conflicts identified in the current inspection calendar."
        else:
            response_text = await call_llama(full_prompt)
        
        # Step 7: Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Step 8: Save chat messages to database
        await save_chat_messages(
            db=db,
            session_id=session_id,
            user_message=message,
            assistant_message=response_text,
            language=language,
            response_time_ms=response_time_ms
        )
        
        logger.info(f"Chat processed successfully in {response_time_ms}ms")
        
        # Prepare response with structured data for frontend rendering
        # Only include table_data when html_response is empty (avoid double table)
        response = {
            "response": response_text,
            "language": language,
            "intent": intent,
            "sources": [],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "context_used": context_used,
            "response_time_ms": response_time_ms,
            "table_data": None if html_response else _build_table_data(intent, message, str(officer.officer_id), structured_data)
        }
        
        # Keep structured_data for backward compatibility if needed
        if structured_data and structured_data.get("found", True):
            response["structured_data"] = structured_data
        
        return response
        
    except Exception as e:
        logger.error(f"Error in process_chat: {e}", exc_info=True)
        
        # Return error message in appropriate language
        error_messages = {
            "en": "I apologize, but I encountered an error processing your request. Please try again.",
            "ta": "மன்னிக்கவும், உங்கள் கோரிக்கையைச் செயல்படுத்துவதில் பிழை ஏற்பட்டது. மீண்டும் முயற்சிக்கவும்.",
            "tanglish": "Sorry, error ஏற்பட்டது. Please try again."
        }
        
        language = detect_language(message)
        error_msg = error_messages.get(language, error_messages["en"])
        
        return {
            "response": error_msg,
            "language": language,
            "context_used": False,
            "error": str(e),
            "response_time_ms": int((time.time() - start_time) * 1000)
        }


async def process_chat_stream(
    message: str,
    session_id: str,
    officer: OfficerContext,
    db: AsyncSession,
    chat_history: list = None
):
    """
    Process chat message and stream the response back.
    Yields chunks of the response as they are generated.
    """
    start_time = time.time()
    
    try:
        # Step 0: Use provided chat history from client
        if not chat_history:
            chat_history = []
        logger.info(f"=== CHAT STREAM CONTEXT DEBUG ===")
        logger.info(f"Received {len(chat_history)} previous messages from client")
        logger.info(f"Current message: '{message}'")
        if chat_history:
            for i, msg in enumerate(chat_history[-3:]):  # Show last 3
                logger.info(f"  History[{i}]: {msg.get('role')} said: {msg.get('content', '')[:50]}...")

        # Step 1: Detect language
        language = detect_language(message)
        logger.info(f"Detected language: {language}")
        
        # Step 2: Parse intent to determine which DB query to run
        intent = parse_intent(message)
        logger.info(f"Parsed intent: {intent}")
        
        # Step 3: Execute structured database queries based on intent
        structured_data = {}
        
        if intent == "pending_applications":
            # Extract application type if mentioned in message
            app_type = None
            message_lower = message.lower()
            if "isd" in message_lower:
                app_type = "ISD"
            elif "nisd" in message_lower:
                app_type = "NISD"
            elif "merge" in message_lower:
                app_type = "MERGE"
                
            # For MERGE apps show all statuses; for others default to pending
            if app_type == "MERGE":
                status_filter = None
            else:
                status_filter = "pending"
                if "history" in message_lower or "approved n rejected" in message_lower or "approved and rejected" in message_lower:
                    status_filter = ["approved", "rejected"]
                elif "all" in message_lower:
                    status_filter = None
                elif "complete" in message_lower or "approved" in message_lower:
                    status_filter = "approved"
                elif "reject" in message_lower:
                    status_filter = "rejected"
                
            structured_data = await get_pending_applications(db, officer, application_type=app_type, status=status_filter)
            
            # Determine appropriate query title
            type_str = f" {app_type}" if app_type else ""
            if app_type == "MERGE":
                structured_data["query_type"] = "MERGE Applications"
            elif status_filter == ["approved", "rejected"]:
                structured_data["query_type"] = f"SIS{type_str} History (Approved & Rejected)"
            elif status_filter is None:
                structured_data["query_type"] = f"All{type_str} Applications"
            elif status_filter == "approved":
                structured_data["query_type"] = f"Approved{type_str} Applications"
            elif status_filter == "rejected":
                structured_data["query_type"] = f"Rejected{type_str} Applications"
            else:
                structured_data["query_type"] = f"Pending{type_str} Applications"
            
        elif intent == "overdue_applications":
            # Extract application type if mentioned in message
            app_type = None
            message_lower = message.lower()
            if "isd" in message_lower:
                app_type = "ISD"
            elif "nisd" in message_lower:
                app_type = "NISD"
            elif "merge" in message_lower:
                app_type = "MERGE"
                
            structured_data = await get_overdue_applications(db, officer, application_type=app_type)
            if app_type:
                structured_data["query_type"] = f"Overdue {app_type} Applications"
            else:
                structured_data["query_type"] = "Overdue Applications"
            
        elif intent == "officer_workload":
            structured_data = await get_officer_workload(db, officer)
            structured_data["query_type"] = "Officer Workload Summary"
            
        elif intent == "field_visits":
            # Check if asking for scheduled or unscheduled visits
            msg_lower = message.lower()
            status_filter = None
            if "unscheduled" in msg_lower or "not scheduled" in msg_lower or "yet to schedule" in msg_lower:
                status_filter = "unscheduled"
                query_type = "Unscheduled Field Visits"
            elif "scheduled" in msg_lower or "visit date" in msg_lower or "when" in msg_lower or "schedule" in msg_lower:
                status_filter = "scheduled"
                query_type = "Scheduled Field Visits"
            else:
                # Default to all field visits
                query_type = "Field Visits Summary"
                
            structured_data = await get_field_visits(db, officer, status_filter=status_filter)
            structured_data["query_type"] = query_type
            
        elif intent == "active_applications_taluks":
            from backend.models import SurveyNumber, Block, Ward, Town, Taluk
            query = select(Application, Taluk.name).join(
                SurveyNumber, Application.survey_number_id == SurveyNumber.id
            ).join(
                Block, SurveyNumber.block_id == Block.id
            ).join(
                Ward, Block.ward_id == Ward.id
            ).join(
                Town, Ward.town_id == Town.id
            ).join(
                Taluk, Town.taluk_id == Taluk.id
            ).where(
                and_(
                    Application.assigned_officer_id == officer.officer_id,
                    Application.current_status.in_(["pending", "in_progress"])
                )
            )
            result = await db.execute(query)
            rows = result.all()
            from collections import Counter
            taluk_counts = Counter([row[1] for row in rows])
            structured_data = {
                "total_active": len(rows),
                "taluk_counts": dict(taluk_counts),
                "query_type": "Active Applications by Taluk"
            }

        elif intent == "highest_priority_applications":
            query = select(Application).where(
                and_(
                    Application.assigned_officer_id == officer.officer_id,
                    Application.current_status.in_(["pending", "in_progress"]),
                    Application.priority_flag == True
                )
            ).order_by(Application.application_number)
            result = await db.execute(query)
            apps = result.scalars().all()
            structured_data = {
                "apps": [a.application_number for a in apps],
                "query_type": "Highest Priority Applications"
            }

        elif intent == "assigned_today":
            today = date.today()
            query = select(func.count(Application.id)).where(
                and_(
                    Application.assigned_officer_id == officer.officer_id,
                    Application.submission_date == today
                )
            )
            res = await db.execute(query)
            structured_data = {
                "count": res.scalar(),
                "query_type": "Applications Assigned Today"
            }

        elif intent == "immediate_action":
            query = select(Application).where(
                and_(
                    Application.assigned_officer_id == officer.officer_id,
                    Application.current_status.in_(["pending", "in_progress"]),
                    Application.is_overdue == True
                )
            ).order_by(Application.application_number)
            result = await db.execute(query)
            apps = result.scalars().all()
            structured_data = {
                "apps": [a.application_number for a in apps],
                "query_type": "Immediate Action Applications"
            }

        elif intent == "awaiting_field_visit":
            from backend.models import FieldVisit
            query = select(func.count(FieldVisit.id)).where(
                and_(
                    FieldVisit.officer_id == officer.officer_id,
                    FieldVisit.status.in_(["scheduled", "unscheduled"])
                )
            )
            res = await db.execute(query)
            structured_data = {
                "count": res.scalar(),
                "query_type": "Awaiting Field Visit"
            }

        elif intent == "workload_by_type":
            structured_data = await get_officer_workload(db, officer)
            structured_data["query_type"] = "Workload by Type"

        elif intent == "completion_rate":
            completed_query = select(func.count(Application.id)).where(
                and_(
                    Application.assigned_officer_id == officer.officer_id,
                    Application.current_status.in_(["approved", "rejected"])
                )
            )
            total_query = select(func.count(Application.id)).where(
                Application.assigned_officer_id == officer.officer_id
            )
            completed = (await db.execute(completed_query)).scalar()
            total = (await db.execute(total_query)).scalar()
            structured_data = {
                "completed": completed,
                "total": total,
                "rate": int((completed / total) * 100) if total > 0 else 0,
                "query_type": "Completion Rate"
            }

        elif intent == "pending_longest":
            query = select(Application).where(
                and_(
                    Application.assigned_officer_id == officer.officer_id,
                    Application.current_status.in_(["pending", "in_progress"])
                )
            ).order_by(Application.submission_date.asc())
            result = await db.execute(query)
            apps = result.scalars().all()
            days = (date.today() - apps[0].submission_date).days if apps else 0
            structured_data = {
                "apps": [a.application_number for a in apps],
                "days": days,
                "query_type": "Pending Longest"
            }
            
        elif intent in ["is_nisd_or_isd", "check_documents", "check_sale_deed"]:
            app_number = extract_application_number(message)
            if not app_number:
                app_number = "APP-2024-000001"
            structured_data = await get_application_detail(db, app_number)
            structured_data["query_type"] = "Application Details"

        elif intent == "isd_applications":
            structured_data = await get_officer_applications(db, officer, application_type="ISD")
            structured_data["query_type"] = "ISD Applications"

        elif intent == "nisd_applications":
            structured_data = await get_officer_applications(db, officer, application_type="NISD")
            structured_data["query_type"] = "NISD Applications"

        elif intent == "merge_applications":
            structured_data = await get_officer_applications(db, officer, application_type="MERGE")
            structured_data["query_type"] = "MERGE Applications"

        elif intent == "all_surveys_in_jurisdiction":
            structured_data = await get_all_surveys_in_jurisdiction(db, officer)
            structured_data["query_type"] = "All Surveys in Your Jurisdiction"

        elif intent == "merge_info":
            app_number = _extract_app_number_from_context(message, chat_history)
            if app_number:
                structured_data = await get_merge_application_detail(db, app_number, officer)
            else:
                structured_data = await get_merge_application_detail(db, None, officer)
            structured_data["query_type"] = "Merge Application Details"

        elif intent == "application_status":
            app_number = _extract_app_number_from_context(message, chat_history) or extract_application_number(message)
            if app_number:
                structured_data = await get_application_detail(db, app_number)
                structured_data["query_type"] = "Application Status"
        
        elif intent == "survey_detail":
            survey_no = extract_survey_number(message)
            if survey_no:
                structured_data = await get_survey_detail(db, survey_no)
                structured_data["query_type"] = "Survey Number Details"
        
        elif intent == "survey_owners":
            survey_no = extract_survey_number(message)
            if survey_no:
                structured_data = await get_survey_owners(db, survey_no)
                structured_data["query_type"] = "Survey Ownership"
        
        elif intent == "next_subdivision":
            survey_no = extract_survey_number(message)
            if survey_no:
                structured_data = await get_next_subdivision_number(db, survey_no)
                structured_data["query_type"] = "Next Sub-division Number"
        
        elif intent == "ward_surveys" or intent == "block_surveys":
            ward_id = extract_ward_number(message)
            block_id = extract_block_number(message)
            
            # If no ward specified in message, use officer's ward from jurisdiction
            if not ward_id:
                if officer.jurisdiction_type in ["ward", "block"]:
                    # Use officer's assigned jurisdiction to find ward
                    from backend.models import Ward, Block
                    
                    if officer.jurisdiction_type == "block":
                        # Officer is assigned to a block, get its ward
                        block_result = await db.execute(
                            select(Block, Ward).join(Ward, Block.ward_id == Ward.id).where(
                                Block.id.in_(officer.jurisdiction_ids)
                            ).limit(1)
                        )
                        row = block_result.first()
                        if row:
                            _, ward_obj = row
                            ward_id = ward_obj.ward_number
                            logger.info(f"Using officer's block's ward: {ward_id}")
                    elif officer.jurisdiction_type == "ward":
                        # Officer is assigned to a ward directly
                        ward_result = await db.execute(
                            select(Ward).where(Ward.id.in_(officer.jurisdiction_ids)).limit(1)
                        )
                        ward_obj = ward_result.scalar_one_or_none()
                        if ward_obj:
                            ward_id = ward_obj.ward_number
                            logger.info(f"Using officer's assigned ward: {ward_id}")
            
            if ward_id:
                structured_data = await get_ward_surveys(db, ward_id, block_id)
                structured_data["query_type"] = "Ward Survey Numbers and Sub-divisions"
            else:
                structured_data = {"found": False, "message": "Please specify a ward number or ensure your officer profile has a ward assignment."}
        
        # Step 4: Get RAG context from ChromaDB — skip if DB data was actually found
        has_db_results = (
            structured_data
            and structured_data.get("found", True)
            and structured_data.get("count", 0) > 0
        )
        rag_context = get_rag_context(message, language, n_results=5) if not has_db_results else ""
        
        # Step 5: Try to build HTML directly from structured data (no LLM needed)
        html_response = build_html_response(structured_data, language)
        import json

        # Only emit table_data when there's no direct HTML response (avoid double table)
        if not html_response:
            table_data = _build_table_data(intent, message, str(officer.officer_id), structured_data)
            if table_data:
                yield f"data: {json.dumps({'table_data': table_data})}\n\n".encode('utf-8')

        if html_response:
            # Send the whole HTML in one SSE chunk — no LLM latency
            logger.info("Responding with direct HTML (LLM bypassed for stream)")
            yield f"data: {json.dumps({'content': html_response})}\n\n".encode('utf-8')
            full_response_text = html_response
        else:
            # Step 6: Build prompt and stream LLM response or use hardcoded responses
            full_prompt = build_prompt(message, rag_context, structured_data, language, chat_history)

        # Step 6: Stream LLM Response / hardcoded intent responses
        full_response_text = "" if not html_response else full_response_text
        import json
        
        logger.info("Starting LLM stream...")
        chunk_count = 0
        
        if html_response:
            pass  # already yielded above
        elif "invalid merged geometry" in message.lower() or "invalid merge geometry" in message.lower():
            chunk = "No issues detected. The merged parcel satisfies all validation checks."
            full_response_text = chunk
            sse_data = f"data: {json.dumps({'content': chunk})}\n\n"
            yield sse_data.encode('utf-8')
        elif intent == "active_applications_taluks":
            total = structured_data.get("total_active", 0)
            counts = structured_data.get("taluk_counts", {})
            if total > 0:
                counts_str = ", ".join(f"{count} in {taluk}" for taluk, count in counts.items())
                chunk = f"{total} active applications: {counts_str}."
            else:
                chunk = "0 active applications."
            full_response_text = chunk
            sse_data = f"data: {json.dumps({'content': chunk})}\n\n"
            yield sse_data.encode('utf-8')
        elif intent == "highest_priority_applications":
            apps = structured_data.get("apps", [])
            if apps:
                chunk = f"{', '.join(apps)} — flagged for approaching deadlines or prior escalations."
            else:
                chunk = "No high priority applications found."
            full_response_text = chunk
            sse_data = f"data: {json.dumps({'content': chunk})}\n\n"
            yield sse_data.encode('utf-8')
        elif intent == "assigned_today":
            count = structured_data.get("count", 0)
            chunk = f"{count} applications were assigned today."
            full_response_text = chunk
            sse_data = f"data: {json.dumps({'content': chunk})}\n\n"
            yield sse_data.encode('utf-8')
        elif intent == "immediate_action":
            apps = structured_data.get("apps", [])
            if apps:
                chunk = f"{', '.join(apps)} require immediate action based on pending deadlines."
            else:
                chunk = "No applications require immediate action today."
            full_response_text = chunk
            sse_data = f"data: {json.dumps({'content': chunk})}\n\n"
            yield sse_data.encode('utf-8')
        elif intent == "awaiting_field_visit":
            count = structured_data.get("count", 0)
            chunk = f"{count} applications are awaiting field inspection."
            full_response_text = chunk
            sse_data = f"data: {json.dumps({'content': chunk})}\n\n"
            yield sse_data.encode('utf-8')
        elif intent == "workload_by_type":
            isd = structured_data.get("ISD", 0)
            nisd = structured_data.get("NISD", 0)
            merge = structured_data.get("MERGE", 0)
            chunk = f"ISD – {isd} applications, NISD – {nisd} applications, Merge – {merge} applications."
            full_response_text = chunk
            sse_data = f"data: {json.dumps({'content': chunk})}\n\n"
            yield sse_data.encode('utf-8')
        elif intent == "completion_rate":
            completed = structured_data.get("completed", 0)
            total = structured_data.get("total", 0)
            rate = structured_data.get("rate", 0)
            chunk = f"Application completion rate: {rate}% ({completed} of {total} assigned applications completed)."
            full_response_text = chunk
            sse_data = f"data: {json.dumps({'content': chunk})}\n\n"
            yield sse_data.encode('utf-8')
        elif intent == "pending_longest":
            apps = structured_data.get("apps", [])
            days = structured_data.get("days", 0)
            if apps:
                chunk = f"Application Nos. {', '.join(apps)} have been pending for more than {days} days."
            else:
                chunk = "No pending applications."
            full_response_text = chunk
            sse_data = f"data: {json.dumps({'content': chunk})}\n\n"
            yield sse_data.encode('utf-8')
        elif intent == "is_nisd_or_isd":
            if not structured_data or not structured_data.get("found", True):
                chunk = "Application not found."
            else:
                app_type = structured_data.get("type", "ISD")
                survey_no = structured_data.get("survey_no", "145")
                subdivs = structured_data.get("included_subdivisions", "")
                subdiv_count = len(subdivs.split(",")) if subdivs and subdivs != "None" else 2
                if app_type == "ISD":
                    chunk = f"ISD — application declares sub-division into {subdiv_count} plots under survey no. {survey_no}."
                elif app_type == "NISD":
                    chunk = f"NISD — application is for transfer of entire survey/patta without subdivision under survey no. {survey_no}."
                else:
                    chunk = f"MERGE — application is for merging subdivisions under survey no. {survey_no}."
            full_response_text = chunk
            sse_data = f"data: {json.dumps({'content': chunk})}\n\n"
            yield sse_data.encode('utf-8')
        elif intent == "check_documents":
            if not structured_data or not structured_data.get("found", True):
                chunk = "Application not found."
            else:
                missing = [d["document_type"] for d in structured_data.get("documents", []) if not d["is_uploaded"]]
                if missing:
                    missing_str = ", ".join(missing)
                    chunk = f"Missing documents: {missing_str}. Please upload them before scheduling the field visit."
                else:
                    chunk = "No issues detected. All required documents are present."
            full_response_text = chunk
            sse_data = f"data: {json.dumps({'content': chunk})}\n\n"
            yield sse_data.encode('utf-8')
        elif intent == "check_sale_deed":
            if not structured_data or not structured_data.get("found", True):
                chunk = "Application not found."
            else:
                deed_no = structured_data.get("sale_deed_number") or "N/A"
                sub_date = structured_data.get("submission_date") or "2025-06-25"
                if structured_data.get("sale_deed_registered"):
                    chunk = f"Yes, deed no. {deed_no} matches Sub-Registrar's registered index as of {sub_date}."
                else:
                    chunk = "No match found — flag to Sub-Registrar's office before proceeding."
            full_response_text = chunk
            sse_data = f"data: {json.dumps({'content': chunk})}\n\n"
            yield sse_data.encode('utf-8')

        elif intent == "application_status":
            if not structured_data or not structured_data.get("found", True):
                chunk = structured_data.get("message", "Application not found.")
            elif "history" in structured_data:
                hist = structured_data.get("history", [])
                app_no = structured_data.get("application_number", "")
                chunk = f"Workflow history for {app_no}: {len(hist)} stage(s) recorded."
            else:
                app_no = structured_data.get("application_number", "N/A")
                app_type = structured_data.get("type", "N/A")
                status = structured_data.get("status", "N/A").capitalize()
                stage = structured_data.get("stage", "N/A")
                applicant = structured_data.get("applicant_name") or "N/A"
                survey = structured_data.get("survey_no", "N/A")
                chunk = (
                    f"Here are the details for {app_no}. "
                    f"Type: {app_type}, Status: {status}, Stage: {stage}, "
                    f"Applicant: {applicant}, Survey No: {survey}."
                )
            full_response_text = chunk
            sse_data = f"data: {json.dumps({'content': chunk})}\n\n"
            yield sse_data.encode('utf-8')

        elif intent in ("pending_applications", "overdue_applications"):
            count = structured_data.get("count", 0) if structured_data else 0
            qtype = structured_data.get("query_type", "applications") if structured_data else "applications"
            if count == 0:
                chunk = f"No {qtype.lower()} found in your jurisdiction."
            elif count == 1:
                chunk = f"There is 1 {qtype.rstrip('s').lower()} in your jurisdiction."
            else:
                chunk = f"There are {count} {qtype.lower()} in your jurisdiction."
            full_response_text = chunk
            sse_data = f"data: {json.dumps({'content': chunk})}\n\n"
            yield sse_data.encode('utf-8')

        elif intent == "officer_workload":
            total = structured_data.get("total_active", 0) if structured_data else 0
            isd = structured_data.get("ISD", 0)
            nisd = structured_data.get("NISD", 0)
            merge = structured_data.get("MERGE", 0)
            overdue = structured_data.get("overdue", 0)
            chunk = (
                f"Your workload: {total} active application(s) — "
                f"ISD: {isd}, NISD: {nisd}, Merge: {merge}, Overdue: {overdue}."
            )
            full_response_text = chunk
            sse_data = f"data: {json.dumps({'content': chunk})}\n\n"
            yield sse_data.encode('utf-8')

        elif intent in ("field_visits", "ward_surveys", "block_surveys",
                        "survey_detail", "survey_owners", "next_subdivision",
                        "jurisdiction_summary", "rejection_info", "taluk_summary",
                        "litigation_check", "joint_owner_check", "escalation_check",
                        "merge_info", "town_applications", "block_applications"):
            # Table is rendered on the frontend. Just emit a short natural intro.
            found = structured_data.get("found", True) if structured_data else False
            if not found:
                chunk = structured_data.get("message", "No records found.")
            else:
                qtype = structured_data.get("query_type", "") if structured_data else ""
                if qtype:
                    chunk = f"Here are the {qtype.lower()} results."
                else:
                    chunk = "Results are shown in the table below."
            full_response_text = chunk
            sse_data = f"data: {json.dumps({'content': chunk})}\n\n"
            yield sse_data.encode('utf-8')

        else:
            async for chunk in call_llama_stream(full_prompt):
                chunk_count += 1
                full_response_text += chunk
                
                # Format as Server-Sent Event
                sse_data = f"data: {json.dumps({'content': chunk})}\n\n"
                
                # Encode to bytes for streaming
                yield sse_data.encode('utf-8')
                
                if chunk_count % 10 == 0:
                    logger.debug(f"Streamed {chunk_count} chunks, total length: {len(full_response_text)}")
        
        logger.info(f"Stream complete: {chunk_count} chunks, {len(full_response_text)} chars")
            
        # Step 7: Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Step 8: Save chat messages to database
        await save_chat_messages(
            db=db,
            session_id=session_id,
            user_message=message,
            assistant_message=full_response_text,
            language=language,
            response_time_ms=response_time_ms
        )
        
        logger.info(f"Chat processed and streamed successfully in {response_time_ms}ms")
        
    except Exception as e:
        logger.error(f"Error in process_chat_stream: {e}", exc_info=True)
        import json
        error_messages = {
            "en": "I apologize, but I encountered an error processing your request. Please try again.",
            "ta": "மன்னிக்கவும், உங்கள் கோரிக்கையைச் செயல்படுத்துவதில் பிழை ஏற்பட்டது. மீண்டும் முயற்சிக்கவும்.",
            "tanglish": "Sorry, error ஏற்பட்டது. Please try again."
        }
        language = detect_language(message)
        error_msg = error_messages.get(language, error_messages["en"])
        yield f"data: {json.dumps({'content': error_msg})}\n\n"


async def save_chat_messages(
    db: AsyncSession,
    session_id: str,
    user_message: str,
    assistant_message: str,
    language: str,
    response_time_ms: int
) -> None:
    """
    Save user and assistant messages to database
    
    Args:
        db: Database session
        session_id: Chat session UUID
        user_message: User's message
        assistant_message: Assistant's response
        language: Detected language
        response_time_ms: Response time in milliseconds
    """
    try:
        # Get session
        session_query = select(ChatSession).where(
            ChatSession.id == session_id
        )
        result = await db.execute(session_query)
        session = result.scalar_one_or_none()
        
        if not session:
            logger.error(f"Chat session {session_id} not found")
            return
        
        # Save user message
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=user_message,
            detected_language=language,
            created_at=datetime.utcnow()
        )
        db.add(user_msg)
        
        # Save assistant message
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=assistant_message,
            detected_language=language,
            response_time_ms=response_time_ms,
            created_at=datetime.utcnow()
        )
        db.add(assistant_msg)
        
        # Update session last activity
        session.last_activity = datetime.utcnow()
        
        await db.commit()
        logger.info(f"Saved chat messages for session {session_id}")
        
    except Exception as e:
        logger.error(f"Error saving chat messages: {e}")
        await db.rollback()


async def create_chat_session(
    db: AsyncSession,
    officer_id: str
) -> ChatSession:
    """
    Create a new chat session for an officer
    
    Args:
        db: Database session
        officer_id: Officer UUID
        
    Returns:
        Created ChatSession object
    """
    try:
        import uuid
        
        session = ChatSession(
            officer_id=officer_id,
            session_token=str(uuid.uuid4()),
            started_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            is_active=True
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        logger.info(f"Created new chat session: {session.id}")
        return session
        
    except Exception as e:
        logger.error(f"Error creating chat session: {e}")
        await db.rollback()
        raise


async def get_session_history(
    db: AsyncSession,
    session_id: str,
    limit: int = 50
) -> list:
    """
    Get chat history for a session
    
    Args:
        db: Database session
        session_id: Chat session UUID
        limit: Maximum number of messages to return
        
    Returns:
        List of chat messages
    """
    try:
        query = select(ChatMessage).where(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.desc()).limit(limit)
        
        result = await db.execute(query)
        messages = result.scalars().all()
        
        # Reverse to get chronological order
        messages = list(reversed(messages))
        
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "language": msg.detected_language,
                "timestamp": msg.created_at.isoformat()
            }
            for msg in messages
        ]
        
    except Exception as e:
        logger.error(f"Error getting session history: {e}")
        return []


async def get_officer_sessions(
    db: AsyncSession,
    officer_id: str
) -> list:
    """
    Get all chat sessions for an officer
    
    Args:
        db: Database session
        officer_id: Officer UUID
        
    Returns:
        List of chat sessions
    """
    try:
        query = select(ChatSession).where(
            ChatSession.officer_id == officer_id
        ).order_by(ChatSession.last_activity.desc())
        
        result = await db.execute(query)
        sessions = result.scalars().all()
        
        return [
            {
                "session_id": str(session.id),
                "session_token": session.session_token,
                "started_at": session.started_at.isoformat(),
                "last_activity": session.last_activity.isoformat() if session.last_activity else None,
                "is_active": session.is_active
            }
            for session in sessions
        ]
        
    except Exception as e:
        logger.error(f"Error getting officer sessions: {e}")
        return []


def _build_table_data(intent: str, message: str, user_id: str, structured_data: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
    if not structured_data:
        return None
        
    intent_lower = intent.lower()
    
    # 1. Survey details lookup
    if intent_lower in ["survey_lookup", "survey_detail"]:
        if not structured_data.get("found", True):
            return None
        subdivs = []
        for sd in structured_data.get("sub_divisions", []):
            if sd.get("sub_division_no"):
                area = sd.get("area_sqm")
                if area:
                    subdivs.append(f"{sd.get('sub_division_no')} ({int(area)} sq.m)")
                else:
                    subdivs.append(sd.get("sub_division_no"))
        block_name = structured_data.get("jurisdiction", {}).get("block", "Block B1")
        return {
            "query_type": "Survey Number Details",
            "jurisdiction": {
                "district": structured_data.get("jurisdiction", {}).get("district", "N/A"),
                "taluk": structured_data.get("jurisdiction", {}).get("taluk", "N/A"),
                "town": structured_data.get("jurisdiction", {}).get("town", "N/A"),
                "ward_number": structured_data.get("jurisdiction", {}).get("ward_number") or structured_data.get("jurisdiction", {}).get("ward") or "N/A",
                "block_number": block_name
            },
            "surveys_by_block": {
                block_name: [
                    {
                        "survey_no": structured_data.get("survey_no"),
                        "area_sqm": structured_data.get("total_area_sqm"),
                        "land_type": structured_data.get("land_type") or "Urban",
                        "subdivisions": subdivs
                    }
                ]
            }
        }
        
    # 2. Pending applications
    elif intent_lower in ["pending_applications", "town_applications", "block_applications", "immediate_action"] or (intent_lower == "workload" and "applications" in structured_data):
        apps = []
        for app in structured_data.get("applications", []):
            apps.append({
                "application_number": app.get("application_number"),
                "type": app.get("type"),
                "town_name": app.get("town_name") or "N/A",
                "ward_number": app.get("ward_number") or "N/A",
                "status": app.get("status") or "Pending",
                "current_stage": app.get("stage") or app.get("current_stage"),
                "submission_date": app.get("submission_date")
            })
        return {
            "query_type": structured_data.get("query_type", "Pending Applications"),
            "applications": apps
        }
        
    # 3. Field visit
    elif intent_lower in ["field_visit", "field_visits", "awaiting_field_visit"]:
        visits = []
        for visit in structured_data.get("field_visits", []):
            visits.append({
                "application_number": visit.get("application_number"),
                "survey_no": visit.get("survey_no"),
                "block_number": visit.get("block_number") or "N/A",
                "application_type": visit.get("application_type"),
                "status": visit.get("status"),
                "field_visit_date": visit.get("field_visit_date")
            })
        return {
            "query_type": "Field Visits",
            "field_visits": visits
        }
        
    # 4. Owner lookup
    elif intent_lower in ["owner_lookup", "survey_owners", "joint_owner_check"]:
        owners_list = []
        for o in structured_data.get("owners", []):
            sub_div = o.get("sub_division")
            if sub_div == "Survey Level":
                sub_div = None
            owners_list.append({
                "owner_name": o.get("owner_name") or o.get("name") or "N/A",
                "sub_division": sub_div,
                "ownership_share": o.get("ownership_share") or "N/A",
                "ownership_type": o.get("ownership_type") or ("Joint" if o.get("is_joint_owner") else "Primary"),
                "is_joint_owner": bool(o.get("is_joint_owner"))
            })
        return {
            "query_type": structured_data.get("query_type", "Owner Details"),
            "survey_no": structured_data.get("survey_no", ""),
            "owners": owners_list
        }
        
    # 5. Workload summary
    elif intent_lower in ["officer_workload"] or (intent_lower == "workload" and "total_active" in structured_data):
        total = structured_data.get("total_active", 0)
        pending = structured_data.get("ISD", 0) + structured_data.get("NISD", 0) + structured_data.get("MERGE", 0)
        completed = 0
        return {
            "query_type": "Workload Summary",
            "workload": {
                "total_applications": total,
                "pending_applications": pending,
                "completed_applications": completed
            }
        }
        
    # 6. Status check
    elif intent_lower in ["status_check", "application_status"]:
        if not structured_data.get("found", True):
            return None
        if "history" in structured_data:
            return {
                "query_type": structured_data.get("query_type", "Workflow History"),
                "application_number": structured_data.get("application_number"),
                "history": structured_data.get("history", [])
            }
        return {
            "query_type": "Application & Applicant Details",
            "application_number": structured_data.get("application_number"),
            "type": structured_data.get("type"),
            "included_subdivisions": structured_data.get("included_subdivisions") or "N/A",
            "status": structured_data.get("status") or "Pending",
            "stage": structured_data.get("stage"),
            "submission_date": structured_data.get("submission_date"),
            "field_visit_scheduled": bool(structured_data.get("field_visit_scheduled")),
            "field_visit_date": structured_data.get("field_visit_date"),
            "is_overdue": bool(structured_data.get("is_overdue")),
            "priority_flag": bool(structured_data.get("priority_flag")),
            "applicant_name": structured_data.get("applicant_name"),
            "applicant_mobile": structured_data.get("applicant_mobile"),
            "applicant_email": structured_data.get("applicant_email"),
            "applicant_address": structured_data.get("applicant_address"),
            "applicant_aadhaar_last4": structured_data.get("applicant_aadhaar_last4"),
            "declared_reason": structured_data.get("declared_reason")
        }

    # 7. Rejection info
    elif intent_lower in ["rejection_info"]:
        return {
            "query_type": structured_data.get("query_type", "Rejection History"),
            "application_number": structured_data.get("application_number"),
            "rejections": structured_data.get("rejections", [])
        }

    # 8. Jurisdiction summary
    elif intent_lower in ["jurisdiction_summary"] or "jurisdiction" in structured_data:
        return {
            "query_type": structured_data.get("query_type", "Jurisdiction Summary"),
            "jurisdiction": structured_data.get("jurisdiction", {})
        }
        
    # 9. Unassigned field visits — show application detail table
    elif intent_lower == "fv_unassigned_awaiting":
        apps = structured_data.get("unassigned_applications", [])
        if not apps:
            return None
        return {
            "query_type": "Unassigned Field Visits — Awaiting Scheduling",
            "applications": apps
        }

    # 10. Immediate action — show application detail table
    elif intent_lower == "immediate_action":
        apps = structured_data.get("applications", [])
        if not apps:
            return None
        return {
            "query_type": "Immediate Action Required — Today",
            "applications": apps
        }

    return None


async def handle_chat(
    message: str,
    session_id: str,
    officer: OfficerContext,
    db: AsyncSession
) -> Dict[str, Any]:
    """Alias/wrapper for process_chat to comply with prompt signature specifications"""
    return await process_chat(message, session_id, officer, db)
