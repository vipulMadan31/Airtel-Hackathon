from typing import List, Dict, Any, Optional
from datetime import datetime
from app.data_loader import DataLoader

PARTNER_REGISTRY: Dict[str, Dict[str, Any]] = {
    "PTR-IND-882": {
        "partner_id": "PTR-IND-882",
        "name": "Vikram Telecom (Mitra Channel Partner)",
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

    def get_stalled_leads_with_propensity(self, limit: int = 15) -> List[Dict[str, Any]]:
        raw_leads = self.loader.get_stalled_leads(limit=limit)
        results = []
        for idx, l in enumerate(raw_leads):
            p_score = self.calculate_propensity_score(l)
            lid = l["lead_id"]
            claim_info = self.claimed_leads.get(lid)

            # Resolve partner via 4-Tier Hierarchical Routing Engine
            city_val = l.get("city", "Indore")
            pin_val = l.get("installation_pincode") or ("452001" if city_val.lower() == "indore" else None)
            routing = self.resolve_partner_for_lead(
                pincode=pin_val,
                city=city_val,
                tier=l.get("city_tier", 2)
            )

            # 4-Hour SLA Computation for Fast-Track Routing
            is_claimed = bool(claim_info)
            if is_claimed:
                sla_remaining = "Locked"
                sla_status = "CLAIMED"
            elif lid == "L00007":
                # Planted exception scenario: SLA expired without claim -> Escalated to Central Ops
                sla_remaining = "0.0h (Breached)"
                sla_status = "BREACHED"
            elif p_score >= 70:
                # High propensity: countdown from 4.0 hours
                hours_left = max(0.5, round(4.0 - ((idx % 6) * 0.6), 1))
                sla_remaining = f"{hours_left}h left"
                sla_status = "WARNING" if hours_left < 1.5 else "ACTIVE"
            else:
                sla_remaining = "24h SLA"
                sla_status = "STANDARD"

            results.append({
                "lead_id": lid,
                "business_name": l["business_name"],
                "city": l["city"],
                "pincode": pin_val or routing.get("hub_pincode", "452001"),
                "stage_reached": l["stage_reached"],
                "drop_reason": l["drop_reason"],
                "monthly_spend_inr": l.get("monthly_telecom_spend_inr", 0),
                "has_gstin": l.get("has_gstin", "N"),
                "propensity_score": p_score,
                "priority": "HIGH" if p_score >= 70 else ("MEDIUM" if p_score >= 50 else "STANDARD"),
                "is_claimed": is_claimed,
                "claimed_by": claim_info.get("partner_id") if claim_info else None,
                "recovery_bounty_inr": 1000,
                # Phase 3 Routing & SLA fields:
                "routing_tier": routing["routing_tier"],
                "routing_label": routing["routing_label"],
                "assigned_partner_id": routing["partner_id"],
                "assigned_partner_name": routing["partner_name"],
                "sla_hours": routing["sla_hours"],
                "sla_remaining": sla_remaining,
                "sla_status": sla_status
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


