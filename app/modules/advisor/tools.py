"""
Deterministic Business Operations and Catalog Tools for AI Advisor.
All pricing, statutory eligibility, feasibility, and bundle compositions
are strictly evaluated and generated here through backend engines.
"""

from typing import Dict, Any, List, Optional, Tuple
from app.data_loader import DataLoader
from app.modules.catalog.engine import CatalogEngine
from app.modules.pricing.calculator import PricingCalculator
from app.modules.advisor.profile import infer_tier_from_city

TAG_TEMPLATES = {
    "P01": "100 Mbps optical fibre connectivity for reliable everyday {biz} operations",
    "P02": "300 Mbps high-speed fibre sized for multi-device operations and digital records",
    "P03": "1 Gbps enterprise-grade ultra-fast connectivity for high-volume data workflows",
    "P04": "High-speed 100 Mbps 5G AirFiber broadband for rapid wireless deployment",
    "P05": "Dedicated 20 Mbps 1:1 leased line with 99.9% uptime SLA",
    "P06": "Dedicated 100 Mbps 1:1 leased line with guaranteed enterprise SLA",
    "P07": "Corporate mobile postpaid with pooled talktime and data for staff",
    "P08": "Executive business postpaid plan with unlimited voice & data roaming",
    "P09": "Automatic 4G/5G wireless failover ensuring zero internet downtime",
    "P10": "Centrally managed SD-WAN connecting multi-site branch locations securely",
    "P11": "Static IPv4 address for hosting servers, CCTV, and VPN access",
    "P12": "Cloud virtual telephony & IVR for automated customer call routing",
    "P13": "1800 toll-free brand number building customer credibility",
    "P14": "10,000 bulk SMS credits for customer transaction and promotional alerts",
    "P15": "Official WhatsApp Business API with verified green badge support",
    "P16": "Professional domain email and cloud productivity suite",
    "P17": "Automated 1 TB cloud backup safeguarding critical {biz} records and data",
    "P18": "Custom domain name and starter website to establish online presence",
    "P19": "Cloud billing & POS with instant UPI soundbox audio payment confirmation",
    "P20": "Endpoint security and proactive cyber threat defense for business systems",
    "P21": "Next-generation enterprise firewall blocking unauthorized network access",
    "P22": "Dual-SSID secure Wi-Fi isolating guest access from internal {biz} networks",
    "P23": "AI-enabled cloud CCTV security surveillance with remote mobile viewing",
    "P24": "Industrial IoT machine telemetry and uptime monitoring sensors",
    "P25": "Real-time GPS fleet tracking with geofencing and vehicle route alerts"
}

def get_explainability_tag(pid: str, pname: Optional[str] = None, business_type: Optional[str] = None) -> str:
    """Generates an itemized explainability tag tailored to the customer's business persona."""
    biz = (business_type or "business").lower()
    tmpl = TAG_TEMPLATES.get(pid)
    if tmpl:
        return tmpl.format(biz=biz)
    name = pname or pid
    return f"Tailored {name} subscription configured for your {biz}"

class AdvisorTools:
    """
    Exposes pure deterministic backend operations for both Gemini Tool-Calling
    and the deterministic fallback engine.
    """
    def __init__(self):
        self.loader = DataLoader.get_instance()
        self.catalog_engine = CatalogEngine()
        self.pricing_calculator = PricingCalculator()

    def get_catalogue(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves official product catalogue records directly from the database/CSV."""
        all_products = self.loader.get_all_products()
        if not category:
            return all_products
        cat_lower = category.strip().lower()
        return [p for p in all_products if p.get("category", "").lower() == cat_lower]

    def check_network_feasibility(self, pincode: str, city: Optional[str] = None) -> Dict[str, Any]:
        """Validates PIN-level network feasibility (FTTH Fibre vs 5G AirFiber)."""
        return self.catalog_engine.check_network_feasibility(pincode, city)

    def check_product_eligibility(self, product_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Checks 5-dimensional statutory and feasibility rules for a product."""
        prod = self.loader.get_product(product_id)
        if not prod:
            return {"eligible": False, "reason": f"Product {product_id} not found in catalogue"}

        city_tier = int(profile.get("city_tier") or (infer_tier_from_city(profile.get("city")) if profile.get("city") else 2))
        emp_count = int(profile.get("employee_count") or 3)
        num_sites = int(profile.get("num_sites") or 1)
        # Default has_gstin to True if not explicitly False
        has_gstin = profile.get("has_gstin") is not False

        eligible, reason = self.catalog_engine.evaluate_product_eligibility(
            prod, city_tier, emp_count, num_sites, has_gstin
        )
        return {
            "product_id": product_id,
            "product_name": prod.get("product_name"),
            "eligible": eligible,
            "reason": reason
        }

    def calculate_quotation(self, bundle: Dict[str, int], has_gstin: bool = True) -> Dict[str, Any]:
        """Calculates itemized quote with digital discounts, 18% GST, and waived setup fees."""
        return self.pricing_calculator.calculate_quote(
            bundle, apply_digital_discount=True, waive_setup_fee=True
        )

    def generate_bundle(self, profile: Dict[str, Any], preferences: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Deterministically builds a compliant solution bundle tailored to customer firmographics.
        Guarantees that all statutory, headcount, tier, and feasibility constraints are met.
        """
        biz = (profile.get("business_type") or "retail").lower()
        emp_count = int(profile.get("employee_count") or 3)
        num_sites = int(profile.get("num_sites") or 1)
        city_tier = int(profile.get("city_tier") or (infer_tier_from_city(profile.get("city")) if profile.get("city") else 2))
        has_gstin = profile.get("has_gstin") is not False
        pincode = profile.get("pincode")
        city = profile.get("city")
        rural = bool(profile.get("rural_location"))
        taar_present = profile.get("taar_present")

        # Check PIN feasibility
        feasibility = None
        if pincode:
            feasibility = self.check_network_feasibility(pincode, city)

        bundle: Dict[str, int] = {}

        # 1. Base Connectivity Selection
        is_airfiber_needed = rural and (taar_present is False or taar_present is None)
        if feasibility and not feasibility.get("is_fibre_feasible"):
            is_airfiber_needed = True

        # Multi-site special handling
        site_headcounts = profile.get("site_headcounts")
        if num_sites > 1 and site_headcounts and len(site_headcounts) == num_sites:
            # Different plan per site
            for hc in site_headcounts:
                if is_airfiber_needed:
                    bundle["P04"] = bundle.get("P04", 0) + 1
                elif hc >= 50 and city_tier == 1 and has_gstin is True:
                    bundle["P03"] = bundle.get("P03", 0) + 1
                elif hc >= 5:
                    bundle["P02"] = bundle.get("P02", 0) + 1
                else:
                    bundle["P01"] = bundle.get("P01", 0) + 1
        elif is_airfiber_needed:
            bundle["P04"] = num_sites
        elif any(k in biz for k in ["tech", "startup", "software", "agency", "it"]):
            if city_tier == 1 and emp_count >= 20 and has_gstin is True:
                bundle["P03"] = num_sites
            else:
                bundle["P02"] = num_sites
        elif any(k in biz for k in ["clinic", "dental", "doctor", "health", "hospital"]):
            bundle["P02"] = num_sites
        elif any(k in biz for k in ["office", "ca", "accounting", "legal", "consulting", "law"]):
            bundle["P02"] = num_sites
        elif any(k in biz for k in ["restaurant", "cafe", "food", "hotel", "bakery"]):
            bundle["P01"] = num_sites
        else:
            # Default retail / kirana / small shop
            bundle["P01"] = num_sites

        # 2. Domain-Specific Digital & SaaS Add-ons
        removed_addons = set(profile.get("removed_addons", []))
        if any(k in biz for k in ["clinic", "dental", "doctor", "health"]):
            bundle["P22"] = 1  # Guest Wi-Fi
            bundle["P17"] = 1  # Cloud Backup 1TB
            bundle["P20"] = 1  # Endpoint Security
        elif any(k in biz for k in ["tech", "startup", "software", "agency", "it"]):
            bundle["P16"] = emp_count  # Cloud Email per user
            bundle["P20"] = min(25, max(2, emp_count))  # Endpoint Security
            bundle["P11"] = 1  # Static IP
        elif any(k in biz for k in ["office", "ca", "accounting", "legal", "consulting"]):
            bundle["P16"] = emp_count  # Cloud Email
            bundle["P17"] = 1  # Cloud Backup
            bundle["P20"] = min(10, max(2, emp_count))  # Endpoint Security
        elif any(k in biz for k in ["restaurant", "cafe", "bakery"]):
            bundle["P19"] = 1  # Cloud POS & Soundbox
            bundle["P22"] = 1  # Guest Wi-Fi
        else:
            # Retail / General merchant
            bundle["P19"] = 1  # Cloud POS & Soundbox
            bundle["P20"] = min(5, max(1, num_sites))  # Endpoint Security

        # Strip any add-ons explicitly removed by customer
        for r_pid in removed_addons:
            if r_pid in bundle:
                del bundle[r_pid]

        # 3. Apply Statutory & Feasibility Filters
        validated_bundle: Dict[str, int] = {}
        for pid, qty in bundle.items():
            prod = self.loader.get_product(pid)
            if not prod:
                continue
            eligible, _ = self.catalog_engine.evaluate_product_eligibility(
                prod, city_tier, emp_count, num_sites, has_gstin
            )
            if eligible:
                validated_bundle[pid] = qty
            elif pid == "P03" and (city_tier > 1 or has_gstin is not True):
                # Downgrade 1G to 300M in non-Tier-1 cities or when GSTIN is not confirmed
                validated_bundle["P02"] = bundle.get("P02", 0) + qty

        # 4. Generate Explainability Tags
        tags = []
        for pid in validated_bundle.keys():
            prod_info = self.loader.get_product(pid)
            pname = prod_info.get("product_name", pid) if prod_info else pid
            tags.append({
                "product_id": pid,
                "name": pname,
                "tag": get_explainability_tag(pid, pname, biz)
            })

        # 5. Authoritative Pricing
        quotation = self.calculate_quotation(validated_bundle, has_gstin=has_gstin)

        return {
            "bundle": validated_bundle,
            "tags": tags,
            "quotation": quotation
        }

    def progressive_downsell(self, current_bundle: Dict[str, int], current_step: int = 1) -> Dict[str, Any]:
        """Executes the 4-step controlled down-sell sequence from the specification."""
        step = max(1, min(4, current_step))
        quote = self.pricing_calculator.execute_downsell_step(current_bundle, step)
        new_quantities = {
            item["product_id"]: item["quantity"] for item in quote.get("items", [])
        }
        tags = []
        for pid in new_quantities.keys():
            prod_info = self.loader.get_product(pid)
            pname = prod_info.get("product_name", pid) if prod_info else pid
            tags.append({
                "product_id": pid,
                "name": pname,
                "tag": get_explainability_tag(pid, pname)
            })
        return {
            "bundle": new_quantities,
            "tags": tags,
            "quotation": quote,
            "step_executed": step,
            "explanation": quote.get("explanation", "")
        }

    def remove_addon(self, current_bundle: Dict[str, int], product_id: str) -> Dict[str, Any]:
        """Removes an optional add-on while maintaining core connectivity."""
        new_bundle = dict(current_bundle)
        pid_upper = product_id.upper().strip()

        # Resolve human name or ID
        target_pid = None
        if pid_upper in new_bundle:
            target_pid = pid_upper
        else:
            for p in self.loader.get_all_products():
                if pid_upper in p.get("product_name", "").upper() or pid_upper in p.get("product_id", "").upper():
                    if p["product_id"] in new_bundle:
                        target_pid = p["product_id"]
                        break

        if target_pid and target_pid in new_bundle:
            prod = self.loader.get_product(target_pid)
            # Never remove base connectivity if it's the only line
            base_pids = {"P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08"}
            remaining_bases = [p for p in new_bundle.keys() if p in base_pids and p != target_pid]
            if target_pid not in base_pids or len(remaining_bases) > 0:
                del new_bundle[target_pid]

        # Validate dependencies
        valid, errs = self.catalog_engine.validate_bundle_dependencies(list(new_bundle.keys()))
        if not valid:
            # If dependency broken (e.g. removed base line that P09 depended on), clean broken items
            for pid in list(new_bundle.keys()):
                p = self.loader.get_product(pid)
                if p and p.get("requires_one_of"):
                    reqs = [r.strip() for r in p["requires_one_of"].split("|")]
                    if not any(r in new_bundle for r in reqs):
                        del new_bundle[pid]

        tags = []
        for pid in new_bundle.keys():
            prod_info = self.loader.get_product(pid)
            pname = prod_info.get("product_name", pid) if prod_info else pid
            tags.append({
                "product_id": pid,
                "name": pname,
                "tag": get_explainability_tag(pid, pname)
            })

        quote = self.calculate_quotation(new_bundle)
        return {
            "bundle": new_bundle,
            "tags": tags,
            "quotation": quote,
            "removed_id": target_pid
        }

    def request_human_assistance(self, reason: str, profile: Dict[str, Any], phone: Optional[str] = None) -> Dict[str, Any]:
        """Schedules a partner / executive callback for enterprise assistance."""
        return {
            "status": "SCHEDULED",
            "reason": reason,
            "contact_phone": phone or profile.get("phone") or "+91 95181 06076",
            "message": "Thanks for your time! An Airtel Business executive will reach out to you shortly on this number to assist you further. 🙏"
        }

