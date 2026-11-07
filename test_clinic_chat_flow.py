import asyncio
import websockets
import subprocess
import time
import json
import requests

async def test_clinic_flow():
    proc = subprocess.Popen([
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "--headless=new",
        "--remote-debugging-port=9245",
        "http://127.0.0.1:8000"
    ])
    time.sleep(2)

    try:
        tabs = requests.get("http://127.0.0.1:9245/json").json()
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

            # Turn 1: "Hi, I live in rohtak and need wifi"
            await run_eval("""
                document.getElementById('chatInput').value = 'Hi, I live in rohtak and need wifi';
                document.getElementById('sendBtn').click();
            """)
            await asyncio.sleep(5)

            # Turn 2: "I run a clinic and have 10 staff members"
            await run_eval("""
                document.getElementById('chatInput').value = 'I run a clinic and have 10 staff members';
                document.getElementById('sendBtn').click();
            """)
            await asyncio.sleep(7)

            pin = await run_eval("document.getElementById('pincodeInput').value")
            subtotal = await run_eval("document.getElementById('monthlySubtotal').innerText")
            gst = await run_eval("document.getElementById('gstTotal').innerText")
            grand = await run_eval("document.getElementById('monthlyGrandTotal').innerText")
            chat_html = await run_eval("document.getElementById('chatMessages').innerText")
            items_list = await run_eval("document.getElementById('selectedItemsList').innerText")

            print("=== VERIFICATION RESULTS ===")
            print(f"Pincode in UI: {pin}")
            print(f"Subtotal in UI: {subtotal}")
            print(f"GST in UI: {gst}")
            print(f"Grand Total in UI: {grand}")
            print(f"Has WHY WE PICKED THIS: {'WHY WE PICKED THIS' in chat_html}")
            print(f"Items in Drawer:\n{items_list}")

            assert pin == "124001", f"Expected pincode 124001, got {pin}"
            assert "WHY WE PICKED THIS FOR YOUR BUSINESS:" in chat_html, "Missing explainability tags!"
            assert "₹2,397.00" in subtotal or "2397" in subtotal, f"Expected subtotal ₹2,397.00, got {subtotal}"
            assert "₹2,828.46 / mo" in grand or "2828" in grand, f"Expected total ₹2,828.46 / mo, got {grand}"
            print("✔ ALL ASSERTIONS PASSED PERFECTLY!")

    finally:
        proc.kill()

if __name__ == "__main__":
    asyncio.run(test_clinic_flow())
