#!/usr/bin/env python3
"""Check overdue field visits in database"""
import asyncio
from datetime import date
from backend.database import get_db_session
from backend.models import FieldVisit, Application, SurveyNumber
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload

async def check_overdue():
    async with get_db_session() as db:
        # Get all field visits with their applications
        all_visits_stmt = select(FieldVisit).options(
            joinedload(FieldVisit.application).joinedload(Application.survey_number)
        )
        all_visits = (await db.execute(all_visits_stmt)).unique().scalars().all()
        
        print(f"=== ALL FIELD VISITS IN DATABASE ===")
        print(f"Total: {len(all_visits)}\n")
        
        today = date.today()
        print(f"Today's date: {today}")
        print(f"=" * 70)
        
        for idx, visit in enumerate(all_visits, 1):
            app = visit.application
            if app:
                survey_no = app.survey_number.survey_no if app.survey_number else "N/A"
                scheduled = visit.scheduled_date
                status = visit.status
                officer_id = str(visit.officer_id)[:8] if visit.officer_id else "N/A"
                
                is_past = scheduled and scheduled < today if scheduled else False
                status_match = status.lower() in ['scheduled', 'rescheduled', 'overdue'] if status else False
                
                print(f"\n{idx}. Application: {app.application_number}")
                print(f"   Survey: {survey_no}")
                print(f"   Officer ID: {officer_id}...")
                print(f"   Scheduled Date: {scheduled}")
                print(f"   Status: '{status}'")
                print(f"   Is Past Due: {is_past}")
                print(f"   Status Matches Query: {status_match}")
                print(f"   → WOULD BE OVERDUE: {is_past and status_match}")

if __name__ == "__main__":
    asyncio.run(check_overdue())
