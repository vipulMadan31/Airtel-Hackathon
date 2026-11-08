"""
Main AI Advisor Orchestration Service for Project Udyam Digital.
Coordinates NLU parsing, profile validation, Gemini tool orchestration,
deterministic fallback execution, and response guardrails.
"""

from typing import Dict, Any, List, Optional
from app.modules.advisor.profile import merge_profiles, get_missing_mandatory_fields, is_ready_for_recommendation
from app.modules.advisor.tools import AdvisorTools
from app.modules.advisor.nlu import NLUParser
from app.modules.advisor.session import SessionStore
from app.modules.advisor.llm_client import GeminiAdvisorClient
from app.modules.advisor.scripted import ScriptedAdvisor
from app.modules.advisor.response_guard import ResponseGuard

class AdvisorService:
    """
    Central orchestration service for conversational sales advisory.
    Ensures that customer intent is properly recognized while all business decisions,
    pricing, and statutory rules remain strictly backend-controlled.
    """
    def __init__(self):
        self.tools = AdvisorTools()
        self.nlu = NLUParser()
        self.session_store = SessionStore.get_instance()
        self.llm_client = GeminiAdvisorClient(tools=self.tools)
        self.scripted_advisor = ScriptedAdvisor(tools=self.tools)
        self.response_guard = ResponseGuard()

    def process_user_message(
        self,
        user_message: str,
        current_profile: Optional[Dict[str, Any]] = None,
        language: str = "en",
        history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None,
        owner_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Orchestrates full advisor cycle:
        1. Context / Session retrieval
        2. Multilingual NLU & entity extraction
        3. Non-destructive profile merge & location synchronization
        4. Intent routing & deterministic consultative discovery
        5. Gemini LLM tool-calling or deterministic fallback execution
        6. Server-side response guardrails and authoritative quote pricing
        """
        # 1. Session resolution
        session = None
        if session_id:
            session = self.session_store.get_or_create(session_id, owner_id)
            effective_profile = merge_profiles(session.profile, current_profile or {})
            effective_history = history if history is not None else session.history
            active_bundle = session.active_bundle
        else:
            effective_profile = dict(current_profile or {})
            effective_history = history or []
            active_bundle = effective_profile.get("current_bundle")

        # 2. Extract NLU signals
        detected_intent = self.nlu.detect_intent(user_message, current_bundle=active_bundle)
        extracted_entities = self.nlu.extract_entities(user_message)

        # 3. Non-destructive profile update & location sync
        merged_profile = merge_profiles(effective_profile, extracted_entities)

        # 4. Mandatory consultative discovery check
        # If employee scale or location is missing and query is not downsell, remove_addon, escalation, inquiry, or rural feasibility:
        # We must trigger progressive clarification!
        missing_fields = get_missing_mandatory_fields(merged_profile)
        is_rural_airfiber_resolved = bool(merged_profile.get("rural_location") and merged_profile.get("taar_present") is False)
        if ("employee_count" in missing_fields or "location" in missing_fields) and detected_intent not in ["downsell_request", "remove_addon", "escalation", "inquiry", "rural_feasibility"] and not is_rural_airfiber_resolved:
            if not is_ready_for_recommendation(merged_profile):
                detected_intent = "clarification"

        # 5. Process through Scripted or LLM
        response_data: Optional[Dict[str, Any]] = None

        # Check if we should use LLM or deterministic engine
        # Deterministic engine handles down-sell, remove add-on, rural wire discovery, multi-site headcounts, and clear-cut consultative turns reliably
        if detected_intent in ["downsell_request", "remove_addon", "greeting", "rural_feasibility"] or bool(merged_profile.get("site_headcounts")):
            response_data = self.scripted_advisor.process(
                user_message,
                merged_profile,
                language=language,
                detected_intent="recommendation" if merged_profile.get("site_headcounts") else detected_intent,
                active_bundle=active_bundle,
                entities=extracted_entities
            )
        elif detected_intent == "clarification":
            # For clarification, if LLM is enabled and configured, let Gemini answer warmly with context
            if self.llm_client.is_configured:
                response_data = self.llm_client.chat_with_gemini(
                    user_message,
                    merged_profile,
                    language=language,
                    history=effective_history,
                    active_bundle=active_bundle
                )
            if not response_data:
                response_data = self.scripted_advisor.process(
                    user_message,
                    merged_profile,
                    language=language,
                    detected_intent="clarification",
                    active_bundle=active_bundle,
                    entities=extracted_entities
                )
        else:
            # Recommendation or Inquiry: try Gemini first if configured
            if self.llm_client.is_configured:
                response_data = self.llm_client.chat_with_gemini(
                    user_message,
                    merged_profile,
                    language=language,
                    history=effective_history,
                    active_bundle=active_bundle
                )

            # Fallback if Gemini unavailable or failed
            if not response_data:
                response_data = self.scripted_advisor.process(
                    user_message,
                    merged_profile,
                    language=language,
                    detected_intent=detected_intent,
                    active_bundle=active_bundle,
                    entities=extracted_entities
                )

        # 6. For recommendations, enforce deterministic backend bundle and pricing authority
        if response_data and response_data.get("intent") == "recommendation":
            is_remove_addon = (detected_intent == "remove_addon" or response_data.get("action") == "remove_addon")
            is_downsell = (detected_intent == "downsell_request" or response_data.get("intent") == "downsell_request")

            if is_remove_addon:
                removed_id = response_data.get("removed_product_id")
                if removed_id:
                    removed_list = list(merged_profile.get("removed_addons", []))
                    if removed_id not in removed_list:
                        removed_list.append(removed_id)
                    merged_profile["removed_addons"] = removed_list
                if response_data.get("recommended_bundle"):
                    merged_profile["current_bundle"] = response_data["recommended_bundle"]
            elif not is_downsell:
                backend_res = self.tools.generate_bundle(merged_profile)
                response_data["recommended_bundle"] = backend_res["bundle"]
                response_data["explainability_tags"] = backend_res["tags"]
                response_data["quotation"] = backend_res["quotation"]
                merged_profile["current_bundle"] = backend_res["bundle"]

        # 7. Apply statutory guardrails & authoritative pricing engine
        guarded_result = self.response_guard.validate_and_guard(
            response_data,
            profile=merged_profile,
            language=language
        )

        # 8. Update session if present
        if session:
            session.profile = guarded_result.get("profile", merged_profile)
            if guarded_result.get("recommended_bundle"):
                session.active_bundle = guarded_result["recommended_bundle"]
            session.append_turn("user", user_message)
            session.append_turn("model", guarded_result.get("message", ""))

        return guarded_result
