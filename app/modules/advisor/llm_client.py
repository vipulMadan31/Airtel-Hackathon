"""
Gemini Integration and Tool-Calling Client for AI Advisor.
Orchestrates natural language conversations with Gemini while keeping
all business calculations and statutory decisions server-side and deterministic.
"""

import json
import requests
from typing import Dict, Any, List, Optional
from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.modules.advisor.prompts import GEMINI_SYSTEM_INSTRUCTION, GEMINI_TOOLS_DECLARATIONS
from app.modules.advisor.tools import AdvisorTools
from app.modules.advisor.profile import merge_profiles

class GeminiAdvisorClient:
    """
    Communicates with Gemini models via REST API with function-calling capabilities.
    Executes backend tools locally and gracefully handles errors and fallbacks.
    """
    def __init__(self, tools: Optional[AdvisorTools] = None):
        self.api_key = GEMINI_API_KEY
        self.model = GEMINI_MODEL or "gemini-2.5-flash"
        self.tools = tools or AdvisorTools()
        self.candidate_models = [self.model, "gemini-2.5-flash", "gemini-3.1-flash-lite", "gemini-3-flash-preview"]

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def execute_tool_call(self, func_name: str, args: Dict[str, Any], current_profile: Dict[str, Any], current_bundle: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """Executes the appropriate backend tool locally."""
        if func_name == "update_profile":
            updated_profile = merge_profiles(current_profile, args)
            return {"status": "success", "profile": updated_profile}

        elif func_name == "check_network_feasibility":
            pincode = args.get("pincode", "")
            city = args.get("city")
            return self.tools.check_network_feasibility(pincode, city)

        elif func_name == "get_catalogue":
            category = args.get("category")
            return {"products": self.tools.get_catalogue(category)}

        elif func_name == "check_product_eligibility":
            pid = args.get("product_id", "")
            return self.tools.check_product_eligibility(pid, current_profile)

        elif func_name == "generate_bundle":
            prof = merge_profiles(current_profile, args)
            result = self.tools.generate_bundle(prof)
            return result

        elif func_name == "progressive_downsell":
            step = int(args.get("step") or (current_profile.get("downsell_level", 0) + 1))
            bundle = current_bundle or current_profile.get("current_bundle") or {"P01": 1}
            return self.tools.progressive_downsell(bundle, step)

        elif func_name == "remove_addon":
            pid = args.get("product_id", "")
            bundle = current_bundle or current_profile.get("current_bundle") or {}
            return self.tools.remove_addon(bundle, pid)

        elif func_name == "request_human_assistance":
            reason = args.get("reason", "Customer requested callback")
            return self.tools.request_human_assistance(reason, current_profile)

        return {"error": f"Unknown tool: {func_name}"}

    def chat_with_gemini(
        self,
        user_message: str,
        current_profile: Dict[str, Any],
        language: str = "en",
        history: Optional[List[Dict[str, str]]] = None,
        active_bundle: Optional[Dict[str, int]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Sends conversation to Gemini with tool definitions and structured JSON schema.
        Returns parsed, validated response dict, or None if Gemini is unavailable.
        """
        if not self.is_configured:
            return None

        profile_context = f"""
CURRENT PROFILE STATE:
- City: {current_profile.get('city') or 'UNKNOWN'}
- City Tier: {current_profile.get('city_tier') or 'UNKNOWN'}
- Pincode: {current_profile.get('pincode') or 'UNKNOWN'}
- Business Type: {current_profile.get('business_type') or 'UNKNOWN'}
- Employees/Devices: {current_profile.get('employee_count') or 'UNKNOWN'}
- Sites: {current_profile.get('num_sites', 1)}
- GST Registered: {current_profile.get('has_gstin') if current_profile.get('has_gstin') is not None else 'UNKNOWN'}
- Rural Location: {current_profile.get('rural_location') if current_profile.get('rural_location') is not None else 'UNKNOWN'}
- Language: {'Marathi' if language == 'mr' else ('Hindi' if language == 'hi' else 'English')}
- Active Bundle: {active_bundle or 'None'}

MANDATORY DISCOVERY POLICY:
1. MANDATORY LOCATION & TIER DISCOVERY:
   Location (City or 6-digit Pincode) is strictly REQUIRED to determine City Tier (Tier 1 Metro, Tier 2, or Tier 3) and check network feasibility.
   Whenever asking clarifying questions, you MUST ask for:
   1) What type of business do you run, and in which CITY or 6-DIGIT PINCODE is it located?
   2) Do you have an active registered GST (GSTIN) for your business, or do you operate under sole-proprietorship (Non-GST / Udyam mode)?
   3) Approximately how many employees, billing devices, or customer connections will be using the network?

2. IF LOCATION IS UNKNOWN:
   If City / Pincode is NOT yet known (e.g. user says "i have a kirana store, i dont have a gst registration, i have 3 employees"):
   DO NOT OUTPUT A BUNDLE YET!
   Set intent="clarification", recommended_bundle=null!
   Acknowledge the known business type and staff count warmly, and ask:
   "Which city or 6-digit pincode is your business located in? This allows us to determine your city tier, confirm fiber/AirFiber feasibility, and calculate your exact quotation."

3. SCALE / HEADCOUNT DISCOVERY:
   If scale/employee count is missing, set intent="clarification", recommended_bundle=null.

4. FULL RECOMMENDATION:
   ONLY when Location (City or Pincode) AND Scale (Employees/devices) are known, set intent="recommendation" and output the tailored bundle!

5. ADD-ON REMOVAL:
   If user asks to remove an add-on (e.g. "remove endpoint security", "remove soundbox", "remove backup"):
   Set intent="recommendation", action="remove_addon", removed_product_id="<Product ID, e.g. P20 or P19>".
   Remove that item from recommended_bundle and acknowledge the removal politely.

6. NEVER assume employee scale or location!
7. If customer says "mehenga", "expensive", or "sasta plan", set intent="downsell_request" and trigger down-sell.
8. If customer asks about plans, speeds, or options in general, set intent="inquiry", recommended_bundle=null.
9. Multi-site (2+ locations): ask for scale at each location if missing, then bundle base lines for each location.
10. Village/Rural: if physical wire feasibility is unstated, ask clarification between Biz 5G AirFiber 100 (₹899) and Biz Fibre 100 (₹999).
"""

        # Build turn contents
        contents = []
        if history:
            for turn in history[-10:]:
                r = "user" if turn.get("role") == "user" else "model"
                txt = turn.get("text", "")
                if txt:
                    contents.append({"role": r, "parts": [{"text": txt}]})
        if not contents or contents[-1]["role"] != "user" or contents[-1]["parts"][0]["text"] != user_message:
            contents.append({"role": "user", "parts": [{"text": user_message}]})

        system_instruction = f"{GEMINI_SYSTEM_INSTRUCTION}\n\n{profile_context}\n\n" + """
RESPONSE FORMAT:
Return a JSON object matching this schema:
{
  "intent": "clarification" | "recommendation" | "downsell_request" | "inquiry" | "escalation",
  "action": "remove_addon" | null,
  "removed_product_id": string | null,
  "message": "Polite conversational reply in requested language",
  "profile": {
    "business_type": string | null,
    "employee_count": integer | null,
    "num_sites": integer,
    "city": string | null,
    "pincode": string | null,
    "has_gstin": boolean | null,
    "rural_location": boolean | null
  },
  "recommended_bundle": { "<product_id>": <quantity> } | null,
  "explainability_tags": [
    { "product_id": "P01", "name": "Biz Fibre 100", "tag": "Reason why picked" }
  ]
}
"""

        payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2
            }
        }

        for model_name in self.candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            try:
                resp = requests.post(url, json=payload, timeout=9)
                if resp.status_code == 200:
                    raw_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    data = json.loads(raw_text)
                    data["ai_engine"] = f"Gemini ({model_name})"
                    return data
            except Exception:
                continue

        return None
