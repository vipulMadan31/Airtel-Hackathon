"""
Output Validation and Statutory Guardrails for AI Advisor.
Ensures that all LLM outputs comply with 5-dimensional feasibility rules,
statutory requirements, valid dependencies, and authoritative pricing calculations.
"""

from typing import Dict, Any, List, Optional
from app.data_loader import DataLoader
from app.modules.catalog.engine import CatalogEngine
from app.modules.pricing.calculator import PricingCalculator
from app.modules.advisor.tools import get_explainability_tag
from app.modules.advisor.profile import infer_tier_from_city

class ResponseGuard:
    """
    Enforces server-side statutory and business constraints on all advisor responses.
    Guarantees zero price fabrication and zero illegal bundle combinations.
    """
    def __init__(self):
        self.loader = DataLoader.get_instance()
        self.catalog_engine = CatalogEngine()
        self.pricing_calculator = PricingCalculator()

    def validate_and_guard(
        self,
        raw_response: Dict[str, Any],
        profile: Dict[str, Any],
        language: str = "en"
    ) -> Dict[str, Any]:
        guarded = dict(raw_response)
        intent = guarded.get("intent", "recommendation")
        message = guarded.get("message", "")
        raw_bundle = guarded.get("recommended_bundle") or {}
        raw_tags = guarded.get("explainability_tags") or []
        ai_engine = guarded.get("ai_engine", "Airtel Business AI")

        # 1. For clarification or inquiry intents, never mutate cart / bundle
        if intent in ["clarification", "inquiry", "greeting"]:
            return {
                "intent": intent,
                "message": message,
                "profile": profile,
                "recommended_bundle": None,
                "explainability_tags": [],
                "ai_engine": ai_engine
            }

        # 2. Extract profile parameters
        city = profile.get("city")
        city_tier = int(profile.get("city_tier") or (infer_tier_from_city(city) if city else 2))
        emp_count = int(profile.get("employee_count") or 3)
        num_sites = int(profile.get("num_sites") or 1)
        has_gstin = profile.get("has_gstin") is not False

        # 3. Filter valid products and evaluate statutory eligibility
        validated_bundle: Dict[str, int] = {}
        for pid, qty in raw_bundle.items():
            prod = self.loader.get_product(pid)
            if not prod:
                continue

            try:
                qty_int = max(1, int(qty))
            except (ValueError, TypeError):
                qty_int = 1

            eligible, reason = self.catalog_engine.evaluate_product_eligibility(
                prod, city_tier, emp_count, num_sites, has_gstin
            )

            if eligible:
                validated_bundle[pid] = qty_int
            elif pid == "P03" and city_tier > 1:
                # Downgrade 1G to 300M in non-Tier-1 cities
                validated_bundle["P02"] = max(1, qty_int)

        # 4. Guarantee base connectivity
        base_pids = {"P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08"}
        has_base = any(pid in validated_bundle for pid in base_pids)
        if not has_base:
            biz = (profile.get("business_type") or "").lower()
            if city_tier == 1 and ("startup" in biz or "tech" in biz) and emp_count >= 20:
                validated_bundle["P03"] = num_sites
            elif "clinic" in biz or "dental" in biz or "office" in biz or "ca" in biz:
                validated_bundle["P02"] = num_sites
            elif profile.get("rural_location") and profile.get("taar_present") is False:
                validated_bundle["P04"] = num_sites
            else:
                validated_bundle["P01"] = num_sites

        # 5. Validate bundle dependencies
        is_valid_dep, dep_errors = self.catalog_engine.validate_bundle_dependencies(list(validated_bundle.keys()))
        if not is_valid_dep:
            for pid in list(validated_bundle.keys()):
                p = self.loader.get_product(pid)
                if p and p.get("requires_one_of"):
                    reqs = [r.strip() for r in p["requires_one_of"].split("|")]
                    if not any(r in validated_bundle for r in reqs):
                        del validated_bundle[pid]

        # 6. Reconcile Explainability Tags
        validated_tags: List[Dict[str, str]] = []
        tagged_pids = set()
        for tag in raw_tags:
            pid = tag.get("product_id")
            if pid in validated_bundle and pid not in tagged_pids:
                validated_tags.append(tag)
                tagged_pids.add(pid)

        # Backfill tags for any untagged products
        for pid in validated_bundle.keys():
            if pid not in tagged_pids:
                prod_info = self.loader.get_product(pid)
                pname = prod_info.get("product_name", pid) if prod_info else pid
                validated_tags.append({
                    "product_id": pid,
                    "name": pname,
                    "tag": get_explainability_tag(pid, pname, profile.get("business_type"))
                })

        # 7. Authoritative Pricing Calculation
        quotation = self.pricing_calculator.calculate_quote(
            validated_bundle, apply_digital_discount=True, waive_setup_fee=True
        )

        return {
            "intent": intent,
            "message": message,
            "profile": profile,
            "recommended_bundle": validated_bundle,
            "explainability_tags": validated_tags,
            "quotation": quotation,
            "ai_engine": ai_engine
        }
