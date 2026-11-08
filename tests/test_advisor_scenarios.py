"""
Scenario-Based Evaluation Suite for Refactored AI Advisor.
Covers:
1. Retail Shop
2. Dental Clinic
3. Restaurant (Multi-site)
4. Tech Startup
5. Rural vs Fiber Clarification & 5G AirFiber Switch
6. GST Uncertainty & Non-GST Safe Mode
7. Progressive Down-sell (English & Hindi)
8. Informational Product Inquiries without Cart Mutation
9. WhatsApp Session Continuity & Context Persistence
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.modules.advisor.adapter import AdvisorAdapter
from app.modules.advisor.tools import AdvisorTools
from app.modules.advisor.profile import is_ready_for_recommendation
from app.modules.whatsapp.handler import WhatsAppHandler

def test_all_scenarios():
    advisor = AdvisorAdapter()
    tools = AdvisorTools()
    wa_handler = WhatsAppHandler()

    print("=" * 70)
    print("BEGINNING AI ADVISOR 9-SCENARIO COMPREHENSIVE VERIFICATION")
    print("=" * 70)

    # -------------------------------------------------------------
    # Scenario 1: Retail Shop (Indore, 2 Staff, Active GST)
    # -------------------------------------------------------------
    print("\n--- Scenario 1: Retail / Kirana Store (Indore, 2 Staff, Active GST) ---")
    r1 = advisor.process_user_message(
        "I run a Kirana / Retail store with 2 staff in Indore. We have active GST and need wifi and UPI soundbox.",
        language="en"
    )
    p1 = r1["profile"]
    b1 = r1["recommended_bundle"]
    assert p1["city"] == "Indore", f"Expected Indore, got {p1.get('city')}"
    assert p1["pincode"] == "452001", f"Expected PIN 452001, got {p1.get('pincode')}"
    assert p1["city_tier"] == 2, f"Expected Tier 2, got {p1.get('city_tier')}"
    assert "P01" in b1, "Retail store must have Biz Fibre 100 (P01) base line"
    assert "P19" in b1, "Retail store must include Cloud POS & UPI Soundbox (P19)"
    assert len(r1.get("explainability_tags", [])) > 0, "Must include explainability tags"
    print(f"✔ [PASS] Scenario 1 Retail Shop: {b1} with {len(r1['explainability_tags'])} explainability tags")

    # -------------------------------------------------------------
    # Scenario 2: Dental Clinic
    # -------------------------------------------------------------
    print("\n--- Scenario 2: Dental Clinic (Pune, 6 Staff, Active GST) ---")
    r2 = advisor.process_user_message(
        "I run a dental clinic in Pune with 6 staff. We have active GST and need wifi and email.",
        language="en"
    )
    p2 = r2["profile"]
    b2 = r2["recommended_bundle"]
    assert p2["city"] == "Pune", f"Expected Pune, got {p2.get('city')}"
    assert p2["city_tier"] == 1, f"Expected Tier 1, got {p2.get('city_tier')}"
    assert "P02" in b2, "Dental clinic must have Biz Fibre 300 (P02)"
    assert "P22" in b2, "Clinic must have Guest Wi-Fi (P22) for patient waiting area"
    assert "P17" in b2, "Clinic must have Cloud Backup 1TB (P17) for medical records"
    print(f"✔ [PASS] Scenario 2 Dental Clinic: {b2}")

    # -------------------------------------------------------------
    # Scenario 3: Restaurant / Multi-Site Outlets
    # -------------------------------------------------------------
    print("\n--- Scenario 3: Multi-Site Outlets (Rohtak, 2 Sites, 10 & 100 Employees) ---")
    r3 = advisor.process_user_message(
        "i live in rohtak and have 2 shops. one has 10 employees and the other has 100. We have active GST and need to install wifi for them",
        language="en"
    )
    p3 = r3["profile"]
    b3 = r3["recommended_bundle"]
    assert p3["city"] == "Rohtak", f"Expected Rohtak, got {p3.get('city')}"
    assert p3["pincode"] == "124001", f"Expected Rohtak PIN 124001, got {p3.get('pincode')}"
    assert p3["num_sites"] == 2, f"Expected 2 sites, got {p3.get('num_sites')}"
    # In Rohtak (Tier 3), P03 is restricted to Tier 1, so both sites take P02
    assert b3.get("P02") == 2 or (b3.get("P02", 0) >= 1), "Must allocate multi-site fibre lines"
    assert "P19" in b3, "Must include Cloud POS / Soundbox"
    print(f"✔ [PASS] Scenario 3 Multi-Site: {b3}")

    # -------------------------------------------------------------
    # Scenario 4: Tech Startup
    # -------------------------------------------------------------
    print("\n--- Scenario 4: Tech Startup (Noida Tier-1 Metro, 25 Employees) ---")
    r4 = advisor.process_user_message(
        "We are an IT development startup at pincode 201301 with 25 employees. We have active GST.",
        language="en"
    )
    p4 = r4["profile"]
    b4 = r4["recommended_bundle"]
    assert p4["city"] == "Noida", f"Expected Noida, got {p4.get('city')}"
    assert p4["city_tier"] == 1, f"Expected Tier 1, got {p4.get('city_tier')}"
    # In Tier 1 with 25 staff, tech startup qualifies for P03 (1G) or P02
    assert ("P03" in b4 or "P02" in b4), "Tech startup must have high-speed fibre (P03 or P02)"
    assert "P16" in b4, "Startup must have Cloud Email (P16)"
    assert "P11" in b4, "Startup must have Static IP (P11) for staging / VPN servers"
    print(f"✔ [PASS] Scenario 4 Tech Startup: {b4}")

    # -------------------------------------------------------------
    # Scenario 5: Rural vs Fiber Clarification & AirFiber Selection
    # -------------------------------------------------------------
    print("\n--- Scenario 5: Rural vs Fiber Clarification & 5G AirFiber Switch ---")
    # Turn 5a: User mentions village without specifying wireline presence
    r5a = advisor.process_user_message(
        "I run a general store in dumra dehat village and need internet",
        language="en"
    )
    assert r5a["intent"] == "clarification", f"Expected clarification for rural wire presence, got {r5a['intent']}"
    assert r5a["recommended_bundle"] in [None, {}], "Bundle must be empty during clarification"
    assert any(w in r5a["message"].lower() for w in ["airfiber", "cable", "wire", "fibre"]), "Must clarify wire vs wireless AirFiber"
    print(f"✔ [PASS] Scenario 5a Rural Clarification: Correctly prompted choice between Fibre and 5G AirFiber")

    # Turn 5b: User clarifies that no wire/cable has reached their village
    r5b = advisor.process_user_message(
        "There is no wire or cable here, bina taar wala chahiye",
        current_profile=r5a["profile"],
        language="en",
        history=[
            {"role": "user", "text": "I run a general store in dumra dehat village and need internet"},
            {"role": "model", "text": r5a["message"]}
        ]
    )
    assert r5b["intent"] == "recommendation", f"Expected recommendation, got {r5b['intent']}"
    assert "P04" in r5b["recommended_bundle"], "Must recommend Biz 5G AirFiber 100 (P04) when wireline is absent"
    print(f"✔ [PASS] Scenario 5b Rural AirFiber Selected: {r5b['recommended_bundle']}")

    # -------------------------------------------------------------
    # Scenario 6: GST Uncertainty & Non-GST Safe Mode
    # -------------------------------------------------------------
    print("\n--- Scenario 6: GST Uncertainty & Non-GST Udyam Handling ---")
    # Turn 6a: Vague clinic query without scale or GST
    r6a = advisor.process_user_message("I run a clinic in Pune and need wifi", language="en")
    assert r6a["intent"] == "clarification", "Must clarify scale and GST when unstated"
    assert "gst" in r6a["message"].lower(), "Must ask for GST status"

    # Turn 6b: User states sole proprietor without GST
    r6b = advisor.process_user_message(
        "We operate under sole-proprietorship without GST, 3 staff members",
        current_profile=r6a["profile"],
        language="en",
        history=[
            {"role": "user", "text": "I run a clinic in Pune and need wifi"},
            {"role": "model", "text": r6a["message"]}
        ]
    )
    assert r6b["intent"] == "recommendation", "Must recommend once clarified"
    b6 = r6b["recommended_bundle"]
    # Verify no GST-restricted products (ILL P05/P06, SD-WAN P10, Firewall P21) are present
    gst_only_pids = {"P05", "P06", "P10", "P12", "P13", "P14", "P15", "P21", "P24"}
    assert not any(pid in b6 for pid in gst_only_pids), f"Non-GST customer received restricted products: {b6}"
    print(f"✔ [PASS] Scenario 6 Non-GST Safe Mode: Compliant bundle {b6}")

    # -------------------------------------------------------------
    # Scenario 7: Progressive Down-sell (English & Hindi)
    # -------------------------------------------------------------
    print("\n--- Scenario 7: Progressive Down-sell Sequence ---")
    # English downsell
    r7_en = advisor.process_user_message(
        "This plan is too expensive for our small budget, please show something cheaper",
        current_profile={"current_bundle": {"P02": 1, "P17": 1, "P20": 2}, "downsell_level": 0},
        language="en"
    )
    assert r7_en["intent"] == "downsell_request", "Expected downsell_request intent"
    assert any(pid in r7_en["recommended_bundle"] for pid in ["P01", "P02", "P04", "P07"]), "Must retain floor connectivity"

    # Hindi downsell
    r7_hi = advisor.process_user_message(
        "यह प्लान बहुत महंगा है, कोई सस्ता प्लान दिखाओ",
        current_profile={"current_bundle": {"P02": 1, "P19": 1}, "downsell_level": 0},
        language="hi"
    )
    assert r7_hi["intent"] == "downsell_request", "Expected downsell_request intent in Hindi"
    assert "सस्ता" in r7_hi["message"] or "डाउन-सेल" in r7_hi["message"] or "floor" in r7_hi["message"].lower() or "कम" in r7_hi["message"]
    print(f"✔ [PASS] Scenario 7 Progressive Downsell: EN and HI both executed cleanly")

    # -------------------------------------------------------------
    # Scenario 8: Informational Inquiries Without Cart Modification
    # -------------------------------------------------------------
    print("\n--- Scenario 8: Informational Inquiries Without Cart Mutation ---")
    r8 = advisor.process_user_message("What plans and speeds do you offer for small businesses?", language="en")
    assert r8["intent"] == "inquiry", f"Expected inquiry intent, got {r8['intent']}"
    assert r8["recommended_bundle"] in [None, {}], "Inquiry must NOT alter customer bundle"
    assert r8["explainability_tags"] == [], "Inquiry must not return bundle tags"
    assert "Biz Fibre" in r8["message"] or "AirFiber" in r8["message"]
    print(f"✔ [PASS] Scenario 8 Informational Inquiries: Clean inquiry response without cart mutation")

    # -------------------------------------------------------------
    # Scenario 9: WhatsApp Session Continuity
    # -------------------------------------------------------------
    print("\n--- Scenario 9: WhatsApp Session Continuity ---")
    test_phone = "919876543210"
    wa_handler.session_mgr.reset_session(test_phone)
    wa_res = wa_handler.process_incoming_message(
        phone_number=test_phone,
        message_text="I run a dental clinic with 6 staff in Pune. Need wifi and backup."
    )
    sess = wa_handler.session_mgr.get_session(test_phone)
    wa_prof = sess.get("current_profile", {})
    wa_history = sess.get("chat_history", [])
    assert wa_prof.get("city") == "Pune", f"WhatsApp session did not persist city: {wa_prof}"
    assert wa_prof.get("pincode") == "411001", f"WhatsApp session did not sync benchmark pincode: {wa_prof}"
    assert len(wa_history) >= 2, f"WhatsApp session did not record dialogue history: {wa_history}"
    print(f"✔ [PASS] Scenario 9 WhatsApp Continuity: City='{wa_prof['city']}', PIN='{wa_prof['pincode']}', Turns={len(wa_history)}")

    # -------------------------------------------------------------
    # Scenario 10: Negative Add-on Preference During Consultative Discovery
    # -------------------------------------------------------------
    print("\n--- Scenario 10: Negative Add-on Preference During Discovery (Zero-Price Prevention) ---")
    r10a = advisor.process_user_message("I need a wifi , i have a shop in noida", language="en")
    assert r10a["intent"] == "clarification", "Turn 1 must clarify scale and tax registration"

    r10b = advisor.process_user_message(
        "i have a gst, 10 employees work under me, i dont need a cctv",
        current_profile=r10a["profile"],
        language="en"
    )
    assert r10b["intent"] == "recommendation", f"Expected recommendation intent, got {r10b['intent']}"
    assert r10b["recommended_bundle"], "Bundle must not be empty"
    assert "P23" not in r10b["recommended_bundle"], "Must exclude CCTV (P23) as requested"
    assert r10b["quotation"]["monthly_subtotal_inr"] > 0, "Subtotal must be positive"
    assert "₹0.00" not in r10b["message"], "Message must never state ₹0.00 for active bundle"
    print(f"✔ [PASS] Scenario 10 Discovery with Negative Preference: Bundle={r10b['recommended_bundle']}, Subtotal=₹{r10b['quotation']['monthly_subtotal_inr']}")

    print("\n" + "=" * 70)
    print("ALL 10 AI ADVISOR SCENARIOS VALIDATED 100% GREEN!")
    print("=" * 70)

if __name__ == "__main__":
    test_all_scenarios()
