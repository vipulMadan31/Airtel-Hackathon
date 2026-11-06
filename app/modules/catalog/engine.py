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
        has_gstin: bool
    ) -> (bool, str):
        """
        Evaluates whether a product is eligible for a given business profile.
        Returns (is_eligible, reason_if_ineligible).
        """
        # 1. City Tier check
        allowed_tiers = [t.strip() for t in str(product["available_city_tiers"]).split(";")]
        if str(city_tier) not in allowed_tiers:
            return False, f"Available only in Tier-{','.join(allowed_tiers)} cities"

        # 2. Minimum Employees check
        if employee_count < int(product["min_employees"]):
            return False, f"Requires at least {product['min_employees']} employees"

        # 3. Minimum Sites check
        if num_sites < int(product["min_sites"]):
            return False, f"Requires at least {product['min_sites']} business locations"

        # 4. GSTIN requirement check
        if str(product["requires_gstin"]).upper() == "Y" and not has_gstin:
            return False, "Requires active GSTIN verification"

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

