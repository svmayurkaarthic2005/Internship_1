# Instructions to Add Test Data

The SQL script has issues with auto-generated IDs. Here's the **easiest way** to add test data:

## Option 1: Use pgAdmin (RECOMMENDED - Easiest!)

1. **Open pgAdmin**
2. **Connect** to database: `sis_chatbot`
3. **Right-click** on `sis_chatbot` → **Query Tool**
4. **Copy** this command and **paste** into the Query Tool:

```sql
-- Quick script to add 6 test applications (3 priority, 3 normal) in SIS stage

DO $$
DECLARE
    v_officer_id UUID;
    v_survey_id UUID;
BEGIN
    -- Get first officer and survey
    SELECT id INTO v_officer_id FROM sis_officers LIMIT 1;
    SELECT id INTO v_survey_id FROM survey_numbers LIMIT 1;
    
    -- Add test applicants and applications
    WITH 
    app1 AS (
        INSERT INTO applicants (name, mobile, email, address, aadhaar_last4)
        VALUES ('Rajesh Kumar', '9876543210', 'rajesh@example.com', '123 Main St', '1234')
        RETURNING id
    )
    INSERT INTO applications (application_number, application_type, survey_number_id, applicant_id, assigned_officer_id, current_status, current_stage, submission_date, is_overdue, priority_flag, declared_reason)
    SELECT 'APP-2026-000101', 'ISD', v_survey_id, app1.id, v_officer_id, 'pending', 'SIS', CURRENT_DATE - 20, true, false, 'partition' FROM app1;
    
    WITH 
    app2 AS (
        INSERT INTO applicants (name, mobile, email, address, aadhaar_last4)
        VALUES ('Priya Sharma', '9876543211', 'priya@example.com', '456 Park Rd', '5678')
        RETURNING id
    )
    INSERT INTO applications (application_number, application_type, survey_number_id, applicant_id, assigned_officer_id, current_status, current_stage, submission_date, is_overdue, priority_flag, declared_reason)
    SELECT 'APP-2026-000102', 'NISD', v_survey_id, app2.id, v_officer_id, 'pending', 'SIS', CURRENT_DATE - 5, false, true, 'sale' FROM app2;
    
    WITH 
    app3 AS (
        INSERT INTO applicants (name, mobile, email, address, aadhaar_last4)
        VALUES ('Murugan A', '9876543212', 'murugan@example.com', '789 Beach Rd', '9012')
        RETURNING id
    )
    INSERT INTO applications (application_number, application_type, survey_number_id, applicant_id, assigned_officer_id, current_status, current_stage, submission_date, is_overdue, priority_flag, declared_reason)
    SELECT 'APP-2026-000103', 'ISD', v_survey_id, app3.id, v_officer_id, 'Pending (Warning)', 'SIS', CURRENT_DATE - 3, false, false, 'inheritance' FROM app3;
    
    WITH 
    app4 AS (
        INSERT INTO applicants (name, mobile, email, address, aadhaar_last4)
        VALUES ('Lakshmi Devi', '9876543213', 'lakshmi@example.com', '321 Temple St', '3456')
        RETURNING id
    )
    INSERT INTO applications (application_number, application_type, survey_number_id, applicant_id, assigned_officer_id, current_status, current_stage, submission_date, is_overdue, priority_flag, declared_reason)
    SELECT 'APP-2026-000104', 'ISD', v_survey_id, app4.id, v_officer_id, 'pending', 'SIS', CURRENT_DATE - 2, false, false, 'gift_deed' FROM app4;
    
    WITH 
    app5 AS (
        INSERT INTO applicants (name, mobile, email, address, aadhaar_last4)
        VALUES ('Senthil Kumar', '9876543214', 'senthil@example.com', '654 Market Rd', '7890')
        RETURNING id
    )
    INSERT INTO applications (application_number, application_type, survey_number_id, applicant_id, assigned_officer_id, current_status, current_stage, submission_date, is_overdue, priority_flag, declared_reason)
    SELECT 'APP-2026-000105', 'NISD', v_survey_id, app5.id, v_officer_id, 'pending', 'SIS', CURRENT_DATE - 7, false, false, 'court_order' FROM app5;
    
    WITH 
    app6 AS (
        INSERT INTO applicants (name, mobile, email, address, aadhaar_last4)
        VALUES ('Anitha Raman', '9876543215', 'anitha@example.com', '987 Lake View', '2468')
        RETURNING id
    )
    INSERT INTO applications (application_number, application_type, survey_number_id, applicant_id, assigned_officer_id, current_status, current_stage, submission_date, is_overdue, priority_flag, declared_reason)
    SELECT 'APP-2026-000106', 'ISD', v_survey_id, app6.id, v_officer_id, 'pending', 'SIS', CURRENT_DATE, false, false, 'sale' FROM app6;
    
    RAISE NOTICE 'SUCCESS! Added 6 test applications';
    RAISE NOTICE '  High Priority (3): APP-2026-000101 (overdue), APP-2026-000102 (priority flag), APP-2026-000103 (warning)';
    RAISE NOTICE '  Normal (3): APP-2026-000104, APP-2026-000105, APP-2026-000106';
END $$;
```

5. **Click Execute** (▶️ button) or press `F5`
6. You should see: "SUCCESS! Added 6 test applications"

## Then Test in Chatbot

1. "show high priority applications" → Should show 3 apps
2. "show pending applications" → Should show all 6 apps

---

## Option 2: If pgAdmin doesn't work

Save the SQL above to a file and run:
```cmd
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d sis_chatbot -f yourfile.sql
```

(Replace `yourfile.sql` with the actual filename)

