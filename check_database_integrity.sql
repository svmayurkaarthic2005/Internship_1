-- =====================================================
-- DATABASE INTEGRITY CHECK SCRIPT
-- Run this to identify data issues before applying fixes
-- =====================================================

-- 1. Check for applications with broken survey_number relationships
-- =====================================================
SELECT 
    'Applications with NULL survey_number_id' AS check_name,
    COUNT(*) AS count
FROM applications
WHERE survey_number_id IS NULL

UNION ALL

SELECT 
    'Applications with invalid survey_number_id (FK broken)' AS check_name,
    COUNT(*) AS count
FROM applications a
LEFT JOIN survey_numbers sn ON a.survey_number_id = sn.id
WHERE a.survey_number_id IS NOT NULL 
  AND sn.id IS NULL;

-- 2. Check for survey numbers with broken block relationships
-- =====================================================
SELECT 
    'Survey numbers with NULL block_id' AS check_name,
    COUNT(*) AS count
FROM survey_numbers
WHERE block_id IS NULL

UNION ALL

SELECT 
    'Survey numbers with invalid block_id (FK broken)' AS check_name,
    COUNT(*) AS count
FROM survey_numbers sn
LEFT JOIN blocks b ON sn.block_id = b.id
WHERE sn.block_id IS NOT NULL 
  AND b.id IS NULL;

-- 3. Check for blocks with broken ward relationships
-- =====================================================
SELECT 
    'Blocks with NULL ward_id' AS check_name,
    COUNT(*) AS count
FROM blocks
WHERE ward_id IS NULL

UNION ALL

SELECT 
    'Blocks with invalid ward_id (FK broken)' AS check_name,
    COUNT(*) AS count
FROM blocks b
LEFT JOIN wards w ON b.ward_id = w.id
WHERE b.ward_id IS NOT NULL 
  AND w.id IS NULL;

-- 4. Check for wards with broken town relationships
-- =====================================================
SELECT 
    'Wards with NULL town_id' AS check_name,
    COUNT(*) AS count
FROM wards
WHERE town_id IS NULL

UNION ALL

SELECT 
    'Wards with invalid town_id (FK broken)' AS check_name,
    COUNT(*) AS count
FROM wards w
LEFT JOIN towns t ON w.town_id = t.id
WHERE w.town_id IS NOT NULL 
  AND t.id IS NULL;

-- 5. Check for towns with broken taluk relationships
-- =====================================================
SELECT 
    'Towns with NULL taluk_id' AS check_name,
    COUNT(*) AS count
FROM towns
WHERE taluk_id IS NULL

UNION ALL

SELECT 
    'Towns with invalid taluk_id (FK broken)' AS check_name,
    COUNT(*) AS count
FROM towns t
LEFT JOIN taluks tk ON t.taluk_id = tk.id
WHERE t.taluk_id IS NOT NULL 
  AND tk.id IS NULL;

-- 6. Check for taluks with broken district relationships
-- =====================================================
SELECT 
    'Taluks with NULL district_id' AS check_name,
    COUNT(*) AS count
FROM taluks
WHERE district_id IS NULL

UNION ALL

SELECT 
    'Taluks with invalid district_id (FK broken)' AS check_name,
    COUNT(*) AS count
FROM taluks tk
LEFT JOIN districts d ON tk.district_id = d.id
WHERE tk.district_id IS NOT NULL 
  AND d.id IS NULL;

-- 7. Check for orphaned sub-divisions
-- =====================================================
SELECT 
    'Sub-divisions with invalid survey_number_id' AS check_name,
    COUNT(*) AS count
FROM sub_divisions sd
LEFT JOIN survey_numbers sn ON sd.survey_number_id = sn.id
WHERE sn.id IS NULL;

-- 8. Check for orphaned application_sub_divisions
-- =====================================================
SELECT 
    'Application sub-divisions with invalid application_id' AS check_name,
    COUNT(*) AS count
FROM application_sub_divisions asd
LEFT JOIN applications a ON asd.application_id = a.id
WHERE a.id IS NULL

UNION ALL

SELECT 
    'Application sub-divisions with invalid sub_division_id' AS check_name,
    COUNT(*) AS count
FROM application_sub_divisions asd
LEFT JOIN sub_divisions sd ON asd.sub_division_id = sd.id
WHERE sd.id IS NULL;

-- 9. Check for applications with invalid assigned_officer_id
-- =====================================================
SELECT 
    'Applications with invalid assigned_officer_id' AS check_name,
    COUNT(*) AS count
FROM applications a
LEFT JOIN sis_officers o ON a.assigned_officer_id = o.id
WHERE a.assigned_officer_id IS NOT NULL 
  AND o.id IS NULL;

-- 10. Check for officers without jurisdiction
-- =====================================================
SELECT 
    'Officers without any jurisdiction assignment' AS check_name,
    COUNT(*) AS count
FROM sis_officers o
LEFT JOIN officer_jurisdictions oj ON o.id = oj.officer_id
WHERE oj.id IS NULL 
  AND o.is_active = TRUE;

-- =====================================================
-- DETAILED REPORTS (for fixing specific records)
-- =====================================================

-- Report: Applications with broken survey_number chain
SELECT 
    'BROKEN_SURVEY_CHAIN' AS issue_type,
    a.application_number,
    a.survey_number_id,
    CASE 
        WHEN sn.id IS NULL THEN 'Survey number not found'
        WHEN b.id IS NULL THEN 'Block not found'
        WHEN w.id IS NULL THEN 'Ward not found'
        WHEN t.id IS NULL THEN 'Town not found'
        WHEN tk.id IS NULL THEN 'Taluk not found'
        WHEN d.id IS NULL THEN 'District not found'
        ELSE 'OK'
    END AS broken_at,
    sn.survey_no,
    b.block_number,
    w.ward_number,
    t.name AS town_name
FROM applications a
LEFT JOIN survey_numbers sn ON a.survey_number_id = sn.id
LEFT JOIN blocks b ON sn.block_id = b.id
LEFT JOIN wards w ON b.ward_id = w.id
LEFT JOIN towns t ON w.town_id = t.id
LEFT JOIN taluks tk ON t.taluk_id = tk.id
LEFT JOIN districts d ON tk.district_id = d.id
WHERE a.survey_number_id IS NOT NULL
  AND (sn.id IS NULL OR b.id IS NULL OR w.id IS NULL OR t.id IS NULL OR tk.id IS NULL OR d.id IS NULL)
ORDER BY a.application_number
LIMIT 100;

-- Report: Escalated applications (not being queried)
SELECT 
    'ESCALATED_NOT_QUERIED' AS issue_type,
    COUNT(*) AS count,
    STRING_AGG(application_number, ', ' ORDER BY submission_date DESC) AS application_numbers
FROM applications
WHERE current_status = 'escalated';

-- Report: Applications in unknown stages
SELECT 
    current_stage,
    COUNT(*) AS count
FROM applications
WHERE current_stage NOT IN ('SIS', 'SD', 'DIS', 'TAHSILDAR', 'COMPLETED', 'REJECTED')
GROUP BY current_stage;

-- Report: Applications in unknown statuses
SELECT 
    current_status,
    COUNT(*) AS count
FROM applications
WHERE current_status NOT IN ('pending', 'in_progress', 'approved', 'rejected', 'escalated')
GROUP BY current_status;

-- Report: Field visits without scheduled dates
SELECT 
    'FIELD_VISITS_UNSCHEDULED' AS issue_type,
    fv.id,
    a.application_number,
    fv.status,
    fv.scheduled_date
FROM field_visits fv
JOIN applications a ON fv.application_id = a.id
WHERE fv.status = 'scheduled' 
  AND fv.scheduled_date IS NULL;

-- Report: Applications marked field_visit_scheduled but no visit record
SELECT 
    'APP_MARKED_SCHEDULED_BUT_NO_VISIT' AS issue_type,
    a.application_number,
    a.field_visit_scheduled,
    a.field_visit_date,
    COUNT(fv.id) AS visit_count
FROM applications a
LEFT JOIN field_visits fv ON a.id = fv.application_id
WHERE a.field_visit_scheduled = TRUE
GROUP BY a.application_number, a.field_visit_scheduled, a.field_visit_date
HAVING COUNT(fv.id) = 0;

-- =====================================================
-- INDEX USAGE ANALYSIS
-- =====================================================

-- Check if recommended indexes exist
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'applications'
ORDER BY indexname;

-- Check for missing recommended indexes
SELECT 
    'Missing composite index: idx_app_officer_status' AS recommendation
WHERE NOT EXISTS (
    SELECT 1 FROM pg_indexes 
    WHERE tablename = 'applications' 
    AND indexname = 'idx_app_officer_status'
)

UNION ALL

SELECT 
    'Missing composite index: idx_app_officer_overdue' AS recommendation
WHERE NOT EXISTS (
    SELECT 1 FROM pg_indexes 
    WHERE tablename = 'applications' 
    AND indexname = 'idx_app_officer_overdue'
)

UNION ALL

SELECT 
    'Missing composite index: idx_app_officer_type' AS recommendation
WHERE NOT EXISTS (
    SELECT 1 FROM pg_indexes 
    WHERE tablename = 'applications' 
    AND indexname = 'idx_app_officer_type'
);

-- =====================================================
-- PERFORMANCE ANALYSIS
-- =====================================================

-- Most common query patterns
SELECT 
    'Applications by officer (pending/in_progress)' AS query_pattern,
    COUNT(*) AS row_count,
    COUNT(DISTINCT assigned_officer_id) AS officer_count
FROM applications
WHERE current_status IN ('pending', 'in_progress');

SELECT 
    'Overdue applications by officer' AS query_pattern,
    COUNT(*) AS row_count,
    COUNT(DISTINCT assigned_officer_id) AS officer_count
FROM applications
WHERE is_overdue = TRUE;

SELECT 
    'Applications by type per officer' AS query_pattern,
    application_type,
    COUNT(*) AS row_count,
    COUNT(DISTINCT assigned_officer_id) AS officer_count
FROM applications
GROUP BY application_type;

-- Table sizes
SELECT 
    schemaname AS schema,
    tablename AS table_name,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS indexes_size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 20;

-- =====================================================
-- DATA QUALITY SUMMARY
-- =====================================================

-- Overall data quality score
WITH quality_checks AS (
    SELECT 
        (SELECT COUNT(*) FROM applications WHERE survey_number_id IS NULL) AS apps_no_survey,
        (SELECT COUNT(*) FROM applications a LEFT JOIN survey_numbers sn ON a.survey_number_id = sn.id WHERE a.survey_number_id IS NOT NULL AND sn.id IS NULL) AS apps_broken_survey,
        (SELECT COUNT(*) FROM survey_numbers WHERE block_id IS NULL) AS surveys_no_block,
        (SELECT COUNT(*) FROM blocks WHERE ward_id IS NULL) AS blocks_no_ward,
        (SELECT COUNT(*) FROM wards WHERE town_id IS NULL) AS wards_no_town,
        (SELECT COUNT(*) FROM applications WHERE current_status = 'escalated') AS escalated_apps,
        (SELECT COUNT(*) FROM sis_officers o LEFT JOIN officer_jurisdictions oj ON o.id = oj.officer_id WHERE oj.id IS NULL AND o.is_active = TRUE) AS officers_no_jurisdiction,
        (SELECT COUNT(*) FROM applications) AS total_applications
)
SELECT 
    'DATA QUALITY SUMMARY' AS report,
    total_applications AS total_records,
    (apps_no_survey + apps_broken_survey + surveys_no_block + blocks_no_ward + wards_no_town) AS total_issues,
    ROUND(
        ((total_applications - (apps_no_survey + apps_broken_survey)) * 100.0 / NULLIF(total_applications, 0)), 
        2
    ) AS data_integrity_percentage,
    CASE 
        WHEN (apps_no_survey + apps_broken_survey + surveys_no_block + blocks_no_ward + wards_no_town) = 0 THEN 'EXCELLENT'
        WHEN (apps_no_survey + apps_broken_survey) < 5 THEN 'GOOD'
        WHEN (apps_no_survey + apps_broken_survey) < 20 THEN 'FAIR'
        ELSE 'POOR - FIX REQUIRED'
    END AS quality_grade
FROM quality_checks;

-- =====================================================
-- END OF INTEGRITY CHECK
-- Run this script and review results before applying fixes
-- =====================================================
