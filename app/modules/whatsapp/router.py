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
