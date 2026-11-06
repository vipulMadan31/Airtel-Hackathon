from typing import List, Dict, Any
from app.data_loader import DataLoader

class PartnerPortal:
    def __init__(self):
        self.loader = DataLoader.get_instance()

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
            results.append({
                "lead_id": l["lead_id"],
                "business_name": l["business_name"],
                "city": l["city"],
                "stage_reached": l["stage_reached"],
                "drop_reason": l["drop_reason"],
                "monthly_spend_inr": l.get("monthly_telecom_spend_inr", 0),
                "has_gstin": l.get("has_gstin", "N"),
                "propensity_score": p_score,
                "priority": "HIGH" if p_score >= 70 else ("MEDIUM" if p_score >= 50 else "STANDARD")
            })
        return sorted(results, key=lambda x: x["propensity_score"], reverse=True)

    def generate_partner_referral_link(self, partner_id: str = "PTR-IND-882") -> Dict[str, str]:
        return {
            "partner_id": partner_id,
            "referral_code": f"REF-{partner_id}",
            "referral_url": f"http://localhost:8000/?ref={partner_id}",
            "commission_tier": "15% of first-month bundle value"
        }

