from typing import List, Dict, Any, Optional
from datetime import datetime
from app.data_loader import DataLoader

class PartnerPortal:
    def __init__(self):
        self.loader = DataLoader.get_instance()
        self.claimed_leads: Dict[str, Dict[str, Any]] = {
            "L00001": {
                "partner_id": "PTR-IND-882",
                "claimed_at": "2026-11-06T18:30:00",
                "bounty_inr": 1000,
                "status": "IN_PROGRESS"
            }
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

    def get_stalled_leads_with_propensity(self, limit: int = 15) -> List[Dict[str, Any]]:
        raw_leads = self.loader.get_stalled_leads(limit=limit)
        results = []
        for l in raw_leads:
            p_score = self.calculate_propensity_score(l)
            lid = l["lead_id"]
            claim_info = self.claimed_leads.get(lid)
            results.append({
                "lead_id": lid,
                "business_name": l["business_name"],
                "city": l["city"],
                "stage_reached": l["stage_reached"],
                "drop_reason": l["drop_reason"],
                "monthly_spend_inr": l.get("monthly_telecom_spend_inr", 0),
                "has_gstin": l.get("has_gstin", "N"),
                "propensity_score": p_score,
                "priority": "HIGH" if p_score >= 70 else ("MEDIUM" if p_score >= 50 else "STANDARD"),
                "is_claimed": bool(claim_info),
                "claimed_by": claim_info.get("partner_id") if claim_info else None,
                "recovery_bounty_inr": 1000
            })
        return sorted(results, key=lambda x: x["propensity_score"], reverse=True)

    def claim_stalled_lead(self, lead_id: str, partner_id: str = "PTR-IND-882") -> Dict[str, Any]:
        self.claimed_leads[lead_id] = {
            "partner_id": partner_id,
            "claimed_at": datetime.now().isoformat(),
            "bounty_inr": 1000,
            "status": "CLAIMED"
        }
        return {
            "status": "SUCCESS",
            "claim_status": "CLAIMED",
            "message": f"Lead {lead_id} successfully claimed. ₹1,000 spot recovery bounty locked upon activation within 24h.",
            "lead_id": lead_id,
            "partner_id": partner_id,
            "bounty_inr": 1000,
            "recovery_sla_hours": 24
        }

    def generate_partner_referral_link(self, partner_id: str = "PTR-IND-882") -> Dict[str, Any]:
        return {
            "partner_id": partner_id,
            "partner_name": "Vikram Telecom (Mitra Channel Partner)",
            "referral_code": f"REF-{partner_id}",
            "referral_url": f"http://localhost:8000/?ref={partner_id}",
            "commission_tier": "15% recurring trail commission on all 12 monthly bills",
            "qr_label": "Scan to order Airtel Business with dedicated Mitra Partner on-site support"
        }

    def get_partner_commissions(self, partner_id: str = "PTR-IND-882") -> Dict[str, Any]:
        claimed_count = sum(1 for c in self.claimed_leads.values() if c.get("partner_id") == partner_id)
        return {
            "partner_id": partner_id,
            "partner_name": "Vikram Telecom",
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


