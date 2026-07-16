"""
Test if overdue field visits intent is being detected correctly
"""
import sys
sys.path.insert(0, 'c:/proj/nic_internship')

from backend.services.rag import detect_intent

# Test queries
test_queries = [
    "Which field visits are overdue?",
    "Show overdue field visits",
    "எந்த கள ஆய்வுகள் காலதாமதமாகின?",
    "List overdue field visits",
    "field visits that are overdue"
]

print("Testing overdue field visit intent detection:")
print("=" * 60)

for query in test_queries:
    intent = detect_intent(query, language="en")
    status = "✅" if intent == "fv_overdue_inspections" else "❌"
    print(f"{status} Query: {query}")
    print(f"   Detected intent: {intent}")
    print()
