import sys
sys.path.insert(0, r"c:\Users\HP\Desktop\Airtel")
from app.modules.advisor.adapter import AdvisorAdapter

advisor = AdvisorAdapter()

print("=" * 65)
print("TESTING AI ADVISOR CONSULTATIVE CLARIFICATION FLOW")
print("=" * 65)

# Test 1: User asks vague query "I run 2 shops in rohtak and need a wifi"
# Expectation: MUST clarify GST and employee count!
print("\n[Turn 1] User: 'I run 2 shops in rohtak and need a wifi'")
r1 = advisor.process_user_message("I run 2 shops in rohtak and need a wifi", language="en")
print("Intent:", r1.get("intent"))
print("Message:\n", r1.get("message"))
print("Recommended Bundle:", r1.get("recommended_bundle"))

assert r1.get("intent") == "clarification", f"Expected clarification, got {r1.get('intent')}"
assert r1.get("recommended_bundle") in [None, {}], "Should not recommend bundle before clarifying!"
assert "gst" in r1.get("message", "").lower(), "Must ask about GST registration!"
assert any(w in r1.get("message", "").lower() for w in ["staff", "employee", "devices"]), "Must ask about employees/staff!"
print("✔ Turn 1 passed: Correctly asks for GST and employees first!")

# Test 2: User answers with GST and Employee count
# Expectation: Now all info is complete -> MUST recommend!
print("\n[Turn 2] User: 'We have 10 employees across both shops and yes we have GST'")
history = [
    {"role": "user", "text": "I run 2 shops in rohtak and need a wifi"},
    {"role": "model", "text": r1.get("message")}
]
r2 = advisor.process_user_message(
    "We have 10 employees across both shops and yes we have GST",
    current_profile=r1.get("profile"),
    language="en",
    history=history
)
print("Intent:", r2.get("intent"))
print("Message:\n", r2.get("message"))
print("Recommended Bundle:", r2.get("recommended_bundle"))
print("Tags:", len(r2.get("explainability_tags", [])))

assert r2.get("intent") == "recommendation", f"Expected recommendation, got {r2.get('intent')}"
assert len(r2.get("recommended_bundle", {})) > 0, "Bundle must have products"
print("✔ Turn 2 passed: Successfully provides recommendation once clarified!")

# Test 3: Test single clinic query without employee count
print("\n[Turn 3] User: 'I run a dental clinic in Pune and need wifi'")
r3 = advisor.process_user_message("I run a dental clinic in Pune and need wifi", language="en")
print("Intent:", r3.get("intent"))
print("Message:\n", r3.get("message"))
assert r3.get("intent") == "clarification", "Should ask for employee count and GST!"
print("✔ Turn 3 passed: Correctly asks clarification for single-site clinic without staff count!")

# Test 4: Clinic Turn 2 with staff count
print("\n[Turn 4] User: 'We have 6 staff members and have GST'")
history_clinic = [
    {"role": "user", "text": "I run a dental clinic in Pune and need wifi"},
    {"role": "model", "text": r3.get("message")}
]
r4 = advisor.process_user_message(
    "We have 6 staff members and have GST",
    current_profile=r3.get("profile"),
    language="en",
    history=history_clinic
)
print("Intent:", r4.get("intent"))
print("Bundle:", r4.get("recommended_bundle"))
assert r4.get("intent") == "recommendation", "Should recommend bundle once clarified!"
print("✔ Turn 4 passed: Clinic recommendation generated after clarification!")

print("\n" + "=" * 65)
print("ALL CONSULTATIVE CLARIFICATION TESTS PASSED 100% GREEN!")
print("=" * 65)

