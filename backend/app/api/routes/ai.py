"""AI Copilot API endpoints."""

from fastapi import APIRouter, Depends

from app.schemas.ai import AIChatRequest, AIChatResponse
from app.services.ai_service import AICopilotService, get_ai_service

router = APIRouter(prefix="/ai", tags=["AI Copilot"])


@router.post("/chat", response_model=AIChatResponse, summary="Send message to AI Copilot")
async def chat_with_copilot(
    payload: AIChatRequest,
    service: AICopilotService = Depends(get_ai_service),
) -> AIChatResponse:
    """Context-aware AI Copilot query answering using live Kubernetes, Prometheus, Incident, and Audit data."""
    return await service.answer(prompt=payload.message, extra_context=payload.context)
