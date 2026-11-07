import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from app.config import DB_PATH

class OrderStateMachine:
    def __init__(self):
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                business_name TEXT,
                contact_phone TEXT,
                language TEXT,
                bundle_json TEXT,
                monthly_total REAL,
                kyc_status TEXT,
                current_milestone INTEGER,
                scheduled_install_date TEXT,
                engineer_name TEXT,
                engineer_phone TEXT,
                nps_rating INTEGER,
                created_at TEXT
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS consent_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT,
                data_items TEXT,
                purpose TEXT,
                action TEXT,
                timestamp TEXT
            )
            """)
            
            # Dynamic schema migrations for payment columns
            cursor = conn.execute("PRAGMA table_info(orders)")
            cols = [col[1] for col in cursor.fetchall()]
            if "token_paid" not in cols:
                conn.execute("ALTER TABLE orders ADD COLUMN token_paid INTEGER DEFAULT 0")
            if "token_amount_inr" not in cols:
                conn.execute("ALTER TABLE orders ADD COLUMN token_amount_inr REAL DEFAULT 0.0")
            if "payment_txn_id" not in cols:
                conn.execute("ALTER TABLE orders ADD COLUMN payment_txn_id TEXT")
            if "payment_method" not in cols:
                conn.execute("ALTER TABLE orders ADD COLUMN payment_method TEXT")
            if "receipt_json" not in cols:
                conn.execute("ALTER TABLE orders ADD COLUMN receipt_json TEXT")
            if "partner_attribution_id" not in cols:
                conn.execute("ALTER TABLE orders ADD COLUMN partner_attribution_id TEXT")
            if "installation_address" not in cols:
                conn.execute("ALTER TABLE orders ADD COLUMN installation_address TEXT")
            conn.commit()

    def create_order(
        self,
        business_name: str,
        contact_phone: str,
        bundle_data: Dict[str, Any],
        kyc_status: str = "VERIFIED",
        language: str = "en",
        typical_install_days: int = 5,
        partner_id: Optional[str] = None,
        installation_address: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        order_id = f"UDYAM-{uuid.uuid4().hex[:6].upper()}"
        install_date = (datetime.now() + timedelta(days=typical_install_days)).strftime("%Y-%m-%d")

        with self._get_connection() as conn:
            conn.execute("""
            INSERT INTO orders (
                order_id, business_name, contact_phone, language,
                bundle_json, monthly_total, kyc_status, current_milestone,
                scheduled_install_date, engineer_name, engineer_phone, nps_rating, 
                partner_attribution_id, installation_address, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id,
                business_name,
                contact_phone,
                language,
                json.dumps(bundle_data),
                bundle_data.get("total_monthly_inr", 0.0),
                kyc_status,
                3, # Milestone 3: Order Confirmed / Scheduled
                install_date,
                "Ramesh Sharma (Field Lead)",
                "+91 98765 43210",
                None,
                partner_id,
                json.dumps(installation_address) if installation_address else None,
                datetime.now().isoformat()
            ))

            # Log DPDP Rule 3 Consent Event
            conn.execute("""
            INSERT INTO consent_logs (order_id, data_items, purpose, action, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """, (
                order_id,
                "GSTIN, Udyam Registration, Principal Address Proof, Signatory ID",
                "DoT Subscriber Verification and Optical Line Installation",
                "EXPLICIT_AFFIRMATIVE_CONSENT_GIVEN",
                datetime.now().isoformat()
            ))
            conn.commit()

        return self.get_order(order_id)

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            res["bundle"] = json.loads(res["bundle_json"])
            res["dpdp_consent_recorded"] = True
            res["is_assisted"] = bool(res.get("partner_attribution_id"))
            if res.get("receipt_json"):
                try:
                    res["receipt"] = json.loads(res["receipt_json"])
                except Exception:
                    res["receipt"] = None
            else:
                res["receipt"] = None

            if res.get("installation_address"):
                try:
                    res["installation_address"] = json.loads(res["installation_address"])
                except Exception:
                    pass
            return res

    def record_payment(
        self,
        order_id: str,
        amount_inr: float,
        txn_id: str,
        payment_method: str,
        receipt: Dict[str, Any]
    ) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("""
            UPDATE orders 
            SET token_paid = 1,
                token_amount_inr = ?,
                payment_txn_id = ?,
                payment_method = ?,
                receipt_json = ?
            WHERE order_id = ?
            """, (
                amount_inr,
                txn_id,
                payment_method,
                json.dumps(receipt),
                order_id
            ))
            conn.commit()
            return cursor.rowcount > 0

    def reschedule_installation(self, order_id: str, new_date: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE orders SET scheduled_install_date = ? WHERE order_id = ?",
                (new_date, order_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def record_nps(self, order_id: str, rating: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE orders SET nps_rating = ?, current_milestone = 5 WHERE order_id = ?",
                (rating, order_id)
            )
            conn.commit()
            return cursor.rowcount > 0

