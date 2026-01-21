from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict

class StyleProfile(BaseModel):
    """
    Sub-schema for AI response styling.
    """
    tone: Optional[str] = Field("casual", description="Response tone (formal, casual, playful, etc.)")
    length: Optional[str] = Field("normal", description="Response length (short, normal, detailed)")
    emoji_level: Optional[str] = Field("medium", description="Emoji usage level (none, low, medium, high)")
    use_markdown: bool = Field(True, description="Whether to use markdown formatting.")
    use_code_blocks: bool = Field(True, description="Whether to use code blocks.")

class ChatRequest(BaseModel):
    """
    Standard Unified Request Schema for Sovereign Core.
    """
    message: str = Field(..., description="User's input message.")
    session_id: Optional[str] = Field(None, description="Unique conversation session identifier (session_id).")
    conversation_id: Optional[str] = Field(None, description="Alias for session_id (conversation_id).")
    model: Optional[str] = Field(None, description="Requested model ID.")
    persona: Optional[str] = Field("standard", description="Applied AI personality.")
    style_profile: Optional[StyleProfile | Dict[str, str]] = Field(None, description="Detailed styling preferences.")
    stream: bool = Field(True, description="Whether to use SSE streaming.")
    force_local: bool = Field(False, description="Force local execution.")
    images: Optional[List[str]] = Field(None, description="List of image paths/filenames.")
    image_settings: Optional[Dict[str, Any]] = Field(None, description="Custom image generation settings.")
    
    class Config:
        extra = "ignore" 

class ChatResponse(BaseModel):
    """
    Standard Sync Response Schema.
    """
    response: str
    session_id: str
    intent: str
    metadata: Optional[dict] = None
