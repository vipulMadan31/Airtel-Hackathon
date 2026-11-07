import requests
import uuid

BASE_URL = "http://127.0.0.1:8000"

def test_auth():
    uid = uuid.uuid4().hex[:6]
    test_email = f"sharma.{uid}@example.com"
    
    # 1. Test Customer Signup
    signup_data = {
        "email": test_email,
        "password": "sharmapassword123",
        "name": "Sharma General Stores",
        "phone": "+91 98765 43210"
    }
    r_signup = requests.post(f"{BASE_URL}/api/auth/signup", json=signup_data)
    print("Signup status:", r_signup.status_code, r_signup.json().get("user", {}).get("email"))
    assert r_signup.status_code == 200, r_signup.text
    token = r_signup.json()["access_token"]

    # 2. Test Customer Login
    login_data = {
        "email": test_email,
        "password": "sharmapassword123",
        "role": "MERCHANT"
    }
    r_login = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
    print("Login status:", r_login.status_code, r_login.json().get("user", {}).get("name"))
    assert r_login.status_code == 200

    # 3. Test Customer Wrong Password
    r_wrong = requests.post(f"{BASE_URL}/api/auth/login", json={"email": test_email, "password": "wrong"})
    print("Wrong password status:", r_wrong.status_code, r_wrong.json())
    assert r_wrong.status_code == 401

    # 4. Test Admin Login with 'airteladmin'
    r_admin = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@airtel.com", "password": "airteladmin", "role": "ADMIN"})
    print("Admin login status:", r_admin.status_code, r_admin.json().get("user", {}).get("role"))
    assert r_admin.status_code == 200
    assert r_admin.json()["user"]["role"] == "ADMIN"

    # 5. Test Admin Wrong Password
    r_admin_wrong = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@airtel.com", "password": "wrongpass", "role": "ADMIN"})
    print("Admin wrong password status:", r_admin_wrong.status_code)
    assert r_admin_wrong.status_code == 401

    # 6. Test Mitra Login with 'airtelmitra'
    r_mitra = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "mitra@airtel.com", "password": "airtelmitra", "role": "PARTNER"})
    print("Mitra login status:", r_mitra.status_code, r_mitra.json().get("user", {}).get("role"))
    assert r_mitra.status_code == 200
    assert r_mitra.json()["user"]["role"] == "PARTNER"

    # 7. Test Mitra Wrong Password
    r_mitra_wrong = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "mitra@airtel.com", "password": "wrongpass", "role": "PARTNER"})
    print("Mitra wrong password status:", r_mitra_wrong.status_code)
    assert r_mitra_wrong.status_code == 401

    # 8. Test OAuth2 Token Password Flow (/api/auth/token)
    r_oa = requests.post(f"{BASE_URL}/api/auth/token", data={"username": "admin@airtel.com", "password": "airteladmin", "scope": "ADMIN"})
    print("OAuth2 Token flow status:", r_oa.status_code, r_oa.json().get("token_type"))
    assert r_oa.status_code == 200
    assert r_oa.json()["token_type"] == "bearer"
    oa_token = r_oa.json()["access_token"]

    # 9. Test /api/auth/me with Bearer token
    r_me = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {oa_token}"})
    print("/api/auth/me status:", r_me.status_code, r_me.json().get("role"))
    assert r_me.status_code == 200
    assert r_me.json()["role"] == "ADMIN"

    # 10. Test Role RBAC with new token
    r_ops_metrics = requests.get(f"{BASE_URL}/api/admin/metrics", headers={"Authorization": f"Bearer {oa_token}"})
    assert r_ops_metrics.status_code == 200
    print("Admin metrics with OAuth token status:", r_ops_metrics.status_code)

    # 11. Test Customer token blocked from Admin metrics
    r_cust_blocked = requests.get(f"{BASE_URL}/api/admin/metrics", headers={"Authorization": f"Bearer {token}"})
    assert r_cust_blocked.status_code == 403
    print("Customer blocked from Admin metrics:", r_cust_blocked.status_code)

    # 12. Test Logout
    r_logout = requests.post(f"{BASE_URL}/api/auth/logout", headers={"Authorization": f"Bearer {oa_token}"})
    assert r_logout.status_code == 200
    print("Logout status:", r_logout.status_code)

    print("✔ ALL BACKEND AUTH API ENDPOINTS VERIFIED 100% GREEN!")

if __name__ == "__main__":
    test_auth()
