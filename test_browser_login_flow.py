import asyncio
import websockets
import subprocess
import time
import json
import requests
import uuid

async def test_login_flow():
    proc = subprocess.Popen([
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "--headless=new",
        "--remote-debugging-port=9247",
        "http://127.0.0.1:8000"
    ])
    time.sleep(2)

    try:
        tabs = requests.get("http://127.0.0.1:9247/json").json()
        target = [t for t in tabs if "8000" in t.get("url", "")][0]
        ws_url = target["webSocketDebuggerUrl"]

        async with websockets.connect(ws_url) as ws:
            await ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))

            eval_id = 100
            async def run_eval(expr):
                nonlocal eval_id
                eval_id += 1
                curr = eval_id
                await ws.send(json.dumps({
                    "id": curr,
                    "method": "Runtime.evaluate",
                    "params": {"expression": expr, "returnByValue": True, "awaitPromise": True}
                }))
                while True:
                    resp = json.loads(await ws.recv())
                    if resp.get("id") == curr:
                        return resp.get("result", {}).get("result", {}).get("value")

            print("\n1. Testing Open Auth Modal...")
            await run_eval("document.getElementById('openAuthModalBtn').click();")
            await asyncio.sleep(0.5)
            is_modal_visible = await run_eval("!document.getElementById('authModal').classList.contains('hidden');")
            print("   Auth Modal Visible:", is_modal_visible)
            assert is_modal_visible is True, "Auth modal should be visible"

            print("\n2. Testing Customer Login with demo credentials...")
            await run_eval("""
                document.getElementById('loginCustEmail').value = 'rajesh@kirana.com';
                document.getElementById('loginCustPassword').value = 'customer123';
                document.getElementById('submitCustLoginBtn').click();
            """)
            await asyncio.sleep(1.5)
            badge_name = await run_eval("document.getElementById('userAuthName').innerText;")
            print("   Logged In User Badge:", badge_name)
            assert "Rajesh" in badge_name, f"Expected Rajesh in user badge, got {badge_name}"

            print("\n3. Testing Logout...")
            await run_eval("document.getElementById('logoutBtn').click();")
            await asyncio.sleep(1)
            is_modal_open_after_logout = await run_eval("!document.getElementById('authModal').classList.contains('hidden');")
            print("   Auth Modal Reopened on Logout:", is_modal_open_after_logout)

            print("\n4. Testing New Customer Sign Up...")
            uid = uuid.uuid4().hex[:5]
            new_email = f"verma.{uid}@stores.in"
            await run_eval(f"""
                document.getElementById('custSubTabSignup').click();
                document.getElementById('signupCustName').value = 'Verma Electricals {uid}';
                document.getElementById('signupCustEmail').value = '{new_email}';
                document.getElementById('signupCustPhone').value = '+91 98765 11223';
                document.getElementById('signupCustPassword').value = 'vermapass123';
                document.getElementById('signupCustConfirmPassword').value = 'vermapass123';
                document.getElementById('submitCustSignupBtn').click();
            """)
            await asyncio.sleep(2)
            new_badge_name = await run_eval("document.getElementById('userAuthName').innerText;")
            print("   Signed Up User Badge:", new_badge_name)
            assert "Verma Electricals" in new_badge_name

            print("\n5. Testing Mitra Partner Login with fixed password 'airtelmitra'...")
            await run_eval("document.getElementById('openAuthModalBtn').click();")
            await asyncio.sleep(0.5)
            await run_eval("document.getElementById('authTabPartner').click();")
            await asyncio.sleep(0.5)

            # Test wrong password first
            await run_eval("""
                document.getElementById('loginMitraEmail').value = 'mitra@airtel.com';
                document.getElementById('loginMitraPassword').value = 'wrongpassword';
                document.getElementById('submitMitraLoginBtn').click();
            """)
            await asyncio.sleep(1)
            alert_text = await run_eval("document.getElementById('authAlertMsg').innerText;")
            print("   Mitra Wrong Password Alert:", alert_text)
            assert "airtelmitra" in alert_text.lower() or "failed" in alert_text.lower()

            # Now submit correct fixed password 'airtelmitra'
            await run_eval("""
                document.getElementById('fillDemoMitraBtn').click();
                document.getElementById('submitMitraLoginBtn').click();
            """)
            await asyncio.sleep(2)
            mitra_badge_name = await run_eval("document.getElementById('userAuthName').innerText;")
            mitra_view_visible = await run_eval("!document.getElementById('mitraView').classList.contains('hidden');")
            print("   Mitra Partner Badge:", mitra_badge_name)
            print("   Mitra View Active:", mitra_view_visible)
            assert "Vikram" in mitra_badge_name or "Mitra" in mitra_badge_name
            assert mitra_view_visible is True, "Mitra view should be active"

            print("\n6. Testing Admin Login with fixed password 'airteladmin'...")
            await run_eval("document.getElementById('openAuthModalBtn').click();")
            await asyncio.sleep(0.5)
            await run_eval("document.getElementById('authTabAdmin').click();")
            await asyncio.sleep(0.5)

            # Test wrong password first
            await run_eval("""
                document.getElementById('loginAdminEmail').value = 'admin@airtel.com';
                document.getElementById('loginAdminPassword').value = 'badpassword';
                document.getElementById('submitAdminLoginBtn').click();
            """)
            await asyncio.sleep(1)
            admin_alert_text = await run_eval("document.getElementById('authAlertMsg').innerText;")
            print("   Admin Wrong Password Alert:", admin_alert_text)
            assert "airteladmin" in admin_alert_text.lower() or "failed" in admin_alert_text.lower()

            # Now submit correct fixed password 'airteladmin'
            await run_eval("""
                document.getElementById('fillDemoAdminBtn').click();
                document.getElementById('submitAdminLoginBtn').click();
            """)
            await asyncio.sleep(2)
            admin_badge_name = await run_eval("document.getElementById('userAuthName').innerText;")
            ops_view_visible = await run_eval("!document.getElementById('opsView').classList.contains('hidden');")
            print("   Admin Badge:", admin_badge_name)
            print("   Ops Admin View Active:", ops_view_visible)
            assert "Priya" in admin_badge_name or "Admin" in admin_badge_name
            assert ops_view_visible is True, "Ops Admin view should be active"

            print("\n7. Testing Direct /login Route Navigation...")
            await run_eval("window.location.href = 'http://127.0.0.1:8000/login';")
            await asyncio.sleep(2)
            login_modal_auto_opened = await run_eval("!document.getElementById('authModal').classList.contains('hidden');")
            print("   /login Route Auto-Opens Auth Modal:", login_modal_auto_opened)
            assert login_modal_auto_opened is True

            print("\n=======================================================")
            print("ALL LOGIN, SIGN UP, MITRA & ADMIN FLOWS ARE 100% GREEN!")
            print("=======================================================")

    finally:
        proc.kill()

if __name__ == "__main__":
    asyncio.run(test_login_flow())
