import sqlite3
import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import DB_PATH
from app.data_loader import DataLoader

PARTNER_REGISTRY: Dict[str, Dict[str, Any]] = {
    "PTR-IND-882": {
        "partner_id": "PTR-IND-882",
        "name": "Airtel Mitra Partner",
        "hub_pincode": "452001",
        "district_prefix": "452",
        "city": "Indore",
        "circle": "MP-CG Circle",
        "phone": "+91 98260 55443"
    },
    "PTR-NOI-101": {
        "partner_id": "PTR-NOI-101",
        "name": "Apex Digital Mitra (Noida Central)",
        "hub_pincode": "201301",
        "district_prefix": "201",
        "city": "Noida",
        "circle": "UP West / Delhi NCR",
        "phone": "+91 98110 44332"
    },
    "PTR-PUN-303": {
        "partner_id": "PTR-PUN-303",
        "name": "Sahyadri Networks (Pune West)",
        "hub_pincode": "411001",
        "district_prefix": "411",
        "city": "Pune",
        "circle": "Maharashtra Circle",
        "phone": "+91 98220 99881"
    },
    "PTR-JAI-404": {
        "partner_id": "PTR-JAI-404",
        "name": "PinkCity Comms (Jaipur North)",
        "hub_pincode": "302001",
        "district_prefix": "302",
        "city": "Jaipur",
        "circle": "Rajasthan Circle",
        "phone": "+91 98290 11223"
    },
    "PTR-BHO-505": {
        "partner_id": "PTR-BHO-505",
        "name": "Bhojpal Telecom (Bhopal South)",
        "hub_pincode": "462001",
        "district_prefix": "462",
        "city": "Bhopal",
        "circle": "MP-CG Circle",
        "phone": "+91 98270 33445"
    },
    "PTR-ROH-606": {
        "partner_id": "PTR-ROH-606",
        "name": "Haryana Mitra Store (Rohtak Urban)",
        "hub_pincode": "124001",
        "district_prefix": "124",
        "city": "Rohtak",
        "circle": "Haryana Circle",
        "phone": "+91 98120 77665"
    }
}

class PartnerPortal:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.loader = DataLoader.get_instance()
        self.claimed_leads: Dict[str, Dict[str, Any]] = {}
        self.commissions: Dict[str, Any] = {
            "active_referrals_count": 28,
            "monthly_recurring_trail_inr": 42850.0,
            "total_pending_payout_inr": 16450.0
        }
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=30000;")
        return conn

    def _init_db(self):
        conn = self._get_connection()
        try:
            with conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("""
                CREATE TABLE IF NOT EXISTS customer_leads (
                    lead_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    business_name TEXT,
                    email TEXT,
                    phone TEXT,
                    city TEXT,
                    pincode TEXT,
                    business_type TEXT,
                    employee_count INTEGER DEFAULT 1,
                    num_sites INTEGER DEFAULT 1,
                    monthly_spend_inr REAL DEFAULT 0.0,
                    has_gstin TEXT DEFAULT 'N',
                    stage_reached TEXT,
                    drop_reason TEXT,
                    propensity_score INTEGER DEFAULT 35,
                    priority TEXT DEFAULT 'STANDARD',
                    bundle_json TEXT,
                    is_claimed INTEGER DEFAULT 0,
                    claimed_by TEXT,
                    claimed_at TEXT,
                    recovery_bounty_inr REAL DEFAULT 1000.0,
                    created_at TEXT,
                    last_activity_at TEXT
                )
                """)
                conn.execute("""
                CREATE TABLE IF NOT EXISTS called_leads (
                    lead_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    business_name TEXT,
                    email TEXT,
                    phone TEXT,
                    called_by TEXT,
                    called_at TEXT,
                    notes TEXT,
                    lead_data TEXT
                )
                """)
        finally:
            conn.close()

    def compute_customer_propensity(
        self,
        stage: str,
        has_gstin: str = "N",
        monthly_spend: float = 0.0,
        employee_count: int = 1,
        num_sites: int = 1,
        pincode: Optional[str] = None,
        is_kyc_verified: bool = False,
        is_token_paid: bool = False
    ) -> int:
        """
        Calculates a real-time propensity score (0-100) dynamically 
        based on active customer signals, verified credentials, and funnel progression.
        """
        score = 30  # Baseline on customer signup/login

        stage_weights = {
            "LOGGED_IN": 0,
            "ADVISOR_ENGAGED": 15,
            "PINCODE_CHECKED": 20,
            "BUNDLE_CUSTOMIZED": 30,
            "KYC_PENDING": 35,
            "KYC_SUBMITTED": 45,
            "KYC_VERIFIED": 50,
            "ADDRESS_ENTERED": 55,
            "TOKEN_PAID": 65,
            "ORDER_CONFIRMED": 65
        }
        score += stage_weights.get(stage.upper(), 10)

        # Signal 1: Formal business identity (GSTIN / Verified Udyam)
        if str(has_gstin).upper() in ["Y", "YES", "TRUE"] or is_kyc_verified:
            score += 15

        # Signal 2: High telecom commitment (Basket value)
        if monthly_spend >= 5000:
            score += 15
        elif monthly_spend >= 2000:
            score += 10
        elif monthly_spend > 0:
            score += 5

        # Signal 3: Scale signals (Multi-site or 5+ staff)
        if num_sites > 1 or employee_count >= 5:
            score += 10

        # Signal 4: Known FTTH serviceable pincode
        if pincode and len(str(pincode).strip()) == 6:
            score += 5

        # Signal 5: Priority token deposit paid -> Fast-Track guaranteed
        if is_token_paid or stage.upper() in ["TOKEN_PAID", "ORDER_CONFIRMED"]:
            score = max(score, 95)

        return min(max(score, 10), 100)

    def _determine_drop_reason(self, stage: str, spend: float) -> str:
        s = stage.upper()
        if s == "LOGGED_IN":
            return "Active Session • Browsing Storefront Plans"
        elif s == "ADVISOR_ENGAGED":
            return "Chatting with AI Advisor • Exploring Recommendations"
        elif s == "PINCODE_CHECKED":
            return "Checked Fibre Feasibility • In Storefront Flow"
        elif s == "BUNDLE_CUSTOMIZED":
            spend_label = f"₹{int(spend)}/mo" if spend > 0 else "Plans"
            return f"Customized Bundle ({spend_label}) • Awaiting Smart KYC"
        elif s == "KYC_PENDING":
            return "Selected KYC Track • Pending Document Upload"
        elif s == "KYC_SUBMITTED":
            return "KYC Submitted • Under System Review"
        elif s == "KYC_VERIFIED":
            return "Smart KYC 100% Verified • Awaiting Address Confirmation"
        elif s == "ADDRESS_ENTERED":
            return "Installation Address Confirmed • Awaiting ₹499 Booking Deposit"
        elif s in ["TOKEN_PAID", "ORDER_CONFIRMED"]:
            return "Priority ₹499 Paid • Physical Installation Dispatched"
        return "Active Digital Customer Session"

    def record_customer_activity(
        self,
        user_id: Optional[str] = None,
        business_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        action: str = "LOGGED_IN",
        stage: Optional[str] = None,
        city: Optional[str] = None,
        pincode: Optional[str] = None,
        business_type: Optional[str] = None,
        employee_count: Optional[int] = None,
        num_sites: Optional[int] = None,
        monthly_spend_inr: Optional[float] = None,
        has_gstin: Optional[str] = None,
        bundle: Optional[Dict[str, Any]] = None,
        lead_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Stores and updates real-time propensity score for any customer action.
        Persisted to SQLite database so Mitra Partners always see real data.
        """
        conn = self._get_connection()
        try:
            with conn:
                row = None
            if lead_id:
                # Check if lead was already contacted and removed
                c_chk = conn.execute("SELECT 1 FROM called_leads WHERE lead_id = ?", (lead_id,)).fetchone()
                if c_chk:
                    return {"lead_id": lead_id, "status": "ALREADY_CALLED"}
                cursor = conn.execute("SELECT * FROM customer_leads WHERE lead_id = ?", (lead_id,))
                row = cursor.fetchone()
            elif user_id:
                cursor = conn.execute("SELECT * FROM customer_leads WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
            elif email:
                cursor = conn.execute("SELECT * FROM customer_leads WHERE email = ?", (email,))
                row = cursor.fetchone()

            now_iso = datetime.now().isoformat()
            existing = dict(row) if row else {}

            cur_user_id = user_id or existing.get("user_id") or f"USR-CUST-{uuid.uuid4().hex[:5].upper()}"
            cur_lead_id = lead_id or existing.get("lead_id") or f"LD-{cur_user_id}"
            cur_bname = business_name or existing.get("business_name") or "MSME Digital Customer"
            cur_email = email or existing.get("email") or "customer@business.in"
            cur_phone = phone or existing.get("phone") or "+91 98110 12345"
            cur_city = city or existing.get("city") or "Rohtak"
            cur_pincode = pincode or existing.get("pincode") or "124001"
            cur_btype = business_type or existing.get("business_type") or "Retail & Commercial Services"
            cur_emp = employee_count if employee_count is not None else existing.get("employee_count", 1)
            cur_sites = num_sites if num_sites is not None else existing.get("num_sites", 1)
            cur_spend = monthly_spend_inr if monthly_spend_inr is not None else existing.get("monthly_spend_inr", 0.0)
            cur_gstin = has_gstin or existing.get("has_gstin", "N")
            cur_bundle = bundle if bundle is not None else (json.loads(existing["bundle_json"]) if existing.get("bundle_json") else {})

            cur_stage = stage or action or existing.get("stage_reached") or "LOGGED_IN"
            cur_drop_reason = self._determine_drop_reason(cur_stage, cur_spend)

            p_score = self.compute_customer_propensity(
                stage=cur_stage,
                has_gstin=cur_gstin,
                monthly_spend=cur_spend,
                employee_count=cur_emp,
                num_sites=cur_sites,
                pincode=cur_pincode,
                is_kyc_verified=(cur_stage in ["KYC_VERIFIED", "ADDRESS_ENTERED", "TOKEN_PAID"]),
                is_token_paid=(cur_stage in ["TOKEN_PAID", "ORDER_CONFIRMED"])
            )
            priority = "HIGH" if p_score >= 70 else ("MEDIUM" if p_score >= 50 else "STANDARD")

            if row:
                conn.execute("""
                    UPDATE customer_leads SET
                        business_name = ?,
                        email = ?,
                        phone = ?,
                        city = ?,
                        pincode = ?,
                        business_type = ?,
                        employee_count = ?,
                        num_sites = ?,
                        monthly_spend_inr = ?,
                        has_gstin = ?,
                        stage_reached = ?,
                        drop_reason = ?,
                        propensity_score = ?,
                        priority = ?,
                        bundle_json = ?,
                        last_activity_at = ?
                    WHERE lead_id = ?
                """, (
                    cur_bname, cur_email, cur_phone, cur_city, cur_pincode,
                    cur_btype, cur_emp, cur_sites, cur_spend, cur_gstin,
                    cur_stage, cur_drop_reason, p_score, priority,
                    json.dumps(cur_bundle) if cur_bundle else None,
                    now_iso, cur_lead_id
                ))
            else:
                conn.execute("""
                    INSERT INTO customer_leads (
                        lead_id, user_id, business_name, email, phone,
                        city, pincode, business_type, employee_count, num_sites,
                        monthly_spend_inr, has_gstin, stage_reached, drop_reason,
                        propensity_score, priority, bundle_json, is_claimed,
                        claimed_by, claimed_at, recovery_bounty_inr, created_at, last_activity_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, NULL, 1000.0, ?, ?)
                """, (
                    cur_lead_id, cur_user_id, cur_bname, cur_email, cur_phone,
                    cur_city, cur_pincode, cur_btype, cur_emp, cur_sites,
                    cur_spend, cur_gstin, cur_stage, cur_drop_reason,
                    p_score, priority, json.dumps(cur_bundle) if cur_bundle else None,
                    now_iso, now_iso
                ))
            conn.commit()
            cursor = conn.execute("SELECT * FROM customer_leads WHERE lead_id = ?", (cur_lead_id,))
            res_row = cursor.fetchone()
            saved_lead = dict(res_row) if res_row else {}
            saved_lead["bundle"] = cur_bundle
            return saved_lead
        finally:
            conn.close()

    def resolve_partner_for_lead(
        self,
        pincode: Optional[str] = None,
        city: Optional[str] = None,
        tier: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        4-Tier Hierarchical Routing Engine:
        Level 1: Exact 6-Digit PIN match -> Local Retail Store
        Level 2: 3-Digit Postal District Prefix match -> Circle District Partner Hub
        Level 3: City / Tier Regional Pool -> Regional Channel Desk
        Level 4: Central Ops Admin Pool -> Pan-India Tele-Sales Desk
        """
        clean_pin = str(pincode or "").strip()
        clean_city = str(city or "").strip().lower()

        # Level 1: Exact 6-Digit PIN match
        if clean_pin and len(clean_pin) == 6:
            for pid, pdata in PARTNER_REGISTRY.items():
                if pdata["hub_pincode"] == clean_pin:
                    return {
                        "routing_level": 1,
                        "routing_tier": "EXACT_PIN",
                        "routing_label": f"Level 1: Exact PIN Match ({clean_pin})",
                        "partner_id": pid,
                        "partner_name": pdata["name"],
                        "circle": pdata["circle"],
                        "channel_type": "Mitra Retail Store Counter",
                        "sla_hours": 4.0
                    }

        # Level 2: 3-Digit Postal District Prefix match
        if clean_pin and len(clean_pin) >= 3:
            pin_prefix = clean_pin[:3]
            for pid, pdata in PARTNER_REGISTRY.items():
                if pdata["district_prefix"] == pin_prefix or clean_pin.startswith(pdata["district_prefix"]):
                    return {
                        "routing_level": 2,
                        "routing_tier": "DISTRICT_PREFIX",
                        "routing_label": f"Level 2: District Prefix Match ({pin_prefix}xxx)",
                        "partner_id": pid,
                        "partner_name": pdata["name"],
                        "circle": pdata["circle"],
                        "channel_type": "District Mitra Partner Hub",
                        "sla_hours": 4.0
                    }

        # Level 3: City / Regional Pool match
        if clean_city:
            for pid, pdata in PARTNER_REGISTRY.items():
                if pdata["city"].lower() == clean_city:
                    return {
                        "routing_level": 3,
                        "routing_tier": "CITY_POOL",
                        "routing_label": f"Level 3: City Circle Pool ({pdata['city']})",
                        "partner_id": pid,
                        "partner_name": pdata["name"],
                        "circle": pdata["circle"],
                        "channel_type": "Circle Regional Partner",
                        "sla_hours": 8.0
                    }

        # Level 4: Central Ops Admin Pool Fallback
        return {
            "routing_level": 4,
            "routing_tier": "CENTRAL_OPS",
            "routing_label": "Level 4: Central Enterprise Ops Pool",
            "partner_id": "ADM-HQ-001",
            "partner_name": "Airtel Enterprise Operations Desk (National HQ)",
            "circle": "Pan-India Central",
            "channel_type": "Direct Central Tele-Sales & Exception Desk",
            "sla_hours": 24.0
        }

    def calculate_propensity_score(self, lead: Dict[str, Any]) -> int:
        """
        Lightweight, transparent rule-based propensity score (0-100)
        calibrated against the smb_leads.csv signals without target leakage.
        """
        score = 20  # baseline

        # Signal 1: Formal Registration (GSTIN adds 35 pts)
        if str(lead.get("has_gstin", "")).upper() == "Y":
            score += 35

        # Signal 2: High Monthly Spend
        spend = float(lead.get("monthly_telecom_spend_inr", 0) or 0)
        if spend >= 5000:
            score += 25
        elif spend >= 2500:
            score += 15

        # Signal 3: Firmographic scale (Sites & Employees)
        sites = int(lead.get("num_sites", 1) or 1)
        employees = int(lead.get("employee_count", 1) or 1)
        if sites > 1 or employees >= 5:
            score += 20

        return min(score, 100)

    def get_stalled_leads_with_propensity(
        self,
        limit: int = 15,
        partner_id: Optional[str] = None,
        partner_pincode: Optional[str] = None,
        is_admin: bool = False
    ) -> List[Dict[str, Any]]:
        results = []

        # 1. Fetch Real Live Customer Leads from SQLite Database
        # Note: If token is already paid or order placed, DO NOT put it out to Mitras.
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT cl.* FROM customer_leads cl
                WHERE cl.email != 'customer@business.in'
                  AND cl.business_name NOT IN ('Airtel MSME Customer', 'Sharma General Stores', 'Friend Business', 'Mobile Friend Store')
                  AND cl.email NOT LIKE '%example.com%'
                  AND cl.email NOT LIKE '%stores.in%'
                  AND cl.email NOT LIKE '%clinic.in%'
                  AND cl.stage_reached NOT IN ('TOKEN_PAID', 'ORDER_CONFIRMED', 'ACTIVATED', 'OUTREACH_CALLED')
                  AND (cl.drop_reason IS NULL OR cl.drop_reason NOT LIKE '%Paid%')
                  AND cl.lead_id NOT IN (SELECT order_id FROM orders WHERE token_paid = 1)
                  AND cl.lead_id NOT IN (SELECT lead_id FROM called_leads)
                ORDER BY cl.propensity_score DESC, cl.last_activity_at DESC
            """)
            real_rows = [dict(r) for r in cursor.fetchall()]
        except Exception:
            real_rows = []
        finally:
            conn.close()

        for r in real_rows:
            stage_str = (r.get("stage_reached") or "").upper()
            drop_str = (r.get("drop_reason") or "").lower()
            if stage_str in ["TOKEN_PAID", "ORDER_CONFIRMED", "ACTIVATED"] or "paid" in drop_str:
                continue

            lid = r["lead_id"]
            claim_info = self.claimed_leads.get(lid)
            is_claimed = bool(r.get("is_claimed")) or bool(claim_info)
            p_score = int(r.get("propensity_score", 35))

            city_val = r.get("city") or "Rohtak"
            pin_val = str(r.get("pincode") or "124001").strip()
            routing = self.resolve_partner_for_lead(
                pincode=pin_val,
                city=city_val,
                tier=2
            )

            # Partner Territory & Assignment Isolation
            # Non-admin partners only see leads assigned to them or in their authorized territory
            if not is_admin and (partner_id or partner_pincode):
                is_assigned_to_me = (routing.get("partner_id") == partner_id) or (r.get("claimed_by") == partner_id)
                clean_partner_pin = str(partner_pincode or "").strip()
                in_my_territory = False
                if clean_partner_pin and clean_partner_pin != "ALL":
                    if pin_val == clean_partner_pin:
                        in_my_territory = True
                    elif len(clean_partner_pin) >= 3 and pin_val.startswith(clean_partner_pin[:3]):
                        in_my_territory = True

                # If claimed by someone else, exclude from feed
                if is_claimed and r.get("claimed_by") and r.get("claimed_by") != partner_id:
                    continue

                if not is_assigned_to_me and not in_my_territory:
                    continue

            # Fast-Track 4-Hour SLA Computation
            if is_claimed:
                sla_remaining = "Locked"
                sla_status = "CLAIMED"
            elif p_score >= 70:
                sla_remaining = "3.5h left"
                sla_status = "ACTIVE"
            else:
                sla_remaining = "24h SLA"
                sla_status = "STANDARD"

            results.append({
                "lead_id": lid,
                "business_name": r["business_name"],
                "city": city_val,
                "pincode": pin_val,
                "phone": r.get("phone") or "+91 98110 12345",
                "stage_reached": r.get("stage_reached", "BUNDLE_CUSTOMIZED"),
                "drop_reason": r.get("drop_reason", "Active Session"),
                "monthly_spend_inr": r.get("monthly_spend_inr", 0.0),
                "has_gstin": r.get("has_gstin", "N"),
                "propensity_score": p_score,
                "priority": r.get("priority") or ("HIGH" if p_score >= 70 else ("MEDIUM" if p_score >= 50 else "STANDARD")),
                "is_claimed": is_claimed,
                "claimed_by": r.get("claimed_by") or (claim_info.get("partner_id") if claim_info else None),
                "recovery_bounty_inr": r.get("recovery_bounty_inr", 1000.0),
                "routing_tier": routing["routing_tier"],
                "routing_label": routing["routing_label"],
                "assigned_partner_id": routing["partner_id"],
                "assigned_partner_name": routing["partner_name"],
                "sla_hours": routing["sla_hours"],
                "sla_remaining": sla_remaining,
                "sla_status": sla_status,
                "is_real_time": True,
                "source": "LIVE_CUSTOMER",
                "last_activity_at": r.get("last_activity_at")
            })

        # Only return genuine live customer leads, sorted by propensity score DESC
        return sorted(results, key=lambda x: -x["propensity_score"])[:limit]

    def claim_stalled_lead(
        self,
        lead_id: str,
        partner_id: str = "PTR-IND-882",
        partner_pincode: Optional[str] = None,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """
        Atomically claims a lead at the database level.
        Enforces partner territory isolation and rejects concurrent claims.
        """
        conn = self._get_connection()
        try:
            with conn:
                # 1. Fetch lead details to verify territory
                cursor = conn.execute("SELECT * FROM customer_leads WHERE lead_id = ?", (lead_id,))
                lead_row = cursor.fetchone()
                if not lead_row:
                    raise ValueError(f"Lead '{lead_id}' not found.")

                lead_dict = dict(lead_row)
                pin_val = str(lead_dict.get("pincode") or "").strip()
                clean_partner_pin = str(partner_pincode or "").strip()

                if not is_admin and clean_partner_pin and clean_partner_pin != "ALL":
                    routing = self.resolve_partner_for_lead(pincode=pin_val, city=lead_dict.get("city"))
                    in_territory = (pin_val == clean_partner_pin) or (len(clean_partner_pin) >= 3 and pin_val.startswith(clean_partner_pin[:3]))
                    is_routed = (routing.get("partner_id") == partner_id)
                    if not in_territory and not is_routed:
                        raise PermissionError(f"Access denied: Lead '{lead_id}' (Pincode: {pin_val}) is outside your authorized territory ({clean_partner_pin}).")

                # 2. Atomic Database Update (prevents race conditions)
                now_iso = datetime.now().isoformat()
                upd_cursor = conn.execute("""
                    UPDATE customer_leads 
                    SET is_claimed = 1, claimed_by = ?, claimed_at = ?
                    WHERE lead_id = ? AND (is_claimed = 0 OR is_claimed IS NULL)
                """, (partner_id, now_iso, lead_id))

                if upd_cursor.rowcount == 0:
                    # Lead was already claimed
                    c_cursor = conn.execute("SELECT claimed_by FROM customer_leads WHERE lead_id = ?", (lead_id,))
                    c_row = c_cursor.fetchone()
                    claimed_by = c_row["claimed_by"] if c_row else "another partner"
                    if claimed_by == partner_id:
                        return {
                            "status": "ALREADY_CLAIMED",
                            "claim_status": "CLAIMED",
                            "message": f"Lead {lead_id} is already claimed by you.",
                            "lead_id": lead_id,
                            "partner_id": partner_id,
                            "bounty_inr": 1000,
                            "recovery_sla_hours": 24
                        }
                    raise RuntimeError(f"Conflict: Lead '{lead_id}' has already been claimed by partner '{claimed_by}'.")

                # 3. Synchronize in-memory cache upon successful database update
                self.claimed_leads[lead_id] = {
                    "partner_id": partner_id,
                    "claimed_at": now_iso,
                    "bounty_inr": 1000,
                    "status": "CLAIMED"
                }

        finally:
            conn.close()

        return {
            "status": "SUCCESS",
            "claim_status": "CLAIMED",
            "message": f"Lead {lead_id} successfully claimed. ₹1,000 spot recovery bounty locked upon activation within 24h.",
            "lead_id": lead_id,
            "partner_id": partner_id,
            "bounty_inr": 1000,
            "recovery_sla_hours": 24
        }

    def call_lead(self, lead_id: str, partner_id: str = "PTR-IND-882", is_admin: bool = False) -> Dict[str, Any]:
        """
        Atomically removes a lead from the active leads pool upon partner outreach call,
        archiving the contact event in called_leads table.
        Enforces partner ownership/claim isolation.
        """
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.execute("SELECT * FROM customer_leads WHERE lead_id = ?", (lead_id,))
                row = cursor.fetchone()
                if not row:
                    c_cursor = conn.execute("SELECT * FROM called_leads WHERE lead_id = ?", (lead_id,))
                    c_row = c_cursor.fetchone()
                    if c_row:
                        return {
                            "status": "ALREADY_CALLED",
                            "lead_id": lead_id,
                            "partner_id": partner_id,
                            "action": "ALREADY_CALLED",
                            "message": f"Lead {lead_id} was already contacted and removed from active pool."
                        }
                    return {
                        "status": "NOT_FOUND",
                        "lead_id": lead_id,
                        "partner_id": partner_id,
                        "action": "NOT_FOUND",
                        "message": f"Lead {lead_id} not found."
                    }

                lead_data = dict(row)
                if not is_admin and lead_data.get("is_claimed") and lead_data.get("claimed_by") and lead_data.get("claimed_by") != partner_id:
                    raise PermissionError(f"Access denied: Lead '{lead_id}' has been claimed by partner '{lead_data.get('claimed_by')}'.")

                now_iso = datetime.now().isoformat()
                conn.execute("""
                    INSERT OR REPLACE INTO called_leads (
                        lead_id, user_id, business_name, email, phone, called_by, called_at, notes, lead_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    lead_data.get("lead_id"),
                    lead_data.get("user_id"),
                    lead_data.get("business_name"),
                    lead_data.get("email"),
                    lead_data.get("phone"),
                    partner_id,
                    now_iso,
                    "Partner outreach call completed",
                    json.dumps(lead_data)
                ))
                conn.execute("DELETE FROM customer_leads WHERE lead_id = ?", (lead_id,))
        finally:
            conn.close()

        # Remove from in-memory claimed tracking
        self.claimed_leads.pop(lead_id, None)

        return {
            "status": "SUCCESS",
            "lead_id": lead_id,
            "partner_id": partner_id,
            "action": "CALLED_AND_REMOVED",
            "message": f"Lead {lead_id} contacted by {partner_id} and atomically removed from leads."
        }

    def generate_partner_referral_link(self, partner_id: str = "PTR-IND-882") -> Dict[str, Any]:
        return {
            "partner_id": partner_id,
            "partner_name": "Airtel Mitra Partner",
            "referral_code": f"REF-{partner_id}",
            "referral_url": f"http://localhost:8000/?ref={partner_id}",
            "commission_tier": "15% recurring trail commission on all 12 monthly bills",
            "qr_label": "Scan to order Airtel Business with dedicated Mitra Partner on-site support"
        }

    def get_partner_commissions(self, partner_id: str = "PTR-IND-882") -> Dict[str, Any]:
        claimed_ids = set()
        for lid, c in self.claimed_leads.items():
            if c.get("partner_id") == partner_id:
                claimed_ids.add(lid)
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT lead_id FROM customer_leads WHERE is_claimed = 1 AND claimed_by = ?", (partner_id,))
            for row in cursor.fetchall():
                claimed_ids.add(row[0])
        except Exception:
            pass
        finally:
            conn.close()

        claimed_count = len(claimed_ids)
        return {
            "partner_id": partner_id,
            "partner_name": "Airtel Mitra Partner",
            "assigned_pincode": "452001",
            "active_referrals_count": 28,
            "monthly_recurring_trail_inr": 42850.0,
            "spot_recovery_bounty_per_lead_inr": 1000.0,
            "stalled_recovery_bounties_inr": 4000.0 + (claimed_count * 1000.0),
            "recovery_bounties_count": claimed_count,
            "recovery_bounties_earned_inr": claimed_count * 1000.0,
            "pending_payout_inr": 16450.0 + (claimed_count * 1000.0),
            "total_pending_payout_inr": 16450.0 + (claimed_count * 1000.0),
            "commission_rate": "15% Recurring Trail"
        }


