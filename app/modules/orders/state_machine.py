import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from contextlib import contextmanager
from app.config import DB_PATH

class OrderStateMachine:
    def __init__(self):
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
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
                user_id TEXT,
                customer_email TEXT,
                consent_type TEXT,
                version TEXT,
                consent_text TEXT,
                purpose TEXT,
                action TEXT,
                timestamp TEXT
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS kyc_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT UNIQUE NOT NULL,
                user_id TEXT,
                customer_email TEXT,
                doc_type TEXT,
                id_number TEXT,
                entity_name TEXT,
                verdict TEXT NOT NULL,
                verification_details_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS kyc_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT,
                user_id TEXT,
                doc_type TEXT,
                udyam_number TEXT,
                gstin TEXT,
                entity_name TEXT,
                installation_address TEXT,
                verification_status TEXT,
                disposition TEXT,
                verified_at TEXT
            )
            """)
            
            # Dynamic schema migrations for consent_logs
            c_cursor = conn.execute("PRAGMA table_info(consent_logs)")
            c_cols = [col[1] for col in c_cursor.fetchall()]
            if "user_id" not in c_cols:
                conn.execute("ALTER TABLE consent_logs ADD COLUMN user_id TEXT")
            if "customer_email" not in c_cols:
                conn.execute("ALTER TABLE consent_logs ADD COLUMN customer_email TEXT")
            if "consent_type" not in c_cols:
                conn.execute("ALTER TABLE consent_logs ADD COLUMN consent_type TEXT")
            if "version" not in c_cols:
                conn.execute("ALTER TABLE consent_logs ADD COLUMN version TEXT")
            if "consent_text" not in c_cols:
                conn.execute("ALTER TABLE consent_logs ADD COLUMN consent_text TEXT")

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
            if "user_id" not in cols:
                conn.execute("ALTER TABLE orders ADD COLUMN user_id TEXT")
            if "udyam_number" not in cols:
                conn.execute("ALTER TABLE orders ADD COLUMN udyam_number TEXT")
            if "gstin" not in cols:
                conn.execute("ALTER TABLE orders ADD COLUMN gstin TEXT")
            if "kyc_details_json" not in cols:
                conn.execute("ALTER TABLE orders ADD COLUMN kyc_details_json TEXT")
            if "customer_email" not in cols:
                conn.execute("ALTER TABLE orders ADD COLUMN customer_email TEXT")
            if "kyc_case_id" not in cols:
                conn.execute("ALTER TABLE orders ADD COLUMN kyc_case_id TEXT")
            conn.commit()

    def create_kyc_case(
        self,
        user_id: Optional[str],
        customer_email: Optional[str],
        doc_type: str,
        id_number: Optional[str],
        entity_name: Optional[str],
        verdict: str,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        case_id = f"KYC-CAS-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute("""
            INSERT INTO kyc_cases (
                case_id, user_id, customer_email, doc_type, id_number,
                entity_name, verdict, verification_details_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                case_id,
                user_id or "",
                (customer_email or "").lower().strip(),
                doc_type,
                id_number or "",
                entity_name or "",
                verdict,
                json.dumps(details or {}),
                now_iso,
                now_iso
            ))
            conn.commit()
        return case_id

    def get_kyc_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM kyc_cases WHERE case_id = ?", (case_id,)).fetchone()
            if row:
                d = dict(row)
                d["details"] = json.loads(d.get("verification_details_json") or "{}")
                return d
        return None

    def get_latest_approved_kyc_case(
        self,
        user_id: Optional[str] = None,
        customer_email: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        user_id = user_id.strip() if user_id else None
        customer_email = customer_email.strip().lower() if customer_email else None
        with self._get_connection() as conn:
            if user_id:
                row = conn.execute(
                    "SELECT * FROM kyc_cases WHERE user_id = ? AND verdict = 'APPROVED' ORDER BY id DESC LIMIT 1",
                    (user_id,)
                ).fetchone()
                if row:
                    d = dict(row)
                    d["details"] = json.loads(d.get("verification_details_json") or "{}")
                    return d
            if customer_email:
                row = conn.execute(
                    "SELECT * FROM kyc_cases WHERE lower(customer_email) = ? AND verdict = 'APPROVED' ORDER BY id DESC LIMIT 1",
                    (customer_email,)
                ).fetchone()
                if row:
                    d = dict(row)
                    d["details"] = json.loads(d.get("verification_details_json") or "{}")
                    return d
        return None

    def record_consent(
        self,
        user_id: str,
        customer_email: str,
        consent_type: str = "REGISTRY_VERIFICATION_CONSENT",
        purpose: str = "Identity & Registry Verification under DPDP Act 2023",
        version: str = "v1.0",
        consent_text: str = "Explicit affirmative consent granted for registry verification.",
        order_id: Optional[str] = None
    ) -> int:
        now_ts = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute("""
            INSERT INTO consent_logs (order_id, user_id, customer_email, consent_type, version, consent_text, purpose, action, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id or "",
                user_id or "",
                (customer_email or "").lower().strip(),
                consent_type,
                version,
                consent_text,
                purpose,
                "EXPLICIT_AFFIRMATIVE_CONSENT_GRANTED",
                now_ts
            ))
            conn.commit()
            return cursor.lastrowid

    def save_kyc_verification_session(
        self,
        session_id: str,
        user_id: str,
        customer_email: str,
        blur_variance: float,
        is_clear: bool,
        extracted_fields: Optional[Dict[str, Any]] = None,
        raw_text: Optional[str] = None
    ):
        now_ts = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS kyc_verification_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                customer_email TEXT,
                blur_variance REAL,
                is_clear INTEGER,
                extracted_fields_json TEXT,
                raw_text TEXT,
                created_at TEXT NOT NULL
            )
            """)
            conn.execute("""
            INSERT OR REPLACE INTO kyc_verification_sessions (
                session_id, user_id, customer_email, blur_variance, is_clear, extracted_fields_json, raw_text, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, user_id, customer_email, blur_variance, 1 if is_clear else 0,
                json.dumps(extracted_fields or {}), raw_text or "", now_ts
            ))
            conn.commit()

    def get_kyc_verification_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            try:
                row = conn.execute("SELECT * FROM kyc_verification_sessions WHERE session_id = ?", (session_id,)).fetchone()
                if row:
                    res = dict(row)
                    res["extracted_fields"] = json.loads(res.get("extracted_fields_json") or "{}")
                    res["is_clear"] = bool(res.get("is_clear"))
                    return res
            except Exception:
                pass
        return None

    def verify_order_ownership(self, order: Optional[Dict[str, Any]], user: Optional[Dict[str, Any]]) -> bool:
        if not order or not user:
            return False
        role = user.get("role", "MERCHANT")
        if role == "ADMIN":
            # Explicitly authorized administrator
            return True

        if role == "PARTNER":
            partner_id = user.get("user_id")
            # 1. Directly assigned/attributed partner
            if order.get("partner_attribution_id") and order.get("partner_attribution_id") == partner_id:
                return True
            if order.get("assigned_partner_id") and order.get("assigned_partner_id") == partner_id:
                return True

            # 2. Authorized territory match (assigned pincode or district prefix)
            assigned_pin = str(user.get("assigned_pincode") or "").strip()
            if not assigned_pin or assigned_pin == "ALL":
                # Partners cannot have wildcard access to orders
                return False

            inst_addr = order.get("installation_address") or {}
            order_pin = ""
            if isinstance(inst_addr, dict):
                order_pin = str(inst_addr.get("pincode") or "").strip()
            elif isinstance(inst_addr, str):
                try:
                    parsed = json.loads(inst_addr)
                    if isinstance(parsed, dict):
                        order_pin = str(parsed.get("pincode") or "").strip()
                except Exception:
                    order_pin = ""

            if order_pin:
                if order_pin == assigned_pin:
                    return True
                if len(assigned_pin) >= 3 and order_pin.startswith(assigned_pin[:3]):
                    return True

            # Partners do not have arbitrary order access outside their territory/assignment
            return False

        # Role MERCHANT (Customer)
        if role == "MERCHANT":
            u_id = user.get("user_id")
            u_email = (user.get("email") or "").lower().strip()
            ord_uid = order.get("user_id")
            ord_email = (order.get("customer_email") or "").lower().strip()
            if ord_uid and ord_uid == u_id:
                return True
            if ord_email and ord_email == u_email:
                return True
            return False

        return False

    def create_order(
        self,
        business_name: str,
        contact_phone: str,
        bundle_data: Dict[str, Any],
        case_id: Optional[str] = None,
        explicit_consent: Optional[Dict[str, Any]] = None,
        kyc_status: Optional[str] = None,
        language: str = "en",
        typical_install_days: int = 5,
        partner_id: Optional[str] = None,
        installation_address: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        udyam_number: Optional[str] = None,
        gstin: Optional[str] = None,
        kyc_details: Optional[Dict[str, Any]] = None,
        customer_email: Optional[str] = None
    ) -> Dict[str, Any]:
        # 1. Enforcement of Explicit DPDP Consent (Requirement 8)
        # Automatic consent assumption is removed; customer must explicitly consent.
        if not explicit_consent or not explicit_consent.get("granted"):
            raise ValueError(
                "DPDP Act 2023 statutory consent required: Customer must explicitly grant consent before an enterprise order can be staged."
            )

        # 2. Server-Controlled KYC Case Verification (Requirement 6)
        # Never accept kyc_status: VERIFIED directly from frontend.
        kyc_case = None
        if case_id:
            kyc_case = self.get_kyc_case(case_id)
        if not kyc_case:
            kyc_case = self.get_latest_approved_kyc_case(user_id=user_id, customer_email=customer_email)

        if not kyc_case or kyc_case.get("verdict") != "APPROVED":
            verdict = kyc_case.get("verdict") if kyc_case else "MISSING"
            raise ValueError(
                f"Cannot create order: Validated server KYC case with approved verdict is required. Current case status: {verdict}. Frontend-asserted kyc_status is strictly rejected."
            )

        # Confirm approved KYC case belongs to the authenticated customer creating this order
        case_uid = kyc_case.get("user_id")
        case_email = (kyc_case.get("customer_email") or "").lower().strip()
        u_email = (customer_email or "").lower().strip()
        is_owner = (case_uid and case_uid == user_id) or (case_email and case_email == u_email)
        if not is_owner:
            raise ValueError(
                f"Cross-account security violation: Approved KYC case '{kyc_case.get('case_id')}' does not belong to authenticated customer '{user_id}'."
            )

        server_kyc_status = "VERIFIED"
        matched_case_id = kyc_case.get("case_id")

        # 3. Central Authoritative Recalculation & Tamper Rejection (Requirement 4)
        from app.modules.pricing.calculator import pricing_calculator
        from app.modules.advisor.profile import infer_tier_from_city, infer_location_from_pincode

        # Resolve product quantities from bundle payload
        product_quantities: Dict[str, int] = {}
        if isinstance(bundle_data, dict):
            if "product_quantities" in bundle_data and isinstance(bundle_data["product_quantities"], dict):
                product_quantities = {k: int(v) for k, v in bundle_data["product_quantities"].items() if int(v or 0) > 0}
            elif "selected_products" in bundle_data and isinstance(bundle_data["selected_products"], list) and bundle_data["selected_products"]:
                for p in bundle_data["selected_products"]:
                    product_quantities[p] = product_quantities.get(p, 0) + 1
            elif "items" in bundle_data and isinstance(bundle_data["items"], list):
                for it in bundle_data["items"]:
                    if isinstance(it, dict):
                        p_id = it.get("product_id")
                        if not p_id and it.get("name"):
                            n = it["name"].lower()
                            if "300" in n: p_id = "P02"
                            elif "1g" in n or "1000" in n: p_id = "P03"
                            elif "airfiber" in n: p_id = "P04"
                            elif "leased" in n and "100" in n: p_id = "P06"
                            elif "leased" in n: p_id = "P05"
                            elif "fibre" in n: p_id = "P01"
                        if p_id:
                            product_quantities[p_id] = product_quantities.get(p_id, 0) + int(it.get("quantity") or 1)

        if not product_quantities:
            product_quantities = {"P01": 1}

        # Derive location and city tier from installation address
        pincode_val = None
        city_val = None
        if isinstance(installation_address, dict):
            pincode_val = installation_address.get("pincode")
            city_val = installation_address.get("city")
        
        city_tier = 2
        if city_val:
            city_tier = infer_tier_from_city(city_val)
        elif pincode_val:
            city_tier = infer_location_from_pincode(str(pincode_val))[1]

        # Derive GST status from server-verified KYC case
        case_details = kyc_case.get("details") or {}
        is_non_gst = kyc_case.get("is_non_gst_mode") or case_details.get("is_non_gst_mode")
        has_gstin = bool(kyc_case.get("id_number") and not is_non_gst) if kyc_case.get("doc_type") == "GST" else False

        submitted_m = None
        submitted_s = None
        waive_setup = True
        if isinstance(bundle_data, dict):
            for k in ["total_monthly_inr", "monthly_recurring_total", "subtotal_inr"]:
                if k in bundle_data and bundle_data[k] is not None:
                    submitted_m = bundle_data[k]
                    break
            for k in ["one_time_setup_inr", "setup_charges_total"]:
                if k in bundle_data and bundle_data[k] is not None:
                    submitted_s = bundle_data[k]
                    break
            if "waive_setup_fee" in bundle_data:
                waive_setup = bool(bundle_data["waive_setup_fee"])
            elif submitted_s is not None and float(submitted_s) > 0:
                waive_setup = False

        # Recalculate quote authoritatively; rejects manipulated prices, invalid SKUs, or violations
        authoritative_quote = pricing_calculator.validate_and_price_order(
            product_quantities=product_quantities,
            city_tier=city_tier,
            city=city_val,
            pincode=str(pincode_val) if pincode_val else None,
            employee_count=int(bundle_data.get("employee_count") or 1) if isinstance(bundle_data, dict) else 1,
            num_sites=int(bundle_data.get("num_sites") or 1) if isinstance(bundle_data, dict) else 1,
            has_gstin=has_gstin,
            contract_months=bundle_data.get("contract_months") if isinstance(bundle_data, dict) else None,
            apply_digital_discount=bundle_data.get("apply_digital_discount", True) if isinstance(bundle_data, dict) else True,
            waive_setup_fee=waive_setup,
            discount_code=bundle_data.get("discount_code") if isinstance(bundle_data, dict) else None,
            customer_submitted_monthly_total=submitted_m,
            customer_submitted_setup_fee=submitted_s
        )

        order_id = f"UDYAM-{uuid.uuid4().hex[:6].upper()}"
        typical_days = authoritative_quote.get("typical_install_days", typical_install_days)
        install_date = (datetime.now() + timedelta(days=typical_days)).strftime("%Y-%m-%d")

        with self._get_connection() as conn:
            conn.execute("""
            INSERT INTO orders (
                order_id, business_name, contact_phone, language,
                bundle_json, monthly_total, kyc_status, current_milestone,
                scheduled_install_date, engineer_name, engineer_phone, nps_rating, 
                partner_attribution_id, installation_address,
                user_id, udyam_number, gstin, kyc_details_json, customer_email, kyc_case_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id,
                business_name,
                contact_phone,
                language,
                json.dumps(authoritative_quote),
                authoritative_quote.get("total_monthly_inr", 0.0),
                server_kyc_status,
                3, # Milestone 3: Order Confirmed / Scheduled
                install_date,
                "SIMULATED / DEMO: Assigned Field Tech (Slot Pending Real Dispatch)",
                "+91-DEMO-SIMULATED",
                None,
                partner_id,
                json.dumps(installation_address) if installation_address else None,
                user_id,
                udyam_number,
                gstin,
                json.dumps(kyc_details) if kyc_details else None,
                customer_email,
                matched_case_id,
                datetime.now().isoformat()
            ))

            # Store verified KYC record linked to verified server case
            formatted_addr = installation_address.get("formatted_address") if isinstance(installation_address, dict) else str(installation_address or "")
            conn.execute("""
            INSERT INTO kyc_records (
                order_id, user_id, doc_type, udyam_number, gstin,
                entity_name, installation_address, verification_status, disposition, verified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id,
                user_id,
                "UDYAM" if udyam_number else "GST",
                udyam_number,
                gstin,
                business_name,
                formatted_addr,
                server_kyc_status,
                f"CERTIFICATE_SHREDDED_POST_VALIDATION_LINKED_CASE_{matched_case_id}",
                datetime.now().isoformat()
            ))

            # Record Explicit DPDP Consent Event with timestamp, version, purpose, and disclosure text
            consent_ver = explicit_consent.get("version") or "v1.0"
            consent_purpose = explicit_consent.get("purpose") or "DoT Identity Verification and Optical Line Installation under DPDP Act 2023"
            consent_text = explicit_consent.get("consent_text") or "Customer explicitly granted affirmative consent for subscriber KYC and optical line installation."
            consent_ts = explicit_consent.get("timestamp") or datetime.now().isoformat()

            conn.execute("""
            INSERT INTO consent_logs (order_id, user_id, customer_email, consent_type, version, consent_text, purpose, action, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id,
                user_id or "",
                (customer_email or "").lower().strip(),
                "DPDP_ACT_2023_KYC_PROCESSING",
                consent_ver,
                consent_text,
                consent_purpose,
                "EXPLICIT_AFFIRMATIVE_CONSENT_GRANTED",
                consent_ts
            ))
            conn.commit()

        # Dispatch immediate post-KYC confirmation email (covers: money given / deferred, what was done, install date)
        try:
            from app.modules.notifications.email_service import EmailNotificationService
            notif_svc = EmailNotificationService.get_instance()
            notif_svc.send_kyc_order_email(
                order_id=order_id,
                recipient_email=customer_email or "customer@business.in",
                business_name=business_name,
                installation_address=installation_address or {},
                scheduled_install_date=install_date,
                bundle_data=bundle_data,
                amount_paid_inr=0.0,
                txn_id=None,
                udyam_number=udyam_number,
                gstin=gstin,
                kyc_status=kyc_status
            )
        except Exception as e:
            pass

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
            res["is_simulated"] = True
            res["order_mode"] = "SIMULATED_DEMO"
            res["simulation_notice"] = "DEMO / SIMULATED ONBOARDING: Staged order is a prototype simulation. Field engineer contact and installation schedule are simulated placeholders and do not constitute an operational dispatch commitment."
            res["installation_commitment"] = "ESTIMATED_PENDING_SURVEY"
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

            if res.get("kyc_details_json"):
                try:
                    res["kyc_details"] = json.loads(res["kyc_details_json"])
                except Exception:
                    res["kyc_details"] = None
            else:
                res["kyc_details"] = None
            return res

    def get_latest_order_for_user(
        self,
        user_id: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        order_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        # Clean inputs
        user_id = user_id.strip() if user_id else None
        phone = phone.strip() if phone else None
        email = email.strip().lower() if email else None
        order_id = order_id.strip() if order_id else None

        with self._get_connection() as conn:
            # 1. Lookup by user_id
            if user_id:
                row = conn.execute(
                    "SELECT order_id FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
                    (user_id,)
                ).fetchone()
                if row:
                    return self.get_order(row["order_id"])

            # 2. Lookup by email
            if email:
                row = conn.execute(
                    "SELECT order_id FROM orders WHERE lower(customer_email) = ? ORDER BY created_at DESC LIMIT 1",
                    (email,)
                ).fetchone()
                if row:
                    return self.get_order(row["order_id"])

            # 3. Lookup by phone digits
            if phone:
                digits = "".join([c for c in phone if c.isdigit()])[-10:]
                if digits:
                    row = conn.execute(
                        "SELECT order_id FROM orders WHERE contact_phone LIKE ? OR installation_address LIKE ? ORDER BY created_at DESC LIMIT 1",
                        (f"%{digits}%", f"%{digits}%")
                    ).fetchone()
                    if row:
                        ord_candidate = self.get_order(row["order_id"])
                        # If authenticated user_id was supplied, verify it matches
                        if not user_id or ord_candidate.get("user_id") == user_id:
                            return ord_candidate

            # 4. Direct order_id lookup (only for guest or if user matches)
            if order_id:
                ord_obj = self.get_order(order_id)
                if ord_obj:
                    # If user is authenticated, ensure this order actually belongs to them
                    if user_id and ord_obj.get("user_id") and ord_obj.get("user_id") != user_id:
                        return None
                    if email and ord_obj.get("customer_email") and ord_obj.get("customer_email").lower() != email:
                        return None
                    return ord_obj

        # If user has no orders, strictly return None (never leak previous user's order)
        return None

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
            if cursor.rowcount > 0:
                try:
                    from app.modules.notifications.email_service import EmailNotificationService
                    order = self.get_order(order_id)
                    if order:
                        notif_svc = EmailNotificationService.get_instance()
                        notif_svc.send_kyc_order_email(
                            order_id=order_id,
                            recipient_email=order.get("customer_email") or "customer@business.in",
                            business_name=order.get("business_name", "Valued Customer"),
                            installation_address=order.get("installation_address") or {},
                            scheduled_install_date=order.get("scheduled_install_date", ""),
                            bundle_data=order.get("bundle") or {},
                            engineer_name=order.get("engineer_name") or "Ramesh Sharma (Field Lead)",
                            engineer_phone=order.get("engineer_phone") or "+91 98765 43210",
                            amount_paid_inr=amount_inr,
                            txn_id=txn_id,
                            payment_method=payment_method,
                            udyam_number=order.get("udyam_number"),
                            gstin=order.get("gstin"),
                            kyc_status=order.get("kyc_status", "VERIFIED")
                        )
                except Exception:
                    pass
                return True
            return False

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

