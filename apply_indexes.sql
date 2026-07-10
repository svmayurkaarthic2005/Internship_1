-- =====================================================
-- APPLY COMPOSITE INDEXES FOR PERFORMANCE
-- Run this script to add the missing indexes
-- =====================================================

-- Check if indexes already exist before creating
DO $$ 
BEGIN
    -- Index 1: assigned_officer_id + current_status
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'applications' 
        AND indexname = 'idx_app_officer_status'
    ) THEN
        CREATE INDEX idx_app_officer_status 
        ON applications(assigned_officer_id, current_status);
        RAISE NOTICE 'Created index: idx_app_officer_status';
    ELSE
        RAISE NOTICE 'Index already exists: idx_app_officer_status';
    END IF;

    -- Index 2: assigned_officer_id + is_overdue
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'applications' 
        AND indexname = 'idx_app_officer_overdue'
    ) THEN
        CREATE INDEX idx_app_officer_overdue 
        ON applications(assigned_officer_id, is_overdue);
        RAISE NOTICE 'Created index: idx_app_officer_overdue';
    ELSE
        RAISE NOTICE 'Index already exists: idx_app_officer_overdue';
    END IF;

    -- Index 3: assigned_officer_id + application_type
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'applications' 
        AND indexname = 'idx_app_officer_type'
    ) THEN
        CREATE INDEX idx_app_officer_type 
        ON applications(assigned_officer_id, application_type);
        RAISE NOTICE 'Created index: idx_app_officer_type';
    ELSE
        RAISE NOTICE 'Index already exists: idx_app_officer_type';
    END IF;
END $$;

-- Verify indexes were created
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'applications'
AND indexname IN ('idx_app_officer_status', 'idx_app_officer_overdue', 'idx_app_officer_type')
ORDER BY indexname;

-- Analyze the table to update statistics
ANALYZE applications;

RAISE NOTICE 'Index creation complete! Run EXPLAIN ANALYZE on your queries to verify they are using the indexes.';
