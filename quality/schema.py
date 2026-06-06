from pyspark.sql.types import IntegerType, StringType, TimestampType

REQUIRED_COLUMNS: list[tuple[str, type]] = [
    ("chunk_id", StringType),
    ("doc_id", StringType),
    ("tenant_id", StringType),
    ("section_heading", StringType),
    ("content", StringType),
    ("doc_type", StringType),
    ("section_count", IntegerType),
    ("raw_path", StringType),
    ("ingested_at", TimestampType),
]

REQUIRED_NON_NULL_COLS: list[str] = [
    "chunk_id",
    "doc_id",
    "tenant_id",
    "content",
    "doc_type",
    "raw_path",
]

CONTENT_LENGTH_MIN: int = 50
CONTENT_LENGTH_MAX: int = 50_000

ALLOWED_DOC_TYPES: frozenset[str] = frozenset(
    {
        "contract",
        "invoice",
        "policy",
        "report",
        "proposal",
        "memo",
        "other",
    }
)