"""
Post-Activation Retention and Customer Support Service
Manages customer support ticketing, lifecycle milestones, and post-activation feedback.
Identifies dissatisfied customers for proactive retention follow-up.
"""

import os
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from contextlib import contextmanager
from app.config import DB_PATH

class SupportService:
    _instance = None

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        self._init_db()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=30000;")
        conn.execute("PRAGMA journal_mode=WAL;")
        try:
            yield conn
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                ticket_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                customer_email TEXT,
                order_id TEXT,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN',
                resolution_milestone TEXT NOT NULL DEFAULT 'TICKET_LOGGED',
                admin_notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolved_at TEXT
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS customer_feedback (
                feedback_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                customer_email TEXT,
                order_id TEXT,
                rating INTEGER NOT NULL,
                feedback_type TEXT NOT NULL DEFAULT 'POST_ACTIVATION_CSAT',
                comments TEXT,
                is_dissatisfied INTEGER DEFAULT 0,
                follow_up_status TEXT DEFAULT 'NOT_REQUIRED',
                follow_up_notes TEXT,
                created_at TEXT NOT NULL
            )
            """)
            conn.commit()

    def create_ticket(
        self,
        user_id: str,
        category: str,
        priority: str,
        subject: str,
        description: str,
        customer_email: Optional[str] = None,
        order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        valid_categories = ["CONNECTIVITY", "BILLING", "INSTALLATION", "EQUIPMENT", "GENERAL"]
        valid_priorities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

        cat = category.strip().upper()
        if cat not in valid_categories:
            cat = "GENERAL"

        prio = priority.strip().upper()
        if prio not in valid_priorities:
            prio = "MEDIUM"

        ticket_id = f"TICK-{uuid.uuid4().hex[:6].upper()}"
        now_ts = datetime.now().isoformat()

        with self._get_connection() as conn:
            conn.execute("""
            INSERT INTO support_tickets (
                ticket_id, user_id, customer_email, order_id,
                category, priority, subject, description,
                status, resolution_milestone, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', 'TICKET_LOGGED', ?, ?)
            """, (
                ticket_id, user_id, customer_email or "", order_id or "",
                cat, prio, subject.strip(), description.strip(),
                now_ts, now_ts
            ))
            conn.commit()

        return self.get_ticket(ticket_id)

    def _format_ticket(self, row) -> Optional[Dict[str, Any]]:
        if not row:
            return None
        d = dict(row)
        d["current_milestone"] = d.get("resolution_milestone")
        return d

    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM support_tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
            return self._format_ticket(row)

    def get_user_tickets(self, user_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM support_tickets WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            ).fetchall()
            return [self._format_ticket(r) for r in rows if r]

    def get_all_tickets(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM support_tickets WHERE status = ? ORDER BY created_at DESC",
                    (status.upper(),)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM support_tickets ORDER BY created_at DESC").fetchall()
            return [self._format_ticket(r) for r in rows if r]

    def update_ticket_milestone(
        self,
        ticket_id: str,
        status: str,
        resolution_milestone: str,
        admin_notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        valid_statuses = ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]
        st = status.upper().strip()
        if st not in valid_statuses:
            raise ValueError(f"Invalid ticket status: {status}")

        now_ts = datetime.now().isoformat()
        resolved_ts = now_ts if st in ["RESOLVED", "CLOSED"] else None

        with self._get_connection() as conn:
            conn.execute("""
            UPDATE support_tickets
            SET status = ?, resolution_milestone = ?, admin_notes = COALESCE(?, admin_notes),
                updated_at = ?, resolved_at = COALESCE(?, resolved_at)
            WHERE ticket_id = ?
            """, (st, resolution_milestone, admin_notes, now_ts, resolved_ts, ticket_id))
            conn.commit()

        return self.get_ticket(ticket_id)

    def submit_feedback(
        self,
        user_id: str,
        rating: int,
        feedback_type: str = "POST_ACTIVATION_CSAT",
        comments: Optional[str] = None,
        customer_email: Optional[str] = None,
        order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            r_val = max(1, min(10, int(rating)))
        except (ValueError, TypeError):
            r_val = 5

        # Rating <= 3 on a 5-star or <= 6 on a 10-star scale indicates customer dissatisfaction
        threshold = 3 if r_val <= 5 else 6
        is_dissatisfied = 1 if r_val <= threshold else 0
        follow_up = "PENDING_RETENTION_OUTREACH" if is_dissatisfied else "NOT_REQUIRED"

        feedback_id = f"FB-{uuid.uuid4().hex[:6].upper()}"
        now_ts = datetime.now().isoformat()

        with self._get_connection() as conn:
            conn.execute("""
            INSERT INTO customer_feedback (
                feedback_id, user_id, customer_email, order_id,
                rating, feedback_type, comments,
                is_dissatisfied, follow_up_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                feedback_id, user_id, customer_email or "", order_id or "",
                r_val, feedback_type, (comments or "").strip(),
                is_dissatisfied, follow_up, now_ts
            ))
            conn.commit()

        return {
            "feedback_id": feedback_id,
            "status": "RECORDED",
            "rating": r_val,
            "is_dissatisfied": bool(is_dissatisfied),
            "follow_up_status": follow_up,
            "message": "Thank you! Your feedback has been recorded." if not is_dissatisfied else
                       "Thank you for your candid feedback. A dedicated relationship manager will reach out to ensure your satisfaction."
        }

    def get_dissatisfied_customers_queue(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("""
            SELECT fb.*, u.name as customer_name, u.phone as customer_phone
            FROM customer_feedback fb
            LEFT JOIN users u ON fb.user_id = u.user_id
            WHERE fb.is_dissatisfied = 1
            ORDER BY fb.created_at DESC
            """).fetchall()
            return [dict(r) for r in rows]

    def update_follow_up(self, feedback_id: str, follow_up_status: str, notes: Optional[str] = None) -> bool:
        with self._get_connection() as conn:
            cur = conn.execute("""
            UPDATE customer_feedback
            SET follow_up_status = ?, follow_up_notes = ?
            WHERE feedback_id = ?
            """, (follow_up_status, notes or "", feedback_id))
            conn.commit()
            return cur.rowcount > 0


support_service = SupportService.get_instance()
