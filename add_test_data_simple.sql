-- Add 6 test applications (3 priority, 3 normal) in SIS stage
-- This version uses WITH clauses to handle ID generation

DO $$
DECLARE
    v_officer_id UUID;
    v_survey_id UUID;
BEGIN
    -- Get first officer and survey
    SELECT id INTO v_officer_id FROM sis_officers LIMIT 1;
    SELECT id INTO v_survey_id FROM survey_numbers LIMIT 1;
    
    IF v_officer_id IS NULL THEN
        RAISE EXCEPTION 'No SIS officers found';
    END IF;
    
    IF v_survey_id IS NULL THEN
        RAISE EXCEPTION 'No survey numbers found';
    END IF;
    
    -- 1. OVERDUE application (20 days old)
    WITH app1 AS (
        INSERT INTO applicants (name, mobile, email, address, aadhaar_last4)
        VALUES ('Rajesh Kumar', '9876543210', 'rajesh@example.com', '123 Main St', '1234')
        RETURNING id
    )
    INSERT INTO applications (application_number, application_type, survey_number_id, applicant_id, assigned_officer_id, current_status, current_stage, submission_date, is_overdue, priority_flag, declared_reason)
    SELECT 'APP-2026-000101', 'ISD', v_survey_id, app1.id, v_officer_id, 'pending', 'SIS', CURRENT_DATE - 20, true, false, 'partition' FROM app1;
    
    RAISE NOTICE 'Added: APP-2026-000101 (OVERDUE)';
    
    -- 2. PRIORITY FLAG application
    WITH app2 AS (
        INSERT INTO applicants (name, mobile, email, address, aadhaar_last4)
        VALUES ('Priya Sharma', '9876543211', 'priya@example.com', '456 Park Rd', '5678')
        RETURNING id
    )
    INSERT INTO applications (application_number, application_type, survey_number_id, applicant_id, assigned_officer_id, current_status, current_stage, submission_date, is_overdue, priority_flag, declared_reason)
    SELECT 'APP-2026-000102', 'NISD', v_survey_id, app2.id, v_officer_id, 'pending', 'SIS', CURRENT_DATE - 5, false, true, 'sale' FROM app2;
    
    RAISE NOTICE 'Added: APP-2026-000102 (PRIORITY FLAG)';
    
    -- 3. WARNING in status
    WITH app3 AS (
        INSERT INTO applicants (name, mobile, email, address, aadhaar_last4)
        VALUES ('Murugan A', '9876543212', 'murugan@example.com', '789 Beach Rd', '9012')
        RETURNING id
    )
    INSERT INTO applications (application_number, application_type, survey_number_id, applicant_id, assigned_officer_id, current_status, current_stage, submission_date, is_overdue, priority_flag, declared_reason)
    SELECT 'APP-2026-000103', 'ISD', v_survey_id, app3.id, v_officer_id, 'Pending (Warning)', 'SIS', CURRENT_DATE - 3, false, false, 'inheritance' FROM app3;
    
    RAISE NOTICE 'Added: APP-2026-000103 (WARNING)';
    
    -- 4. NORMAL application
    WITH app4 AS (
        INSERT INTO applicants (name, mobile, email, address, aadhaar_last4)
        VALUES ('Lakshmi Devi', '9876543213', 'lakshmi@example.com', '321 Temple St', '3456')
        RETURNING id
    )
    INSERT INTO applications (application_number, application_type, survey_number_id, applicant_id, assigned_officer_id, current_status, current_stage, submission_date, is_overdue, priority_flag, declared_reason)
    SELECT 'APP-2026-000104', 'ISD', v_survey_id, app4.id, v_officer_id, 'pending', 'SIS', CURRENT_DATE - 2, false, false, 'gift_deed' FROM app4;
    
    RAISE NOTICE 'Added: APP-2026-000104 (NORMAL)';
    
    -- 5. NORMAL application
    WITH app5 AS (
        INSERT INTO applicants (name, mobile, email, address, aadhaar_last4)
        VALUES ('Senthil Kumar', '9876543214', 'senthil@example.com', '654 Market Rd', '7890')
        RETURNING id
    )
    INSERT INTO applications (application_number, application_type, survey_number_id, applicant_id, assigned_officer_id, current_status, current_stage, submission_date, is_overdue, priority_flag, declared_reason)
    SELECT 'APP-2026-000105', 'NISD', v_survey_id, app5.id, v_officer_id, 'pending', 'SIS', CURRENT_DATE - 7, false, false, 'court_order' FROM app5;
    
    RAISE NOTICE 'Added: APP-2026-000105 (NORMAL)';
    
    -- 6. NORMAL application
    WITH app6 AS (
        INSERT INTO applicants (name, mobile, email, address, aadhaar_last4)
        VALUES ('Anitha Raman', '9876543215', 'anitha@example.com', '987 Lake View', '2468')
        RETURNING id
    )
    INSERT INTO applications (application_number, application_type, survey_number_id, applicant_id, assigned_officer_id, current_status, current_stage, submission_date, is_overdue, priority_flag, declared_reason)
    SELECT 'APP-2026-000106', 'ISD', v_survey_id, app6.id, v_officer_id, 'pending', 'SIS', CURRENT_DATE, false, false, 'sale' FROM app6;
    
    RAISE NOTICE 'Added: APP-2026-000106 (NORMAL)';
    
    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'SUCCESS! Added 6 test applications to SIS stage';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'High Priority (3): APP-2026-000101, 000102, 000103';
    RAISE NOTICE 'Normal (3): APP-2026-000104, 000105, 000106';
    RAISE NOTICE '';
    RAISE NOTICE 'Test with: "show high priority applications"';
    
END $$;
