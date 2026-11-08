"""
Concise System Prompts, Tool Definitions, and Formatting Guidelines for Gemini.
Ensures Gemini understands customer dialogue and drives deterministic backend tools.
"""

from typing import List, Dict, Any

GEMINI_SYSTEM_INSTRUCTION = """
You are the AI Business Advisor for Project Udyam Digital (Airtel Business Enterprise self-serve portal).
Your mission is to understand Indian MSMEs (Kirana, Dental Clinics, Restaurants, Offices, Startups)
and consultatively recommend compliant, tailored Airtel Business telecom & digital SaaS bundles.

CORE PRINCIPLES:
1. DETERMINISTIC BACKEND CONTROL:
   All product prices, statutory eligibility (GST, City Tier, Headcount), network feasibility,
   and bundle generation are handled exclusively by backend tools. NEVER invent prices, discounts,
   or product IDs.
2. NO ASSUMPTIONS:
   Never assume customer location, employee count, or GST registration without explicit mention.
   If information is missing, ask for it warmly in the customer's language.
3. CONVERSATIONAL CONTINUITY:
   Remember facts stated across earlier turns. Never re-ask for details the customer already provided.
4. BILINGUAL FLUENCY:
   Respond fluently in the customer's language (English or Hindi/Hinglish).
"""

GEMINI_TOOLS_DECLARATIONS = [
    {
        "name": "update_profile",
        "description": "Updates customer business profile with newly stated facts (city, pincode, business_type, employee_count, num_sites, has_gstin, rural).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "business_type": {"type": "STRING", "description": "Type of business (e.g. retail, clinic, restaurant, office, startup)"},
                "city": {"type": "STRING", "description": "City name if stated"},
                "pincode": {"type": "STRING", "description": "6-digit postal pincode if stated"},
                "employee_count": {"type": "INTEGER", "description": "Number of employees, staff, or connected devices"},
                "num_sites": {"type": "INTEGER", "description": "Number of shops, branches, or locations"},
                "has_gstin": {"type": "BOOLEAN", "description": "True if customer confirmed active GST registration, False if Non-GST/sole proprietor"},
                "rural_location": {"type": "BOOLEAN", "description": "True if business is in village/rural area"}
            }
        }
    },
    {
        "name": "check_network_feasibility",
        "description": "Checks network coverage and infrastructure feasibility (Optical Wireline Fibre FTTH vs 5G AirFiber) for a given pincode and city.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "pincode": {"type": "STRING", "description": "6-digit postal code"},
                "city": {"type": "STRING", "description": "City name"}
            },
            "required": ["pincode"]
        }
    },
    {
        "name": "get_catalogue",
        "description": "Retrieves official Airtel Business products and current pricing.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {"type": "STRING", "description": "Optional category filter: Connectivity, Security, Cloud, Voice, IoT"}
            }
        }
    },
    {
        "name": "generate_bundle",
        "description": "Generates a fully validated, tailored product bundle with explainability tags and official quotation based on customer profile.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "business_type": {"type": "STRING", "description": "Business persona"},
                "employee_count": {"type": "INTEGER", "description": "Staff/device scale"},
                "num_sites": {"type": "INTEGER", "description": "Number of locations"},
                "has_gstin": {"type": "BOOLEAN", "description": "GST status"},
                "city": {"type": "STRING", "description": "City name"},
                "pincode": {"type": "STRING", "description": "Pincode"}
            }
        }
    },
    {
        "name": "progressive_downsell",
        "description": "Executes down-selling when customer indicates current recommendation is too expensive or exceeds budget.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "step": {"type": "INTEGER", "description": "Downsell step level (1=unbundle add-ons, 2=floor price, 3=mobile SIM)"}
            }
        }
    },
    {
        "name": "remove_addon",
        "description": "Removes a specific optional add-on (e.g. soundbox, cloud backup, cctv) from the active bundle.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "product_id": {"type": "STRING", "description": "Product ID (e.g. P19, P17, P23) or product keyword"}
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "request_human_assistance",
        "description": "Schedules an Airtel Business executive callback for partner or enterprise support.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "reason": {"type": "STRING", "description": "Customer inquiry topic or escalation reason"}
            },
            "required": ["reason"]
        }
    }
]
