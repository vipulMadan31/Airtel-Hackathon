import asyncio
import websockets
import subprocess
import time
import json
import requests

async def test_tabs():
    proc = subprocess.Popen([
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "--headless=new",
        "--remote-debugging-port=9233",
        "http://127.0.0.1:8000"
    ])
    time.sleep(3)

    try:
        tabs = requests.get("http://127.0.0.1:9233/json").json()
        target = [t for t in tabs if "8000" in t.get("url", "")][0]
        ws_url = target["webSocketDebuggerUrl"]

        async with websockets.connect(ws_url) as ws:
            await ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))

            eval_id = 200
            async def run_eval(expr):
                nonlocal eval_id
                eval_id += 1
                curr = eval_id
                await ws.send(json.dumps({
                    "id": curr,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": f"(async () => {{ {expr} }})()",
                        "awaitPromise": True,
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

            # Wait for ready
            for _ in range(20):
                ready = await run_eval("return document.readyState === 'complete';")
                if ready:
                    break
                await asyncio.sleep(0.5)

            # Test Nav Tab Partner
            print("\n1. Testing Click on Top Tab 'Airtel Mitra Partner'...")
            res1 = await run_eval("""
                document.getElementById('navTabPartner').click();
                await new Promise(r => setTimeout(r, 400));
                return {
                    role: window.STATE.auth.role,
                    custHidden: document.getElementById('customerView').classList.contains('hidden'),
                    mitraHidden: document.getElementById('mitraView').classList.contains('hidden'),
                    url: window.location.pathname
                };
            """)
            print("   -> Tab Click Result:", res1)
            assert res1["role"] == "PARTNER"
            assert res1["custHidden"] is True, "customerView must be hidden for partner!"
            assert res1["mitraHidden"] is False, "mitraView must be visible for partner!"

            # Test Nav Tab Admin
            print("\n2. Testing Click on Top Tab 'Enterprise Ops Admin'...")
            res2 = await run_eval("""
                document.getElementById('navTabAdmin').click();
                await new Promise(r => setTimeout(r, 400));
                return {
                    role: window.STATE.auth.role,
                    custHidden: document.getElementById('customerView').classList.contains('hidden'),
                    opsHidden: document.getElementById('opsView').classList.contains('hidden'),
                    url: window.location.pathname
                };
            """)
            print("   -> Tab Click Result:", res2)
            assert res2["role"] == "ADMIN"
            assert res2["custHidden"] is True, "customerView must be hidden for admin!"
            assert res2["opsHidden"] is False, "opsView must be visible for admin!"

            # Test Nav Tab Customer
            print("\n3. Testing Click on Top Tab 'Customer Self-Serve'...")
            res3 = await run_eval("""
                document.getElementById('navTabMerchant').click();
                await new Promise(r => setTimeout(r, 400));
                return {
                    role: window.STATE.auth.role,
                    custHidden: document.getElementById('customerView').classList.contains('hidden'),
                    opsHidden: document.getElementById('opsView').classList.contains('hidden'),
                    mitraHidden: document.getElementById('mitraView').classList.contains('hidden')
                };
            """)
            print("   -> Tab Click Result:", res3)
            assert res3["role"] == "MERCHANT"
            assert res3["custHidden"] is False, "customerView must be visible for merchant!"
            assert res3["opsHidden"] is True
            assert res3["mitraHidden"] is True

            print("\n=======================================================")
            print("ALL TOP NAVIGATION TABS CLICK & SWITCH 100% PERFECTLY!")
            print("=======================================================")

    finally:
        proc.kill()

if __name__ == "__main__":
    asyncio.run(test_tabs())

