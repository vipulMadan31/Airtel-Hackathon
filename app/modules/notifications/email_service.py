# app/modules/notifications/email_service.py
import os
import sqlite3
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from app.config import DB_PATH

logger = logging.getLogger("AirtelEmailService")

class EmailNotificationService:
    _instance: Optional["EmailNotificationService"] = None

    @classmethod
    def get_instance(cls) -> "EmailNotificationService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self._init_db()

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
            CREATE TABLE IF NOT EXISTS email_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                recipient_email TEXT NOT NULL,
                subject TEXT NOT NULL,
                body_html TEXT NOT NULL,
                body_text TEXT,
                amount_paid_inr REAL DEFAULT 0.0,
                payment_status TEXT DEFAULT 'NOT_PAID',
                install_date TEXT,
                status TEXT DEFAULT 'SENT',
                error_message TEXT,
                sent_at TEXT NOT NULL
            )
            """)
            conn.commit()

    def send_kyc_order_email(
        self,
        order_id: str,
        recipient_email: str,
        business_name: str,
        installation_address: Dict[str, Any],
        scheduled_install_date: str,
        bundle_data: Dict[str, Any],
        engineer_name: str = "Ramesh Sharma (Field Lead)",
        engineer_phone: str = "+91 98765 43210",
        amount_paid_inr: float = 0.0,
        txn_id: Optional[str] = None,
        payment_method: Optional[str] = None,
        udyam_number: Optional[str] = None,
        gstin: Optional[str] = None,
        kyc_status: str = "VERIFIED"
    ) -> Dict[str, Any]:
        """
        Generates and dispatches a comprehensive post-KYC confirmation email:
        - Exactly how much money was given (or ₹0 if payment deferred)
        - What has been done (Smart KYC validated, line route tested, hardware staged)
        - Estimated date of installation & technician contact
        """
        clean_email = (recipient_email or "").strip().lower()
        if not clean_email or "@" not in clean_email:
            clean_email = "customer@business.in"

        # Determine financial status
        has_paid = amount_paid_inr > 0 and bool(txn_id)
        payment_status_text = "PAID" if has_paid else "NOT_PAID_DEFERRED"

        formatted_address = ""
        if isinstance(installation_address, dict):
            formatted_address = installation_address.get("formatted_address") or f"{installation_address.get('unit_no', '')}, {installation_address.get('building', '')}, {installation_address.get('street', '')}, {installation_address.get('city', '')} - {installation_address.get('pincode', '')}"
            slot = installation_address.get("preferred_slot", "MORNING (10:00 AM – 01:00 PM)")
        else:
            formatted_address = str(installation_address or "Rohtak Premises")
            slot = "Morning (10:00 AM – 01:00 PM)"

        # Product items list
        items = bundle_data.get("items", [])
        items_html = ""
        items_text = ""
        for it in items:
            p_name = it.get("product_name") or it.get("name") or "Plan"
            p_price = it.get("line_monthly_inr") or it.get("price_inr") or it.get("unit_price_inr", 0)
            items_html += f"<tr><td style='padding: 6px 0; color: #334155; font-size: 13px;'>• <strong>{p_name}</strong></td><td style='padding: 6px 0; text-align: right; color: #0f172a; font-weight: bold; font-size: 13px;'>₹{float(p_price):,.2f}/mo</td></tr>"
            items_text += f"  - {p_name}: ₹{float(p_price):,.2f}/mo\n"

        monthly_total = bundle_data.get("total_monthly_inr", 0.0)

        # Money given card
        if has_paid:
            money_badge_html = f"""
            <div style="background-color: #ecfdf5; border: 1px solid #10b981; border-radius: 8px; padding: 14px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 12px; font-weight: 800; color: #065f46; text-transform: uppercase; letter-spacing: 0.5px;">Payment Collected Today:</span>
                    <span style="background-color: #059669; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">₹{amount_paid_inr:.2f} PAID</span>
                </div>
                <div style="font-size: 20px; font-weight: 900; color: #065f46; margin: 6px 0 2px 0;">₹{amount_paid_inr:.2f} <span style="font-size: 12px; font-weight: normal; color: #047857;">(Priority Booking Deposit)</span></div>
                <div style="font-size: 12px; color: #065f46; line-height: 1.4;">
                    <strong>Transaction Ref:</strong> {txn_id} &bull; <strong>Method:</strong> {payment_method or 'UPI AutoPay'}<br>
                    <span style="color: #047857;">&bull; 100% of this ₹{amount_paid_inr:.2f} deposit will be credited against your Month 1 recurring bill.</span>
                </div>
            </div>
            """
            money_text = f"Payment Collected Today: ₹{amount_paid_inr:.2f} (PAID)\nRef: {txn_id} | Mode: {payment_method or 'UPI AutoPay'}\nBenefit: 100% of ₹{amount_paid_inr:.2f} credited against Month 1 recurring invoice."
        else:
            money_badge_html = """
            <div style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 12px; font-weight: 800; color: #475569; text-transform: uppercase; letter-spacing: 0.5px;">Payment Collected Today:</span>
                    <span style="background-color: #64748b; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">₹0.00 (DEFERRED / PAY ON HANDOVER)</span>
                </div>
                <div style="font-size: 20px; font-weight: 900; color: #1e293b; margin: 6px 0 2px 0;">₹0.00 <span style="font-size: 12px; font-weight: normal; color: #64748b;">(No Advance Collected)</span></div>
                <div style="font-size: 12px; color: #475569; line-height: 1.4;">
                    You have opted to pay after physical optical line installation and speed-test sign-off on your premises.<br>
                    <strong>Due Today:</strong> ₹0.00. No deduction has been made.
                </div>
            </div>
            """
            money_text = "Payment Collected Today: ₹0.00 (DEFERRED / NO ADVANCE TAKEN)\nDue Today: ₹0.00\nPayment will be collected after line wiring & speed test sign-off."

        subject = f"[Airtel Business] Smart KYC Completed & Installation Scheduled — Order #{order_id}"

        # HTML Email Body
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 20px; color: #1e293b; }}
  .email-container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
  .header {{ background-color: #E40000; padding: 20px 24px; color: #ffffff; }}
  .header h1 {{ margin: 0; font-size: 20px; font-weight: 900; letter-spacing: 0.5px; }}
  .content {{ padding: 24px; }}
  .section-card {{ background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
  .section-title {{ font-size: 13px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; color: #E40000; margin-bottom: 8px; display: flex; align-items: center; }}
  .check-item {{ font-size: 13px; color: #334155; margin-bottom: 6px; line-height: 1.4; }}
  .footer {{ background-color: #f8fafc; padding: 16px 24px; text-align: center; font-size: 11px; color: #64748b; border-top: 1px solid #e2e8f0; }}
</style>
</head>
<body>
  <div class="email-container">
    <div class="header">
      <div style="font-size: 11px; text-transform: uppercase; font-weight: 700; opacity: 0.9; letter-spacing: 1px;">Airtel Business Enterprise Broadband</div>
      <h1>Order Confirmation & Smart KYC Update</h1>
      <div style="font-size: 12px; margin-top: 4px; opacity: 0.95;">Order ID: <strong>{order_id}</strong> &bull; {datetime.now().strftime('%d %B %Y')}</div>
    </div>
    <div class="content">
      <p style="font-size: 14px; margin-top: 0; color: #0f172a;">
        Dear <strong>{business_name}</strong>,
      </p>
      <p style="font-size: 13px; color: #475569; line-height: 1.5;">
        Thank you for choosing Airtel Business. Your enterprise line order has been successfully registered, Smart KYC has been statutory-approved, and technician dispatch has been scheduled.
      </p>

      <!-- 1. Money Given / Payment Status -->
      {money_badge_html}

      <!-- 2. What Has Been Done -->
      <div class="section-card">
        <div class="section-title">✓ What Has Been Done</div>
        <div class="check-item">✅ <strong>Smart KYC Statutory Approval:</strong> {f'Udyam Registration verified ({udyam_number})' if udyam_number else (f'GSTIN verified ({gstin})' if gstin else 'Identity & Entity records validated active')}. Raw document shredded post-OCR per DPDP data minimization rules.</div>
        <div class="check-item">✅ <strong>Line Route Feasibility:</strong> Optical Distribution Point (ODP) line path verified for high-speed symmetric connectivity.</div>
        <div class="check-item">✅ <strong>Hardware Allocation:</strong> Dual-band Gigabit Wi-Fi 6 Router & Optical Network Terminal (ONT) staged for field delivery.</div>
        <div class="check-item">✅ <strong>Field Lead Assigned:</strong> <strong>{engineer_name}</strong> (Ph: {engineer_phone}).</div>
      </div>

      <!-- 3. Estimated Date of Installation -->
      <div class="section-card" style="border-left: 4px solid #E40000;">
        <div class="section-title" style="color: #0f172a;">📅 Estimated Installation Timeline</div>
        <div style="font-size: 16px; font-weight: 900; color: #E40000; margin: 4px 0;">{scheduled_install_date}</div>
        <div style="font-size: 12px; color: #334155; margin-bottom: 8px;">
          <strong>Preferred Slot:</strong> {slot}<br>
          <strong>Premises Address:</strong> {formatted_address}
        </div>
        <div style="font-size: 11px; color: #64748b; background-color: #f8fafc; padding: 8px; border-radius: 6px;">
          Our engineer will call you 30 minutes prior to arrival. Physical drop cable wiring, optical power sign-off, and Wi-Fi throughput test will be completed on-site.
        </div>
      </div>

      <!-- 4. Selected Digital Bundle -->
      <div class="section-card">
        <div class="section-title">📋 Selected Digital Bundle</div>
        <table style="width: 100%; border-collapse: collapse; margin-top: 4px;">
          {items_html}
          <tr style="border-top: 1px dashed #cbd5e1;">
            <td style="padding: 8px 0 0 0; font-size: 13px; font-weight: bold; color: #0f172a;">Monthly Total (inc. 18% GST):</td>
            <td style="padding: 8px 0 0 0; text-align: right; font-size: 14px; font-weight: 900; color: #E40000;">₹{monthly_total:,.2f}/mo</td>
          </tr>
          <tr>
            <td style="padding: 2px 0 0 0; font-size: 11px; color: #059669; font-weight: bold;">One-Time Fiber Setup & Wi-Fi 6 Router Fee:</td>
            <td style="padding: 2px 0 0 0; text-align: right; font-size: 11px; color: #059669; font-weight: bold;">₹0.00 (100% WAIVED)</td>
          </tr>
        </table>
      </div>

      <div style="text-align: center; margin-top: 20px;">
        <p style="font-size: 12px; color: #64748b;">Track your technician live or reschedule installation from your customer portal anytime.</p>
      </div>
    </div>

    <div class="footer">
      <p style="margin: 0 0 4px 0;"><strong>Bharti Airtel Limited &bull; Airtel Business Enterprise Care</strong></p>
      <p style="margin: 0; color: #94a3b8;">Toll Free: 1800-103-0405 &bull; Email: 121@airtel.com &bull; Certified DPDP Act Compliant</p>
    </div>
  </div>
</body>
</html>
        """

        # Plain text version for fallback
        text_content = f"""
==============================================================
AIRTEL BUSINESS - ORDER CONFIRMATION & SMART KYC UPDATE
Order ID: {order_id} | Date: {datetime.now().strftime('%Y-%m-%d')}
==============================================================

Dear {business_name},

Your Airtel Business fiber connection order has been registered and verified.

1. PAYMENT SUMMARY:
--------------------------------------------------------------
{money_text}

2. WHAT HAS BEEN DONE:
--------------------------------------------------------------
* Smart KYC Verified: {udyam_number or gstin or 'Approved'} (DPDP data minimization compliant)
* Optical Line Route: Confirmed to {formatted_address}
* Hardware Staging: Enterprise Wi-Fi 6 Router + Optical Terminal staged
* Field Lead Assigned: {engineer_name} ({engineer_phone})

3. ESTIMATED INSTALLATION DATE:
--------------------------------------------------------------
* Scheduled Date: {scheduled_install_date}
* Preferred Slot: {slot}
* On-Site Premises: {formatted_address}

4. BUNDLE PLAN SUMMARY:
--------------------------------------------------------------
{items_text}
Monthly Total: ₹{monthly_total:,.2f}/mo (inc. 18% GST)
Setup & Installation Fee: ₹0.00 (100% Waived)

Thank you for choosing Airtel Business.
Toll Free: 1800-103-0405 | 121@airtel.com
==============================================================
        """

        # Dispatch via SMTP if configured in environment
        dispatch_status = "SENT_SIMULATED_LOGGED"
        error_msg = None

        smtp_host = os.getenv("SMTP_HOST") or os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        smtp_from = os.getenv("SMTP_FROM", "Airtel Business <onboarding@airtel.com>")

        if smtp_host and smtp_user and smtp_password:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = smtp_from
                msg["To"] = clean_email
                msg.attach(MIMEText(text_content, "plain"))
                msg.attach(MIMEText(html_content, "html"))

                with smtplib.SMTP(smtp_host, smtp_port, timeout=8) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_from, [clean_email], msg.as_string())
                dispatch_status = "SENT_VIA_SMTP"
                logger.info(f"Successfully sent live SMTP email to {clean_email} for order {order_id}")
            except Exception as e:
                error_msg = str(e)
                dispatch_status = "SMTP_FAILED_FALLBACK_STORED"
                logger.warning(f"SMTP dispatch to {clean_email} failed: {e}. Stored in local DB.")

        # Persist notification in SQLite database
        now_iso = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute("""
            INSERT INTO email_notifications (
                order_id, recipient_email, subject, body_html, body_text,
                amount_paid_inr, payment_status, install_date, status, error_message, sent_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id,
                clean_email,
                subject,
                html_content,
                text_content,
                amount_paid_inr,
                payment_status_text,
                scheduled_install_date,
                dispatch_status,
                error_msg,
                now_iso
            ))
            conn.commit()
            notif_id = cursor.lastrowid

        return {
            "notification_id": notif_id,
            "order_id": order_id,
            "recipient_email": clean_email,
            "subject": subject,
            "amount_paid_inr": amount_paid_inr,
            "payment_status": payment_status_text,
            "scheduled_install_date": scheduled_install_date,
            "dispatch_status": dispatch_status,
            "sent_at": now_iso,
            "html_content": html_content
        }

    def get_notifications_for_order(self, order_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM email_notifications WHERE order_id = ? ORDER BY id DESC",
                (order_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_latest_notification_for_email(self, email: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM email_notifications WHERE recipient_email = ? ORDER BY id DESC LIMIT 1",
                (email.strip().lower(),)
            ).fetchone()
            return dict(row) if row else None

    def get_notification_by_id(self, notif_id: int) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM email_notifications WHERE id = ?",
                (notif_id,)
            ).fetchone()
            return dict(row) if row else None

