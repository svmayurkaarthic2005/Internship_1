"""
Automated Test Script for All Applied Fixes
Run this after applying all fixes to verify everything works
"""
import asyncio
import asyncpg
from datetime import datetime
import sys

# Test configurations
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "database": "sis_chatbot",
    "user": "postgres",
    "password": "Mayur@2005"
}

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(name, passed, message=""):
    status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
    print(f"{status} - {name}")
    if message:
        print(f"     {message}")

async def test_database_indexes():
    """Test 1: Verify composite indexes were created"""
    print(f"\n{Colors.BLUE}=== Test 1: Database Indexes ==={Colors.END}")
    
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        
        indexes = await conn.fetch("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'applications' 
            AND indexname IN ('idx_app_officer_status', 'idx_app_officer_overdue', 'idx_app_officer_type')
        """)
        
        index_names = [idx['indexname'] for idx in indexes]
        
        print_test(
            "idx_app_officer_status exists",
            'idx_app_officer_status' in index_names,
            f"Found: {len([i for i in index_names if 'officer_status' in i])} matching indexes"
        )
        
        print_test(
            "idx_app_officer_overdue exists",
            'idx_app_officer_overdue' in index_names,
            f"Found: {len([i for i in index_names if 'officer_overdue' in i])} matching indexes"
        )
        
        print_test(
            "idx_app_officer_type exists",
            'idx_app_officer_type' in index_names,
            f"Found: {len([i for i in index_names if 'officer_type' in i])} matching indexes"
        )
        
        await conn.close()
        return len(index_names) == 3
        
    except Exception as e:
        print_test("Database connection", False, f"Error: {str(e)}")
        return False

async def test_district_code_attribute():
    """Test 2: Verify District has district_code attribute"""
    print(f"\n{Colors.BLUE}=== Test 2: District Model Attribute ==={Colors.END}")
    
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        
        # Check if district_code column exists
        result = await conn.fetchrow("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'districts' 
            AND column_name = 'district_code'
        """)
        
        has_column = result is not None
        print_test(
            "District.district_code column exists",
            has_column,
            "Column found in database schema"
        )
        
        # Check for wrong 'code' column (should not exist)
        wrong_result = await conn.fetchrow("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'districts' 
            AND column_name = 'code'
        """)
        
        no_wrong_column = wrong_result is None
        print_test(
            "No incorrect 'code' column exists",
            no_wrong_column,
            "Verified no ambiguous 'code' column"
        )
        
        await conn.close()
        return has_column and no_wrong_column
        
    except Exception as e:
        print_test("District attribute check", False, f"Error: {str(e)}")
        return False

async def test_relationship_integrity():
    """Test 3: Check for broken relationships in database"""
    print(f"\n{Colors.BLUE}=== Test 3: Relationship Integrity ==={Colors.END}")
    
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        
        # Check applications with broken survey_number relationships
        broken_surveys = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM applications a
            LEFT JOIN survey_numbers sn ON a.survey_number_id = sn.id
            WHERE a.survey_number_id IS NOT NULL AND sn.id IS NULL
        """)
        
        print_test(
            "No applications with broken survey_number FK",
            broken_surveys == 0,
            f"Found {broken_surveys} broken relationships" if broken_surveys > 0 else "All relationships intact"
        )
        
        # Check survey numbers with broken block relationships
        broken_blocks = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM survey_numbers sn
            LEFT JOIN blocks b ON sn.block_id = b.id
            WHERE sn.block_id IS NOT NULL AND b.id IS NULL
        """)
        
        print_test(
            "No survey_numbers with broken block FK",
            broken_blocks == 0,
            f"Found {broken_blocks} broken relationships" if broken_blocks > 0 else "All relationships intact"
        )
        
        # Check blocks with broken ward relationships
        broken_wards = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM blocks b
            LEFT JOIN wards w ON b.ward_id = w.id
            WHERE b.ward_id IS NOT NULL AND w.id IS NULL
        """)
        
        print_test(
            "No blocks with broken ward FK",
            broken_wards == 0,
            f"Found {broken_wards} broken relationships" if broken_wards > 0 else "All relationships intact"
        )
        
        await conn.close()
        return broken_surveys == 0 and broken_blocks == 0 and broken_wards == 0
        
    except Exception as e:
        print_test("Relationship integrity check", False, f"Error: {str(e)}")
        return False

async def test_application_data_quality():
    """Test 4: Verify applications have complete location data"""
    print(f"\n{Colors.BLUE}=== Test 4: Application Data Quality ==={Colors.END}")
    
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        
        # Get sample applications with full location chain
        apps_with_location = await conn.fetch("""
            SELECT 
                a.application_number,
                sn.survey_no,
                b.block_number,
                w.ward_number,
                t.name AS town_name
            FROM applications a
            JOIN survey_numbers sn ON a.survey_number_id = sn.id
            JOIN blocks b ON sn.block_id = b.id
            JOIN wards w ON b.ward_id = w.id
            JOIN towns t ON w.town_id = t.id
            LIMIT 5
        """)
        
        has_complete_data = len(apps_with_location) > 0
        print_test(
            "Applications have complete location chain",
            has_complete_data,
            f"Found {len(apps_with_location)} applications with complete data"
        )
        
        if has_complete_data:
            for app in apps_with_location[:3]:  # Show first 3
                print(f"     Sample: {app['application_number']} → Town: {app['town_name']}, Ward: {app['ward_number']}")
        
        # Count applications with NULL survey_number_id
        null_surveys = await conn.fetchval("""
            SELECT COUNT(*) FROM applications WHERE survey_number_id IS NULL
        """)
        
        print_test(
            "No applications with NULL survey_number_id",
            null_surveys == 0,
            f"Found {null_surveys} applications without survey" if null_surveys > 0 else "All applications have surveys"
        )
        
        await conn.close()
        return has_complete_data and null_surveys == 0
        
    except Exception as e:
        print_test("Application data quality", False, f"Error: {str(e)}")
        return False

async def test_query_performance():
    """Test 5: Measure query performance with new indexes"""
    print(f"\n{Colors.BLUE}=== Test 5: Query Performance ==={Colors.END}")
    
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        
        # Test 1: Query pending applications by officer
        start = datetime.now()
        result = await conn.fetch("""
            SELECT COUNT(*) 
            FROM applications 
            WHERE assigned_officer_id = (SELECT id FROM sis_officers LIMIT 1)
            AND current_status IN ('pending', 'in_progress')
        """)
        query1_time = (datetime.now() - start).total_seconds() * 1000
        
        print_test(
            "Pending applications query < 200ms",
            query1_time < 200,
            f"Query time: {query1_time:.2f}ms"
        )
        
        # Test 2: Query overdue applications
        start = datetime.now()
        result = await conn.fetch("""
            SELECT COUNT(*) 
            FROM applications 
            WHERE assigned_officer_id = (SELECT id FROM sis_officers LIMIT 1)
            AND is_overdue = TRUE
        """)
        query2_time = (datetime.now() - start).total_seconds() * 1000
        
        print_test(
            "Overdue applications query < 200ms",
            query2_time < 200,
            f"Query time: {query2_time:.2f}ms"
        )
        
        # Test 3: Query by application type
        start = datetime.now()
        result = await conn.fetch("""
            SELECT COUNT(*) 
            FROM applications 
            WHERE assigned_officer_id = (SELECT id FROM sis_officers LIMIT 1)
            AND application_type = 'ISD'
        """)
        query3_time = (datetime.now() - start).total_seconds() * 1000
        
        print_test(
            "Application type query < 200ms",
            query3_time < 200,
            f"Query time: {query3_time:.2f}ms"
        )
        
        await conn.close()
        return query1_time < 200 and query2_time < 200 and query3_time < 200
        
    except Exception as e:
        print_test("Query performance test", False, f"Error: {str(e)}")
        return False

def test_frontend_auth_security():
    """Test 6: Check frontend auth.js for security fixes"""
    print(f"\n{Colors.BLUE}=== Test 6: Frontend Security ==={Colors.END}")
    
    try:
        with open('frontend/js/auth.js', 'r', encoding='utf-8') as f:
            auth_content = f.read()
        
        # Check that access_token is NOT stored in sessionStorage
        has_token_in_storage = 'access_token: data.data.access_token' in auth_content
        print_test(
            "Token NOT stored in sessionStorage",
            not has_token_in_storage,
            "✓ Security fix applied" if not has_token_in_storage else "✗ Token still in sessionStorage (security risk)"
        )
        
        # Check that Authorization header is NOT used
        has_auth_header = "'Authorization': `Bearer ${data.access_token}`" in auth_content or \
                         "'Authorization': `Bearer ${officerData.access_token}`" in auth_content
        print_test(
            "No Authorization header in auth checks",
            not has_auth_header,
            "✓ Using cookies only" if not has_auth_header else "✗ Still using Authorization header"
        )
        
        # Check for credentials: 'include'
        has_credentials = "credentials: 'include'" in auth_content
        print_test(
            "Using credentials: 'include' for cookies",
            has_credentials,
            "✓ Cookie support enabled"
        )
        
        return not has_token_in_storage and not has_auth_header and has_credentials
        
    except Exception as e:
        print_test("Frontend security check", False, f"Error: {str(e)}")
        return False

def test_pagination_implementation():
    """Test 7: Check if pagination is implemented"""
    print(f"\n{Colors.BLUE}=== Test 7: Pagination Implementation ==={Colors.END}")
    
    try:
        with open('frontend/js/dataTable.js', 'r', encoding='utf-8') as f:
            datatable_content = f.read()
        
        # Check if handlePagination has real implementation
        has_placeholder = "Pagination logic would go here" in datatable_content
        print_test(
            "Pagination has real implementation",
            not has_placeholder,
            "✓ Full implementation" if not has_placeholder else "✗ Still a placeholder"
        )
        
        # Check if createTableHTML returns object with fullDataset
        returns_object = 'return { html: tableHTML, fullDataset:' in datatable_content or \
                        'return {html: tableHTML, fullDataset:' in datatable_content
        print_test(
            "createTableHTML returns object with dataset",
            returns_object,
            "✓ Returns {html, fullDataset}" if returns_object else "✗ Still returns string only"
        )
        
        # Check if renderDataTable stores dataset
        stores_dataset = 'tableCard._fullDataset' in datatable_content
        print_test(
            "renderDataTable stores full dataset",
            stores_dataset,
            "✓ Dataset stored for pagination"
        )
        
        return not has_placeholder and returns_object and stores_dataset
        
    except Exception as e:
        print_test("Pagination implementation check", False, f"Error: {str(e)}")
        return False

async def main():
    """Run all tests"""
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"  SIS CHATBOT - FIX VERIFICATION TEST SUITE")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}{Colors.END}\n")
    
    results = []
    
    # Database tests
    results.append(("Database Indexes", await test_database_indexes()))
    results.append(("District Attribute", await test_district_code_attribute()))
    results.append(("Relationship Integrity", await test_relationship_integrity()))
    results.append(("Data Quality", await test_application_data_quality()))
    results.append(("Query Performance", await test_query_performance()))
    
    # Frontend tests
    results.append(("Frontend Security", test_frontend_auth_security()))
    results.append(("Pagination", test_pagination_implementation()))
    
    # Summary
    passed = sum(1 for _, result in results if result)
    total = len(results)
    percentage = (passed / total) * 100
    
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"  TEST SUMMARY")
    print(f"{'='*60}{Colors.END}\n")
    
    for name, result in results:
        status = f"{Colors.GREEN}PASS{Colors.END}" if result else f"{Colors.RED}FAIL{Colors.END}"
        print(f"  [{status}] {name}")
    
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    
    if passed == total:
        print(f"{Colors.GREEN}✓ ALL TESTS PASSED! ({passed}/{total}){Colors.END}")
        print(f"\n{Colors.GREEN}Your application is ready for deployment!{Colors.END}\n")
        return 0
    else:
        print(f"{Colors.YELLOW}⚠ SOME TESTS FAILED ({passed}/{total} passed - {percentage:.1f}%){Colors.END}")
        print(f"\nPlease review the failed tests and apply the necessary fixes.\n")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
