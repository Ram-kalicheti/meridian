import hashlib
from .models import Section, Chunk


class SectionSplitter:
    def split(
        self,
        sections: list[Section],
        doc_id: str,
        tenant_id: str,
        doc_type: str,
    ) -> list[Chunk]:
        total = len(sections)
        return [
            self._make_chunk(section, idx, doc_id, tenant_id, doc_type, total)
            for idx, section in enumerate(sections)
        ]

    def _make_chunk(
        self,
        section: Section,
        idx: int,
        doc_id: str,
        tenant_id: str,
        doc_type: str,
        section_count: int,
    ) -> Chunk:
        content = self._assemble_content(section)
        return Chunk(
            chunk_id=self._chunk_id(doc_id, idx),
            doc_id=doc_id,
            tenant_id=tenant_id,
            section_heading=section.heading,
            content=content,
            page_number=section.page_number,
            char_count=len(content),
            section_count=section_count,
            doc_type=doc_type,
            tables=section.tables,
        )

    def _chunk_id(self, doc_id: str, idx: int) -> str:
        # deterministic — same doc_id + position always yields the same id
        # enables idempotent MERGE into Delta without tracking external state
        return hashlib.sha256(f"{doc_id}:{idx}".encode()).hexdigest()[:16]

    def _assemble_content(self, section: Section) -> str:
        # tables rendered as markdown so their content is included in the embedding
        parts = [section.content] if section.content else []
        for tbl in section.tables:
            md = self._table_to_markdown(tbl)
            if md:
                parts.append(md)
        return "\n\n".join(parts)

    def _table_to_markdown(self, table: dict) -> str:
        rows: dict[int, dict[int, str]] = {}
        for cell in table.get("cells", []):
            rows.setdefault(cell["row"], {})[cell["col"]] = cell["content"]

        if not rows:
            return ""

        col_count = table.get("column_count", 1)
        lines = []
        for row_idx in sorted(rows):
            row = rows[row_idx]
            cols = [row.get(c, "") for c in range(col_count)]
            lines.append("| " + " | ".join(cols) + " |")
            if row_idx == 0:
                lines.append("| " + " | ".join(["---"] * col_count) + " |")
        return "\n".join(lines)