"""
Backward-Compatible Facade for Project Udyam Digital AI Advisor.
Delegates all conversational NLU, discovery, planning, tool execution,
and statutory response guarding to the modular AdvisorService architecture.
"""

from typing import Dict, Any, List, Optional
from app.modules.advisor.profile import CITY_BENCHMARK_PINCODES, PINCODE_PREFIX_MAP
from app.modules.advisor.service import AdvisorService
from app.modules.catalog.engine import CatalogEngine
from app.data_loader import DataLoader
from app.config import GEMINI_API_KEY, OPENAI_API_KEY

class AdvisorAdapter:
    """
    Modular AI Advisor Adapter for Project Udyam Digital:
    - Zero API key required for full functionality via deterministic backend rules & tools.
    - Automatic tool-based orchestration with Gemini when GEMINI_API_KEY is present.
    - Full native bilingual support for English and Hindi/Hinglish.
    - Strict consultative discovery (no assumptions of headcount, GST, or location).
    - 5-dimensional statutory & technical guardrails (GST, City Tier, Headcount, Sites, Feasibility).
    """
    def __init__(self):
        self.service = AdvisorService()
        self.catalog_engine = CatalogEngine()
        self.loader = DataLoader.get_instance()

    @property
    def has_llm_key(self) -> bool:
        return bool((GEMINI_API_KEY and len(GEMINI_API_KEY.strip()) > 5) or (OPENAI_API_KEY and len(OPENAI_API_KEY.strip()) > 5))

    def process_user_message(
        self,
        user_message: str,
        current_profile: Optional[Dict[str, Any]] = None,
        language: str = "en",
        history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Public entrypoint for conversational AI advisory.
        Delegates orchestration to AdvisorService.
        """
        return self.service.process_user_message(
            user_message=user_message,
            current_profile=current_profile,
            language=language,
            history=history,
            session_id=session_id
        )
