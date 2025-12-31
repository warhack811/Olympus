from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any

# Mock Models
class User(BaseModel):
    id: str
    email: str
    is_active: bool
    is_superuser: bool = False
    full_name: Optional[str] = None

app = FastAPI(
    title="Mami AI Core V2 (Mock Mode)",
    description="Emergency Mock Backend for UI Stabilization",
    version="2.0.0-mock",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://olympus-dyvv.vercel.app",
        "https://mami-ai-core.onrender.com",
        "http://localhost:5173",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Conversation-ID"],
)

# --- MOCK ROUTERS ---

@app.get("/api/v1/auth/me", response_model=User)
def read_users_me():
    """Mock Auth Endpoint"""
    return {
        "id": "mock-admin-id",
        "email": "admin@mami.ai",
        "is_active": True,
        "is_superuser": True,
        "full_name": "System Admin"
    }

@app.get("/api/v1/user/personas")
def read_personas():
    """Mock Personas List"""
    return [
        {"id": "default", "name": "Mami AI", "description": "Default Assistant", "is_system": True}
    ]

@app.get("/api/v1/user/preferences")
def read_preferences(category: Optional[str] = None):
    """Mock User Preferences"""
    return {
        "theme": "dark", 
        "language": "tr",
        "notifications": True
    }

@app.get("/api/v1/user/conversations")
def read_conversations():
    """Mock Conversation History"""
    return []

@app.get("/api/v1/admin/ai-identity")
def read_ai_identity():
    """Mock AI Identity Config"""
    return {
        "display_name": "Mami AI",
        "developer_name": "Mami Team",
        "product_family": "Core V2",
        "short_intro": "I am a Mock AI Assistant.",
        "forbid_provider_mention": False
    }

# --- WEBSOCKET ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back to keep connection alive
            await websocket.send_json({
                "type": "ack", 
                "content": f"Server received: {data}",
                "timestamp": "now"
            })
    except Exception as e:
        print(f"WebSocket disconnected: {e}")

@app.get("/health")
@app.get("/")
def root():
    return {"status": "active", "mode": "mock", "version": "v2.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("core_v2.main:app", host="0.0.0.0", port=8000)
