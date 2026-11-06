# app/modules/payment/gateway.py
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from app.modules.orders.state_machine import OrderStateMachine

class PaymentGateway:
    """
    Simulated Payment Gateway & UPI AutoPay Mandate Engine:
    - Implements ₹499 fully refundable priority booking token.
    - Simulates UPI deep links & dynamic QR codes (PhonePe, GPay, Paytm, Airtel Payments Bank).
    - Sets up recurring e-Mandate for consolidated post-activation billing.
    - Generates compliant GST tax receipt with 18% itemization.
    """
    def __init__(self, order_sm: Optional[OrderStateMachine] = None):
        self.order_sm = order_sm or OrderStateMachine()

    def create_payment_intent(
        self,
        order_id: str,
        amount_inr: float = 499.0,
        business_name: str = "",
        phone: str = ""
    ) -> Dict[str, Any]:
        txn_id = f"TXN-UPI-{uuid.uuid4().hex[:8].upper()}"
        upi_vpa = "accelbusiness.pay@airtel"
        upi_intent = (
            f"upi://pay?pa={upi_vpa}&pn=Airtel%20Business"
            f"&am={amount_inr:.2f}&cu=INR&tn=UDYAM_PRIORITY_SLOT_{order_id}"
        )

        base_amt = round(amount_inr / 1.18, 2)
        gst_18 = round(amount_inr - base_amt, 2)

        return {
            "status": "INITIATED",
            "order_id": order_id,
            "txn_id": txn_id,
            "amount_inr": amount_inr,
            "base_amount_inr": base_amt,
            "gst_18_inr": gst_18,
            "currency": "INR",
            "upi_vpa": upi_vpa,
            "upi_intent_url": upi_intent,
            "supported_apps": [
                {"id": "phonepe", "name": "PhonePe", "icon": "🟣"},
                {"id": "gpay", "name": "Google Pay", "icon": "🔵"},
                {"id": "paytm", "name": "Paytm UPI", "icon": "🔷"},
                {"id": "airtel_bank", "name": "Airtel Payments Bank", "icon": "🔴"}
            ],
            "terms": {
                "refundable": True,
                "credit_window": "Adjusted 100% on first monthly recurring bill",
                "mandate_type": "UPI AutoPay e-Mandate",
                "max_cycle_amount_inr": 15000.0
            }
        }

    def confirm_payment(
        self,
        order_id: str,
        txn_id: str,
        payment_method: str = "UPI_PHONEPE",
        mandate_active: bool = True,
        amount_inr: float = 499.0
    ) -> Dict[str, Any]:
        receipt_num = f"RCT-{uuid.uuid4().hex[:8].upper()}"
        mandate_auth_id = f"MND-UPI-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now().isoformat()

        base_amt = round(amount_inr / 1.18, 2)
        gst_18 = round(amount_inr - base_amt, 2)

        receipt = {
            "receipt_number": receipt_num,
            "order_id": order_id,
            "txn_id": txn_id,
            "payment_status": "SUCCESS",
            "payment_method": payment_method,
            "amount_paid_inr": amount_inr,
            "base_amount_inr": base_amt,
            "gst_18_inr": gst_18,
            "sac_code": "998411",  # Telecommunications services SAC
            "gst_treatment": "B2B Telecom Priority Installation Token",
            "mandate_status": "ACTIVE" if mandate_active else "SKIPPED",
            "mandate_auth_id": mandate_auth_id if mandate_active else None,
            "timestamp": now_iso,
            "benefit_notice": "100% of ₹499.00 will be credited against Month 1 recurring bill upon physical optical line activation."
        }

        # Update order database if order exists
        if order_id:
            self.order_sm.record_payment(
                order_id=order_id,
                amount_inr=amount_inr,
                txn_id=txn_id,
                payment_method=payment_method,
                receipt=receipt
            )

        return receipt

