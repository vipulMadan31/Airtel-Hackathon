# app/modules/auth/db.py
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
from app.config import DB_PATH

FIXED_ADMIN_PASSWORD = "airteladmin"
FIXED_MITRA_PASSWORD = "airtelmitra"

class UserDatabase:
    _instance: Optional["UserDatabase"] = None

    @classmethod
    def get_instance(cls) -> "UserDatabase":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=30000;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL,
                name TEXT NOT NULL,
                phone TEXT,
                assigned_pincode TEXT,
                badge TEXT,
                created_at TEXT,
                last_login_at TEXT
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS user_tokens (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """)
            conn.commit()

        # Seed standard default accounts
        self._seed_default_accounts()

    def _hash_password(self, password: str, salt: Optional[str] = None) -> (str, str):
        if not salt:
            salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000
        ).hex()
        return pwd_hash, salt

    def _verify_password(self, password: str, salt: str, expected_hash: str) -> bool:
        computed_hash, _ = self._hash_password(password, salt)
        return secrets.compare_digest(computed_hash, expected_hash)

    def _seed_default_accounts(self):
        # 1. Admin
        admin = self.get_user_by_email("admin@airtel.com")
        if not admin:
            h, s = self._hash_password(FIXED_ADMIN_PASSWORD)
            self._insert_user_raw(
                user_id="ADM-HQ-001",
                email="admin@airtel.com",
                password_hash=h,
                salt=s,
                role="ADMIN",
                name="Airtel Enterprise Ops Admin",
                phone="+91 98765 00001",
                assigned_pincode="ALL",
                badge="🛡️ Airtel Ops Admin"
            )

        # 2. Mitra Partner
        mitra = self.get_user_by_email("mitra@airtel.com")
        if not mitra:
            h, s = self._hash_password(FIXED_MITRA_PASSWORD)
            self._insert_user_raw(
                user_id="PTR-IND-882",
                email="mitra@airtel.com",
                password_hash=h,
                salt=s,
                role="PARTNER",
                name="Airtel Mitra Partner",
                phone="+91 98260 55443",
                assigned_pincode="452001",
                badge="🤝 Airtel Mitra Partner"
            )

        # Ensure canonical names for admin and mitra
        try:
            with self._get_connection() as conn:
                conn.execute("UPDATE users SET name = 'Airtel Enterprise Ops Admin' WHERE role = 'ADMIN'")
                conn.execute("UPDATE users SET name = 'Airtel Mitra Partner' WHERE role = 'PARTNER'")
                conn.commit()
        except Exception:
            pass

        # 3. Customer Seed Account
        customer = self.get_user_by_email("customer@business.in")
        if not customer:
            h, s = self._hash_password("customer123")
            self._insert_user_raw(
                user_id="USR-CUST-1001",
                email="customer@business.in",
                password_hash=h,
                salt=s,
                role="MERCHANT",
                name="Airtel MSME Customer",
                phone="+91 98110 12345",
                assigned_pincode="452001",
                badge="🛒 Customer Mode"
            )
        
        # Purge legacy demo accounts if present
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM users WHERE email = 'rajesh@kirana.com'")
                conn.commit()
        except Exception:
            pass

    def _insert_user_raw(
        self,
        user_id: str,
        email: str,
        password_hash: str,
        salt: str,
        role: str,
        name: str,
        phone: Optional[str] = None,
        assigned_pincode: Optional[str] = None,
        badge: Optional[str] = None
    ):
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO users (
                user_id, email, password_hash, salt, role, name, phone, assigned_pincode, badge, created_at, last_login_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, email.lower().strip(), password_hash, salt, role, name,
                phone or "", assigned_pincode or "", badge or "", now, now
            ))
            conn.commit()

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        clean_email = (email or "").lower().strip()
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (clean_email,)).fetchone()
            if row:
                return self._row_to_user_dict(row)
        return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if row:
                return self._row_to_user_dict(row)
        return None

    def register_customer(
        self,
        email: str,
        password: str,
        name: str,
        phone: Optional[str] = None,
        assigned_pincode: Optional[str] = "452001"
    ) -> Dict[str, Any]:
        clean_email = (email or "").lower().strip()
        if not clean_email or "@" not in clean_email:
            raise ValueError("A valid email address is required.")
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters.")
        if not name or not name.strip():
            raise ValueError("Full name / business name is required.")

        existing = self.get_user_by_email(clean_email)
        if existing:
            raise ValueError(f"An account with email '{clean_email}' already exists. Please log in.")

        user_id = f"USR-CUST-{secrets.token_hex(3).upper()}"
        pwd_hash, salt = self._hash_password(password)

        self._insert_user_raw(
            user_id=user_id,
            email=clean_email,
            password_hash=pwd_hash,
            salt=salt,
            role="MERCHANT",
            name=name.strip(),
            phone=phone.strip() if phone else "+91 98110 00000",
            assigned_pincode=assigned_pincode,
            badge="🛒 Customer Mode"
        )
        user = self.get_user_by_id(user_id)
        token = self.create_token(user_id, "MERCHANT")
        return {"user": user, "token": token}

    def authenticate(
        self,
        email: str,
        password: str,
        role: Optional[str] = None
    ) -> Dict[str, Any]:
        clean_email = (email or "").lower().strip()
        clean_role = (role or "").upper().strip()

        if not clean_email:
            raise ValueError("Email address is required.")
        if not password:
            raise ValueError("Password is required.")

        # If role is ADMIN, or email indicates admin, or password matches airteladmin:
        if clean_role == "ADMIN" or clean_email.startswith("admin@") or "admin" in clean_email:
            if password != FIXED_ADMIN_PASSWORD:
                raise ValueError("Invalid password for Admin. Required fixed password: 'airteladmin'")
            
            # Lookup or create Admin user in DB
            user = self.get_user_by_email(clean_email)
            if not user or user["role"] != "ADMIN":
                h, s = self._hash_password(FIXED_ADMIN_PASSWORD)
                user_id = f"ADM-HQ-{secrets.token_hex(2).upper()}"
                display_name = clean_email.split("@")[0].replace(".", " ").title() + " (Airtel Ops Admin)"
                self._insert_user_raw(
                    user_id=user_id,
                    email=clean_email,
                    password_hash=h,
                    salt=s,
                    role="ADMIN",
                    name=display_name,
                    phone="+91 98765 00001",
                    assigned_pincode="ALL",
                    badge="🛡️ Airtel Ops Admin"
                )
                user = self.get_user_by_email(clean_email)
            
            token = self.create_token(user["user_id"], "ADMIN")
            self._update_last_login(user["user_id"])
            return {"user": user, "token": token}

        # If role is PARTNER, or email indicates mitra/partner, or password matches airtelmitra:
        if clean_role == "PARTNER" or "mitra" in clean_email or "partner" in clean_email:
            if password != FIXED_MITRA_PASSWORD:
                raise ValueError("Invalid password for Mitra Partner. Required fixed password: 'airtelmitra'")
            
            # Lookup or create Mitra user in DB
            user = self.get_user_by_email(clean_email)
            if not user or user["role"] != "PARTNER":
                h, s = self._hash_password(FIXED_MITRA_PASSWORD)
                user_id = f"PTR-IND-{secrets.token_hex(2).upper()}"
                display_name = clean_email.split("@")[0].replace(".", " ").title() + " (Mitra Channel Partner)"
                self._insert_user_raw(
                    user_id=user_id,
                    email=clean_email,
                    password_hash=h,
                    salt=s,
                    role="PARTNER",
                    name=display_name,
                    phone="+91 98260 55443",
                    assigned_pincode="452001",
                    badge="🤝 Mitra Channel Partner"
                )
                user = self.get_user_by_email(clean_email)
            
            token = self.create_token(user["user_id"], "PARTNER")
            self._update_last_login(user["user_id"])
            return {"user": user, "token": token}

        # Standard Customer (MERCHANT)
        # Also check if password happens to be fixed passwords for Mitra or Admin without role specified:
        if password == FIXED_ADMIN_PASSWORD and clean_role != "MERCHANT":
            return self.authenticate(clean_email, password, role="ADMIN")
        if password == FIXED_MITRA_PASSWORD and clean_role != "MERCHANT":
            return self.authenticate(clean_email, password, role="PARTNER")

        user = self.get_user_by_email(clean_email)
        if not user:
            raise ValueError(f"No account found with email '{clean_email}'. Please sign up first.")

        if not self._verify_password(password, user["salt"], user["password_hash"]):
            raise ValueError("Incorrect password. Please verify your credentials.")

        token = self.create_token(user["user_id"], user["role"])
        self._update_last_login(user["user_id"])
        return {"user": user, "token": token}

    def create_token(self, user_id: str, role: str, expiry_hours: int = 24) -> str:
        token = f"oa_{role.lower()}_{secrets.token_urlsafe(24)}"
        now = datetime.now()
        expires = now + timedelta(hours=expiry_hours)
        with self._get_connection() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO user_tokens (token, user_id, role, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """, (token, user_id, role, now.isoformat(), expires.isoformat()))
            conn.commit()
        return token

    def get_user_by_token(self, token: Optional[str]) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        now_iso = datetime.now().isoformat()
        with self._get_connection() as conn:
            row = conn.execute("""
            SELECT u.* FROM users u
            JOIN user_tokens t ON u.user_id = t.user_id
            WHERE t.token = ? AND t.expires_at > ?
            """, (token, now_iso)).fetchone()
            if row:
                return self._row_to_user_dict(row)
        return None

    def logout_token(self, token: str) -> bool:
        if not token:
            return False
        with self._get_connection() as conn:
            conn.execute("DELETE FROM user_tokens WHERE token = ?", (token,))
            conn.commit()
        return True

    def _update_last_login(self, user_id: str):
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute("UPDATE users SET last_login_at = ? WHERE user_id = ?", (now, user_id))
            conn.commit()

    def _row_to_user_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        role = row["role"]
        perms = ["view_my_quote", "view_my_order", "submit_kyc", "chat_advisor"]
        if role == "PARTNER":
            perms.extend(["view_partner_leads", "claim_bounty", "generate_referral_qr"])
        elif role == "ADMIN":
            perms = ["*"]

        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "email": row["email"],
            "role": role,
            "name": row["name"],
            "phone": row["phone"],
            "assigned_pincode": row["assigned_pincode"],
            "badge": row["badge"],
            "created_at": row["created_at"],
            "last_login_at": row["last_login_at"],
            "permissions": perms,
            "salt": row["salt"],
            "password_hash": row["password_hash"]
        }

