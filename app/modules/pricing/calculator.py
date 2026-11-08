from typing import List, Dict, Any, Optional
from app.data_loader import DataLoader
from app.modules.catalog.engine import CatalogEngine
from app.config import (
    BOOKING_TOKEN_AMOUNT_INR,
    SETUP_FEE_WAIVER_PROMO,
    DIGITAL_DISCOUNT_ENABLED,
    VALID_DISCOUNT_CODES
)

class PricingCalculator:
    """
    Authoritative Pricing and Commercial Rules Engine.
    Treats product_catalogue.csv as the single source of truth for pricing,
    contract terms, setup fees, and commercial eligibility.
    """
    def __init__(self):
        self.loader = DataLoader.get_instance()
        self.catalog_engine = CatalogEngine()

    def validate_and_price_order(
        self,
        product_quantities: Dict[str, int],
        city_tier: int = 1,
        city: Optional[str] = None,
        pincode: Optional[str] = None,
        employee_count: int = 1,
        num_sites: int = 1,
        has_gstin: Optional[bool] = None,
        contract_months: Optional[int] = None,
        apply_digital_discount: bool = True,
        waive_setup_fee: bool = True,
        discount_code: Optional[str] = None,
        customer_submitted_monthly_total: Optional[float] = None,
        customer_submitted_setup_fee: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Central server-side order validation and quotation engine:
        - Accepts product IDs, quantities, customer details, location, and contract terms.
        - Validates every product against the catalogue.
        - Checks all product dependencies and eligibility requirements.
        - Calculates recurring charges, setup fees, applicable taxes, and authorised discounts.
        - Rejects invalid or manipulated requests with clear, descriptive error messages.
        """
        # 1. Non-empty bundle validation
        if not product_quantities or not any(int(q or 0) > 0 for q in product_quantities.values()):
            raise ValueError("Empty bundle: Order must contain at least one valid product.")

        # Infer city tier if city or pincode is supplied
        if city:
            from app.modules.advisor.profile import infer_tier_from_city
            inferred = infer_tier_from_city(city)
            if inferred:
                city_tier = inferred
        elif pincode:
            from app.modules.advisor.profile import infer_location_from_pincode
            _, inferred_tier = infer_location_from_pincode(str(pincode))
            if inferred_tier:
                city_tier = inferred_tier

        # 2. Validate product SKUs and quantities
        selected_products = []
        for pid, qty in product_quantities.items():
            clean_pid = str(pid).strip().upper()
            prod = self.loader.get_product(clean_pid)
            if not prod:
                raise ValueError(f"Invalid product SKU '{clean_pid}'. Product does not exist in the official Airtel product catalogue.")

            try:
                qty_int = int(qty)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid quantity '{qty}' for product {clean_pid}. Quantity must be a valid integer.")

            if qty_int <= 0:
                raise ValueError(f"Invalid quantity {qty_int} for product {clean_pid}. Quantity must be at least 1.")

            selected_products.append((prod, qty_int))

        # 3. Base connectivity requirement
        base_pids = {"P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08"}
        selected_pids = {p["product_id"] for p, _ in selected_products}
        has_base = any(pid in base_pids for pid in selected_pids)
        if not has_base:
            raise ValueError("Invalid bundle: Order must include at least one base connectivity service (e.g. Biz Fibre, 5G AirFiber, or Business Postpaid).")

        # 4. Product dependencies check (requires_one_of)
        is_dep_valid, dep_errors = self.catalog_engine.validate_bundle_dependencies(list(selected_pids))
        if not is_dep_valid:
            raise ValueError(f"Product dependency violation: {'; '.join(dep_errors)}")

        # 5. Contract duration validation
        if contract_months is not None:
            effective_contract = int(contract_months)
        else:
            effective_contract = max([int(p.get("min_contract_months", 1)) for p, _ in selected_products] or [1])

        for prod, qty in selected_products:
            min_c = int(prod.get("min_contract_months", 1))
            if effective_contract < min_c:
                raise ValueError(
                    f"Contract duration violation: Product '{prod['product_name']}' ({prod['product_id']}) requires a minimum contract duration of {min_c} months (requested: {effective_contract} months)."
                )

        # 6. Profile & Statutory Eligibility Checks (City Tier, GSTIN, Scale, Quantities)
        for prod, qty in selected_products:
            pid = prod["product_id"]
            eligible, reason = self.catalog_engine.evaluate_product_eligibility(
                product=prod,
                city_tier=city_tier,
                employee_count=employee_count,
                num_sites=num_sites,
                has_gstin=has_gstin,
                contract_months=effective_contract,
                quantity=qty
            )
            if not eligible:
                raise ValueError(f"Ineligible product '{prod['product_name']}' ({pid}): {reason}")

        # 7. Authorised Discount & Fee Waiver Rules
        if discount_code:
            clean_code = str(discount_code).strip().upper()
            if clean_code not in VALID_DISCOUNT_CODES:
                raise ValueError(f"Unauthorized discount code '{discount_code}'. Valid promotional discount code required.")
            apply_digital_discount = True
            waive_setup_fee = True
        else:
            if apply_digital_discount and not DIGITAL_DISCOUNT_ENABLED:
                raise ValueError("Unauthorized discount: Promotional digital discount is currently disabled by commercial policy.")
            if waive_setup_fee and not SETUP_FEE_WAIVER_PROMO:
                raise ValueError("Unauthorized fee waiver: Setup fee waiver is not authorized without valid promotion.")

        # 8. Recalculate Authoritative Itemized Charges
        items_breakdown = []
        monthly_base_subtotal = 0.0
        total_setup_fees = 0.0
        total_discount_inr = 0.0
        total_waived_setup_inr = 0.0
        typical_install_days = 3

        for prod, qty in selected_products:
            pid = prod["product_id"]
            floor_p = float(prod["price_min_inr_per_month"])
            list_p = float(prod["price_max_inr_per_month"])
            cat_setup = float(prod.get("one_time_setup_inr", 0.0))

            if apply_digital_discount:
                unit_p = floor_p
                unit_disc = list_p - floor_p
            else:
                unit_p = list_p
                unit_disc = 0.0

            if waive_setup_fee:
                line_setup = 0.0
                line_waived_setup = cat_setup * qty
            else:
                line_setup = cat_setup * qty
                line_waived_setup = 0.0

            line_monthly = round(unit_p * qty, 2)
            line_discount = round(unit_disc * qty, 2)

            monthly_base_subtotal += line_monthly
            total_setup_fees += line_setup
            total_discount_inr += line_discount
            total_waived_setup_inr += line_waived_setup

            if int(prod.get("typical_install_days", 3)) > typical_install_days:
                typical_install_days = int(prod["typical_install_days"])

            items_breakdown.append({
                "product_id": pid,
                "product_name": prod["product_name"],
                "category": prod["category"],
                "quantity": qty,
                "unit": prod["unit"],
                "unit_price_inr": unit_p,
                "list_price_inr": list_p,
                "line_monthly_inr": line_monthly,
                "setup_fee_inr": line_setup,
                "min_contract_months": int(prod["min_contract_months"])
            })

        gst_18_percent = round(monthly_base_subtotal * 0.18, 2)
        total_monthly_commitment = round(monthly_base_subtotal + gst_18_percent, 2)
        booking_token = BOOKING_TOKEN_AMOUNT_INR
        total_due_today = booking_token if waive_setup_fee else round(total_setup_fees + total_monthly_commitment, 2)

        # 9. Client Price Tampering & Manipulation Guardrail
        if customer_submitted_monthly_total is not None:
            try:
                submitted_m = float(customer_submitted_monthly_total)
                if abs(submitted_m - total_monthly_commitment) > 0.50 and abs(submitted_m - monthly_base_subtotal) > 0.50:
                    raise ValueError(
                        f"Manipulated price detected: Client-submitted monthly total (₹{submitted_m:.2f}) does not match authoritative backend recalculation (₹{total_monthly_commitment:.2f} incl GST or ₹{monthly_base_subtotal:.2f} base)."
                    )
            except (TypeError, ValueError) as e:
                if "Manipulated price" in str(e):
                    raise

        if customer_submitted_setup_fee is not None:
            try:
                submitted_s = float(customer_submitted_setup_fee)
                if abs(submitted_s - total_setup_fees) > 0.50 and (not waive_setup_fee or abs(submitted_s - 0.0) > 0.50):
                    raise ValueError(
                        f"Manipulated setup fee detected: Client-submitted setup fee (₹{submitted_s:.2f}) does not match authoritative backend recalculation (₹{total_setup_fees:.2f})."
                    )
            except (TypeError, ValueError) as e:
                if "Manipulated setup fee" in str(e):
                    raise

        return {
            "is_valid": True,
            "dependency_errors": [],
            "items": items_breakdown,
            "monthly_subtotal_inr": round(monthly_base_subtotal, 2),
            "gst_18_inr": gst_18_percent,
            "total_monthly_inr": total_monthly_commitment,
            "one_time_setup_inr": round(total_setup_fees, 2),
            "booking_token_inr": booking_token,
            "total_due_today_inr": total_due_today,
            "contract_months": effective_contract,
            "authorized_discounts_monthly_inr": round(total_discount_inr, 2),
            "waived_setup_fees_inr": round(total_waived_setup_inr, 2),
            "typical_install_days": typical_install_days,
            "selected_products": [p["product_id"] for p, _ in selected_products],
            "product_quantities": {p["product_id"]: q for p, q in selected_products},
            "is_simulated": True,
            "mode": "DEMO_SIMULATED",
            "simulation_notice": "DEMO / SIMULATED QUOTE: Commercial quotation computed using prototype benchmark catalogue rates."
        }

    def calculate_quote(
        self,
        product_quantities: Dict[str, int],
        apply_digital_discount: bool = True,
        waive_setup_fee: bool = True,
        contract_months: Optional[int] = None,
        city_tier: int = 1,
        employee_count: int = 1,
        num_sites: int = 1,
        has_gstin: Optional[bool] = None,
        discount_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Wraps validate_and_price_order for storefront and advisor quote generation.
        Handles partial/draft bundles gracefully with is_valid status.
        """
        try:
            return self.validate_and_price_order(
                product_quantities=product_quantities,
                city_tier=city_tier,
                employee_count=employee_count,
                num_sites=num_sites,
                has_gstin=has_gstin,
                contract_months=contract_months,
                apply_digital_discount=apply_digital_discount,
                waive_setup_fee=waive_setup_fee,
                discount_code=discount_code
            )
        except ValueError as e:
            # For draft / exploratory quotes, return clear structured error
            return {
                "is_valid": False,
                "dependency_errors": [str(e)],
                "items": [],
                "monthly_subtotal_inr": 0.0,
                "gst_18_inr": 0.0,
                "total_monthly_inr": 0.0,
                "one_time_setup_inr": 0.0,
                "booking_token_inr": BOOKING_TOKEN_AMOUNT_INR,
                "total_due_today_inr": BOOKING_TOKEN_AMOUNT_INR,
                "contract_months": contract_months or 12,
                "authorized_discounts_monthly_inr": 0.0,
                "waived_setup_fees_inr": 0.0,
                "typical_install_days": 3,
                "selected_products": list(product_quantities.keys()),
                "error": str(e),
                "is_simulated": True,
                "mode": "DEMO_SIMULATED"
            }

    def execute_downsell_step(
        self,
        current_quantities: Dict[str, int],
        step: int
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
            for pid in list(new_quantities.keys()):
                prod = self.loader.get_product(pid)
                if prod and prod["category"] not in ["Connectivity"]:
                    del new_quantities[pid]
            explanation = "Removed optional cloud & security add-ons to reach the lowest essential price."

        elif step == 2:
            explanation = "Applied self-serve digital floor pricing and 100% setup fee waiver (saving up to ₹2,500)."

        elif step == 3:
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

# Expose a module-level instance and function for convenient access
pricing_calculator = PricingCalculator()

def validate_and_price_order(*args, **kwargs) -> Dict[str, Any]:
    return pricing_calculator.validate_and_price_order(*args, **kwargs)
