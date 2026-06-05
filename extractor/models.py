from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Section:
    heading: str
    content: str
    page_number: int
    tables: list[dict] = field(default_factory=list)


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    tenant_id: str
    section_heading: str
    content: str
    page_number: int
    char_count: int
    section_count: int
    doc_type: str
    tables: list[dict] = field(default_factory=list)
    ingested_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DocRecord:
    doc_id: str
    tenant_id: str
    raw_path: str
    doc_type: str
    page_count: int
    ingested_at: datetime = field(default_factory=datetime.utcnow)