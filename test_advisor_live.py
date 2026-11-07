import requests
import json

base = "http://127.0.0.1:8000"

def run_test():
    print("=" * 65)
    print("AI ADVISOR - LIVE GEMINI & CLARIFICATION VERIFICATION")
    print("=" * 65)

    # 1. Vague query: should trigger Progressive Clarification
    print("\n[Query 1] User asks: 'I need wifi'")
    r1 = requests.post(f"{base}/api/advisor/chat", json={"message": "I need wifi", "language": "en"}).json()
    print("Intent:", r1.get("intent"))
    print("Message:\n", r1.get("message"))
    print("Bundle:", r1.get("recommended_bundle"))
    assert r1.get("intent") == "clarification", "Should trigger clarification"
    assert r1.get("recommended_bundle") in [None, {}], "Bundle should be empty on clarification"
    print("✔ [1/3] Progressive Clarification: PASSED")

    # 2. Specific Query: should recommend compliant bundle with tags once parameters are provided
    print("\n[Query 2] User asks: 'We are a CA accounting firm with 8 auditors in Jaipur, we have active GST'")
    r2 = requests.post(f"{base}/api/advisor/chat", json={"message": "We are a CA accounting firm with 8 auditors in Jaipur, we have active GST", "language": "en"}).json()
    print("Intent:", r2.get("intent"))
    print("Message:\n", r2.get("message"))
    print("Bundle:", r2.get("recommended_bundle"))
    print("Tags:", len(r2.get("explainability_tags", [])))
    print("Engine:", r2.get("ai_engine"))
    assert r2.get("intent") == "recommendation", "Should recommend bundle"
    assert len(r2.get("recommended_bundle", {})) > 0, "Bundle must have products"
    print("✔ [2/3] Policy Recommendation: PASSED")

    # 3. Hindi Down-sell query
    print("\n[Query 3] User asks in Hindi: 'यह प्लान बहुत महंगा है, कोई सस्ता प्लान दिखाओ'")
    r3 = requests.post(f"{base}/api/advisor/chat", json={"message": "यह प्लान बहुत महंगा है, कोई सस्ता प्लान दिखाओ", "language": "hi"}).json()
    print("Intent:", r3.get("intent"))
    print("Message:\n", r3.get("message"))
    print("Bundle:", r3.get("recommended_bundle"))
    print("Engine:", r3.get("ai_engine"))
    assert r3.get("intent") == "downsell_request", "Should trigger downsell"
    assert any(pid in r3.get("recommended_bundle", {}) for pid in ["P01", "P04", "P07"]), "Should contain floor connectivity (P01 or P04)"
    print("✔ [3/3] Hindi Vernacular Downsell: PASSED")

    print("\n" + "=" * 65)
    print("ALL 3 AI ASSISTANT CONVERSATION MODES ARE 100% OPERATIONAL!")
    print("=" * 65)

if __name__ == "__main__":
    run_test()

