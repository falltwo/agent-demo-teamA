from fastapi import APIRouter

from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.chat_adapter import run_chat_turn

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def post_chat(body: ChatRequest) -> ChatResponse:
    """送出一則使用者訊息並取得回答（與 Streamlit 主流程相同之 `answer_with_rag_and_log`）。"""
    return run_chat_turn(body)
