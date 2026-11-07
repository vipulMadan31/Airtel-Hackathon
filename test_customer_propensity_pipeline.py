import requests
import uuid

BASE_URL = "http://127.0.0.1:8000"

def test_customer_propensity_and_mitra_view():
    print("=================================================================")
    print("TESTING REAL CUSTOMER PROPENSITY TRACKING & MITRA REAL-TIME VIEW")
    print("=================================================================")

    # 1. New Customer Sign Up
    uid = uuid.uuid4().hex[:5]
    cust_email = f"sharma.{uid}@clinic.in"
    cust_name = f"Sharma LifeCare Clinic {uid}"

    signup_res = requests.post(f"{BASE_URL}/api/auth/signup", json={
        "name": cust_name,
        "email": cust_email,
        "phone": "+91 98110 55667",
        "password": "clinicpass123",
        "role": "MERCHANT"
    })
    assert signup_res.status_code == 200, f"Signup failed: {signup_res.text}"
    cust_token = signup_res.json()["access_token"]
    user_id = signup_res.json()["user"]["user_id"]
    print(f"✔ 1. Customer Registered: {cust_name} ({user_id}), Initial Lead Created in SQLite")

    # 2. Customer Activity 1: AI Advisor & Chat
    act1_res = requests.post(
        f"{BASE_URL}/api/leads/activity",
        headers={"Authorization": f"Bearer {cust_token}"},
        json={
            "user_id": user_id,
            "business_name": cust_name,
            "action": "ADVISOR_ENGAGED",
            "city": "Rohtak",
            "pincode": "124001",
            "business_type": "Clinic / Healthcare",
            "employee_count": 10,
            "num_sites": 1
        }
    )
    assert act1_res.status_code == 200
    act1_data = act1_res.json()
    score1 = act1_data["propensity_score"]
    print(f"✔ 2. Chat Engagement: Propensity={score1}/100, Stage={act1_data['stage_reached']}")

    # 3. Customer Activity 2: Bundle Customized
    act2_res = requests.post(
        f"{BASE_URL}/api/leads/activity",
        headers={"Authorization": f"Bearer {cust_token}"},
        json={
            "user_id": user_id,
            "action": "BUNDLE_CUSTOMIZED",
            "monthly_spend_inr": 2397.0,
            "has_gstin": "Y",
            "bundle": {"P02": 1, "P17": 1, "P22": 1}
        }
    )
    assert act2_res.status_code == 200
    act2_data = act2_res.json()
    score2 = act2_data["propensity_score"]
    assert score2 > score1, f"Expected score to increase, got {score2} vs {score1}"
    print(f"✔ 3. Bundle Customized: Propensity={score2}/100, Priority={act2_data['priority']}")

    # 4. Customer Activity 3: KYC Verified
    act3_res = requests.post(
        f"{BASE_URL}/api/leads/activity",
        headers={"Authorization": f"Bearer {cust_token}"},
        json={
            "user_id": user_id,
            "action": "KYC_VERIFIED",
            "has_gstin": "Y"
        }
    )
    assert act3_res.status_code == 200
    act3_data = act3_res.json()
    score3 = act3_data["propensity_score"]
    assert score3 >= score2
    print(f"✔ 4. Smart KYC Verified: Propensity={score3}/100, Stage={act3_data['stage_reached']}")

    # 5. Customer Activity 4: Installation Address Booked
    act4_res = requests.post(
        f"{BASE_URL}/api/leads/activity",
        headers={"Authorization": f"Bearer {cust_token}"},
        json={
            "user_id": user_id,
            "action": "ADDRESS_ENTERED",
            "city": "Rohtak",
            "pincode": "124001"
        }
    )
    assert act4_res.status_code == 200
    act4_data = act4_res.json()
    score4 = act4_data["propensity_score"]
    print(f"✔ 5. Installation Address Booked: Propensity={score4}/100")

    # 6. Customer Activity 5: ₹499 Token Paid
    act5_res = requests.post(
        f"{BASE_URL}/api/leads/activity",
        headers={"Authorization": f"Bearer {cust_token}"},
        json={
            "user_id": user_id,
            "action": "TOKEN_PAID"
        }
    )
    assert act5_res.status_code == 200
    act5_data = act5_res.json()
    score5 = act5_data["propensity_score"]
    assert score5 >= 95, f"Expected propensity >= 95 on token paid, got {score5}"
    print(f"✔ 6. Priority ₹499 Deposit Paid: Propensity={score5}/100 (Fast-Track STP)")

    # 7. Mitra Partner Log In & Lead Retrieval
    mitra_login = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "mitra@airtel.com",
        "password": "airtelmitra",
        "role": "PARTNER"
    })
    assert mitra_login.status_code == 200
    mitra_token = mitra_login.json()["access_token"]

    leads_res = requests.get(
        f"{BASE_URL}/api/partner/leads",
        headers={"Authorization": f"Bearer {mitra_token}"}
    )
    assert leads_res.status_code == 200
    leads = leads_res.json()
    assert len(leads) > 0

    # Verify that real customer lead is present and marked as real-time
    real_leads = [l for l in leads if l.get("is_real_time") or l.get("source") == "LIVE_CUSTOMER"]
    assert len(real_leads) > 0, "Mitra should see real customer leads from SQLite!"
    
    matching_lead = next((l for l in real_leads if l["business_name"] == cust_name), None)
    assert matching_lead is not None, f"Real customer {cust_name} should be visible in Mitra lead queue!"
    assert matching_lead["propensity_score"] == score5
    assert matching_lead["stage_reached"] == "TOKEN_PAID"
    assert matching_lead["city"] == "Rohtak"
    assert matching_lead["pincode"] == "124001"
    print(f"✔ 7. Mitra View Verified: Found Real Customer Lead [{matching_lead['lead_id']}] '{matching_lead['business_name']}', Propensity={matching_lead['propensity_score']}, Routing={matching_lead['routing_label']}")

    # 8. Mitra Claims the Lead
    claim_res = requests.post(
        f"{BASE_URL}/api/partner/leads/{matching_lead['lead_id']}/claim",
        headers={"Authorization": f"Bearer {mitra_token}"}
    )
    assert claim_res.status_code == 200
    print(f"✔ 8. Mitra Claimed Real Lead: Status={claim_res.json()['status']}, Bounty Locked=₹{claim_res.json()['bounty_inr']}")

    # 9. Verify Lead Status Updated to Claimed
    leads_after = requests.get(
        f"{BASE_URL}/api/partner/leads",
        headers={"Authorization": f"Bearer {mitra_token}"}
    ).json()
    claimed_in_queue = next(l for l in leads_after if l["lead_id"] == matching_lead["lead_id"])
    assert claimed_in_queue["is_claimed"] is True
    assert claimed_in_queue["sla_status"] == "CLAIMED"
    print("✔ 9. Real Customer Lead Claim Status Persisted in Database: is_claimed=True, sla_status=CLAIMED")

    print("\n=================================================================")
    print("ALL REAL CUSTOMER PROPENSITY & MITRA QUEUE CHECKS PASSED 100%!")
    print("=================================================================")

if __name__ == "__main__":
    test_customer_propensity_and_mitra_view()

