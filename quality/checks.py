from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from quality.schema import (
    ALLOWED_DOC_TYPES,
    CONTENT_LENGTH_MAX,
    CONTENT_LENGTH_MIN,
    REQUIRED_COLUMNS,
    REQUIRED_NON_NULL_COLS,
)


def check_schema_validation(df: DataFrame) -> tuple[bool, str]:
    actual = {f.name: type(f.dataType) for f in df.schema.fields}
    for col_name, expected_type in REQUIRED_COLUMNS:
        if col_name not in actual:
            return False, f"missing required column: {col_name}"
        if actual[col_name] is not expected_type:
            return (
                False,
                f"column '{col_name}' has type {actual[col_name].__name__} — "
                f"expected {expected_type.__name__}",
            )
    return True, ""


def check_null_completeness(df: DataFrame) -> tuple[bool, str]:
    for col_name in REQUIRED_NON_NULL_COLS:
        if col_name not in df.columns:
            return False, f"column '{col_name}' missing — cannot check nulls"
        null_count = df.filter(F.col(col_name).isNull()).count()
        if null_count > 0:
            return False, f"{null_count} null(s) in required column: {col_name}"
    return True, ""


def check_content_length(df: DataFrame) -> tuple[bool, str]:
    violations = df.filter(
        (F.length(F.col("content")) < CONTENT_LENGTH_MIN)
        | (F.length(F.col("content")) > CONTENT_LENGTH_MAX)
    ).count()
    if violations:
        return (
            False,
            f"{violations} chunk(s) outside content length bounds "
            f"[{CONTENT_LENGTH_MIN}, {CONTENT_LENGTH_MAX}]",
        )
    return True, ""


def check_section_count_positive(df: DataFrame) -> tuple[bool, str]:
    violations = df.filter(F.col("section_count") <= 0).count()
    if violations:
        return False, f"{violations} row(s) with section_count <= 0"
    return True, ""


def check_chunk_id_uniqueness(df: DataFrame) -> tuple[bool, str]:
    total = df.count()
    distinct = df.select("chunk_id").distinct().count()
    if distinct < total:
        return False, f"{total - distinct} duplicate chunk_id(s) in batch"
    return True, ""


def check_doc_type_enum(df: DataFrame) -> tuple[bool, str]:
    invalid_rows = (
        df.filter(~F.col("doc_type").isin(list(ALLOWED_DOC_TYPES)))
        .select("doc_type")
        .distinct()
        .collect()
    )
    if invalid_rows:
        values = [r["doc_type"] for r in invalid_rows]
        return False, f"invalid doc_type value(s): {values}"
    return True, ""