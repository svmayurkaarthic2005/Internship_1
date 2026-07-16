"""
Script to add standalone fv_overdue_inspections handler in chatbot.py
This fixes the bug where "show overdue field visit" query returns 0 results
"""

def fix_chatbot():
    file_path = r"c:\proj\nic_internship\backend\services\chatbot.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the standalone block right after officer_workload and before field_visits
    # Look for this unique pattern in process_chat() function
    search_pattern = '''        elif intent == "officer_workload":
            structured_data = await get_officer_workload(db, officer)
            structured_data["query_type"] = "Officer Workload Summary"
            
        elif intent == "field_visits":'''
    
    replacement = '''        elif intent == "officer_workload":
            structured_data = await get_officer_workload(db, officer)
            structured_data["query_type"] = "Officer Workload Summary"
            
        elif intent == "fv_overdue_inspections":
            # Get field visits that are overdue (scheduled date in past, not completed)
            try:
                logger.info(f"🔍 Fetching overdue field visits for officer {officer.officer_id}")
                from datetime import date
                today = date.today()
                
                query = select(FieldVisit).join(
                    Application, FieldVisit.application_id == Application.id
                ).where(
                    and_(
                        Application.assigned_officer_id == officer.officer_id,
                        FieldVisit.scheduled_date < today,
                        FieldVisit.status.in_(["scheduled", "rescheduled", "overdue"])
                    )
                )
                
                result = await db.execute(query)
                overdue_visits = result.scalars().all()
                
                logger.info(f"📊 Found {len(overdue_visits)} overdue field visits")
                
                # Build structured data for table rendering
                visit_data = []
                for fv in overdue_visits:
                    app = await db.get(Application, fv.application_id)
                    survey = await db.get(SurveyNumber, app.survey_number_id) if app else None
                    
                    days_overdue = (today - fv.scheduled_date).days
                    
                    visit_data.append({
                        "visit_id": fv.visit_id,
                        "application_number": app.application_number if app else "N/A",
                        "survey_number": survey.survey_number if survey else "N/A",
                        "scheduled_date": fv.scheduled_date.strftime("%Y-%m-%d"),
                        "status": fv.status,
                        "days_overdue": days_overdue,
                        "purpose": fv.purpose or "Field Inspection"
                    })
                
                structured_data = {
                    "overdue_count": len(overdue_visits),
                    "field_visits": visit_data,
                    "query_type": "Overdue Field Visits"
                }
                
                logger.info(f"✅ Built structured data with {len(visit_data)} overdue visits")
                
            except Exception as e:
                logger.error(f"❌ Error fetching overdue field visits: {str(e)}")
                structured_data = {
                    "error": f"Error fetching overdue field visits: {str(e)}",
                    "query_type": "Overdue Field Visits"
                }
            
        elif intent == "field_visits":'''
    
    # Only replace the FIRST occurrence (in process_chat function, not process_chat_stream)
    if search_pattern in content:
        new_content = content.replace(search_pattern, replacement, 1)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ Successfully added standalone fv_overdue_inspections handler in process_chat()")
        print(f"📍 Location: after officer_workload, before field_visits")
        return True
    else:
        print("❌ Could not find the search pattern in chatbot.py")
        print("The file structure may have changed")
        return False

if __name__ == "__main__":
    success = fix_chatbot()
    if success:
        print("\n🎯 Fix complete! The standalone overdue handler has been added.")
        print("⚠️  NOTE: You still need to restart the FastAPI server for changes to take effect!")
    else:
        print("\n⚠️  Fix failed - manual intervention needed")
