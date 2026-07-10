"""
Seed script for SIS Chatbot Portal
Populates the database with dummy test data
Run: python -m backend.seed
"""
import asyncio
import sys
from datetime import date, datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Add parent directory to path
sys.path.insert(0, '.')

from backend.config import settings
from backend.models import (
    Base, District, Taluk, Town, Ward, Block,
    SurveyNumber, SubDivision, Owner, SurveyOwnership,
    SISOfficer, OfficerJurisdiction, Applicant, Application,
    ApplicationSubDivision, ApplicationDocument, WorkflowHistory,
    FieldVisit, PattaTransfer, Notification
)
from backend.services.auth_service import get_password_hash


async def seed_database():
    """Main seed function"""
    print("[SEED] Starting database seeding...")

    # All dates are relative to today so data always looks realistic
    today = date.today()

    # Import engine from database.py to use Windows-compatible configuration
    from backend.database import engine
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("[OK] Database tables created")
    
    # Create session
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        # ========== GEOGRAPHY ==========
        print("[GEO] Seeding geography data...")
        
        # District: Chennai (Code: CHN)
        chennai = District(name="Chennai", district_code="CHN")
        db.add(chennai)
        await db.flush()
        
        # Taluks (Code: District-Taluk)
        ambattur = Taluk(district_id=chennai.id, name="Ambattur", taluk_code="CHN-AMB")
        tambaram = Taluk(district_id=chennai.id, name="Tambaram", taluk_code="CHN-TAM")
        db.add_all([ambattur, tambaram])
        await db.flush()
        
        # Towns (Code: District-Taluk-Town)
        ambattur_town = Town(taluk_id=ambattur.id, name="Ambattur", town_code="AMB-T01")
        tambaram_town = Town(taluk_id=tambaram.id, name="Tambaram", town_code="TAM-T01")
        db.add_all([ambattur_town, tambaram_town])
        await db.flush()
        
        # Wards (Code: Ward number only)
        ward_12 = Ward(town_id=ambattur_town.id, ward_number="12", ward_name="Ward 12")
        ward_15 = Ward(town_id=ambattur_town.id, ward_number="15", ward_name="Ward 15")
        ward_5 = Ward(town_id=tambaram_town.id, ward_number="5", ward_name="Ward 5")
        db.add_all([ward_12, ward_15, ward_5])
        await db.flush()
        
        # Blocks (Code: Block identifier)
        block_b1 = Block(ward_id=ward_12.id, block_number="B1", block_name="Block B1")
        block_b2 = Block(ward_id=ward_12.id, block_number="B2", block_name="Block B2")
        block_b3 = Block(ward_id=ward_15.id, block_number="B3", block_name="Block B3")
        block_b10 = Block(ward_id=ward_5.id, block_number="B10", block_name="Block B10")
        db.add_all([block_b1, block_b2, block_b3, block_b10])
        await db.flush()
        
        print("[OK] Geography data seeded")
        
        # ========== SURVEY NUMBERS & SUB-DIVISIONS ==========
        print("[SURVEY] Seeding survey numbers...")
        
        # Block B1 surveys
        survey_145 = SurveyNumber(
            block_id=block_b1.id, survey_no="145", total_area_sqm=1950.00,
            land_type="residential", patta_number="P-145-2020"
        )
        survey_146 = SurveyNumber(
            block_id=block_b1.id, survey_no="146", total_area_sqm=1200.00,
            land_type="agricultural", patta_number="P-146-2019"
        )
        survey_147 = SurveyNumber(
            block_id=block_b1.id, survey_no="147", total_area_sqm=1550.00,
            land_type="residential", patta_number="P-147-2021"
        )
        db.add_all([survey_145, survey_146, survey_147])
        await db.flush()
        
        # Sub-divisions for 145
        sub_145_1a = SubDivision(survey_number_id=survey_145.id, sub_division_no="145/1A", area_sqm=600.00, status="active")
        sub_145_1b = SubDivision(survey_number_id=survey_145.id, sub_division_no="145/1B", area_sqm=700.00, status="active")
        sub_145_1c = SubDivision(survey_number_id=survey_145.id, sub_division_no="145/1C", area_sqm=650.00, status="active")
        db.add_all([sub_145_1a, sub_145_1b, sub_145_1c])
        
        # Sub-divisions for 146
        sub_146_1 = SubDivision(survey_number_id=survey_146.id, sub_division_no="146/1", area_sqm=400.00, status="active")
        sub_146_2 = SubDivision(survey_number_id=survey_146.id, sub_division_no="146/2", area_sqm=400.00, status="active")
        sub_146_3 = SubDivision(survey_number_id=survey_146.id, sub_division_no="146/3", area_sqm=400.00, status="active")
        db.add_all([sub_146_1, sub_146_2, sub_146_3])

        # Sub-divisions for 147
        sub_147_1 = SubDivision(survey_number_id=survey_147.id, sub_division_no="147/1", area_sqm=800.00, status="active")
        sub_147_2 = SubDivision(survey_number_id=survey_147.id, sub_division_no="147/2", area_sqm=750.00, status="active")
        db.add_all([sub_147_1, sub_147_2])
        await db.flush()
        
        # Block B2 surveys
        survey_200 = SurveyNumber(
            block_id=block_b2.id, survey_no="200", total_area_sqm=980.00,
            land_type="commercial", patta_number="P-200-2022"
        )
        survey_201 = SurveyNumber(
            block_id=block_b2.id, survey_no="201", total_area_sqm=950.00,
            land_type="residential", patta_number="P-201-2020"
        )
        db.add_all([survey_200, survey_201])
        await db.flush()
        
        # Sub-divisions for 200
        sub_200_1 = SubDivision(survey_number_id=survey_200.id, sub_division_no="200/1", area_sqm=500.00, status="active")
        sub_200_2 = SubDivision(survey_number_id=survey_200.id, sub_division_no="200/2", area_sqm=480.00, status="active")
        db.add_all([sub_200_1, sub_200_2])
        await db.flush()
        
        # Block B3 surveys
        survey_300 = SurveyNumber(
            block_id=block_b3.id, survey_no="300", total_area_sqm=1800.00,
            land_type="agricultural", patta_number="P-300-2018"
        )
        survey_301 = SurveyNumber(
            block_id=block_b3.id, survey_no="301", total_area_sqm=1500.00,
            land_type="residential", patta_number="P-301-2021"
        )
        db.add_all([survey_300, survey_301])
        await db.flush()
        
        # Block B10 surveys
        survey_500 = SurveyNumber(
            block_id=block_b10.id, survey_no="500", total_area_sqm=2200.00,
            land_type="residential", patta_number="P-500-2019"
        )
        survey_501 = SurveyNumber(
            block_id=block_b10.id, survey_no="501", total_area_sqm=1900.00,
            land_type="agricultural", patta_number="P-501-2020"
        )
        survey_502 = SurveyNumber(
            block_id=block_b10.id, survey_no="502", total_area_sqm=1600.00,
            land_type="commercial", patta_number="P-502-2022"
        )
        db.add_all([survey_500, survey_501, survey_502])
        await db.flush()
        
        print("[OK] Survey numbers seeded")
        
        # ========== OWNERS ==========
        print("[OWNERS] Seeding owners...")
        
        owner_1 = Owner(name="Murugan Rajan", name_tamil="??????? ?????", father_name="Rajan Pillai", 
                        aadhaar_last4="4521", mobile="9876543210", address="No 12, Gandhi Street, Ambattur, Chennai")
        owner_2 = Owner(name="Kavitha Selvi", name_tamil="????? ??????", father_name="Selvaraj Kumar",
                        aadhaar_last4="7823", mobile="9123456789", address="No 45, Nehru Nagar, Ambattur, Chennai")
        owner_3 = Owner(name="Suresh Babu", name_tamil="?????? ????", father_name="Babu Naidu",
                        aadhaar_last4="9012", mobile="8765432109", address="No 67, Anna Salai, Ambattur, Chennai")
        owner_4 = Owner(name="Ramya Suresh", name_tamil="????? ??????", father_name="Sundaram Raja",
                        aadhaar_last4="3456", mobile="7654321098", address="No 67, Anna Salai, Ambattur, Chennai")
        owner_5 = Owner(name="Bala Krishnan", name_tamil="??? ?????????", father_name="Krishnan Iyer",
                        aadhaar_last4="6789", mobile="9988776655", address="No 89, Periyar Street, Ambattur, Chennai")
        owner_6 = Owner(name="Anbu Chelvan", name_tamil="????? ???????", father_name="Chelvan Mudaliar",
                        aadhaar_last4="2345", mobile="8877665544", address="No 23, Kamarajar Road, Ambattur, Chennai")
        
        db.add_all([owner_1, owner_2, owner_3, owner_4, owner_5, owner_6])
        await db.flush()
        
        # Survey ownership
        ownership_1a = SurveyOwnership(survey_number_id=survey_145.id, sub_division_id=sub_145_1a.id, owner_id=owner_1.id, 
                                      ownership_share=100.00, ownership_type="sole", effective_from=date(2020, 1, 15))
        ownership_1b = SurveyOwnership(survey_number_id=survey_145.id, sub_division_id=sub_145_1b.id, owner_id=owner_2.id, 
                                      ownership_share=100.00, ownership_type="sole", effective_from=date(2020, 1, 15))
        ownership_1c_1 = SurveyOwnership(survey_number_id=survey_145.id, sub_division_id=sub_145_1c.id, owner_id=owner_3.id, 
                                        ownership_share=50.00, is_joint_owner=True, ownership_type="joint", effective_from=date(2020, 1, 15))
        ownership_1c_2 = SurveyOwnership(survey_number_id=survey_145.id, sub_division_id=sub_145_1c.id, owner_id=owner_4.id, 
                                        ownership_share=50.00, is_joint_owner=True, ownership_type="joint", effective_from=date(2020, 1, 15))
        ownership_2 = SurveyOwnership(survey_number_id=survey_146.id, owner_id=owner_2.id,
                                     ownership_share=100.00, ownership_type="sole", effective_from=date(2019, 5, 20))
        ownership_3 = SurveyOwnership(survey_number_id=survey_147.id, sub_division_id=sub_147_1.id, owner_id=owner_3.id,
                                     ownership_share=50.00, is_joint_owner=True, ownership_type="joint", effective_from=date(2021, 3, 10))
        ownership_4 = SurveyOwnership(survey_number_id=survey_147.id, sub_division_id=sub_147_1.id, owner_id=owner_4.id,
                                     ownership_share=50.00, is_joint_owner=True, ownership_type="joint", effective_from=date(2021, 3, 10))
        ownership_5 = SurveyOwnership(survey_number_id=survey_147.id, sub_division_id=sub_147_2.id, owner_id=owner_5.id,
                                     ownership_share=100.00, ownership_type="sole", effective_from=date(2021, 3, 10))
        ownership_6 = SurveyOwnership(survey_number_id=survey_200.id, sub_division_id=sub_200_1.id, owner_id=owner_6.id,
                                     ownership_share=100.00, ownership_type="sole", effective_from=date(2022, 7, 1))
        
        db.add_all([ownership_1a, ownership_1b, ownership_1c_1, ownership_1c_2, ownership_2, ownership_3, ownership_4, ownership_5, ownership_6])
        await db.flush()
        
        print("[OK] Owners seeded")
        
        # ========== SIS OFFICERS ==========
        print("[OFFICERS] Seeding SIS officers...")
        
        officer_1 = SISOfficer(
            employee_id="SIS-001",
            name="Arjun Kumar",
            name_tamil="??????? ??????",
            email="arjun.kumar@sis.tn.gov.in",
            password_hash=get_password_hash("Test@1234"),
            mobile="9876501234",
            designation="Sub Inspector Surveyor",
            is_active=True
        )
        officer_2 = SISOfficer(
            employee_id="SIS-002",
            name="Priya Devi",
            name_tamil="?????? ????",
            email="priya.devi@sis.tn.gov.in",
            password_hash=get_password_hash("Test@1234"),
            mobile="9123450678",
            designation="Sub Inspector Surveyor",
            is_active=True
        )
        officer_3 = SISOfficer(
            employee_id="SIS-003",
            name="Ramesh Babu",
            name_tamil="????? ????",
            email="ramesh.babu@sis.tn.gov.in",
            password_hash=get_password_hash("Test@1234"),
            mobile="8765401234",
            designation="Sub Inspector Surveyor",
            is_active=True
        )
        
        db.add_all([officer_1, officer_2, officer_3])
        await db.flush()
        
        # Officer jurisdictions
        juris_1 = OfficerJurisdiction(
            officer_id=officer_1.id, jurisdiction_type="block",
            district_id=chennai.id, taluk_id=ambattur.id, town_id=ambattur_town.id,
            ward_id=ward_12.id, block_id=block_b1.id
        )
        juris_2 = OfficerJurisdiction(
            officer_id=officer_2.id, jurisdiction_type="ward",
            district_id=chennai.id, taluk_id=ambattur.id, town_id=ambattur_town.id,
            ward_id=ward_15.id
        )
        juris_3 = OfficerJurisdiction(
            officer_id=officer_3.id, jurisdiction_type="taluk",
            district_id=chennai.id, taluk_id=tambaram.id
        )
        
        db.add_all([juris_1, juris_2, juris_3])
        await db.flush()
        
        print("[OK] SIS officers seeded")
        
        # ========== APPLICANTS & APPLICATIONS ==========
        print("[APPS] Seeding applications...")
        
        applicants = []
        for i in range(1, 16):
            applicant = Applicant(
                name=f"Applicant {i}",
                mobile=f"9{i:09d}",
                email=f"applicant{i}@email.com",
                aadhaar_last4=f"{i:04d}",
                address=f"Address for Applicant {i}, Chennai"
            )
            applicants.append(applicant)
            db.add(applicant)
        await db.flush()
        
        # Application 1: ISD, pending, field visit scheduled (5 days ago, visit in 3 days)
        app_1 = Application(
            application_number="APP-2024-000001",
            application_type="ISD",
            applicant_id=applicants[0].id,
            survey_number_id=survey_145.id,
            assigned_officer_id=officer_1.id,
            submission_channel="CSC",
            submission_date=today - timedelta(days=5),
            sale_deed_number="SD-2025-1001",
            sale_deed_registered=True,
            declared_reason="sale",
            current_stage="SIS",
            current_status="pending",
            field_visit_date=today + timedelta(days=3),
            field_visit_scheduled=True,
            is_overdue=False,
            priority_flag=False,
            notes="New sub-division requested for Survey 145"
        )
        db.add(app_1)
        await db.flush()
        
        # Application 2: NISD, forwarded to SD (12 days ago)
        app_2 = Application(
            application_number="APP-2024-000002",
            application_type="NISD",
            applicant_id=applicants[1].id,
            survey_number_id=survey_146.id,
            assigned_officer_id=officer_1.id,
            submission_channel="citizen",
            submission_date=today - timedelta(days=12),
            sale_deed_number="SD-2025-1002",
            sale_deed_registered=True,
            declared_reason="inheritance",
            current_stage="SD",
            current_status="in_progress",
            field_visit_scheduled=False,
            is_overdue=False,
            priority_flag=False,
            notes="Patta transfer without sub-division"
        )
        db.add(app_2)
        await db.flush()
        
        # Application 3: ISD, at DIS, overdue (25 days ago)
        app_3 = Application(
            application_number="APP-2024-000003",
            application_type="ISD",
            applicant_id=applicants[2].id,
            survey_number_id=survey_147.id,
            assigned_officer_id=officer_1.id,
            submission_channel="sub_registrar",
            submission_date=today - timedelta(days=25),
            sale_deed_number="SD-2025-1003",
            sale_deed_registered=True,
            declared_reason="partition",
            current_stage="DIS",
            current_status="pending",
            field_visit_scheduled=False,
            is_overdue=True,
            priority_flag=True,
            notes="Pending at DIS for 20+ days"
        )
        db.add(app_3)
        await db.flush()
        
        # Application 4: MERGE, completed (45 days ago)
        app_4 = Application(
            application_number="APP-2024-000004",
            application_type="MERGE",
            applicant_id=applicants[3].id,
            survey_number_id=survey_145.id,
            assigned_officer_id=officer_1.id,
            submission_channel="CSC",
            submission_date=today - timedelta(days=45),
            sale_deed_number="SD-2025-1004",
            sale_deed_registered=True,
            declared_reason="sale",
            current_stage="COMPLETED",
            current_status="approved",
            field_visit_scheduled=False,
            is_overdue=False,
            priority_flag=False,
            notes="Merge of 145/1A, 145/1B, 145/1C completed successfully"
        )
        db.add(app_4)
        await db.flush()
        
        # Application 5: ISD, unscheduled field visit (8 days ago)
        app_5 = Application(
            application_number="APP-2024-000005",
            application_type="ISD",
            applicant_id=applicants[4].id,
            survey_number_id=survey_200.id,
            assigned_officer_id=officer_1.id,
            submission_channel="citizen",
            submission_date=today - timedelta(days=8),
            declared_reason="sale",
            current_stage="SIS",
            current_status="pending",
            field_visit_scheduled=False,
            is_overdue=False,
            priority_flag=False,
            notes="Field visit not yet scheduled"
        )
        db.add(app_5)
        await db.flush()
        
        # Application 6: NISD, rejected by SD (18 days ago)
        app_6 = Application(
            application_number="APP-2024-000006",
            application_type="NISD",
            applicant_id=applicants[5].id,
            survey_number_id=survey_201.id,
            assigned_officer_id=officer_1.id,
            submission_channel="CSC",
            submission_date=today - timedelta(days=18),
            declared_reason="gift_deed",
            current_stage="REJECTED",
            current_status="rejected",
            field_visit_scheduled=False,
            is_overdue=False,
            priority_flag=False,
            notes="Rejected due to boundary mismatch"
        )
        db.add(app_6)
        await db.flush()
        
        # Applications 7-15 for other officers
        app_7 = Application(
            application_number="APP-2024-000007",
            application_type="ISD",
            applicant_id=applicants[6].id,
            survey_number_id=survey_300.id,
            assigned_officer_id=officer_2.id,
            submission_channel="citizen",
            submission_date=today - timedelta(days=6),
            declared_reason="sale",
            current_stage="SIS",
            current_status="pending",
            field_visit_scheduled=False,
            is_overdue=False,
            priority_flag=False
        )
        db.add(app_7)

        app_8 = Application(
            application_number="APP-2024-000008",
            application_type="ISD",
            applicant_id=applicants[7].id,
            survey_number_id=survey_301.id,
            assigned_officer_id=officer_2.id,
            submission_channel="CSC",
            submission_date=today - timedelta(days=10),
            declared_reason="partition",
            current_stage="SD",
            current_status="pending",
            field_visit_scheduled=False,
            is_overdue=False,
            priority_flag=True
        )
        db.add(app_8)

        app_9 = Application(
            application_number="APP-2024-000009",
            application_type="NISD",
            applicant_id=applicants[8].id,
            survey_number_id=survey_500.id,
            assigned_officer_id=officer_3.id,
            submission_channel="sub_registrar",
            submission_date=today - timedelta(days=30),
            declared_reason="inheritance",
            current_stage="COMPLETED",
            current_status="approved",
            field_visit_scheduled=False,
            is_overdue=False,
            priority_flag=False
        )
        db.add(app_9)

        app_10 = Application(
            application_number="APP-2024-000010",
            application_type="ISD",
            applicant_id=applicants[9].id,
            survey_number_id=survey_501.id,
            assigned_officer_id=officer_3.id,
            submission_channel="CSC",
            submission_date=today - timedelta(days=20),
            declared_reason="sale",
            current_stage="TAHSILDAR",
            current_status="pending",
            field_visit_scheduled=False,
            is_overdue=False,
            priority_flag=False
        )
        db.add(app_10)
        
        # Add more applications (11-15) with various stages
        # Survey pool that has sub-divisions for merge eligibility:
        #   survey_145 → 145/1A, 145/1B, 145/1C
        #   survey_146 → 146/1, 146/2, 146/3
        #   survey_147 → 147/1, 147/2
        #   survey_200 → 200/1, 200/2
        survey_map = [survey_145, survey_146, survey_147, survey_200, survey_201]

        # MERGE surveys pool (all have sub-divisions with real areas)
        merge_surveys = [survey_145, survey_146]

        loop_apps = {}
        merge_idx = 0
        for i in range(10, 15):
            app_type = ["ISD", "NISD", "MERGE"][i % 3]
            if app_type == "MERGE":
                linked_survey = merge_surveys[merge_idx % len(merge_surveys)]
                merge_idx += 1
            else:
                linked_survey = survey_map[i % 5]

            app = Application(
                application_number=f"APP-2024-{i+1:06d}",
                application_type=app_type,
                applicant_id=applicants[i].id,
                survey_number_id=linked_survey.id,
                assigned_officer_id=officer_1.id,
                submission_channel=["CSC", "citizen", "sub_registrar"][i % 3],
                submission_date=today - timedelta(days=3 + i),
                declared_reason=["sale", "inheritance", "partition", "gift_deed"][i % 4],
                current_stage=["SIS", "SD", "DIS"][i % 3],
                current_status=["pending", "in_progress"][i % 2],
                field_visit_scheduled=False,
                is_overdue=False,
                priority_flag=False,
                notes=f"Merge of sub-divisions under survey {linked_survey.survey_no}" if app_type == "MERGE" else None
            )
            db.add(app)
            loop_apps[i+1] = (app, app_type, linked_survey)
        
        await db.flush()
        print("[OK] Applications seeded")
        
        # ========== APPLICATION SUBDIVISIONS ==========
        print("[SUBDIVISIONS] Seeding application sub-divisions...")
        # app_4: MERGE of all 3 sub-divisions of survey 145 (completed)
        asd_1 = ApplicationSubDivision(application_id=app_4.id, sub_division_id=sub_145_1a.id, proposed_area_sqm=600.00)
        asd_2 = ApplicationSubDivision(application_id=app_4.id, sub_division_id=sub_145_1b.id, proposed_area_sqm=700.00)
        asd_3 = ApplicationSubDivision(application_id=app_4.id, sub_division_id=sub_145_1c.id, proposed_area_sqm=650.00)
        db.add_all([asd_1, asd_2, asd_3])

        # Link all MERGE apps from the loop to their survey's sub-divisions
        merge_subdiv_map = {
            survey_145.id: [
                (sub_145_1a, 600.00),
                (sub_145_1b, 700.00),
            ],
            survey_146.id: [
                (sub_146_1, 400.00),
                (sub_146_2, 400.00),
                (sub_146_3, 400.00),
            ],
        }
        for app_num, (app_obj, app_type, linked_survey) in loop_apps.items():
            if app_type == "MERGE":
                subdiv_list = merge_subdiv_map.get(linked_survey.id, [])
                for sd, area in subdiv_list:
                    db.add(ApplicationSubDivision(
                        application_id=app_obj.id,
                        sub_division_id=sd.id,
                        proposed_area_sqm=area
                    ))

        await db.flush()
        print("[OK] Application sub-divisions seeded")
        
        # ========== WORKFLOW HISTORY ==========
        print("[WORKFLOW] Seeding workflow history...")
        
        wf_1 = WorkflowHistory(
            application_id=app_1.id,
            from_stage=None,
            to_stage="SIS",
            action="APPLICATION_SUBMITTED",
            performed_by_officer_id=None,
            remarks="Application submitted via CSC",
            performed_at=datetime.combine(today - timedelta(days=5), datetime.min.time().replace(hour=10, minute=30))
        )

        wf_2 = WorkflowHistory(
            application_id=app_2.id,
            from_stage=None,
            to_stage="SIS",
            action="APPLICATION_SUBMITTED",
            performed_by_officer_id=None,
            remarks="Application submitted by citizen",
            performed_at=datetime.combine(today - timedelta(days=12), datetime.min.time().replace(hour=9, minute=0))
        )

        wf_3 = WorkflowHistory(
            application_id=app_2.id,
            from_stage="SIS",
            to_stage="SD",
            action="FORWARDED_TO_SD",
            performed_by_officer_id=officer_1.id,
            remarks="Field verification completed, forwarding to SD",
            performed_at=datetime.combine(today - timedelta(days=8), datetime.min.time().replace(hour=14, minute=30))
        )

        wf_4 = WorkflowHistory(
            application_id=app_6.id,
            from_stage="SD",
            to_stage="REJECTED",
            action="REJECTED",
            performed_by_officer_id=None,
            remarks="Rejected by SD",
            rejection_reason="Boundary mismatch detected in field verification",
            performed_at=datetime.combine(today - timedelta(days=10), datetime.min.time().replace(hour=11, minute=15))
        )
        
        db.add_all([wf_1, wf_2, wf_3, wf_4])
        await db.flush()
        print("[OK] Workflow history seeded")
        
        # ========== FIELD VISITS ==========
        print("[VISITS] Seeding field visits...")
        
        fv_1 = FieldVisit(
            application_id=app_1.id,
            officer_id=officer_1.id,
            scheduled_date=today + timedelta(days=3),
            status="scheduled",
            visit_notes=None
        )

        fv_2 = FieldVisit(
            application_id=app_3.id,
            officer_id=officer_1.id,
            scheduled_date=today - timedelta(days=5),
            status="overdue",
            visit_notes="Field visit not completed on scheduled date"
        )
        
        fv_3 = FieldVisit(
            application_id=app_5.id,
            officer_id=officer_1.id,
            status="unscheduled"
        )
        
        db.add_all([fv_1, fv_2, fv_3])
        await db.flush()
        print("[OK] Field visits seeded")
        
        # ========== APPLICATION DOCUMENTS ==========
        print("[DOCS] Seeding documents...")
        
        doc_1 = ApplicationDocument(
            application_id=app_1.id,
            document_type="Sale Deed",
            document_name="sale_deed_145.pdf",
            is_uploaded=True,
            is_verified=True,
            uploaded_at=datetime.combine(today - timedelta(days=5), datetime.min.time().replace(hour=10, minute=35))
        )

        doc_2 = ApplicationDocument(
            application_id=app_1.id,
            document_type="Encumbrance Certificate",
            document_name="ec_145.pdf",
            is_uploaded=True,
            is_verified=False,
            uploaded_at=datetime.combine(today - timedelta(days=5), datetime.min.time().replace(hour=10, minute=37))
        )
        
        doc_3 = ApplicationDocument(
            application_id=app_1.id,
            document_type="Sketch",
            document_name=None,
            is_uploaded=False,
            is_verified=False
        )
        
        db.add_all([doc_1, doc_2, doc_3])
        await db.flush()
        print("[OK] Documents seeded")
        
        await db.commit()
    
    await engine.dispose()
    print("[DONE] Database seeding completed successfully!")
    print("\n[NOTE] Test Credentials:")
    print("   Email: arjun.kumar@sis.tn.gov.in | Password: Test@1234")
    print("   Email: priya.devi@sis.tn.gov.in | Password: Test@1234")
    print("   Email: ramesh.babu@sis.tn.gov.in | Password: Test@1234")


if __name__ == "__main__":
    asyncio.run(seed_database())

