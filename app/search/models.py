from dataclasses import dataclass

@dataclass
class SearchQuery:
    id: str
    query: str

@dataclass
class SearchSnippet:
    """LLM'e gönderilecek standardize edilmiş arama sonucu."""
    title: str
    url: str
    snippet: str
