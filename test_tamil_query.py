"""
Test script to verify Tamil applicant name query fix
"""
from backend.services.rag import parse_intent, detect_language

# Test queries
test_queries = [
    "விண்ணப்பதாரரின் நாமாகும் பெயர் APP-2024-000001",  # Your actual query
    "விண்ணப்பதாரர் பெயர் என்ன APP-2024-000001",
    "What is the applicant name for APP-2024-000001",
    "விண்ணப்பங்கள் பட்டியல் காட்டு",  # Should be pending_applications
]

print("=" * 80)
print("Tamil Applicant Name Query Test")
print("=" * 80)

for query in test_queries:
    lang = detect_language(query)
    intent = parse_intent(query)
    print(f"\nQuery: {query}")
    print(f"Language: {lang}")
    print(f"Intent: {intent}")
    print(f"Expected: {'application_status' if 'APP-' in query or 'name' in query.lower() or 'பெயர்' in query or 'நாமாகும்' in query else 'pending_applications'}")
    print("-" * 80)
