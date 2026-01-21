"""
Beautiful Response Models - Blocks
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class BaseBlock(BaseModel):
    """Tüm blok tipleri için temel sınıf"""

    block_type: str = Field(..., description="Blok tipi")


class TextBlock(BaseBlock):
    """Basit metin bloğu"""

    block_type: Literal["text"] = "text"
    content: str
    format: Literal["markdown", "plain"] = "markdown"


class CodeBlock(BaseBlock):
    """Kod bloğu"""

    block_type: Literal["code"] = "code"
    content: str
    language: str = "plaintext"
    filename: str | None = None


class CitationBlock(BaseBlock):
    """Alıntı/Kaynak bloğu"""

    block_type: Literal["citation"] = "citation"
    source_id: str
    text: str
    url: str | None = None


class TableBlock(BaseBlock):
    """Tablo bloğu"""

    block_type: Literal["table"] = "table"
    headers: list[str]
    rows: list[list[str]]
    alignments: list[str] = Field(default_factory=list)  # "left", "center", "right"


class MermaidBlock(BaseBlock):
    """Mermaid diyagram bloğu"""

    block_type: Literal["mermaid"] = "mermaid"
    content: str
    caption: str | None = None


class MathBlock(BaseBlock):
    """LaTeX matematik bloğu"""

    block_type: Literal["math"] = "math"
    content: str
    is_inline: bool = False


class TaskItem(BaseModel):
    """Tek bir görev maddesi"""

    text: str
    checked: bool


class TaskBlock(BaseBlock):
    """Görev listesi bloğu"""

    block_type: Literal["task_list"] = "task_list"
    items: list[TaskItem]


class StructuredResponse(BaseModel):
    """
    Yapılandırılmış Tam Yanıt Modeli
    """

    version: str = "1.0"
    blocks: list[TextBlock | CodeBlock | CitationBlock | TableBlock | MermaidBlock | MathBlock | TaskBlock] = Field(
        default_factory=list
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
