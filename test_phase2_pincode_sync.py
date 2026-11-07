from app.modules.advisor.adapter import AdvisorAdapter
from app.modules.catalog.engine import CatalogEngine
from app.modules.whatsapp.handler import WhatsAppHandler

def test_pincode_city_sync():
    advisor = AdvisorAdapter()
    engine = CatalogEngine()
    wa_handler = WhatsAppHandler()

    print("=================================================================")
    print("TESTING PHASE 2: CONVERSATIONAL PINCODE & CITY SYNCHRONIZATION")
    print("=================================================================")

    # Test 1: City extraction automatically populates benchmark pincode
    res1 = advisor.process_user_message("I run a Kirana / Retail store with 2 staff in Indore.")
    p1 = res1["profile"]
    assert p1["city"] == "Indore", f"Expected Indore, got {p1.get('city')}"
    assert p1["city_tier"] == 2, f"Expected Tier 2, got {p1.get('city_tier')}"
    assert p1["pincode"] == "452001", f"Expected benchmark pincode 452001, got {p1.get('pincode')}"
    print(f"✔ Turn 1 [City -> Pincode]: 'Indore' mapped to PIN {p1['pincode']} (Tier {p1['city_tier']})")

    # Test 2: Explicit 6-digit postal pincode automatically infers city & tier
    res2 = advisor.process_user_message("We are an IT development startup at pincode 201301 with 25 employees.")
    p2 = res2["profile"]
    assert p2["pincode"] == "201301", f"Expected pincode 201301, got {p2.get('pincode')}"
    assert p2["city"] == "Noida", f"Expected inferred city Noida, got {p2.get('city')}"
    assert p2["city_tier"] == 1, f"Expected Tier 1 metro, got {p2.get('city_tier')}"
    print(f"✔ Turn 2 [Pincode -> City]: '201301' mapped to City {p2['city']} (Tier {p2['city_tier']})")

    # Test 3: Various Benchmark Cities
    test_cases = [
        ("We operate a dental clinic in Pune with 6 staff", "Pune", 1, "411001"),
        ("CA office in Jaipur, 8 employees", "Jaipur", 2, "302001"),
        ("Stationery shop in Bhopal with 1 helper", "Bhopal", 2, "462001"),
        ("Kirana store in Rohtak", "Rohtak", 3, "124001"),
        ("Software firm in Bengaluru with 40 staff", "Bengaluru", 1, "560001"),
        ("Multi-site restaurant in Mumbai", "Mumbai", 1, "400001"),
    ]

    for user_msg, exp_city, exp_tier, exp_pin in test_cases:
        r = advisor.process_user_message(user_msg)
        prof = r["profile"]
        assert prof["city"] == exp_city, f"Expected {exp_city}, got {prof.get('city')}"
        assert prof["city_tier"] == exp_tier, f"Expected Tier {exp_tier}, got {prof.get('city_tier')}"
        assert prof["pincode"] == exp_pin, f"Expected {exp_pin}, got {prof.get('pincode')}"
        print(f"✔ Benchmark City: '{exp_city}' -> PIN {exp_pin} (Tier {exp_tier})")

    # Test 4: Catalog Network Feasibility Check (Fiber vs 5G AirFiber)
    feas1 = engine.check_network_feasibility("452001", city="Indore")
    assert feas1["is_fibre_feasible"] is True
    assert feas1["technology"] == "Optical Wireline Fibre (FTTH)"
    assert feas1["city"] == "Indore"
    print(f"✔ Feasibility [452001 / Indore]: Fiber Feasible (FTTH)")

    # Planted unfeasible pincode
    feas2 = engine.check_network_feasibility("452010", city="Indore")
    assert feas2["is_fibre_feasible"] is False
    assert feas2["airfiber_feasible"] is True
    assert "AirFiber" in feas2["technology"]
    assert feas2["recommended_base_id"] == "P04"
    print(f"✔ Feasibility [452010 / Unfeasible Digging]: Switched to 5G AirFiber (P04 @ ₹899/mo)")

    # Test 5: WhatsApp Handler Session Carries Synchronized Pincode
    test_phone = "919876599999"
    wa_handler.session_mgr.reset_session(test_phone)
    wa_res = wa_handler.process_incoming_message(
        phone_number=test_phone,
        message_text="नमस्ते, मेरी इंदौर में 2 कर्मचारियों के साथ किराना दुकान है"
    )
    sess = wa_handler.session_mgr.get_session(test_phone)
    wa_prof = sess.get("current_profile", {})
    assert wa_prof.get("city") == "Indore"
    assert wa_prof.get("pincode") == "452001"
    print(f"✔ WhatsApp Engine Session: Captured City='{wa_prof['city']}', PIN='{wa_prof['pincode']}'")

    print("\n=================================================================")
    print("PHASE 2 CONVERSATIONAL PINCODE & CITY SYNC VALIDATED 100% GREEN!")
    print("=================================================================")

if __name__ == "__main__":
    test_pincode_city_sync()
