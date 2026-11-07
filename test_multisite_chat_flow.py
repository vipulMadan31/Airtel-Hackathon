import asyncio
import websockets
import subprocess
import time
import json
import requests

async def test_multisite_flow():
    proc = subprocess.Popen([
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "--headless=new",
        "--remote-debugging-port=9246",
        "http://127.0.0.1:8000"
    ])
    time.sleep(2)

    try:
        tabs = requests.get("http://127.0.0.1:9246/json").json()
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

            # Multi-site message
            await run_eval("""
                document.getElementById('chatInput').value = 'i live in rohtak and have 2 shops. one has 10 employees and the other has 100. I need to install wifi for them';
                document.getElementById('sendBtn').click();
            """)
            await asyncio.sleep(6)

            pin = await run_eval("document.getElementById('pincodeInput').value")
            subtotal = await run_eval("document.getElementById('monthlySubtotal').innerText")
            gst = await run_eval("document.getElementById('gstTotal').innerText")
            grand = await run_eval("document.getElementById('monthlyGrandTotal').innerText")
            chat_html = await run_eval("document.getElementById('chatMessages').innerText")
            items_list = await run_eval("document.getElementById('selectedItemsList').innerText")

            print("=== MULTI-SITE VERIFICATION RESULTS ===")
            print(f"Pincode in UI: {pin}")
            print(f"Subtotal in UI: {subtotal}")
            print(f"GST in UI: {gst}")
            print(f"Grand Total in UI: {grand}")
            print(f"Has WHY WE PICKED THIS: {'WHY WE PICKED THIS' in chat_html}")
            print(f"Items in Drawer:\n{items_list}")

            assert pin == "124001", f"Expected pincode 124001, got {pin}"
            assert "WHY WE PICKED THIS FOR YOUR BUSINESS:" in chat_html, "Missing explainability tags!"
            assert "2 Shops" in items_list or "Shop / Site" in items_list or "P02" in items_list
            assert subtotal != "₹0.00", "Subtotal should not be 0!"

            # Test Remove Add-on button in UI
            print("\nTesting Remove Add-on button (removing P19)...")
            old_subtotal = subtotal
            await run_eval("""
                removeProduct('P19');
            """)
            await asyncio.sleep(2)
            new_subtotal = await run_eval("document.getElementById('monthlySubtotal').innerText")
            print(f"Subtotal before remove: {old_subtotal}, after remove: {new_subtotal}")
            assert new_subtotal != old_subtotal, "Subtotal should have decreased after removing P19!"
            print("✔ MULTI-SITE AND ADD-ON REMOVAL VALIDATED 100% GREEN!")

    finally:
        proc.kill()

if __name__ == "__main__":
    asyncio.run(test_multisite_flow())

