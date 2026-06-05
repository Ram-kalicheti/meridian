from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from .models import Section


def analyze_document(
    client: DocumentIntelligenceClient,
    document_bytes: bytes,
) -> list[Section]:
    poller = client.begin_analyze_document(
        "prebuilt-layout",
        analyze_request=AnalyzeDocumentRequest(bytes_source=document_bytes),
    )
    result = poller.result()
    return _extract_sections(result)


def _extract_sections(result) -> list[Section]:
    pending_tables: dict[int, list[dict]] = {}
    for table in result.tables or []:
        first_page = (
            table.bounding_regions[0].page_number
            if table.bounding_regions
            else 1
        )
        pending_tables.setdefault(first_page, []).append(_serialize_table(table))

    sections: list[Section] = []
    current_heading = ""
    current_parts: list[str] = []
    current_tables: list[dict] = []
    current_page = 1

    def _flush() -> None:
        if current_parts or current_tables:
            sections.append(
                Section(
                    heading=current_heading,
                    content=" ".join(current_parts).strip(),
                    page_number=current_page,
                    tables=list(current_tables),
                )
            )

    for para in result.paragraphs or []:
        page = (
            para.bounding_regions[0].page_number
            if para.bounding_regions
            else current_page
        )
        for tbl in pending_tables.pop(page, []):
            current_tables.append(tbl)

        if para.role == "sectionHeading":
            _flush()
            current_heading = para.content or ""
            current_parts = []
            current_tables = []
            current_page = page
        else:
            current_parts.append(para.content or "")
            current_page = page

    for tbls in pending_tables.values():
        current_tables.extend(tbls)
    _flush()

    return sections


def _serialize_table(table) -> dict:
    cells = []
    for cell in table.cells or []:
        cells.append(
            {
                "row": cell.row_index,
                "col": cell.column_index,
                "content": cell.content,
                "kind": cell.kind or "content",
            }
        )
    return {
        "row_count": table.row_count,
        "column_count": table.column_count,
        "cells": cells,
    }