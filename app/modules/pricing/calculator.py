from typing import List, Dict, Any, Optional
from app.data_loader import DataLoader
from app.modules.catalog.engine import CatalogEngine

class PricingCalculator:
    def __init__(self):
        self.loader = DataLoader.get_instance()
        self.catalog_engine = CatalogEngine()

    def calculate_quote(
        self,
        product_quantities: Dict[str, int],  # e.g. {"P01": 1, "P07": 2}
        apply_digital_discount: bool = True,  # Floor price vs max price
        waive_setup_fee: bool = True,        # Digital checkout promotion
        contract_months: int = 12
    ) -> Dict[str, Any]:
        """
        Authoritative pricing function. Reconciles strictly against product_catalogue.csv.
        """
        items_breakdown = []
        monthly_base_subtotal = 0.0
        one_time_setup_total = 0.0
        typical_install_days = 3

        selected_ids = list(product_quantities.keys())
        is_valid, dep_errors = self.catalog_engine.validate_bundle_dependencies(selected_ids)

        for pid, qty in product_quantities.items():
            if qty <= 0:
                continue
            prod = self.loader.get_product(pid)
            if not prod:
                continue

            unit_price = float(prod["price_min_inr_per_month"]) if apply_digital_discount else float(prod["price_max_inr_per_month"])
            setup_fee = 0.0 if waive_setup_fee else float(prod["one_time_setup_inr"])

            line_monthly = unit_price * qty
            line_setup = setup_fee * qty

            monthly_base_subtotal += line_monthly
            one_time_setup_total += line_setup

            if int(prod.get("typical_install_days", 3)) > typical_install_days:
                typical_install_days = int(prod["typical_install_days"])

            items_breakdown.append({
                "product_id": pid,
                "product_name": prod["product_name"],
                "category": prod["category"],
                "quantity": qty,
                "unit_price_inr": unit_price,
                "line_monthly_inr": line_monthly,
                "setup_fee_inr": line_setup,
                "min_contract_months": int(prod["min_contract_months"])
            })

        gst_18_percent = round(monthly_base_subtotal * 0.18, 2)
        total_monthly_commitment = round(monthly_base_subtotal + gst_18_percent, 2)
        total_due_today = 499.0 if waive_setup_fee else (one_time_setup_total + total_monthly_commitment)

        return {
            "is_valid": is_valid,
            "dependency_errors": dep_errors,
            "items": items_breakdown,
            "monthly_subtotal_inr": round(monthly_base_subtotal, 2),
            "gst_18_inr": gst_18_percent,
            "total_monthly_inr": total_monthly_commitment,
            "one_time_setup_inr": round(one_time_setup_total, 2),
            "booking_token_inr": 499.0 if waive_setup_fee else 0.0,
            "total_due_today_inr": total_due_today,
            "contract_months": contract_months,
            "typical_install_days": typical_install_days,
            "digital_exclusive_savings_monthly": 0.0  # calculated if compared to max
        }

    def execute_downsell_step(
        self,
        current_quantities: Dict[str, int],
        step: int  # 1 to 4
    ) -> Dict[str, Any]:
        """
        Executes the 4-step controlled down-sell sequence from the specification:
        Step 1: Unbundle non-essential add-ons (keep only connectivity)
        Step 2: Apply floor price + 100% setup fee waiver
        Step 3: Down-tier base connectivity (P01 -> P07 Business SIM)
        Step 4: Consequence warning guardrail
        """
        new_quantities = dict(current_quantities)
        explanation = ""

        if step == 1:
            # Strip optional software & add-ons (keep only base broadband / SIM)
            for pid in list(new_quantities.keys()):
                prod = self.loader.get_product(pid)
                if prod and prod["category"] not in ["Connectivity"]:
                    del new_quantities[pid]
            explanation = "Removed optional cloud & security add-ons to reach the lowest essential price."

        elif step == 2:
            # Apply floor price & waive setup fee
            explanation = "Applied self-serve digital floor pricing and 100% setup fee waiver (saving up to ₹2,500)."

        elif step == 3:
            # Downgrade from fixed fibre (P01/P02) to Business SIM (P07)
            if "P01" in new_quantities:
                del new_quantities["P01"]
                new_quantities["P07"] = 1
            elif "P02" in new_quantities:
                del new_quantities["P02"]
                new_quantities["P07"] = 1
            explanation = "Downgraded base service to Business Mobile SIM (P07) at ₹299/month for ultra-low budget setup."

        elif step == 4:
            explanation = "Consequence Guardrail: Warning that mobile data caps can disrupt evening UPI billing and CCTV backup."

        quote = self.calculate_quote(new_quantities, apply_digital_discount=True, waive_setup_fee=True)
        quote["explanation"] = explanation
        quote["step_executed"] = step
        return quote

