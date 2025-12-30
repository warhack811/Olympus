from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_active_user
from app.core.models import User
from app.memory.store import add_memory, delete_memory, list_memories, update_memory

router = APIRouter()

# --- ŞEMALAR ---


class MemoryItemOut(BaseModel):
    id: str  # Index yerine ID (str)
    text: str
    created_at: Any
    importance: float
    tags: list[str] | None = None
    category: str | None = "genel"


class MemoryCreateIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    importance: float = 0.5
    tags: list[str] | None = None
    category: str | None = "genel"


class MemoryUpdateIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    importance: float | None = None
    tags: list[str] | None = None
    category: str | None = "genel"


# --- ENDPOINTS ---


@router.get("/memories", response_model=list[MemoryItemOut])
async def list_user_memories(user: User = Depends(get_current_active_user)):
    items = await list_memories(user.username)
    result = []
    for it in items:
        safe_id = it.id if it.id else "unknown"
        result.append(
            MemoryItemOut(
                id=safe_id,
                text=it.text,
                created_at=it.created_at,
                importance=it.importance,
                tags=it.tags,
                category=it.topic or "genel",
            )
        )
    return result


@router.post("/memories", response_model=MemoryItemOut)
async def create_user_memory(body: MemoryCreateIn, user: User = Depends(get_current_active_user)):
    item = await add_memory(
        username=user.username,
        text=body.text,
        importance=body.importance,
        tags=body.tags,
    )
    safe_id = item.id if item.id else "new"
    return MemoryItemOut(
        id=safe_id,
        text=item.text,
        created_at=item.created_at,
        importance=item.importance,
        tags=item.tags,
        category=item.topic or "genel",
    )


@router.delete("/memories/all-delete")
async def delete_all_user_memories(user: User = Depends(get_current_active_user)):
    items = await list_memories(user.username)
    deleted = 0
    for item in items:
        mem_id = getattr(item, "id", None)
        if not mem_id:
            continue
        ok = await delete_memory(user.username, mem_id)
        if ok:
            deleted += 1
    return {"ok": True, "deleted": deleted}


@router.put("/memories/{memory_id}", response_model=MemoryItemOut)
async def update_user_memory(body: MemoryUpdateIn, memory_id: str, user: User = Depends(get_current_active_user)):
    item = await update_memory(
        username=user.username,
        memory_id=memory_id,
        text=body.text,
        importance=body.importance,
    )
    if not item:
        raise HTTPException(status_code=404, detail="Memory not found")
    safe_id = item.id if item.id else memory_id
    return MemoryItemOut(
        id=safe_id,
        text=item.text,
        created_at=item.created_at,
        importance=item.importance,
        tags=item.tags,
        category=item.topic or "genel",
    )


@router.delete("/memories/{memory_id}")
async def delete_user_memory_endpoint(memory_id: str, user: User = Depends(get_current_active_user)):
    ok = await delete_memory(user.username, memory_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Silinemedi.")
    return {"ok": True}
