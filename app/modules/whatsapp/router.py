import os
import uuid
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, Response, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.modules.whatsapp.handler import WhatsAppHandler
from app.config import UPLOAD_DIR

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp"])
whatsapp_handler = WhatsAppHandler()

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "airtel_udyam_secure_token")

class SimulatorChatRequest(BaseModel):
    phone: str = "919876543210"
    message: Optional[str] = None
    button_payload: Optional[str] = None
    language: Optional[str] = None

@router.get("/webhook")
async def verify_webhook(request: Request):
    """
    Standard Meta WhatsApp Cloud API Webhook Verification Endpoint.
    Validates hub.mode, hub.verify_token, and returns hub.challenge.
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    
    raise HTTPException(status_code=403, detail="Verification token mismatch")

@router.post("/webhook")
async def receive_meta_webhook(request: Request):
    """
    Receives production webhook events from Meta WhatsApp Cloud API.
    Handles user messages, quick reply button clicks, and media notifications.
    """
    try:
        body = await request.json()
    except Exception:
        return {"status": "ignored"}

    entries = body.get("entry", [])
    for entry in entries:
        changes = entry.get("changes", [])
        for ch in changes:
            val = ch.get("value", {})
            messages = val.get("messages", [])
            for msg in messages:
                phone = msg.get("from")
                msg_type = msg.get("type")
                text = None
                button_payload = None

                if msg_type == "text":
                    text = msg.get("text", {}).get("body")
                elif msg_type == "interactive":
                    interactive = msg.get("interactive", {})
                    if interactive.get("type") == "button_reply":
                        button_payload = interactive.get("button_reply", {}).get("id")
                    elif interactive.get("type") == "list_reply":
                        button_payload = interactive.get("list_reply", {}).get("id")
                elif msg_type == "button":
                    button_payload = msg.get("button", {}).get("payload")

                if phone and (text or button_payload):
                    whatsapp_handler.process_incoming_message(
                        phone_number=phone,
                        message_text=text,
                        button_payload=button_payload
                    )

    return {"status": "success"}

@router.api_route("/twilio", methods=["GET", "POST", "HEAD"])
@router.api_route("/twilio/", methods=["GET", "POST", "HEAD"])
async def receive_twilio_webhook(request: Request):
    """
    Production Webhook for Twilio WhatsApp Sandbox / Twilio WhatsApp Numbers.
    Accepts GET, POST, HEAD from Twilio, executes discovery/advisor/KYC,
    and returns a compliant TwiML XML response for direct zero-latency delivery.
    """
    if request.method == "HEAD":
        return Response(status_code=200)

    if request.method == "GET":
        body_text = request.query_params.get("Body", "").strip()
        from_user = request.query_params.get("From", "")
        phone = from_user.replace("whatsapp:", "").strip()
        num_media = 0
        media_url = None
        if not body_text and not phone:
            # Health check from Twilio
            return Response(content="<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response></Response>", media_type="application/xml")
    else:
        form = await request.form()
        from_user = form.get("From", "")
        phone = from_user.replace("whatsapp:", "").strip()
        body_text = form.get("Body", "").strip()
        num_media = int(form.get("NumMedia", 0) or 0)
        media_url = form.get("MediaUrl0")

    print(f"🔥 [TWILIO WEBHOOK HIT] method={request.method} From={from_user} Body='{body_text}'")

    image_path = None
    if num_media > 0 and media_url:
        try:
            import requests as req
            resp = req.get(str(media_url), timeout=15)
            if resp.status_code == 200:
                content_type = form.get("MediaContentType0", "image/jpeg")
                ext = ".png" if "png" in content_type else ".jpg"
                file_id = f"twilio_{uuid.uuid4().hex[:8]}{ext}"
                saved_path = UPLOAD_DIR / file_id
                with open(saved_path, "wb") as f:
                    f.write(resp.content)
                image_path = str(saved_path)
        except Exception as e:
            print("Twilio media download error:", e)

    result = whatsapp_handler.process_incoming_message(
        phone_number=phone or "twilio_user",
        message_text=body_text if not image_path else None,
        image_path=image_path
    )

    messages = result.get("messages", [])
    buttons = result.get("buttons", [])

    # Compose all messages into single TwiML message
    combined_body = "\n\n".join(messages)
    if buttons:
        btn_hints = "\n".join([f"👉 *{b['title']}* (Reply: {b['payload']})" for b in buttons])
        combined_body += f"\n\n*Quick Actions:*\n{btn_hints}"

    # Return valid TwiML XML
    escaped_body = (
        combined_body.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    twiml_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>
        <Body>{escaped_body}</Body>
    </Message>
</Response>"""
    return Response(content=twiml_xml, media_type="application/xml")

@router.post("/simulate")
async def simulate_chat(req: SimulatorChatRequest):
    """
    Interactive Simulator API for in-browser testing of the WhatsApp bot.
    Allows testing full natural language discovery, feasibility inquiries, down-sells, and button taps.
    """
    result = whatsapp_handler.process_incoming_message(
        phone_number=req.phone,
        message_text=req.message,
        button_payload=req.button_payload,
        language_override=req.language
    )
    session = whatsapp_handler.session_mgr.get_session(req.phone)
    return {
        "status": "success",
        "phone": req.phone,
        "responses": result.get("messages", []),
        "buttons": result.get("buttons", []),
        "session": session
    }

@router.post("/simulate/upload")
async def simulate_document_upload(
    phone: str = Form("919876543210"),
    language: str = Form("en"),
    file: UploadFile = File(...)
):
    """
    Simulates a user sending a photo (Electricity bill, GST certificate, etc.) inside WhatsApp.
    Executes real-time OpenCV blur check, Tesseract OCR, and statutory KYC validation.
    """
    file_id = f"wa_{uuid.uuid4().hex[:8]}_{file.filename}"
    saved_path = UPLOAD_DIR / file_id

    with open(saved_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    result = whatsapp_handler.process_incoming_message(
        phone_number=phone,
        image_path=str(saved_path),
        language_override=language
    )
    session = whatsapp_handler.session_mgr.get_session(phone)
    return {
        "status": "success",
        "phone": phone,
        "responses": result.get("messages", []),
        "buttons": result.get("buttons", []),
        "session": session
    }

@router.get("/session/{phone}")
def get_session_info(phone: str):
    """
    Retrieves the current state of a WhatsApp conversation session.
    """
    return whatsapp_handler.session_mgr.get_session(phone)

@router.get("/token/{token}")
def get_token_session(token: str):
    """
    Returns the pre-filled bundle, quote, and customer profile associated with a WhatsApp lead token.
    Enables zero-friction handoff to the web portal for DoT-compliant Smart KYC.
    """
    import json
    suffix = token.replace("TK-", "").replace("token_", "")
    with whatsapp_handler.session_mgr._get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM whatsapp_sessions WHERE phone_number LIKE ?", (f"%{suffix}",))
        row = cur.fetchone()
        if row:
            bundle_data = json.loads(row["active_bundle"] or "{}")
            if not bundle_data:
                bundle_data = {"P01": 1}
            return {
                "status": "success",
                "token": token,
                "phone_number": row["phone_number"],
                "stage": row["current_stage"],
                "profile": json.loads(row["current_profile"] or "{}"),
                "bundle": bundle_data,
                "quote": json.loads(row["active_quote"] or "{}")
            }

    # Fallback to standard starter bundle
    return {
        "status": "fallback",
        "token": token,
        "bundle": {"P01": 1, "P07": 2, "P19": 1},
        "profile": {"business_type": "Retail", "city": "Indore", "employee_count": 3}
    }
