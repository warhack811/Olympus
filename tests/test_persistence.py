
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel

# Mock Models
class MockUser:
    id = 1
    username = "testuser"
    active_persona = "standard"

class MockPayload(BaseModel):
    message: str = "Hello"
    conversation_id: str = "conv-123"
    stream: bool = False
    force_local: bool = False
    model: str = "groq-model"
    style_profile: dict | None = None
    images: list | None = None
    image_settings: dict | None = None

@pytest.mark.asyncio
async def test_orchestrator_persistence():
    """Verify conv_append is called in Orchestrator flow."""
    # Patch EVERYTHING that could possibly cause the Real Code to run
    with patch("app.api.routes.chat.get_settings") as mock_settings, \
         patch("app.api.routes.chat.orchestrator_gateway.try_handle", new_callable=AsyncMock) as mock_gateway, \
         patch("app.api.routes.chat.conv_append") as mock_append, \
         patch("app.memory.conversation.append_message") as mock_append_safety, \
         patch("app.api.routes.chat.limiter"), \
         patch("app.api.routes.chat.conv_create"), \
         patch("app.api.routes.chat.user_preferences"), \
         patch("app.memory.conversation._resolve_user_id", return_value=1): # SAFETY NET
        
        # Setup Orchestrator Enabled
        mock_settings.return_value.ORCH_ENABLED = True
        
        # Mock Gateway Response
        mock_res = MagicMock()
        mock_res.response_text = "Orchestrator Reply"
        mock_res.model_name = "orch-model"
        mock_gateway.return_value = mock_res
        
        # Mock Append Return (We set both just in case)
        mock_msg = MagicMock(id=999)
        mock_append.return_value = mock_msg
        mock_append_safety.return_value = mock_msg
        
        # Import chat function here
        from app.api.routes.chat import chat
        
        # Call Endpoint
        payload = MockPayload(conversation_id="conv-123")
        user = MockUser()
        
        response = await chat(payload, user)
        
        # Verify Persistence (Check mock_append first as it is the direct alias)
        # Note: Chat calls append for USER and ASSISTANT. We want to check ASSISTANT.
        
        # Filter calls for role="assistant"
        assistant_calls = [
            call for call in mock_append.call_args_list 
            if call.kwargs.get("role") == "assistant"
        ]
        
        if not assistant_calls:
             # Try safety mock
             assistant_calls = [
                call for call in mock_append_safety.call_args_list 
                if call.kwargs.get("role") == "assistant"
            ]
        
        assert assistant_calls, "No assistant message was appended!"
        
        start_call = assistant_calls[0]
        assert start_call.kwargs["text"] == "Orchestrator Reply"
        assert start_call.kwargs["conv_id"] == "conv-123"
        assert start_call.kwargs["extra_metadata"]["engine"] == "orchestrator"
        
        # Verify Response ID
        assert response.id == 999

@pytest.mark.asyncio
async def test_legacy_processor_persistence():
    """Verify persistence in processor.py using mocked internal imports."""
    with patch("app.memory.conversation.append_message") as mock_append, \
         patch("app.memory.conversation._resolve_user_id", return_value=1), \
         patch("app.chat.answerer.generate_answer", new_callable=AsyncMock) as mock_answ, \
         patch("app.chat.decider.decide_memory_storage_async", new_callable=AsyncMock) as mock_mem, \
         patch("app.services.semantic_classifier.analyze_message_semantics", new_callable=AsyncMock) as mock_sem, \
         patch("app.services.user_context.build_user_context", new_callable=AsyncMock) as mock_ctx, \
         patch("app.chat.smart_router.route_message") as mock_route, \
         patch("app.core.feature_flags.feature_enabled", return_value=True), \
         patch("app.config.get_settings"):
         
        from app.chat.processor import process_chat_message
         
        mock_answ.return_value = "Legacy Reply"
        mock_mem.return_value = {} 
        mock_sem.return_value = MagicMock(dict=lambda: {})
        mock_ctx.return_value = {}
        mock_route.return_value = MagicMock(blocked=False, target=MagicMock(value="openai"), tool_intent=MagicMock(value="none")) 
        
        await process_chat_message(
            username="testuser",
            message="Hi",
            conversation_id="conv-123"
        )
        
        bot_call = [c for c in mock_append.call_args_list if c[1]['role'] == 'bot']
        assert bot_call, "Bot message was not appended"
        text_arg = bot_call[0][1].get('text')
        assert text_arg == "Legacy Reply"
        assert bot_call[0][1]['conv_id'] == "conv-123"
