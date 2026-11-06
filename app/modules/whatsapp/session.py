import sqlite3
import json
from typing import Dict, Any, Optional, List
from app.config import DB_PATH

class WhatsAppSessionManager:
    """
    Manages persistent stateful sessions for WhatsApp numbers.
    Tracks discovery profile, bundle, active quote, uploaded KYC documents, and order status.
    """
    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        self._init_table()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_table(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS whatsapp_sessions (
                    phone_number TEXT PRIMARY KEY,
                    current_stage TEXT NOT NULL DEFAULT 'DISCOVERY',
                    language TEXT NOT NULL DEFAULT 'en',
                    current_profile TEXT,
                    active_bundle TEXT,
                    active_quote TEXT,
                    kyc_data TEXT,
                    order_id TEXT,
                    chat_history TEXT,
                    last_interaction DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            try:
                conn.execute("ALTER TABLE whatsapp_sessions ADD COLUMN chat_history TEXT")
                conn.commit()
            except Exception:
                pass

    def get_session(self, phone: str) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM whatsapp_sessions WHERE phone_number = ?", (phone,))
            row = cur.fetchone()
            if not row:
                # Create initial fresh session
                default_profile = {
                    "business_type": None,
                    "employee_count": None,
                    "city": None,
                    "city_tier": None,
                    "has_gstin": None
                }
                cur.execute("""
                    INSERT INTO whatsapp_sessions (phone_number, current_stage, language, current_profile, active_bundle, chat_history)
                    VALUES (?, 'DISCOVERY', 'en', ?, '{}', '[]')
                """, (phone, json.dumps(default_profile)))
                conn.commit()
                return {
                    "phone_number": phone,
                    "current_stage": "DISCOVERY",
                    "language": "en",
                    "current_profile": default_profile,
                    "active_bundle": {},
                    "active_quote": None,
                    "kyc_data": None,
                    "order_id": None,
                    "chat_history": []
                }

            chat_hist = []
            try:
                if "chat_history" in row.keys() and row["chat_history"]:
                    chat_hist = json.loads(row["chat_history"])
            except Exception:
                chat_hist = []

            return {
                "phone_number": row["phone_number"],
                "current_stage": row["current_stage"],
                "language": row["language"],
                "current_profile": json.loads(row["current_profile"] or "{}"),
                "active_bundle": json.loads(row["active_bundle"] or "{}"),
                "active_quote": json.loads(row["active_quote"]) if row["active_quote"] else None,
                "kyc_data": json.loads(row["kyc_data"]) if row["kyc_data"] else None,
                "order_id": row["order_id"],
                "chat_history": chat_hist
            }

    def update_session(
        self,
        phone: str,
        stage: Optional[str] = None,
        language: Optional[str] = None,
        profile: Optional[Dict[str, Any]] = None,
        bundle: Optional[Dict[str, int]] = None,
        quote: Optional[Dict[str, Any]] = None,
        kyc_data: Optional[Dict[str, Any]] = None,
        order_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        curr = self.get_session(phone)
        new_stage = stage if stage is not None else curr["current_stage"]
        new_lang = language if language is not None else curr["language"]
        new_profile = profile if profile is not None else curr["current_profile"]
        new_bundle = bundle if bundle is not None else curr["active_bundle"]
        new_quote = quote if quote is not None else curr["active_quote"]
        new_kyc = kyc_data if kyc_data is not None else curr["kyc_data"]
        new_order = order_id if order_id is not None else curr["order_id"]
        new_chat = chat_history if chat_history is not None else curr.get("chat_history", [])

        with self._get_connection() as conn:
            conn.execute("""
                UPDATE whatsapp_sessions
                SET current_stage = ?,
                    language = ?,
                    current_profile = ?,
                    active_bundle = ?,
                    active_quote = ?,
                    kyc_data = ?,
                    order_id = ?,
                    chat_history = ?,
                    last_interaction = CURRENT_TIMESTAMP
                WHERE phone_number = ?
            """, (
                new_stage,
                new_lang,
                json.dumps(new_profile),
                json.dumps(new_bundle),
                json.dumps(new_quote) if new_quote else None,
                json.dumps(new_kyc) if new_kyc else None,
                new_order,
                json.dumps(new_chat[-14:]) if new_chat else "[]",
                phone
            ))
            conn.commit()

        return self.get_session(phone)

    def reset_session(self, phone: str):
        with self._get_connection() as conn:
            default_profile = {
                "business_type": None,
                "employee_count": None,
                "city": None,
                "city_tier": None,
                "has_gstin": None
            }
            conn.execute("""
                UPDATE whatsapp_sessions
                SET current_stage = 'DISCOVERY',
                    current_profile = ?,
                    active_bundle = '{}',
                    active_quote = NULL,
                    kyc_data = NULL,
                    order_id = NULL,
                    chat_history = '[]',
                    last_interaction = CURRENT_TIMESTAMP
                WHERE phone_number = ?
            """, (json.dumps(default_profile), phone))
            conn.commit()
        return self.get_session(phone)
