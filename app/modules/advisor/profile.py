"""
Customer Profile Module for Project Udyam Digital.
Handles profile schema, non-destructive merging, missing-field tracking,
and strict city-to-pincode and pincode-to-city synchronization.
"""

from typing import Dict, Any, List, Optional, Tuple

# Authoritative benchmark pincodes for Indian commercial hubs & cities
CITY_BENCHMARK_PINCODES: Dict[str, str] = {
    "Delhi": "110001",
    "Delhi NCR": "110001",
    "New Delhi": "110001",
    "Mumbai": "400001",
    "Bangalore": "560001",
    "Bengaluru": "560001",
    "Chennai": "600001",
    "Hyderabad": "500001",
    "Pune": "411001",
    "Kolkata": "700001",
    "Ahmedabad": "380001",
    "Noida": "201301",
    "Gurgaon": "122001",
    "Gurugram": "122001",
    "Indore": "452001",
    "Bhopal": "462001",
    "Jaipur": "302001",
    "Ludhiana": "141001",
    "Kochi": "682001",
    "Nagpur": "440001",
    "Visakhapatnam": "530001",
    "Patna": "800001",
    "Surat": "395001",
    "Lucknow": "226001",
    "Chandigarh": "160001",
    "Rohtak": "124001",
    "Faridabad": "121001",
    "Ghaziabad": "201001",
    "Kanpur": "208001",
    "Varanasi": "221001",
    "Agra": "282001",
    "Amritsar": "143001",
    "Dehradun": "248001",
    "Mysore": "570001",
    "Coimbatore": "641001",
    "Vadodara": "390001",
    "Rajkot": "360001",
    "Meerut": "250001",
    "Jalandhar": "144001",
    "Raipur": "492001",
    "Jabalpur": "482001",
    "Gwalior": "474001",
    "Nashik": "422001",
    "Aurangabad": "431001",
    "Madurai": "625001",
    "Mangalore": "575001",
    "Thiruvananthapuram": "695001",
    "Kozhikode": "673001"
}

# Pincode prefix map: (City, Tier)
PINCODE_PREFIX_MAP: Dict[str, Tuple[str, int]] = {
    "110": ("Delhi", 1),
    "121": ("Faridabad", 2),
    "122": ("Gurgaon", 1),
    "124": ("Rohtak", 3),
    "141": ("Ludhiana", 2),
    "143": ("Amritsar", 2),
    "144": ("Jalandhar", 2),
    "160": ("Chandigarh", 2),
    "2010": ("Ghaziabad", 2),
    "2013": ("Noida", 1),
    "208": ("Kanpur", 2),
    "221": ("Varanasi", 2),
    "226": ("Lucknow", 2),
    "248": ("Dehradun", 2),
    "250": ("Meerut", 2),
    "282": ("Agra", 2),
    "302": ("Jaipur", 2),
    "380": ("Ahmedabad", 1),
    "390": ("Vadodara", 2),
    "395": ("Surat", 2),
    "400": ("Mumbai", 1),
    "411": ("Pune", 1),
    "422": ("Nashik", 2),
    "431": ("Aurangabad", 2),
    "440": ("Nagpur", 2),
    "452": ("Indore", 2),
    "462": ("Bhopal", 2),
    "474": ("Gwalior", 2),
    "482": ("Jabalpur", 2),
    "492": ("Raipur", 2),
    "500": ("Hyderabad", 1),
    "530": ("Visakhapatnam", 2),
    "560": ("Bengaluru", 1),
    "570": ("Mysore", 2),
    "575": ("Mangalore", 2),
    "600": ("Chennai", 1),
    "625": ("Madurai", 2),
    "641": ("Coimbatore", 2),
    "673": ("Kozhikode", 2),
    "682": ("Kochi", 2),
    "695": ("Thiruvananthapuram", 2),
    "700": ("Kolkata", 1),
    "800": ("Patna", 2),
}

CITY_TIER_MAP: Dict[str, int] = {
    "delhi": 1, "new delhi": 1, "delhi ncr": 1, "mumbai": 1, "bangalore": 1, "bengaluru": 1,
    "chennai": 1, "hyderabad": 1, "pune": 1, "kolkata": 1, "ahmedabad": 1, "noida": 1, "gurgaon": 1, "gurugram": 1,
    "indore": 2, "bhopal": 2, "jaipur": 2, "ludhiana": 2, "kochi": 2, "nagpur": 2, "visakhapatnam": 2,
    "patna": 2, "surat": 2, "lucknow": 2, "chandigarh": 2, "faridabad": 2, "ghaziabad": 2, "kanpur": 2,
    "varanasi": 2, "agra": 2, "amritsar": 2, "dehradun": 2, "mysore": 2, "coimbatore": 2, "vadodara": 2,
    "rajkot": 2, "meerut": 2, "jalandhar": 2, "raipur": 2, "jabalpur": 2, "gwalior": 2, "nashik": 2,
    "aurangabad": 2, "madurai": 2, "mangalore": 2, "thiruvananthapuram": 2, "kozhikode": 2,
    "rohtak": 3
}

def normalize_city(city_raw: Optional[str]) -> Optional[str]:
    """Finds canonical casing for a city name."""
    if not city_raw:
        return None
    c_lower = city_raw.strip().lower()
    for canonical in CITY_BENCHMARK_PINCODES:
        if canonical.lower() == c_lower:
            return canonical
    # Title-case fallback
    return city_raw.strip().title()

def infer_location_from_pincode(pincode: str) -> Tuple[Optional[str], int]:
    """Infers city and city tier from a 6-digit postal code."""
    clean_pin = str(pincode).strip()
    # Check 4-digit prefixes first, then 3-digit
    for prefix in sorted(PINCODE_PREFIX_MAP.keys(), key=len, reverse=True):
        if clean_pin.startswith(prefix):
            city, tier = PINCODE_PREFIX_MAP[prefix]
            return city, tier
    # Default fallback: Tier 2 if unknown prefix
    return None, 2

def infer_tier_from_city(city_name: str) -> int:
    """Returns city tier (1, 2, or 3) for a given city name."""
    c_lower = city_name.strip().lower()
    return CITY_TIER_MAP.get(c_lower, 2)

def sync_location(profile: Dict[str, Any], city: Optional[str] = None, pincode: Optional[str] = None) -> Dict[str, Any]:
    """
    Synchronizes city, pincode, and city_tier.
    - If 6-digit pincode is supplied: derives city and tier.
    - If city is supplied: derives benchmark pincode and tier.
    - If neither is supplied: preserves existing profile fields without guessing.
    """
    prof = dict(profile)
    effective_pin = pincode or prof.get("pincode")
    effective_city = city or prof.get("city")

    if effective_pin and len(str(effective_pin).strip()) == 6 and str(effective_pin).strip().isdigit():
        clean_pin = str(effective_pin).strip()
        prof["pincode"] = clean_pin
        inferred_city, inferred_tier = infer_location_from_pincode(clean_pin)
        if inferred_city and (not effective_city or effective_city.lower() != inferred_city.lower()):
            prof["city"] = inferred_city
            prof["city_tier"] = inferred_tier
        elif effective_city:
            prof["city"] = normalize_city(effective_city)
            prof["city_tier"] = infer_tier_from_city(effective_city)
        else:
            prof["city_tier"] = inferred_tier
    elif effective_city:
        norm_city = normalize_city(effective_city)
        prof["city"] = norm_city
        prof["city_tier"] = infer_tier_from_city(norm_city)
        if not prof.get("pincode"):
            # Set benchmark pincode
            for c_name, pin in CITY_BENCHMARK_PINCODES.items():
                if c_name.lower() == norm_city.lower():
                    prof["pincode"] = pin
                    break

    return prof

def merge_profiles(existing: Optional[Dict[str, Any]], updates: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Non-destructive merge of profile updates into existing profile.
    Maintains clean typing and runs location synchronization.
    """
    merged = dict(existing or {})
    if not updates:
        return merged

    for key, val in updates.items():
        if val is None or val == "":
            continue
        if key in ["employee_count", "num_sites"]:
            try:
                val_int = int(val)
                if val_int > 0:
                    merged[key] = val_int
            except (ValueError, TypeError):
                pass
        elif key == "has_gstin":
            merged["has_gstin"] = bool(val)
        elif key == "downsell_level":
            try:
                merged["downsell_level"] = int(val)
            except (ValueError, TypeError):
                pass
        else:
            merged[key] = val

    # Non-GST safe mode handling
    if merged.get("safe_mode") or merged.get("safeModeNonGst"):
        merged["has_gstin"] = False

    # Synchronize location if city or pincode present
    if "city" in updates or "pincode" in updates or "city" in merged or "pincode" in merged:
        merged = sync_location(merged, city=updates.get("city"), pincode=updates.get("pincode"))

    return merged

def get_missing_mandatory_fields(profile: Dict[str, Any]) -> List[str]:
    """
    Tracks which mandatory discovery fields are missing before a compliant
    telecom recommendation can be finalized:
    1. employee_count (scale of operation)
    2. has_gstin (statutory eligibility)
    """
    missing = []
    if profile.get("employee_count") is None:
        missing.append("employee_count")
    if profile.get("has_gstin") is None:
        missing.append("has_gstin")
    return missing

def is_ready_for_recommendation(profile: Dict[str, Any]) -> bool:
    """
    Determines if sufficient consultative discovery has been gathered
    to produce a tailored product bundle. Scale (employee_count or site_headcounts)
    is the critical mandatory dimension, or resolved rural AirFiber feasibility.
    """
    if profile.get("rural_location") and profile.get("taar_present") is not None:
        return True
    has_scale = (profile.get("employee_count") is not None) or bool(profile.get("site_headcounts"))
    return has_scale
