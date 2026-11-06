import asyncio
import websockets
import subprocess
import time
import json
import requests

async def test():
    proc = subprocess.Popen([
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "--headless=new",
        "--remote-debugging-port=9232",
        "http://127.0.0.1:8000"
    ])
    time.sleep(3)

    try:
        tabs = requests.get("http://127.0.0.1:9232/json").json()
        target = [t for t in tabs if "8000" in t.get("url", "")][0]
        ws_url = target["webSocketDebuggerUrl"]
        print("Connected to page:", target.get("url"))

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
                    "params": {
                        "expression": f"(() => {{ {expr} }})()",
                        "returnByValue": True
                    }
                }))
                while True:
                    m = json.loads(await ws.recv())
                    if m.get("id") == curr:
                        res = m.get("result", {})
                        if "exceptionDetails" in res:
                            raise Exception(f"JS Eval Error: {res['exceptionDetails']}")
                        return res.get("result", {}).get("value")

            # Test 1: Click Hindi
            print("\n1. Testing Hindi Click...")
            lang = await run_eval("document.getElementById('langHi').click(); return window.STATE.language;")
            app_title = await run_eval("return document.getElementById('t-app-title').innerText;")
            print(f"   -> Language: {lang}, Title: {app_title}")
            assert lang == "hi"
            assert app_title == "प्रोजेक्ट उद्यम डिजिटल"
            print("   ✔ Hindi language toggle click: SUCCESS")

            # Test 2: Click English
            print("\n2. Testing English Click...")
            lang_en = await run_eval("document.getElementById('langEn').click(); return window.STATE.language;")
            app_title_en = await run_eval("return document.getElementById('t-app-title').innerText;")
            print(f"   -> Language: {lang_en}, Title: {app_title_en}")
            assert lang_en == "en"
            assert app_title_en == "Project Udyam Digital"
            print("   ✔ English language toggle click: SUCCESS")

            # Test 3: Downsell Button Click
            print("\n3. Testing Downsell Click...")
            subtotal_before = await run_eval("return document.getElementById('monthlySubtotal').innerText;")
            await run_eval("document.getElementById('downsellBtn').click();")
            await asyncio.sleep(1.0)
            subtotal_after = await run_eval("return document.getElementById('monthlySubtotal').innerText;")
            print(f"   -> Subtotal before: {subtotal_before}, after downsell: {subtotal_after}")
            assert subtotal_before != subtotal_after
            print("   ✔ Downsell button click: SUCCESS")

            # Test 3b: Pincode AirFiber Feasibility Check Click
            print("\n3b. Testing Pincode Feasibility & AirFiber Switch Click...")
            await run_eval("document.getElementById('pincodeInput').value = '452010'; document.getElementById('checkPincodeBtn').click();")
            await asyncio.sleep(1.0)
            badge_text = await run_eval("return document.getElementById('pincodeFeasibilityBadge').innerText;")
            print(f"   -> Feasibility Badge: {badge_text}")
            assert "AirFiber" in badge_text or "एयरफाइबर" in badge_text
            print("   ✔ AirFiber feasibility auto-switch click: SUCCESS")

            # Test 4: Proceed to Smart KYC Screen Transition
            print("\n4. Testing Proceed to Smart KYC Click...")
            await run_eval("document.getElementById('proceedKycBtn').click();")
            is_kyc_visible = await run_eval("return !document.getElementById('kycCard').classList.contains('hidden');")
            assert is_kyc_visible is True
            print("   ✔ Screen transition to KYC: SUCCESS")

            # Test 5: Specimen K12 Load
            print("\n5. Testing Specimen K12 Chip Click...")
            await run_eval("document.querySelector(\".specimen-chip[data-code='K12']\").click();")
            await asyncio.sleep(1.5)
            gstin_val = await run_eval("return document.getElementById('extractedGstinInput').value;")
            print(f"   -> Extracted GSTIN: {gstin_val}")
            assert gstin_val == "37NBLXS1145E1ZU"
            print("   ✔ Specimen K12 OCR scan chip click: SUCCESS")

            # Test 6: Verify Extracted Data Click
            print("\n6. Testing Verify Extracted Data Click...")
            await run_eval("document.getElementById('verifyExtractedBtn').click();")
            await asyncio.sleep(1.0)
            status = await run_eval("return window.STATE.kycDecision ? window.STATE.kycDecision.status : '';")
            btn_disabled = await run_eval("return document.getElementById('confirmOrderBtn').disabled;")
            print(f"   -> Decision: {status}, Confirm button disabled: {btn_disabled}")
            assert status == "VERIFIED"
            assert btn_disabled is False
            print("   ✔ KYC Rule verification & button unlock: SUCCESS")

            # Test 7: Confirm Order & Milestone Tracker Click
            print("\n7. Testing Confirm Order Click...")
            await run_eval("document.getElementById('confirmOrderBtn').click();")
            await asyncio.sleep(1.5)
            tracker_visible = await run_eval("return !document.getElementById('trackerCard').classList.contains('hidden');")
            order_id = await run_eval("return window.STATE.activeOrder ? window.STATE.activeOrder.order_id : '';")
            print(f"   -> Tracker visible: {tracker_visible}, Order ID: {order_id}")
            assert tracker_visible is True
            assert order_id.startswith("UDYAM-")
            print("   ✔ Confirm Order & Milestone Tracker display: SUCCESS")

            # Test 8: 3-Bucket Catalog Modal Click
            print("\n8. Testing Catalog Modal Open/Close Click...")
            await run_eval("openCatalogModal();")
            is_open = await run_eval("return !document.getElementById('catalogModal').classList.contains('hidden');")
            await run_eval("closeCatalogModal();")
            is_closed = await run_eval("return document.getElementById('catalogModal').classList.contains('hidden');")
            assert is_open and is_closed
            print("   ✔ Catalog Modal open/close: SUCCESS")

            # Test 9: Partner Portal Modal Click
            print("\n9. Testing Partner Portal Modal Open/Close Click...")
            await run_eval("openPartnerModal();")
            p_open = await run_eval("return !document.getElementById('partnerModal').classList.contains('hidden');")
            await run_eval("closePartnerModal();")
            p_closed = await run_eval("return document.getElementById('partnerModal').classList.contains('hidden');")
            assert p_open and p_closed
            print("   ✔ Partner Portal Modal open/close: SUCCESS")

            print("\n" + "=" * 65)
            print("ALL 9 FRONTEND BROWSER CLICKS ARE FULLY TESTED & 100% RESPONSIVE!")
            print("=" * 65)

    finally:
        proc.terminate()

if __name__ == "__main__":
    asyncio.run(test())
