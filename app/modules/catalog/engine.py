from typing import List, Dict, Any, Optional
from app.data_loader import DataLoader

class CatalogEngine:
    def __init__(self):
        self.loader = DataLoader.get_instance()

    def evaluate_product_eligibility(
        self,
        product: Dict[str, Any],
        city_tier: int,
        employee_count: int,
        num_sites: int,
        has_gstin: Optional[bool] = None,
        contract_months: Optional[int] = None,
        quantity: Optional[int] = None
    ) -> (bool, str):
        """
        Evaluates whether a product is eligible for a given business profile against catalogue truth.
        Returns (is_eligible, reason_if_ineligible).
        """
        # 1. City Tier check (single source of truth in product catalogue)
        allowed_tiers = [t.strip() for t in str(product["available_city_tiers"]).split(";")]
        tier_str = str(city_tier)
        if "2" in allowed_tiers and city_tier >= 2:
            pass  # Standard pan-India non-metro availability across Tier 2, Tier 3, and Tier 4 towns
        elif tier_str not in allowed_tiers:
            return False, f"Available only in Tier-{','.join(allowed_tiers)} cities (current location is Tier-{city_tier})"

        # 2. Minimum Employees check
        min_emp = int(product.get("min_employees", 1))
        if employee_count < min_emp:
            return False, f"Requires at least {min_emp} employees (profile has {employee_count})"

        # 3. Minimum Sites check (Catalogue truth: P10 requires 3 sites, ILL requires 1 site, etc.)
        min_sites_req = int(product.get("min_sites", 1))
        if num_sites < min_sites_req:
            return False, f"Requires at least {min_sites_req} business locations (profile has {num_sites})"

        # 4. GSTIN requirement check: An unknown GST status must never be treated as confirmed GST eligibility
        if str(product.get("requires_gstin", "N")).upper() == "Y":
            if has_gstin is not True:
                return False, "Requires active GSTIN verification (GSTIN not confirmed)"

        # 5. Minimum contract duration check
        if contract_months is not None:
            min_c = int(product.get("min_contract_months", 1))
            if contract_months < min_c:
                return False, f"Requires minimum contract duration of {min_c} months (selected: {contract_months} months)"

        # 6. Quantity restrictions
        if quantity is not None:
            if quantity <= 0:
                return False, f"Quantity must be a positive integer (got {quantity})"
            unit = str(product.get("unit", "")).lower().strip()
            if unit == "per site" and quantity > num_sites:
                return False, f"Quantity ({quantity}) cannot exceed total declared sites ({num_sites}) for site-level product"
            if unit == "per account" and quantity > 1:
                return False, f"Maximum 1 subscription allowed per account (requested {quantity})"

        return True, "Eligible"

    def validate_bundle_dependencies(self, selected_product_ids: List[str]) -> (bool, List[str]):
        """
        Ensures that any product requiring a base product has at least one of them present.
        Returns (is_valid, list_of_error_reasons).
        """
        errors = []
        selected_set = set(selected_product_ids)

        for pid in selected_product_ids:
            prod = self.loader.get_product(pid)
            if not prod:
                errors.append(f"Invalid product code: {pid}")
                continue

            req_one_of = str(prod["requires_one_of"]).strip()
            if req_one_of:
                required_options = [opt.strip() for opt in req_one_of.split("|")]
                if not any(req in selected_set for req in required_options):
                    errors.append(
                        f"{prod['product_name']} ({pid}) requires at least one base service from [{', '.join(required_options)}]"
                    )

        return (len(errors) == 0), errors

    def get_three_buckets(
        self,
        city_tier: int,
        employee_count: int,
        num_sites: int,
        has_gstin: bool,
        current_base_id: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Implements the 3-Bucket Catalog view:
        - Bucket A: Cheaper & Alternative Base Plans
        - Bucket B: Modular Eligible Add-ons
        - Bucket C: Ineligible / Locked Plans with exact lock reasons
        """
        all_products = self.loader.get_all_products()
        bucket_a = []
        bucket_b = []
        bucket_c = []

        for prod in all_products:
            eligible, reason = self.evaluate_product_eligibility(
                prod, city_tier, employee_count, num_sites, has_gstin
            )

            item = dict(prod)
            item["eligible"] = eligible
            item["ineligible_reason"] = reason

            if not eligible:
                bucket_c.append(item)
            else:
                # Is it a Base connectivity product?
                if prod["product_id"] in ["P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08"]:
                    bucket_a.append(item)
                else:
                    # Check dependency
                    req_one_of = str(prod["requires_one_of"]).strip()
                    if req_one_of and current_base_id:
                        req_options = [opt.strip() for opt in req_one_of.split("|")]
                        if current_base_id not in req_options:
                            item["eligible"] = False
                            item["ineligible_reason"] = f"Requires base broadband [{', '.join(req_options)}]"
                            bucket_c.append(item)
                            continue
                    bucket_b.append(item)

        return {
            "bucket_a_base_plans": bucket_a,
            "bucket_b_modular_addons": bucket_b,
            "bucket_c_locked_plans": bucket_c
        }

    def check_network_feasibility(self, pincode: str, city: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluates fiber wireline vs 5G AirFiber feasibility for an installation pincode.
        Addresses the 41 historical leads lost due to 'Site not feasible for fibre'.
        """
        pin = str(pincode).strip()
        UNFEASIBLE_FIBRE_PINCODES = {"452010", "530016", "411028", "110092", "400078", "560068"}

        is_fibre_feasible = not (pin in UNFEASIBLE_FIBRE_PINCODES or (len(pin) == 6 and pin.endswith("0")))

        if is_fibre_feasible:
            return {
                "pincode": pin,
                "city": city,
                "is_fibre_feasible": True,
                "technology": "Optical Wireline Fibre (FTTH)",
                "recommended_base_id": "P01",
                "recommended_product_name": "Biz Fibre 100",
                "typical_install_days": 5,
                "monthly_price_inr": 999,
                "message": "High-speed optical wireline fibre is verified and feasible at your address (5-day typical install).",
                "is_simulated": True,
                "mode": "DEMO_SIMULATED",
                "simulation_notice": "DEMO / SIMULATED: Network feasibility is estimated based on postal prefix heuristics for demonstration and does not constitute a physical survey commitment."
            }
        else:
            return {
                "pincode": pin,
                "city": city,
                "is_fibre_feasible": False,
                "airfiber_feasible": True,
                "technology": "Airtel 5G AirFiber (Fixed Wireless Access)",
                "recommended_base_id": "P04",
                "recommended_product_name": "Biz 5G AirFiber 100",
                "typical_install_days": 2,
                "monthly_price_inr": 899,
                "message": "Wireline optical digging is pending in your area. Seamlessly switched to Airtel Biz 5G AirFiber 100 (P04) — zero wires, instant 48-hour setup!",
                "is_simulated": True,
                "mode": "DEMO_SIMULATED",
                "simulation_notice": "DEMO / SIMULATED: Network feasibility is estimated based on postal prefix heuristics for demonstration and does not constitute a physical survey commitment."
            }

